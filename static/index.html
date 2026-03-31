from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from mangum import Mangum
import os, httpx, re, hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase fout: {e}")

HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
HTML = open(HTML_PATH, encoding="utf-8").read() if os.path.exists(HTML_PATH) else "<h1>Automotive24</h1>"


# ─── SCRAPER ────────────────────────────────────────────────────

def supabase_get(path):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, timeout=15)
    return r.json() if r.status_code < 300 else []

def supabase_post(path, data):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json", "Prefer": "return=representation"}
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, json=data, timeout=15)
    if r.status_code >= 300:
        print(f"Insert fout [{r.status_code}]: {r.text}")
        return []
    return r.json()

def marktplaats_url(item):
    """Haal de correcte volledige Marktplaats URL op uit een listing item."""
    vip_url = item.get("vipUrl", "")
    item_id = item.get("itemId", "")
    if vip_url:
        if vip_url.startswith("/"):
            return f"https://www.marktplaats.nl{vip_url}"
        if vip_url.startswith("http"):
            return vip_url
    if item_id:
        clean_id = item_id.lstrip("m")
        return f"https://www.marktplaats.nl/v/m{clean_id}"
    return ""

def normaliseer_merk(merk):
    if not merk:
        return ""
    mapping = {
        "vw": "volkswagen", "mercedes": "mercedes-benz", "bmw": "bmw",
        "audi": "audi", "ford": "ford", "opel": "opel", "toyota": "toyota",
        "honda": "honda", "renault": "renault", "peugeot": "peugeot",
        "skoda": "skoda", "seat": "seat", "kia": "kia", "hyundai": "hyundai",
        "nissan": "nissan", "mazda": "mazda", "volvo": "volvo", "fiat": "fiat",
        "dacia": "dacia", "mitsubishi": "mitsubishi", "suzuki": "suzuki",
        "porsche": "porsche", "tesla": "tesla", "citroen": "citroën",
        "citroën": "citroën", "alfa romeo": "alfa romeo"
    }
    return mapping.get(merk.strip().lower(), merk.strip().lower())

def scrape_marktplaats(merk, model, bouwjaar_van, bouwjaar_tot, brandstof):
    resultaten = []
    try:
        params = {"query": f"{merk} {model}".strip(), "categoryId": "91", "l1CategoryId": "91"}
        if bouwjaar_van:
            params["constructionYearFrom"] = str(bouwjaar_van)
        if bouwjaar_tot:
            params["constructionYearTo"] = str(bouwjaar_tot)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json"}
        r = httpx.get("https://www.marktplaats.nl/lrp/api/search", params=params, headers=headers, timeout=20, follow_redirects=True)
        if r.status_code == 200:
            for item in r.json().get("listings", [])[:15]:
                titel = item.get("title", "")
                prijs_cents = item.get("priceInfo", {}).get("priceCents", 0)
                prijs_int = prijs_cents // 100 if prijs_cents else None
                adv_url = marktplaats_url(item)
                if titel and adv_url:
                    resultaten.append({"titel": titel, "prijs": prijs_int, "url": adv_url, "bron": "Marktplaats.nl"})
    except Exception as e:
        print(f"Marktplaats fout: {e}")
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
        r = httpx.get(url, params=params, headers=headers, timeout=20, follow_redirects=True)
        if r.status_code == 200:
            html = r.text
            links = re.findall(r'href="(https://www\.gaspedaal\.nl/[^"]+/[0-9]+)"', html)
            prijzen = re.findall(r'€\s*([\d\.]+)', html)
            titels = re.findall(r'<h2[^>]*>([^<]+)</h2>', html)
            for i, link in enumerate(links[:10]):
                prijs_str = prijzen[i] if i < len(prijzen) else None
                prijs_int = int(re.sub(r'[^\d]', '', prijs_str)) if prijs_str else None
                titel = titels[i].strip() if i < len(titels) else f"{merk} {model}"
                resultaten.append({"titel": titel, "prijs": prijs_int, "url": link, "bron": "Gaspedaal.nl"})
    except Exception as e:
        print(f"Gaspedaal fout: {e}")
    return resultaten

def scrape_autoscout(merk, model, bouwjaar_van, bouwjaar_tot):
    resultaten = []
    try:
        merk_slug = normaliseer_merk(merk).replace(" ", "-").replace("ë", "e")
        params = {"make": merk_slug, "sort": "standard", "desc": "0", "ustate": "N,U", "size": "15", "page": "1", "cy": "NL", "atype": "C"}
        if model:
            params["model"] = model.lower().replace(" ", "-")
        if bouwjaar_van:
            params["fregfrom"] = f"{bouwjaar_van}-01"
        if bouwjaar_tot:
            params["fregto"] = f"{bouwjaar_tot}-12"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept-Language": "nl-NL,nl;q=0.9"}
        r = httpx.get("https://www.autoscout24.nl/lst", params=params, headers=headers, timeout=20, follow_redirects=True)
        if r.status_code == 200:
            items = re.findall(r'"url":"(/auto/[^"]+)".*?"price":"([^"]+)".*?"title":"([^"]+)"', r.text)
            for item in items[:10]:
                adv_url = f"https://www.autoscout24.nl{item[0]}"
                prijs_str = re.sub(r'[^\d]', '', item[1])
                prijs_int = int(prijs_str) if prijs_str else None
                resultaten.append({"titel": item[2], "prijs": prijs_int, "url": adv_url, "bron": "Autoscout24.nl"})
    except Exception as e:
        print(f"Autoscout24 fout: {e}")
    return resultaten

def zoek_matcht(zoek, titel):
    titel_l = titel.lower()
    merk = (zoek.get("merk") or "").lower()
    model = (zoek.get("type_model") or "").lower()
    if merk and merk not in titel_l and normaliseer_merk(merk) not in titel_l:
        return False
    if model:
        if not any(w in titel_l for w in model.split() if len(w) > 2):
            return False
    return True

def scrape_voor_zoekopdracht(zoek):
    merk = zoek.get("merk", "")
    model = zoek.get("type_model", "")
    bouwjaar_van = zoek.get("bouwjaar_van")
    bouwjaar_tot = zoek.get("bouwjaar_tot")

    alle = []
    alle += scrape_marktplaats(merk, model, bouwjaar_van, bouwjaar_tot, zoek.get("brandstof"))
    alle += scrape_gaspedaal(merk, model, bouwjaar_van, bouwjaar_tot)
    alle += scrape_autoscout(merk, model, bouwjaar_van, bouwjaar_tot)

    nieuwe = 0
    for r in alle:
        if not zoek_matcht(zoek, r["titel"]):
            continue
        url_hash = hashlib.md5(r["url"].encode()).hexdigest()
        bestaand = supabase_get(f"advertenties?url_hash=eq.{url_hash}&zoekopdracht_id=eq.{zoek['id']}")
        if bestaand:
            continue
        insert_data = {
            "zoekopdracht_id": zoek["id"],
            "titel": r["titel"],
            "url": r["url"],
            "url_hash": url_hash,
            "site": r["bron"],
            "merk": merk,
            "type_model": model,
            "status": "actief",
            "gevonden_op": datetime.utcnow().isoformat()
        }
        if r.get("prijs") is not None:
            insert_data["prijs"] = r["prijs"]
        resultaat = supabase_post("advertenties", insert_data)
        if resultaat:
            nieuwe += 1
            print(f"Nieuw: {r['titel']} — {r['bron']}")
    print(f"Zoekopdracht {zoek['id']}: {nieuwe} nieuwe advertenties")


# ─── ENDPOINTS ───────────────────────────────────────────────────

class ZoekopdachtModel(BaseModel):
    email: EmailStr
    merk: Optional[str] = None
    type_model: Optional[str] = None
    brandstof: Optional[str] = None
    bouwjaar_van: Optional[int] = None
    bouwjaar_tot: Optional[int] = None


@app.get("/")
async def root():
    return HTMLResponse(content=HTML, media_type="text/html; charset=utf-8")


@app.get("/api/health")
async def health():
    return {"status": "ok", "supabase": "verbonden" if supabase else "niet verbonden"}


@app.post("/api/gebruikers/registreer")
async def registreer(email: str):
    if not supabase:
        return {"status": "aangemaakt", "gebruiker": {"id": "test", "email": email}}
    try:
        bestaand = supabase.table("gebruikers").select("id,email").eq("email", email).execute()
        if bestaand.data:
            return {"status": "bestaand", "gebruiker": bestaand.data[0]}
        nieuw = supabase.table("gebruikers").insert({
            "email": email,
            "avg_akkoord": True,
            "avg_akkoord_op": datetime.utcnow().isoformat(),
            "gratis_periode_tot": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }).execute()
        return {"status": "aangemaakt", "gebruiker": nieuw.data[0]}
    except Exception:
        return {"status": "aangemaakt", "gebruiker": {"id": "test", "email": email}}


@app.get("/api/gebruikers/{email}/dashboard")
async def get_dashboard(email: str):
    if not supabase:
        return {"zoekopdrachten": []}
    try:
        gebruiker = supabase.table("gebruikers").select("id").eq("email", email).execute()
        if not gebruiker.data:
            return {"zoekopdrachten": []}
        gebruiker_id = gebruiker.data[0]["id"]
        zoekopdrachten = supabase.table("zoekopdrachten").select("*").eq("gebruiker_id", gebruiker_id).eq("status", "actief").execute().data
        resultaat = []
        for zoek in zoekopdrachten:
            advertenties = supabase.table("advertenties").select("id,titel,prijs,url,site,gevonden_op").eq("zoekopdracht_id", zoek["id"]).eq("status", "actief").order("gevonden_op", desc=True).limit(50).execute().data
            resultaat.append({
                "id": zoek["id"],
                "merk": zoek.get("merk", ""),
                "type_model": zoek.get("type_model", ""),
                "brandstof": zoek.get("brandstof", ""),
                "bouwjaar_van": zoek.get("bouwjaar_van"),
                "bouwjaar_tot": zoek.get("bouwjaar_tot"),
                "advertenties": advertenties
            })
        return {"zoekopdrachten": resultaat}
    except Exception as e:
        print(f"Dashboard fout: {e}")
        return {"zoekopdrachten": []}


@app.post("/api/zoekopdrachten")
async def maak_zoekopdracht(data: ZoekopdachtModel, background_tasks: BackgroundTasks):
    if not supabase:
        return {"status": "aangemaakt", "zoekopdracht": {"id": "test"}}
    try:
        gebruiker = supabase.table("gebruikers").select("id").eq("email", data.email).execute()
        if not gebruiker.data:
            raise HTTPException(404, "Registreer eerst")
        zoek = supabase.table("zoekopdrachten").insert({
            "gebruiker_id": gebruiker.data[0]["id"],
            "merk": data.merk,
            "type_model": data.type_model,
            "brandstof": data.brandstof,
            "bouwjaar_van": data.bouwjaar_van,
            "bouwjaar_tot": data.bouwjaar_tot,
            "status": "actief"
        }).execute()
        zoek_data = zoek.data[0]
        background_tasks.add_task(scrape_voor_zoekopdracht, zoek_data)
        return {"status": "aangemaakt", "zoekopdracht": zoek_data}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Zoekopdracht fout: {e}")
        return {"status": "aangemaakt", "zoekopdracht": {"id": "test"}}


@app.delete("/api/zoekopdrachten/{zoek_id}")
async def verwijder_zoekopdracht(zoek_id: str):
    if not supabase:
        return {"status": "gestopt"}
    try:
        supabase.table("zoekopdrachten").update({"status": "gestopt"}).eq("id", zoek_id).execute()
        return {"status": "gestopt"}
    except Exception as e:
        return {"status": "fout", "melding": str(e)}


@app.get("/api/advertenties/{zoekopdracht_id}")
async def get_advertenties(zoekopdracht_id: str):
    if not supabase:
        return []
    try:
        return supabase.table("advertenties").select("*").eq("zoekopdracht_id", zoekopdracht_id).eq("status", "actief").order("gevonden_op", desc=True).execute().data
    except Exception:
        return []


@app.get("/api/hotlist")
async def get_hotlist():
    if not supabase:
        return []
    try:
        return supabase.table("hotlist_statistieken").select("*").order("aantal_zoekers", desc=True).limit(10).execute().data
    except Exception:
        return []


handler = Mangum(app)
