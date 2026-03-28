from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from pydantic import BaseModel, EmailStr
from typing import Optional
import os, hashlib, httpx, asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Automotive24 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://automotive24.nl", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# ─────────────────────────────────────────
# MODELLEN
# ─────────────────────────────────────────

class ZoekopdachtModel(BaseModel):
    email: EmailStr
    merk: Optional[str] = None
    type_model: Optional[str] = None
    uitvoering: Optional[str] = None
    brandstof: Optional[str] = None
    bouwjaar_van: Optional[int] = None
    bouwjaar_tot: Optional[int] = None
    bijzonder: Optional[str] = None
    is_bijzonder: bool = False

class ContactReactieModel(BaseModel):
    lead_id: str
    naam: str
    telefoon: str

class ContactBevestigModel(BaseModel):
    lead_id: str
    gelukt: bool

class BeoordelingModel(BaseModel):
    advertentie_id: str
    gebruiker_id: str
    beoordeling: str  # positief of negatief

# ─────────────────────────────────────────
# GEBRUIKERS
# ─────────────────────────────────────────

@app.post("/api/gebruikers/registreer")
async def registreer(email: str, avg_ip: str = ""):
    bestaand = supabase.table("gebruikers")\
        .select("id,email,abonnement")\
        .eq("email", email).execute()

    if bestaand.data:
        return {"status": "bestaand", "gebruiker": bestaand.data[0]}

    nieuw = supabase.table("gebruikers").insert({
        "email": email,
        "avg_akkoord": True,
        "avg_akkoord_op": datetime.utcnow().isoformat(),
        "avg_akkoord_ip": avg_ip,
        "gratis_periode_tot": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }).execute()

    return {"status": "aangemaakt", "gebruiker": nieuw.data[0]}

@app.get("/api/gebruikers/{email}/status")
async def gebruiker_status(email: str):
    result = supabase.table("gebruikers")\
        .select("*")\
        .eq("email", email).execute()
    if not result.data:
        raise HTTPException(404, "Gebruiker niet gevonden")
    return result.data[0]

# ─────────────────────────────────────────
# ZOEKOPDRACHTEN
# ─────────────────────────────────────────

@app.post("/api/zoekopdrachten")
async def maak_zoekopdracht(data: ZoekopdachtModel):
    gebruiker = supabase.table("gebruikers")\
        .select("id,betaald_tot,gratis_periode_tot")\
        .eq("email", data.email).execute()

    if not gebruiker.data:
        raise HTTPException(404, "Registreer eerst")

    g = gebruiker.data[0]
    nu = datetime.utcnow()
    betaald_tot = g.get("betaald_tot")
    gratis_tot = g.get("gratis_periode_tot")

    if betaald_tot:
        actief = datetime.fromisoformat(betaald_tot.replace("Z","")) > nu
    elif gratis_tot:
        actief = datetime.fromisoformat(gratis_tot.replace("Z","")) > nu
    else:
        actief = False

    if not actief:
        raise HTTPException(402, "Abonnement verlopen — verlengen vereist")

    zoek = supabase.table("zoekopdrachten").insert({
        "gebruiker_id": g["id"],
        "merk": data.merk,
        "type_model": data.type_model,
        "uitvoering": data.uitvoering,
        "brandstof": data.brandstof,
        "bouwjaar_van": data.bouwjaar_van,
        "bouwjaar_tot": data.bouwjaar_tot,
        "bijzonder": data.bijzonder,
        "is_bijzonder": data.is_bijzonder,
    }).execute()

    return {"status": "aangemaakt", "zoekopdracht": zoek.data[0]}

@app.get("/api/zoekopdrachten/{gebruiker_id}")
async def get_zoekopdrachten(gebruiker_id: str):
    result = supabase.table("zoekopdrachten")\
        .select("*")\
        .eq("gebruiker_id", gebruiker_id)\
        .eq("status", "actief")\
        .order("aangemaakt_op", desc=True).execute()
    return result.data

@app.delete("/api/zoekopdrachten/{zoek_id}")
async def verwijder_zoekopdracht(zoek_id: str):
    supabase.table("zoekopdrachten")\
        .update({"status": "gestopt", "gestopt_op": datetime.utcnow().isoformat()})\
        .eq("id", zoek_id).execute()
    return {"status": "gestopt"}

# ─────────────────────────────────────────
# ADVERTENTIES
# ─────────────────────────────────────────

@app.get("/api/advertenties/{zoekopdracht_id}")
async def get_advertenties(zoekopdracht_id: str):
    result = supabase.table("advertenties")\
        .select("*")\
        .eq("zoekopdracht_id", zoekopdracht_id)\
        .eq("status", "actief")\
        .order("gevonden_op", desc=True).execute()
    return result.data

@app.post("/api/advertenties/{adv_id}/check")
async def check_advertentie(adv_id: str):
    adv = supabase.table("advertenties")\
        .select("url,status")\
        .eq("id", adv_id).execute()
    if not adv.data:
        raise HTTPException(404, "Niet gevonden")

    url = adv.data[0]["url"]
    actief = await controleer_url(url)

    nieuwe_status = "actief" if actief else "verlopen"
    supabase.table("advertenties").update({
        "status": nieuwe_status,
        "laatste_check": datetime.utcnow().isoformat()
    }).eq("id", adv_id).execute()

    return {"actief": actief, "status": nieuwe_status}

# ─────────────────────────────────────────
# LEADS — CONTACTFLOW
# ─────────────────────────────────────────

@app.post("/api/leads/reageer")
async def zoeker_reageer(data: ContactReactieModel, request: Request):
    lead = supabase.table("leads")\
        .select("*")\
        .eq("id", data.lead_id).execute()

    if not lead.data:
        raise HTTPException(404, "Lead niet gevonden")

    l = lead.data[0]
    deadline = datetime.fromisoformat(l["reactie_deadline"].replace("Z",""))

    if datetime.utcnow() > deadline:
        raise HTTPException(410, "Reactietermijn van 24 uur verstreken")

    # Versleuteld opslaan (basis base64 — in productie: pgcrypto)
    import base64
    naam_enc = base64.b64encode(data.naam.encode()).decode()
    tel_enc = base64.b64encode(data.telefoon.encode()).decode()

    nu = datetime.utcnow()
    supabase.table("leads").update({
        "zoeker_naam_enc": naam_enc,
        "zoeker_telefoon_enc": tel_enc,
        "zoeker_reageerde_op": nu.isoformat(),
        "contact_status": "zoeker_reageerde",
        "handelaar_deadline": (nu + timedelta(hours=24)).isoformat()
    }).eq("id", data.lead_id).execute()

    return {"status": "geregistreerd", "bericht": "Handelaar neemt binnen 24 uur contact op"}

@app.post("/api/leads/bevestig")
async def handelaar_bevestig(data: ContactBevestigModel):
    lead = supabase.table("leads")\
        .select("*")\
        .eq("id", data.lead_id).execute()

    if not lead.data:
        raise HTTPException(404, "Lead niet gevonden")

    l = lead.data[0]
    nieuwe_status = "contact_gelukt" if data.gelukt else "niet_bereikbaar"

    update_data = {
        "contact_status": nieuwe_status,
        "handelaar_bevestigd_op": datetime.utcnow().isoformat()
    }

    if data.gelukt:
        # Credit afschrijven
        supabase.table("handelaars").update({
            "credit_balans": supabase.rpc("decrement_credits", {
                "handelaar_id": l["handelaar_id"],
                "bedrag": l["credit_gereserveerd"]
            })
        }).eq("id", l["handelaar_id"]).execute()
        update_data["credit_afgeschreven"] = True
        update_data["credit_afgeschreven_op"] = datetime.utcnow().isoformat()
    else:
        # Credit terug
        supabase.table("handelaars").update({
            "credit_balans": supabase.rpc("increment_credits", {
                "handelaar_id": l["handelaar_id"],
                "bedrag": l["credit_gereserveerd"]
            })
        }).eq("id", l["handelaar_id"]).execute()

    supabase.table("leads").update(update_data).eq("id", data.lead_id).execute()

    return {"status": nieuwe_status}

# ─────────────────────────────────────────
# HOTLIST
# ─────────────────────────────────────────

@app.get("/api/hotlist")
async def get_hotlist():
    result = supabase.table("hotlist_statistieken")\
        .select("*")\
        .order("aantal_zoekers", desc=True)\
        .limit(10).execute()
    return result.data

@app.get("/api/bijzonder")
async def get_bijzonder():
    result = supabase.table("zoekopdrachten")\
        .select("id,merk,type_model,bijzonder,bouwjaar_van,bouwjaar_tot,aangemaakt_op")\
        .eq("is_bijzonder", True)\
        .eq("status", "actief")\
        .order("aangemaakt_op", desc=True).execute()
    return result.data

# ─────────────────────────────────────────
# BEOORDELINGEN
# ─────────────────────────────────────────

@app.post("/api/beoordelingen")
async def beoordeel(data: BeoordelingModel):
    if data.beoordeling not in ["positief", "negatief"]:
        raise HTTPException(400, "Beoordeling moet positief of negatief zijn")

    bestaand = supabase.table("beoordelingen")\
        .select("id")\
        .eq("advertentie_id", data.advertentie_id)\
        .eq("gebruiker_id", data.gebruiker_id).execute()

    if bestaand.data:
        supabase.table("beoordelingen").update({
            "beoordeling": data.beoordeling
        }).eq("id", bestaand.data[0]["id"]).execute()
    else:
        supabase.table("beoordelingen").insert({
            "advertentie_id": data.advertentie_id,
            "gebruiker_id": data.gebruiker_id,
            "beoordeling": data.beoordeling
        }).execute()

    veld = "score_positief" if data.beoordeling == "positief" else "score_negatief"
    supabase.rpc("increment_score", {
        "adv_id": data.advertentie_id,
        "veld": veld
    }).execute()

    # Na 5 negatief: automatisch verlopen
    adv = supabase.table("advertenties")\
        .select("score_negatief")\
        .eq("id", data.advertentie_id).execute()
    if adv.data and adv.data[0]["score_negatief"] >= 5:
        supabase.table("advertenties").update({
            "status": "verkocht",
            "verlopen_op": datetime.utcnow().isoformat()
        }).eq("id", data.advertentie_id).execute()

    return {"status": "opgeslagen"}

# ─────────────────────────────────────────
# MOLLIE WEBHOOK
# ─────────────────────────────────────────

@app.post("/api/webhook/mollie")
async def mollie_webhook(request: Request):
    body = await request.form()
    payment_id = body.get("id")

    if not payment_id:
        raise HTTPException(400, "Geen payment ID")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.mollie.com/v2/payments/{payment_id}",
            headers={"Authorization": f"Bearer {os.getenv('MOLLIE_API_KEY')}"}
        )
        payment = resp.json()

    if payment.get("status") != "paid":
        return {"status": "niet betaald"}

    betaling = supabase.table("betalingen")\
        .select("*")\
        .eq("mollie_payment_id", payment_id).execute()

    if not betaling.data or betaling.data[0]["verwerkt"]:
        return {"status": "al verwerkt"}

    b = betaling.data[0]
    nu = datetime.utcnow()

    if b["type"] in ["dag", "maand"]:
        dagen = 1 if b["type"] == "dag" else 30
        geldig_tot = (nu + timedelta(days=dagen)).isoformat()
        supabase.table("gebruikers").update({
            "betaald_tot": geldig_tot,
            "abonnement": b["type"]
        }).eq("id", b["gebruiker_id"]).execute()

    elif b["type"] == "credits":
        credits = float(b["bedrag"]) / 5.0
        supabase.rpc("increment_credits", {
            "handelaar_id": b["handelaar_id"],
            "bedrag": float(b["bedrag"])
        }).execute()

    supabase.table("betalingen").update({
        "mollie_status": "paid",
        "betaald_op": nu.isoformat(),
        "verwerkt": True
    }).eq("mollie_payment_id", payment_id).execute()

    return {"status": "verwerkt"}

# ─────────────────────────────────────────
# HULPFUNCTIE: URL CHECK
# ─────────────────────────────────────────

async def controleer_url(url: str) -> bool:
    verkocht_signalen = [
        "niet meer beschikbaar", "advertentie verlopen",
        "deze auto is verkocht", "sold", "verwijderd",
        "helaas, deze auto", "niet gevonden"
    ]
    try:
        async with httpx.AsyncClient(timeout=6, follow_redirects=True) as client:
            r = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Automotive24Bot/1.0)"
            })
            if r.status_code in [404, 410]:
                return False
            body = r.text.lower()
            if any(s in body for s in verkocht_signalen):
                return False
            return True
    except Exception:
        return False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

**Bestand 3: `requirements.txt`**
```
fastapi==0.111.0
uvicorn==0.29.0
supabase==2.4.2
httpx==0.27.0
python-dotenv==1.0.1
pydantic[email]==2.7.1
python-multipart==0.0.9