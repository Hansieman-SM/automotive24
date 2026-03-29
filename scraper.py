import os, httpx, asyncio, re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
APP_URL = os.getenv("APP_URL", "https://automotive24-production.up.railway.app")

def supabase_request(method, path, data=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    with httpx.Client(timeout=30) as client:
        if method == "GET":
            r = client.get(url, headers=headers)
        elif method == "POST":
            r = client.post(url, headers=headers, json=data)
        elif method == "PATCH":
            r = client.patch(url, headers=headers, json=data)
        return r.json() if r.status_code < 300 else []

def stuur_email(naar, onderwerp, html):
    if not RESEND_API_KEY:
        return
    try:
        with httpx.Client(timeout=15) as client:
            client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={"from": "Automotive24 <onboarding@resend.dev>", "to": [naar], "subject": onderwerp, "html": html}
            )
    except Exception as e:
        print(f"E-mail fout: {e}")

def match_html(merk, model, prijs, url, bron):
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
      <div style="background:#0D47A1;padding:24px;border-radius:12px 12px 0 0;text-align:center">
        <h1 style="color:white;margin:0">🚗 Automotive24</h1>
        <p style="color:rgba(255,255,255,.8);margin:8px 0 0">De bot heeft iets gevonden!</p>
      </div>
      <div style="background:white;padding:24px;border:1px solid #E0E0E0;border-top:none">
        <h2 style="color:#2E7D32">Match gevonden!</h2>
        <div style="background:#F5F5F5;border-radius:8px;padding:16px;margin:16px 0">
          <div style="font-size:18px;font-weight:700;color:#0D47A1">{merk} {model}</div>
          <div style="font-size:22px;font-weight:700;color:#1565C0;margin:8px 0">{prijs}</div>
          <div style="font-size:13px;color:#888">Gevonden op: {bron}</div>
        </div>
        <div style="text-align:center;margin:24px 0">
          <a href="{url}" style="background:#2E7D32;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600">Bekijk de advertentie</a>
        </div>
      </div>
      <div style="background:#F5F5F5;padding:12px;border-radius:0 0 12px 12px;text-align:center">
        <p style="color:#aaa;font-size:11px;margin:0">Automotive24 · TDEG BV · Groningen</p>
      </div>
    </div>
    """

def normaliseer_merk(merk):
    if not merk:
        return ""
    merk = merk.strip().lower()
    mapping = {
        "vw": "volkswagen", "mercedes": "mercedes-benz", "merc": "mercedes-benz",
        "bmw": "bmw", "audi": "audi", "ford": "ford", "opel": "opel",
        "toyota": "toyota", "honda": "honda", "renault": "renault",
        "peugeot": "peugeot", "citroen": "citroën", "citroën": "citroën",
        "skoda": "skoda", "seat": "seat", "kia": "kia", "hyundai": "hyundai",
        "nissan": "nissan", "mazda": "mazda", "volvo": "volvo", "fiat": "fiat",
        "dacia": "dacia", "mitsubishi": "mitsubishi", "suzuki": "suzuki",
        "porsche": "porsche", "land rover": "land rover", "jaguar": "jaguar",
        "alfa romeo": "alfa romeo", "tesla": "tesla"
    }
    return mapping.get(merk, merk)

def scrape_marktplaats(merk, model, bouwjaar_van, bouwjaar_tot, brandstof):
    resultaten = []
    try:
        params = {"query": f"{merk} {model}".strip(), "categoryId": "91", "l1CategoryId": "91"}
        if bouwjaar_van:
            params["constructionYearFrom"] = str(bouwjaar_van)
        if bouwjaar_tot:
            params["constructionYearTo"] = str(bouwjaar_tot)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        url = "https://www.marktplaats.nl/lrp/api/search"
        with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as client:
            r = client.get(url, params=params)
            if r.status_code == 200:
                data = r.json()
                listings = data.get("listings", [])
                for item in listings[:10]:
                    titel = item.get("title", "")
                    prijs_data = item.get("priceInfo", {})
                    prijs = prijs_data.get("priceCents", 0)
                    prijs_str = f"€{prijs//100:,}".replace(",", ".") if prijs else "Vraagprijs onbekend"
                    item_id = item.get("itemId", "")
                    adv_url = f"https://www.marktplaats.nl/a/{item_id}" if item_id else ""
                    if titel and adv_url:
                        resultaten.append({
                            "titel": titel,
                            "prijs": prijs_str,
                            "url": adv_url,
                            "bron": "Marktplaats.nl",
                            "extern_id": f"mp_{item_id}"
                        })
    except Exception as e:
        print(f"Marktplaats fout: {e}")
    return resultaten

def scrape_autoscout(merk, model, bouwjaar_van, bouwjaar_tot, brandstof):
    resultaten = []
    try:
        merk_slug = normaliseer_merk(merk).replace(" ", "-").replace("ë", "e")
        params = {"make": merk_slug, "sort": "standard", "desc": "0", "ustate": "N,U", "size": "10", "page": "1", "cy": "NL", "atype": "C"}
        if model:
            params["model"] = model.lower().replace(" ", "-")
        if bouwjaar_van:
            params["fregfrom"] = f"{bouwjaar_van}-01"
        if bouwjaar_tot:
            params["fregto"] = f"{bouwjaar_tot}-12"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "nl-NL,nl;q=0.9"
        }
        url = "https://www.autoscout24.nl/lst"
        with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as client:
            r = client.get(url, params=params)
            if r.status_code == 200:
                html = r.text
                items = re.findall(r'"url":"(/auto/[^"]+)".*?"price":"([^"]+)".*?"title":"([^"]+)"', html)
                for item in items[:10]:
                    adv_url = f"https://www.autoscout24.nl{item[0]}"
                    prijs = item[1]
                    titel = item[2]
                    extern_id = f"as24_{item[0].replace('/', '_')}"
                    resultaten.append({
                        "titel": titel,
                        "prijs": prijs,
                        "url": adv_url,
                        "bron": "Autoscout24.nl",
                        "extern_id": extern_id
                    })
    except Exception as e:
        print(f"Autoscout24 fout: {e}")
    return resultaten

def scrape_gaspedaal(merk, model, bouwjaar_van, bouwjaar_tot):
    resultaten = []
    try:
        query = f"{merk} {model}".strip()
        url = f"https://www.gaspedaal.nl/{normaliseer_merk(merk).replace(' ', '-')}"
        if model:
            url += f"/{model.lower().replace(' ', '-')}"
        params = {}
        if bouwjaar_van:
            params["bouwjaar_van"] = str(bouwjaar_van)
        if bouwjaar_tot:
            params["bouwjaar_tot"] = str(bouwjaar_tot)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as client:
            r = client.get(url, params=params)
            if r.status_code == 200:
                html = r.text
                links = re.findall(r'href="(https://www\.gaspedaal\.nl/[^"]+/[0-9]+)"', html)
                prijzen = re.findall(r'€\s*([\d\.]+)', html)
                titels = re.findall(r'<h2[^>]*>([^<]+)</h2>', html)
                for i, link in enumerate(links[:8]):
                    extern_id = f"gp_{link.split('/')[-1]}"
                    prijs = f"€{prijzen[i]}" if i < len(prijzen) else "Prijs onbekend"
                    titel = titels[i].strip() if i < len(titels) else query
                    resultaten.append({
                        "titel": titel,
                        "prijs": prijs,
                        "url": link,
                        "bron": "Gaspedaal.nl",
                        "extern_id": extern_id
                    })
    except Exception as e:
        print(f"Gaspedaal fout: {e}")
    return resultaten

def zoek_matcht(zoek, resultaat_titel):
    titel_lower = resultaat_titel.lower()
    merk = (zoek.get("merk") or "").lower()
    model = (zoek.get("type_model") or "").lower()
    if merk and merk not in titel_lower and normaliseer_merk(merk) not in titel_lower:
        return False
    if model:
        model_woorden = model.split()
        if not any(w in titel_lower for w in model_woorden if len(w) > 2):
            return False
    return True

def verwerk_resultaten(zoek, resultaten, gebruiker_email):
    nieuwe_matches = 0
    for r in resultaten:
        if not zoek_matcht(zoek, r["titel"]):
            continue
        bestaand = supabase_request("GET", f"advertenties?extern_id=eq.{r['extern_id']}&zoekopdracht_id=eq.{zoek['id']}")
        if bestaand:
            continue
        supabase_request("POST", "advertenties", {
            "zoekopdracht_id": zoek["id"],
            "titel": r["titel"],
            "prijs": r["prijs"],
            "url": r["url"],
            "bron": r["bron"],
            "extern_id": r["extern_id"],
            "status": "actief",
            "gevonden_op": datetime.utcnow().isoformat()
        })
        nieuwe_matches += 1
        print(f"Nieuwe match: {r['titel']} — {r['prijs']} op {r['bron']}")
        if gebruiker_email:
            merk = zoek.get("merk", "")
            model = zoek.get("type_model", "")
            stuur_email(
                gebruiker_email,
                f"Match gevonden: {merk} {model}",
                match_html(merk, model, r["prijs"], r["url"], r["bron"])
            )
    return nieuwe_matches

def run_scraper():
    print(f"\n=== Automotive24 Scraper === {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    if not SUPABASE_KEY:
        print("Geen Supabase key — stop")
        return

    zoekopdrachten = supabase_request("GET", "zoekopdrachten?status=eq.actief&select=*,gebruikers(email)")
    if not zoekopdrachten:
        print("Geen actieve zoekopdrachten")
        return

    print(f"{len(zoekopdrachten)} actieve zoekopdrachten gevonden")
    totaal_nieuw = 0

    for zoek in zoekopdrachten:
        merk = zoek.get("merk", "")
        model = zoek.get("type_model", "")
        bouwjaar_van = zoek.get("bouwjaar_van")
        bouwjaar_tot = zoek.get("bouwjaar_tot")
        brandstof = zoek.get("brandstof")
        gebruiker_email = None
        if zoek.get("gebruikers"):
            gebruiker_email = zoek["gebruikers"].get("email")

        print(f"\nZoeken: {merk} {model} ({bouwjaar_van}–{bouwjaar_tot})")

        alle_resultaten = []
        alle_resultaten += scrape_marktplaats(merk, model, bouwjaar_van, bouwjaar_tot, brandstof)
        alle_resultaten += scrape_autoscout(merk, model, bouwjaar_van, bouwjaar_tot, brandstof)
        alle_resultaten += scrape_gaspedaal(merk, model, bouwjaar_van, bouwjaar_tot)

        print(f"Gevonden: {len(alle_resultaten)} advertenties op 3 sites")
        nieuw = verwerk_resultaten(zoek, alle_resultaten, gebruiker_email)
        totaal_nieuw += nieuw
        print(f"Nieuwe matches opgeslagen: {nieuw}")

    print(f"\nTotaal nieuwe matches: {totaal_nieuw}")
    print("=== Scraper klaar ===")

if __name__ == "__main__":
    run_scraper()
