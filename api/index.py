from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase verbonden")
    except Exception as e:
        print(f"Supabase fout: {e}")
        supabase = None

@app.get("/")
async def root():
    return {
        "status": "Automotive24 API actief",
        "supabase": "verbonden" if supabase else "niet verbonden",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/hotlist")
async def get_hotlist():
    if not supabase:
        return []
    result = supabase.table("hotlist_statistieken")\
        .select("*").order("aantal_zoekers", desc=True)\
        .limit(10).execute()
    return result.data

@app.post("/api/gebruikers/registreer")
async def registreer(email: str, avg_ip: str = ""):
    if not supabase:
        raise HTTPException(503, "Database niet beschikbaar")
    bestaand = supabase.table("gebruikers")\
        .select("id,email").eq("email", email).execute()
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
