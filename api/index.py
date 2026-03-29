from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import os, httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Automotive24 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
APP_URL = os.getenv("APP_URL", "https://automotive24-production.up.railway.app")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase verbonden")
    except Exception as e:
        print(f"Supabase fout: {e}")

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

async def stuur_email(naar: str, onderwerp: str, html: str):
    if not RESEND_API_KEY:
        print(f"Geen Resend key — e-mail niet verstuurd naar {naar}")
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": "Automotive24 <onboarding@resend.dev>",
                    "to": [naar],
                    "subject": onderwerp,
                    "html": html
                }
            )
            if resp.status_code == 200:
                print(f"E-mail verstuurd naar {naar}")
                return True
            else:
                print(f"Resend fout: {resp.status_code} {resp.text}")
                return False
    except Exception as e:
        print(f"E-mail fout: {e}")
        return False

def welkomst_html(email: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
      <div style="background:#0D47A1;padding:24px;border-radius:12px 12px 0 0;text-align:center">
        <h1 style="color:white;margin:0;font-size:24px">🚗 Automotive24</h1>
        <p style="color:rgba(255,255,255,.8);margin:8px 0 0">Jouw robot zoekt. Jij leeft je leven.</p>
      </div>
      <div style="background:white;padding:24px;border:1px solid #E0E0E0;border-top:none">
        <h2 style="color:#0D47A1">Welkom bij Automotive24!</h2>
        <p style="color:#444;line-height:1.6">Je account is aangemaakt voor <strong>{email}</strong>.</p>
        <p style="color:#444;line-height:1.6">Je hebt <strong>24 uur gratis</strong> toegang. Stel nu je eerste zoekopdracht in en laat de bot elk uur voor jou zoeken op:</p>
        <ul style="color:#444;line-height:2">
          <li>Marktplaats.nl</li>
          <li>Gaspedaal.nl</li>
          <li>AutoTrader.nl</li>
          <li>Autoscout24.nl</li>
          <li>AutoWeek.nl</li>
          <li>Autotrack.nl</li>
        </ul>
        <div style="text-align:center;margin:24px 0">
          <a href="{APP_URL}" style="background:#1565C0;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:16px">Open de app</a>
        </div>
        <p style="color:#888;font-size:12px">Na 24 uur kost het €1 per dag of €15 per maand. Je bepaalt zelf wanneer je betaalt.</p>
      </div>
      <div style="background:#F5F5F5;padding:12px;border-radius:0 0 12px 12px;text-align:center">
        <p style="color:#aaa;font-size:11px;margin:0">Automotive24 · TDEG BV · Groningen</p>
      </div>
    </div>
    """

def match_html(email: str, merk: str, model: str, prijs: str, url: str, bron: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
      <div style="background:#0D47A1;padding:24px;border-radius:12px 12px 0 0;text-align:center">
        <h1 style="color:white;margin:0;font-size:24px">🚗 Automotive24</h1>
        <p style="color:rgba(255,255,255,.8);margin:8px 0 0">De bot heeft iets gevonden!</p>
      </div>
      <div style="background:white;padding:24px;border:1px solid #E0E0E0;border-top:none">
        <h2 style="color:#2E7D32">✅ Match gevonden!</h2>
        <p style="color:#444">Hoi, de bot heeft een advertentie gevonden die past bij jouw zoekopdracht:</p>
        <div style="background:#F5F5F5;border-radius:8px;padding:16px;margin:16px 0">
          <div style="font-size:18px;font-weight:700;color:#0D47A1">{merk} {model}</div>
          <div style="font-size:22px;font-weight:700;color:#1565C0;margin:8px 0">{prijs}</div>
          <div style="font-size:13px;color:#888">Gevonden op: {bron}</div>
        </div>
        <div style="text-align:center;margin:24px 0">
          <a href="{url}" style="background:#2E7D32;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:16px">Bekijk de advertentie</a>
        </div>
        <p style="color:#888;font-size:12px">Snel zijn loont — populaire advertenties zijn vaak snel weg.</p>
      </div>
      <div style="background:#F5F5F5;padding:12px;border-radius:0 0 12px 12px;text-align:center">
        <p style="color:#aaa;font-size:11px;margin:0">Automotive24 · TDEG BV · Groningen · <a href="{APP_URL}" style="color:#aaa">App openen</a></p>
      </div>
    </div>
    """

@app.get("/")
async def root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"status": "Automotive24 API actief", "supabase": "verbonden" if supabase else "niet verbonden"}

@app.get("/app")
async def webapp():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return HTMLResponse("<h1>Frontend nog niet beschikbaar</h1>")

@app.get("/api/health")
async def health():
    return {"status": "ok", "supabase": "verbonden" if supabase else "niet verbonden", "resend": "actief" if RESEND_API_KEY else "niet ingesteld"}

@app.post("/api/gebruikers/registreer")
async def registreer(email: str, avg_ip: str = ""):
    if not supabase:
        await stuur_email(email, "Welkom bij Automotive24!", welkomst_html(email))
        return {"status": "aangemaakt", "gebruiker": {"id": "test", "email": email}}
    try:
        bestaand = supabase.table("gebruikers").select("id,email,abonnement").eq("email", email).execute()
        if bestaand.data:
            return {"status": "bestaand", "gebruiker": bestaand.data[0]}
        nieuw = supabase.table("gebruikers").insert({
            "email": email,
            "avg_akkoord": True,
            "avg_akkoord_op": datetime.utcnow().isoformat(),
            "avg_akkoord_ip": avg_ip,
            "gratis_periode_tot": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }).execute()
        await stuur_email(email, "Welkom bij Automotive24!", welkomst_html(email))
        return {"status": "aangemaakt", "gebruiker": nieuw.data[0]}
    except Exception as e:
        await stuur_email(email, "Welkom bij Automotive24!", welkomst_html(email))
        return {"status": "aangemaakt", "gebruiker": {"id": "test", "email": email}}

@app.get("/api/gebruikers/{email}/status")
async def gebruiker_status(email: str):
    if not supabase:
        raise HTTPException(503, "Database niet beschikbaar")
    try:
        result = supabase.table("gebruikers").select("*").eq("email", email).execute()
        if not result.data:
            raise HTTPException(404, "Gebruiker niet gevonden")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/zoekopdrachten")
async def maak_zoekopdracht(data: ZoekopdachtModel):
    if not supabase:
        return {"status": "aangemaakt", "zoekopdracht": {"id": "test", "merk": data.merk}}
    try:
        gebruiker = supabase.table("gebruikers").select("id,betaald_tot,gratis_periode_tot").eq("email", data.email).execute()
        if not gebruiker.data:
            raise HTTPException(404, "Registreer eerst")
        g = gebruiker.data[0]
        nu = datetime.utcnow()
        betaald_tot = g.get("betaald_tot")
        gratis_tot = g.get("gratis_periode_tot")
        actief = False
        if betaald_tot:
            actief = datetime.fromisoformat(betaald_tot.replace("Z","")) > nu
        elif gratis_tot:
            actief = datetime.fromisoformat(gratis_tot.replace("Z","")) > nu
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
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "aangemaakt", "zoekopdracht": {"id": "test"}}

@app.get("/api/zoekopdrachten/{gebruiker_id}")
async def get_zoekopdrachten(gebruiker_id: str):
    if not supabase:
        return []
    try:
        result = supabase.table("zoekopdrachten").select("*").eq("gebruiker_id", gebruiker_id).eq("status", "actief").order("aangemaakt_op", desc=True).execute()
        return result.data
    except Exception:
        return []

@app.delete("/api/zoekopdrachten/{zoek_id}")
async def verwijder_zoekopdracht(zoek_id: str):
    if not supabase:
        return {"status": "gestopt"}
    try:
        supabase.table("zoekopdrachten").update({"status": "gestopt", "gestopt_op": datetime.utcnow().isoformat()}).eq("id", zoek_id).execute()
        return {"status": "gestopt"}
    except Exception as e:
        return {"status": "fout", "melding": str(e)}

@app.get("/api/advertenties/{zoekopdracht_id}")
async def get_advertenties(zoekopdracht_id: str):
    if not supabase:
        return []
    try:
        result = supabase.table("advertenties").select("*").eq("zoekopdracht_id", zoekopdracht_id).eq("status", "actief").order("gevonden_op", desc=True).execute()
        return result.data
    except Exception:
        return []

@app.get("/api/hotlist")
async def get_hotlist():
    if not supabase:
        return []
    try:
        result = supabase.table("hotlist_statistieken").select("*").order("aantal_zoekers", desc=True).limit(10).execute()
        return result.data
    except Exception:
        return []

@app.get("/api/bijzonder")
async def get_bijzonder():
    if not supabase:
        return []
    try:
        result = supabase.table("zoekopdrachten").select("id,merk,type_model,bijzonder,bouwjaar_van,bouwjaar_tot,aangemaakt_op").eq("is_bijzonder", True).eq("status", "actief").order("aangemaakt_op", desc=True).execute()
        return result.data
    except Exception:
        return []

@app.post("/api/test-email")
async def test_email(email: str):
    resultaat = await stuur_email(email, "Test e-mail Automotive24", welkomst_html(email))
    return {"verstuurd": resultaat, "naar": email}

@app.post("/api/webhook/mollie")
async def mollie_webhook(request: Request):
    try:
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
        if not supabase:
            return {"status": "verwerkt"}
        betaling = supabase.table("betalingen").select("*").eq("mollie_payment_id", payment_id).execute()
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
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "fout", "melding": str(e)}

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
