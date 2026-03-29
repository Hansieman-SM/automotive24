Skip to content
Hansieman-SM
automotive24
Repository navigation
Code
Issues
Pull requests
Actions
Projects
Security
Insights
Settings
Files
Go to file
t
.github/workflows
scraper.yml
api
index.py
api.py
requirements.txt
scraper.py
vercel.json
automotive24
/
api.py
in
main

Edit

Preview
Indent mode

Spaces
Indent size

4
Line wrap mode

No wrap
Editing api.py file contents
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
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
Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the next interactive element on the page.
 
