from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from pydantic import BaseModel, EmailStr
from typing import Optional
from mangum import Mangum
import os, hashlib, httpx
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
    os.getenv("SUPABASE_URL", "https://omytylfnkebocsjjvtwj.supabase.co"),
    os.getenv("SUPABASE_SERVICE_KEY", "")
)

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
    beoordeling: str

@app.get("/")
async def root():
    return {"status": "Automotive24 API actief"}

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

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
        .select("*").eq("email", email).execute()
    if not result.data:
        raise HTTPException(404, "Gebruiker niet gevonden")
    return result.data[0]

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
        raise HTTPException(402, "Abonnement verlopen")
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
        .select("*").eq("gebruiker_id", gebruiker_id)\
        .eq("status", "actief")\
        .order("aangemaakt_op", desc=True).execute()
    return result.data

@app.delete("/api/zoekopdrachten/{zoek_id}")
async def verwijder_zoekopdracht(zoek_id: str):
    supabase.table("zoekopdrachten").update({
        "status": "gestopt",
        "gestopt_op": datetime.utcnow().isoformat()
    }).eq("id", zoek_id).execute()
    return {"status": "gestopt"}

@app.get("/api/advertenties/{zoekopdracht_id}")
async def get_advertenties(zoekopdracht_id: str):
    result = supabase.table("advertenties")\
        .select("*").eq("zoekopdracht_id", zoekopdracht_id)\
        .eq("status", "actief")\
        .order("gevonden_op", desc=True).execute()
    return result.data

@app.get("/api/hotlist")
async def get_hotlist():
    result = supabase.table("hotlist_statistieken")\
        .select("*").order("aantal_zoekers", desc=True)\
        .limit(10).execute()
    return result.data

@app.get("/api/bijzonder")
async def get_bijzonder():
    result = supabase.table("zoekopdrachten")\
        .select("id,merk,type_model,bijzonder,bouwjaar_van,bouwjaar_tot,aangemaakt_op")\
        .eq("is_bijzonder", True).eq("status", "actief")\
        .order("aangemaakt_op", desc=True).execute()
    return result.data

@app.post("/api/beoordelingen")
async def beoordeel(data: BeoordelingModel):
    if data.beoordeling not in ["positief", "negatief"]:
        raise HTTPException(400, "Beoordeling moet positief of negatief zijn")
    bestaand = supabase.table("beoordelingen")\
        .select("id").eq("advertentie_id", data.advertentie_id)\
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
    return {"status": "opgeslagen"}

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
        .select("*").eq("mollie_payment_id", payment_id).execute()
    if not betaling.data or betaling.data[0]["verwerkt"]:
        return {"status": "al verwerkt"}
    b = betaling.data[0]
    nu = datetime.utcnow()
    if b["type"] in ["dag", "maand"]:
        dagen = 1 if b["type"] == "dag" else 30
        supabase.table("gebruikers").update({
            "betaald_tot": (nu + timedelta(days=dagen)).isoformat(),
            "abonnement": b["type"]
        }).eq("id", b["gebruiker_id"]).execute()
    supabase.table("betalingen").update({
        "mollie_status": "paid",
        "betaald_op": nu.isoformat(),
        "verwerkt": True
    }).eq("mollie_payment_id", payment_id).execute()
    return {"status": "verwerkt"}

handler = Mangum(app)
