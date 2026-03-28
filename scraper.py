import httpx, asyncio, hashlib, os, re
from supabase import create_client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# ─────────────────────────────────────────
# NORMALISATIE — voorkomt 530i vs 530d fouten
# ─────────────────────────────────────────

def normaliseer_model(tekst: str) -> str:
    if not tekst:
        return ""
    tekst = tekst.lower().strip()
    tekst = re.sub(r'\s+', ' ', tekst)
    tekst = tekst.replace(" i ", "i ").replace("-i ", "i ")
    return tekst

def match_zoek(adv: dict, zoek: dict) -> bool:
    if zoek.get("merk"):
        if zoek["merk"].lower() not in adv.get("titel","").lower():
            return False
    if zoek.get("type_model"):
        zoek_model = normaliseer_model(zoek["type_model"])
        adv_titel = normaliseer_model(adv.get("titel",""))
        if zoek_model not in adv_titel:
            return False
    if zoek.get("bouwjaar_van") and adv.get("bouwjaar"):
        if adv["bouwjaar"] < zoek["bouwjaar_van"]:
            return False
    if zoek.get("bouwjaar_tot") and adv.get("bouwjaar"):
        if adv["bouwjaar"] > zoek["bouwjaar_tot"]:
            return False
    if zoek.get("brandstof") and adv.get("brandstof"):
        if zoek["brandstof"].lower() != adv["brandstof"].lower():
            return False
    return True

def maak_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()

# ─────────────────────────────────────────
# MARKTPLAATS SCRAPER
# ─────────────────────────────────────────

async def scrape_marktplaats(zoek: dict) -> list:
    params = {"query": f"{zoek.get('merk','')} {zoek.get('type_model','')}".strip()}
    if zoek.get("bouwjaar_van"):
        params["yearFrom"] = zoek["bouwjaar_van"]
    if zoek.get("bouwjaar_tot"):
        params["yearTo"] = zoek["bouwjaar_tot"]

    url = "https://www.marktplaats.nl/lrp/api/search"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Automotive24Bot/1.0)"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params, headers=headers)
            data = r.json()

        resultaten = []
        for item in data.get("listings", [])[:20]:
            adv = {
                "titel": item.get("title",""),
                "prijs": int(item.get("priceInfo",{}).get("priceCents",0)),
                "url": f"https://www.marktplaats.nl{item.get('vipUrl','')}",
                "site": "marktplaats",
                "foto_url": item.get("imageUrls",[""])[0] if item.get("imageUrls") else None,
                "locatie": item.get("location",{}).get("cityName",""),
                "bouwjaar": item.get("attributes",{}).get("constructionYear"),
                "brandstof": None,
                "km_stand": None,
                "merk": zoek.get("merk"),
                "type_model": zoek.get("type_model"),
            }
            adv["url_hash"] = maak_hash(adv["url"])
            if match_zoek(adv, zoek):
                resultaten.append(adv)
        return resultaten
    except Exception as e:
        print(f"Marktplaats fout: {e}")
        return []

# ─────────────────────────────────────────
# LIVENESS CHECK VOOR BESTAANDE ADVERTENTIES
# ─────────────────────────────────────────

async def check_bestaande_advertenties():
    actief = supabase.table("advertenties")\
        .select("id,url")\
        .eq("status", "actief").execute()

    verkocht_signalen = [
        "niet meer beschikbaar", "advertentie verlopen",
        "deze auto is verkocht", "sold", "verwijderd"
    ]

    async def check_een(adv):
        try:
            async with httpx.AsyncClient(timeout=6, follow_redirects=True) as client:
                r = await client.get(adv["url"], headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Automotive24Bot/1.0)"
                })
                if r.status_code in [404, 410]:
                    return adv["id"], "verlopen"
                if any(s in r.text.lower() for s in verkocht_signalen):
                    return adv["id"], "verkocht"
                return adv["id"], "actief"
        except:
            return adv["id"], "onzeker"

    taken = [check_een(a) for a in (actief.data or [])]
    resultaten = await asyncio.gather(*taken)

    for adv_id, status in resultaten:
        if status != "actief":
            supabase.table("advertenties").update({
                "status": status,
                "verlopen_op": datetime.utcnow().isoformat(),
                "laatste_check": datetime.utcnow().isoformat()
            }).eq("id", adv_id).execute()
            print(f"Advertentie {adv_id} → {status}")

# ─────────────────────────────────────────
# VERLOPEN LEADS AFHANDELEN
# ─────────────────────────────────────────

async def verwerk_verlopen_leads():
    nu = datetime.utcnow().isoformat()

    # Zoeker reageerde niet binnen 24u
    verlopen = supabase.table("leads")\
        .select("id,handelaar_id,credit_gereserveerd")\
        .eq("contact_status", "wacht_op_zoeker")\
        .lt("reactie_deadline", nu).execute()

    for lead in (verlopen.data or []):
        supabase.table("leads").update({
            "contact_status": "verlopen"
        }).eq("id", lead["id"]).execute()
        print(f"Lead {lead['id']} verlopen — credit terug")

    # Handelaar bevestigde niet binnen 24u
    niet_bevestigd = supabase.table("leads")\
        .select("id,handelaar_id,credit_gereserveerd")\
        .eq("contact_status", "zoeker_reageerde")\
        .lt("handelaar_deadline", nu).execute()

    for lead in (niet_bevestigd.data or []):
        supabase.table("leads").update({
            "contact_status": "verlopen"
        }).eq("id", lead["id"]).execute()
        print(f"Lead {lead['id']} handelaar deadline verlopen")

# ─────────────────────────────────────────
# PERSOONSDATA WISSEN NA 48U (AVG)
# ─────────────────────────────────────────

async def wis_persoonsdata():
    cutoff = (datetime.utcnow() - __import__('datetime').timedelta(hours=48)).isoformat()

    oud = supabase.table("leads")\
        .select("id")\
        .eq("persoonsdata_gewist", False)\
        .lt("zoeker_reageerde_op", cutoff).execute()

    for lead in (oud.data or []):
        supabase.table("leads").update({
            "zoeker_naam_enc": None,
            "zoeker_telefoon_enc": None,
            "persoonsdata_gewist": True,
            "persoonsdata_gewist_op": datetime.utcnow().isoformat()
        }).eq("id", lead["id"]).execute()
        print(f"Persoonsdata gewist voor lead {lead['id']}")

# ─────────────────────────────────────────
# HOOFDFUNCTIE
# ─────────────────────────────────────────

async def main():
    print(f"Scraper gestart: {datetime.utcnow()}")

    # Check bestaande advertenties
    await check_bestaande_advertenties()

    # Verwerk verlopen leads
    await verwerk_verlopen_leads()

    # Wis persoonsdata ouder dan 48u
    await wis_persoonsdata()

    # Haal actieve zoekopdrachten op
    zoekopdrachten = supabase.table("zoekopdrachten")\
        .select("*")\
        .eq("status", "actief").execute()

    if not zoekopdrachten.data:
        print("Geen actieve zoekopdrachten")
        return

    print(f"{len(zoekopdrachten.data)} actieve zoekopdrachten")

    for zoek in zoekopdrachten.data:
        print(f"Scraping: {zoek.get('merk')} {zoek.get('type_model')}")
        resultaten = await scrape_marktplaats(zoek)

        nieuwe = 0
        for adv in resultaten:
            bestaand = supabase.table("advertenties")\
                .select("id")\
                .eq("zoekopdracht_id", zoek["id"])\
                .eq("url_hash", adv["url_hash"]).execute()

            if not bestaand.data:
                supabase.table("advertenties").insert({
                    **adv,
                    "zoekopdracht_id": zoek["id"]
                }).execute()
                nieuwe += 1

        supabase.table("zoekopdrachten").update({
            "laatste_scan": datetime.utcnow().isoformat(),
            "aantal_resultaten": supabase.table("advertenties")
                .select("id", count="exact")
                .eq("zoekopdracht_id", zoek["id"])
                .eq("status", "actief").execute().count
        }).eq("id", zoek["id"]).execute()

        print(f"  → {nieuwe} nieuwe advertenties")

    print(f"Scraper klaar: {datetime.utcnow()}")

if __name__ == "__main__":
    asyncio.run(main())