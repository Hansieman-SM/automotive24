from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from mangum import Mangum
import os, httpx
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
    """Haalt alle zoekopdrachten + advertenties op voor een gebruiker."""
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
async def maak_zoekopdracht(data: ZoekopdachtModel):
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
        return {"status": "aangemaakt", "zoekopdracht": zoek.data[0]}
    except HTTPException:
        raise
    except Exception:
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
