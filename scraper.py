import os, httpx, re, hashlib
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
APP_URL = os.getenv("APP_URL", "https://automotive24.nl")

def supabase_request(method, path, data=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    try:
        with httpx.Client(timeout=30) as client:
            if method == "GET":
                r = client.get(url, headers=headers)
            elif method == "POST":
                r = client.post(url, headers=headers, json=data)
            elif method == "PATCH":
                r = client.patch(url, headers=headers, json=data)
            if r.status_code >= 300:
                print(f"Supabase fout [{r.status_code}] op {path}: {r.text}")
                return []
            return r.json()
    except Exception as e:
        print(f"Supabase request fout: {e}")
        return []

def prijs_naar_int(prijs_str):
    if not prijs_str:
        return None
    try:
        cleaned = re.sub(r'[^\d]', '', str(prijs_str))
        return int(cleaned) if cleaned else None
    except:
        return None

def marktplaats_url(item):
    """Haal de correcte volledige Marktplaats URL op uit een listing item."""
    vip_url = item.get("vipUrl", "")
    item_id = item.get("itemId", "")
    if vip_url:
        # Relatieve URL: /v/auto-s/... → maak absoluut
        if vip_url.startswith("/"):
            return f"https://www.marktplaats.nl{vip_url}"
        # Al absoluut
        if vip_url.startswith("http"):
            return vip_url
    # Fallback: gebruik itemId
    if item_id:
        return f"https://www.marktplaats.nl/v/m{item_id}"
    return ""

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
                for item in listings[:15]:
                    titel = item.get("title", "")
                    prijs_data = item.get("priceInfo", {})
                    prijs_cents = prijs_data.get("priceCents", 0)
                    prijs_int = prijs_cents // 100 if prijs_cents else None
                    prijs_tekst = f"€{prijs_int:,}".replace(",", ".") if prijs_int else "Vraagprijs onbekend"
                    adv_url = marktplaats_url(item)
                    if titel and adv_url:
                        resultaten.append({
                            "titel": titel,
                            "prijs": prijs_int,
                            "prijs_tekst": prijs_tekst,
                            "url": adv_url,
                            "bron": "Marktplaats.nl"
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
                    prijs_tekst = item[1]
                    prijs_int = prijs_naar_int(prijs_tekst)
                    titel = item[2]
                    resultaten.append({
                        "titel": titel,
                        "prijs": prijs_int,
                        "prijs_tekst": prijs_tekst,
                        "url": adv_url,
                        "bron": "Autoscout24.nl"
                    })
    except Exception as e:
        print(f"Autoscout24 fout: {e}")
    return resultaten

def scrape_gaspedaal(merk, model, bouwjaar_van, bouwjaar_tot):
    resultaten = []
    try:
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
                    prijs_tekst = f"€{prijzen[i]}" if i < len(prijzen) else "Prijs onbekend"
                    prijs_int = prijs_naar_int(prijs_tekst)
                    titel = titels[i].strip() if i < len(titels) else f"{merk} {model}"
                    resultaten.append({
                        "titel": titel,
                        "prijs": prijs_int,
                        "prijs_tekst": prijs_tekst,
                        "url": link,
                        "bron": "Gaspedaal.nl"
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

        url_hash = hashlib.md5(r["url"].encode()).hexdigest()

        bestaand = supabase_request("GET", f"advertenties?url_hash=eq.{url_hash}&zoekopdracht_id=eq.{zoek['id']}")
        if bestaand:
            continue

        insert_data = {
            "zoekopdracht_id": zoek["id"],
            "titel": r["titel"],
            "prijs": r.get("prijs"),
            "url": r["url"],
            "url_hash": url_hash,
            "site": r["bron"],
            "merk": zoek.get("merk"),
            "type_model": zoek.get("type_model"),
            "status": "actief",
            "gevonden_op": datetime.utcnow().isoformat()
        }
        insert_data = {k: v for k, v in insert_data.items() if v is not None}

        resultaat = supabase_request("POST", "advertenties", insert_data)
        if resultaat:
            nieuwe_matches += 1
            prijs_display = r.get("prijs_tekst", str(r.get("prijs", "onbekend")))
            print(f"Nieuwe match: {r['titel']} — {prijs_display} op {r['bron']}")
            if gebruiker_email:
                stuur_email(
                    gebruiker_email,
                    f"Match gevonden: {zoek.get('merk', '')} {zoek.get('type_model', '')}",
                    match_html(zoek.get('merk', ''), zoek.get('type_model', ''), prijs_display, r["url"], r["bron"])
                )
        else:
            print(f"Insert mislukt voor: {r['titel']}")

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
