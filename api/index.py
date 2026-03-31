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
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = "Hansieman-SM/automotive24"

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase fout: {e}")

HTML = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Automotive24</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
body{background:#F4F6F9;color:#222;min-height:100vh}
.screen{display:none;min-height:100vh}.screen.active{display:block}
nav{background:#0D47A1;padding:0 16px}
.nav-inner{max-width:640px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:56px}
.nav-logo{color:white;font-size:18px;font-weight:600}
.nav-sub{font-size:11px;color:rgba(255,255,255,.6)}
.tabs{background:#0D47A1;display:flex;max-width:640px;margin:0 auto}
.tab{flex:1;padding:10px 4px;border:none;background:transparent;color:rgba(255,255,255,.55);border-bottom:3px solid transparent;font-size:10px;cursor:pointer;text-transform:uppercase;letter-spacing:.5px}
.tab.active{color:white;border-bottom:3px solid white;font-weight:600}
.content{max-width:640px;margin:0 auto;padding:14px}
.card{background:white;border-radius:12px;border:.5px solid #E0E0E0;padding:16px;margin-bottom:10px}
.card-title{font-size:15px;font-weight:600;color:#0D47A1;margin-bottom:3px}
.card-sub{font-size:12px;color:#888;margin-bottom:14px}
label{display:block;font-size:11px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px;margin-top:10px}
input,select{width:100%;padding:10px 12px;border:1px solid #DDD;border-radius:8px;font-size:14px;background:#FAFAFA;color:#222;outline:none}
input:focus,select:focus{border-color:#1565C0;background:white}
.btn{width:100%;padding:13px;background:#1565C0;color:white;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;margin-top:14px}
.btn:hover{background:#1976D2}
.btn.groen{background:#2E7D32}
.btn.grijs{background:#eee;color:#555;border:.5px solid #ddd;margin-top:8px}
.btn:disabled{background:#90CAF9;cursor:not-allowed}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.badge{display:inline-block;padding:3px 8px;border-radius:20px;font-size:11px;font-weight:600}
.badge-groen{background:#E8F5E9;color:#2E7D32}
.zoek-blok{background:white;border-radius:12px;border:.5px solid #E0E0E0;margin-bottom:16px;overflow:hidden}
.zoek-header-blok{background:#0D47A1;padding:12px 16px;display:flex;justify-content:space-between;align-items:center}
.zoek-naam{color:white;font-size:14px;font-weight:600}
.zoek-meta{color:rgba(255,255,255,.7);font-size:11px;margin-top:2px}
.zoek-count{color:white;font-size:20px;font-weight:700;text-align:right}
.zoek-count-lbl{color:rgba(255,255,255,.7);font-size:9px}
.adv-link-rij{display:block;text-decoration:none;color:inherit;border-bottom:.5px solid #F0F0F0}
.adv-link-rij:last-child{border-bottom:none}
.adv-link-rij:hover .adv-item{background:#F8FBFF}
.adv-item{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;gap:12px;cursor:pointer}
.adv-titel{font-size:13px;font-weight:600;color:#222;margin-bottom:3px}
.adv-meta-txt{font-size:11px;color:#888}
.adv-prijs{font-size:16px;font-weight:700;color:#1565C0;white-space:nowrap;text-align:right;flex-shrink:0}
.adv-arrow{font-size:18px;color:#1565C0;margin-left:4px;flex-shrink:0}
.scanning{padding:16px;text-align:center;color:#1565C0;font-size:13px;font-weight:500}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.scanning-dot{animation:pulse 1.2s infinite;display:inline-block}
.hot-item{background:white;border-radius:10px;border:.5px solid #E0E0E0;padding:10px 12px;margin-bottom:6px;display:flex;align-items:center;gap:10px;cursor:pointer}
.hot-rank{font-size:15px;font-weight:700;color:#1565C0;width:22px;flex-shrink:0}
.hot-rank.top{color:#E65100}
.hot-body{flex:1}.hot-merk{font-size:13px;font-weight:600;color:#222}.hot-detail{font-size:11px;color:#888}
.hot-count{text-align:right}.hot-num{font-size:14px;font-weight:700;color:#1565C0}.hot-lbl{font-size:9px;color:#aaa}
.bijz{background:white;border-radius:10px;border:.5px solid #D1C4E9;padding:12px;margin-bottom:8px}
.bijz-title{font-size:13px;font-weight:600;color:#4527A0;margin-bottom:2px}
.bijz-detail{font-size:11px;color:#888;margin-bottom:6px}
.bijz-bottom{display:flex;justify-content:space-between;align-items:center}
.bijz-budget{font-size:12px;font-weight:600;color:#1565C0}.bijz-watchers{font-size:10px;color:#aaa}
.info-box{border-radius:8px;padding:10px 12px;font-size:12px;line-height:1.6;margin-bottom:12px}
.info-box.blauw{background:#E8F0FE;color:#1A3C8F;border-left:3px solid #1565C0;border-radius:0 8px 8px 0}
.sites{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.site-badge{background:#E8F0FE;color:#1A3C8F;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.plan-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.plan{background:white;border-radius:12px;border:.5px solid #E0E0E0;padding:14px;text-align:center;cursor:pointer}
.plan.selected{border:2px solid #1565C0}
.plan-naam{font-size:12px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}
.plan-prijs{font-size:28px;font-weight:700;color:#222;line-height:1}
.plan-per{font-size:12px;color:#888;margin-bottom:8px}
.plan-feat{font-size:11px;color:#666;text-align:left;list-style:none}
.plan-feat li{padding:3px 0;border-bottom:.5px solid #F0F0F0}
.plan-feat li::before{content:'v ';color:#2E7D32}
.zoek-item{background:white;border-radius:10px;border:.5px solid #E0E0E0;padding:12px;margin-bottom:8px}
.zoek-item-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px}
.zoek-item-merk{font-size:14px;font-weight:600;color:#0D47A1}
.zoek-item-detail{font-size:11px;color:#888;margin-top:2px}
.zoek-item-actions{display:flex;gap:6px;margin-top:8px}
.btn-sm{flex:1;padding:7px;border:.5px solid #E0E0E0;border-radius:8px;font-size:11px;cursor:pointer;background:#F9F9F9;color:#333}
.btn-del{background:#FFEBEE;color:#C62828;border:none}
.sec-title{font-size:14px;font-weight:600;color:#222;margin-bottom:10px}
.data-rij{display:flex;justify-content:space-between;padding:8px 0;border-bottom:.5px solid #EEE;font-size:13px}
.data-label{color:#888}.data-val{font-weight:600;color:#222}.data-val.groen{color:#2E7D32}
.onboard{text-align:center;padding:40px 20px}
.onboard-icon{font-size:48px;margin-bottom:16px}
.onboard-title{font-size:22px;font-weight:700;color:#0D47A1;margin-bottom:8px}
.onboard-sub{font-size:14px;color:#666;line-height:1.6;margin-bottom:24px}
.laden{text-align:center;padding:30px;color:#aaa;font-size:13px}
.refresh-bar{background:#E8F0FE;padding:8px 16px;text-align:center;font-size:12px;color:#1A3C8F;display:none;font-weight:500}
</style>
</head>
<body>
<div class="screen active" id="s-welkom">
  <div style="background:#0D47A1;min-height:100vh;display:flex;flex-direction:column;justify-content:center;padding:24px">
    <div style="max-width:380px;margin:0 auto;width:100%">
      <div style="text-align:center;margin-bottom:40px">
        <div style="font-size:56px;margin-bottom:12px">&#128663;</div>
        <h1 style="color:white;font-size:28px;font-weight:700;margin-bottom:8px">Automotive24</h1>
        <p style="color:rgba(255,255,255,.7);font-size:15px;line-height:1.6">Jouw robot zoekt.<br>Jij leeft je leven.</p>
      </div>
      <div style="background:white;border-radius:16px;padding:24px">
        <p style="font-size:14px;color:#555;margin-bottom:16px;text-align:center">Voer je e-mailadres in om te beginnen</p>
        <label>E-mailadres</label>
        <input type="email" id="login-email" placeholder="jouw@email.nl" onkeydown="if(event.key==='Enter')inloggen()" />
        <button class="btn" onclick="inloggen()">Doorgaan</button>
      </div>
    </div>
  </div>
</div>
<div class="screen" id="s-app">
  <div style="background:#F4F6F9;min-height:100vh">
    <div style="background:#0D47A1">
      <div class="nav-inner">
        <div><div class="nav-logo">&#128663; Automotive24</div><div class="nav-sub" id="nav-email"></div></div>
        <button onclick="naarAccount()" style="background:rgba(255,255,255,.15);border:none;color:white;border-radius:20px;padding:5px 12px;font-size:12px;cursor:pointer">Account</button>
      </div>
      <div class="tabs">
        <button class="tab active" onclick="showTab('resultaten',this)">Resultaten</button>
        <button class="tab" onclick="showTab('zoeken',this)">Zoeken</button>
        <button class="tab" onclick="showTab('hotlist',this)">Hotlist</button>
        <button class="tab" onclick="showTab('bijzonder',this)">Bijzonder</button>
      </div>
    </div>
    <div id="refresh-bar" class="refresh-bar">&#128260; Zoeken... vernieuwen over <span id="refresh-countdown">8</span>s</div>
    <div class="content">
      <div id="tab-resultaten"><div id="resultaten-list"><div class="laden">Laden...</div></div></div>
      <div id="tab-zoeken" style="display:none">
        <div class="card">
          <div class="card-title">Nieuwe zoekopdracht</div>
          <div class="card-sub">Resultaten verschijnen direct na het starten</div>
          <label>Merk</label>
          <select id="f-merk">
            <option value="">Alle merken</option>
            <option>Alfa Romeo</option><option>Audi</option><option>BMW</option><option>Citro&euml;n</option>
            <option>Dacia</option><option>Fiat</option><option>Ford</option><option>Honda</option>
            <option>Hyundai</option><option>Kia</option><option>Mazda</option><option>Mercedes-Benz</option>
            <option>Mitsubishi</option><option>Nissan</option><option>Opel</option><option>Peugeot</option>
            <option>Renault</option><option>Seat</option><option>Skoda</option><option>Suzuki</option>
            <option>Toyota</option><option>Volkswagen</option><option>Volvo</option>
          </select>
          <label>Brandstof</label>
          <select id="f-brandstof">
            <option value="">Alle brandstoftypen</option>
            <option>Benzine</option><option>Diesel</option><option>Elektrisch</option><option>Hybride</option><option>LPG</option>
          </select>
          <label>Type / Model</label>
          <input type="text" id="f-type" placeholder="bijv. Golf, 3-Serie, A6..."/>
          <label>Bouwjaar van / tot</label>
          <div class="row2"><select id="f-jaar-van"></select><select id="f-jaar-tot"></select></div>
          <div class="info-box blauw" style="margin-top:12px">Resultaten verschijnen direct &mdash; daarna elk uur opnieuw gescand op Marktplaats, Gaspedaal en Autoscout24.</div>
          <div style="display:grid;grid-template-columns:1fr auto;gap:8px;margin-top:14px">
            <button class="btn" id="start-btn" onclick="startZoek()" style="margin-top:0">&#128269; Zoekopdracht starten</button>
            <button onclick="wisFormulier()" style="padding:13px 16px;background:#eee;color:#555;border:.5px solid #ddd;border-radius:10px;font-size:13px;cursor:pointer">&#10005; Wis</button>
          </div>
        </div>
        <div class="card">
          <div style="font-size:11px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px">Gescande websites</div>
          <div class="sites">
            <span class="site-badge">Marktplaats.nl</span>
            <span class="site-badge">Gaspedaal.nl</span>
            <span class="site-badge">Autoscout24.nl</span>
          </div>
        </div>
        <div class="sec-title">Mijn zoekopdrachten</div>
        <div id="zoek-list"></div>
      </div>
      <div id="tab-hotlist" style="display:none">
        <div class="sec-title">Top 10 meest gezocht</div>
        <div id="hotlist-list"><div class="laden">Laden...</div></div>
      </div>
      <div id="tab-bijzonder" style="display:none">
        <div class="sec-title">Bijzondere zoekopdrachten</div>
        <div class="info-box blauw">Voor klassiekers en zeldzame modellen.</div>
        <div class="bijz"><div class="bijz-title">DeLorean DMC-12</div><div class="bijz-detail">1981&ndash;1982 &middot; Rijdbaar</div><div class="bijz-bottom"><div class="bijz-budget">Budget: &euro;45.000&ndash;&euro;70.000</div><div class="bijz-watchers">7 zoekers</div></div></div>
        <div class="bijz"><div class="bijz-title">Porsche 944 Turbo</div><div class="bijz-detail">1987 &middot; Project toegestaan</div><div class="bijz-bottom"><div class="bijz-budget">Budget: &euro;8.000&ndash;&euro;15.000</div><div class="bijz-watchers">18 zoekers</div></div></div>
        <button class="btn" style="background:#4527A0" onclick="bijzonderPlaatsen()">+ Bijzondere zoekopdracht</button>
      </div>
    </div>
  </div>
</div>
<div class="screen" id="s-account">
  <div style="background:#0D47A1;padding:16px">
    <div style="max-width:640px;margin:0 auto;display:flex;align-items:center;gap:12px">
      <button onclick="toonApp()" style="background:rgba(255,255,255,.15);border:none;color:white;border-radius:20px;padding:5px 12px;font-size:12px;cursor:pointer">&larr; Terug</button>
      <span style="color:white;font-size:16px;font-weight:600">Mijn account</span>
    </div>
  </div>
  <div class="content">
    <div class="card">
      <div class="sec-title">Accountgegevens</div>
      <div class="data-rij"><span class="data-label">E-mailadres</span><span class="data-val" id="acc-email">-</span></div>
      <div class="data-rij"><span class="data-label">Abonnement</span><span class="data-val groen">Gratis periode</span></div>
      <div class="data-rij"><span class="data-label">Zoekopdrachten</span><span class="data-val" id="acc-zoek">0</span></div>
    </div>
    <div class="card">
      <div class="sec-title">Abonnement verlengen</div>
      <div class="plan-grid">
        <div class="plan" id="plan-dag" onclick="selectPlan('dag')">
          <div class="plan-naam">Dag</div><div class="plan-prijs">&euro;1</div><div class="plan-per">per 24 uur</div>
          <ul class="plan-feat"><li>Alle zoekopdrachten</li><li>Elk uur scan</li></ul>
        </div>
        <div class="plan selected" id="plan-maand" onclick="selectPlan('maand')">
          <div class="plan-naam">Maand &#11088;</div><div class="plan-prijs">&euro;15</div><div class="plan-per">per 30 dagen</div>
          <ul class="plan-feat"><li>Alle zoekopdrachten</li><li>Elk uur scan</li><li>50% korting</li></ul>
        </div>
      </div>
      <button class="btn groen" onclick="betalen()">Betalen via iDEAL</button>
    </div>
    <div class="card">
      <button class="btn grijs" onclick="gegevensOpvragen()">Mijn gegevens opvragen (AVG)</button>
      <button class="btn" style="background:#FFEBEE;color:#C62828;border:none;margin-top:8px" onclick="uitloggen()">Uitloggen</button>
    </div>
  </div>
</div>
<script>
var API='https://automotive24-production.up.railway.app';
var huidigEmail=localStorage.getItem('a24_email')||'';
var dashboardData=[];
var gekozenPlan='maand';
var refreshInterval=null,refreshTimer=null,refreshSecs=0;
function wisFormulier(){document.getElementById('f-merk').selectedIndex=0;document.getElementById('f-brandstof').selectedIndex=0;document.getElementById('f-type').value='';document.getElementById('f-jaar-van').selectedIndex=0;document.getElementById('f-jaar-tot').selectedIndex=0;}
function vulJaren(){var vf=document.getElementById('f-jaar-van'),vt=document.getElementById('f-jaar-tot'),nu=new Date().getFullYear();vf.innerHTML='<option value="">Van</option>';vt.innerHTML='<option value="">Tot</option>';for(var j=nu;j>=1940;j--){vf.innerHTML+='<option value="'+j+'">'+j+'</option>';vt.innerHTML+='<option value="'+j+'">'+j+'</option>';}}
function inloggen(){var email=document.getElementById('login-email').value.trim();if(!email||!email.includes('@')){alert('Vul een geldig e-mailadres in');return;}huidigEmail=email;localStorage.setItem('a24_email',email);fetch(API+'/api/gebruikers/registreer?email='+encodeURIComponent(email),{method:'POST'}).catch(function(){});toonApp();}
function toonApp(){document.querySelectorAll('.screen').forEach(function(s){s.classList.remove('active');});document.getElementById('s-app').classList.add('active');document.getElementById('nav-email').textContent=huidigEmail;laadDashboard();laadHotlist();}
function naarAccount(){document.querySelectorAll('.screen').forEach(function(s){s.classList.remove('active');});document.getElementById('s-account').classList.add('active');document.getElementById('acc-email').textContent=huidigEmail;document.getElementById('acc-zoek').textContent=dashboardData.length;}
function uitloggen(){localStorage.removeItem('a24_email');huidigEmail='';dashboardData=[];stopRefresh();document.querySelectorAll('.screen').forEach(function(s){s.classList.remove('active');});document.getElementById('s-welkom').classList.add('active');}
function showTab(name,btn){['resultaten','zoeken','hotlist','bijzonder'].forEach(function(t){var el=document.getElementById('tab-'+t);if(el)el.style.display='none';});document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});var tab=document.getElementById('tab-'+name);if(tab)tab.style.display='block';if(btn)btn.classList.add('active');if(name==='hotlist')laadHotlist();if(name==='zoeken')renderZoekLijst();}
function startAutoRefresh(){stopRefresh();var bar=document.getElementById('refresh-bar'),cd=document.getElementById('refresh-countdown');bar.style.display='block';refreshSecs=8;cd.textContent=refreshSecs;refreshInterval=setInterval(function(){refreshSecs--;cd.textContent=refreshSecs;if(refreshSecs<=0){laadDashboard();refreshSecs=8;cd.textContent=refreshSecs;}},1000);refreshTimer=setTimeout(function(){stopRefresh();},120000);}
function stopRefresh(){if(refreshInterval){clearInterval(refreshInterval);refreshInterval=null;}if(refreshTimer){clearTimeout(refreshTimer);refreshTimer=null;}var bar=document.getElementById('refresh-bar');if(bar)bar.style.display='none';}
function laadDashboard(){var reslist=document.getElementById('resultaten-list');if(!dashboardData.length)reslist.innerHTML='<div class="laden">Laden...</div>';fetch(API+'/api/gebruikers/'+encodeURIComponent(huidigEmail)+'/dashboard').then(function(r){return r.json();}).then(function(data){dashboardData=data.zoekopdrachten||[];renderResultaten();renderZoekLijst();}).catch(function(){if(!dashboardData.length)reslist.innerHTML='<div class="onboard"><div class="onboard-icon">&#9888;</div><div class="onboard-title">Kon niet laden</div><button class="btn" onclick="laadDashboard()">Opnieuw</button></div>';});}
function renderResultaten(){var reslist=document.getElementById('resultaten-list');if(!dashboardData.length){reslist.innerHTML='<div class="onboard"><div class="onboard-icon">&#128269;</div><div class="onboard-title">Nog geen zoekopdrachten</div><div class="onboard-sub">Ga naar Zoeken om je eerste zoekopdracht in te stellen.</div><button class="btn" onclick="showTab(&quot;zoeken&quot;,document.querySelectorAll(&quot;.tab&quot;)[1])">Zoekopdracht instellen</button></div>';return;}var html=dashboardData.map(function(zoek){var brandstof=zoek.brandstof||'';var jaren=zoek.bouwjaar_van&&zoek.bouwjaar_tot?zoek.bouwjaar_van+'\u2013'+zoek.bouwjaar_tot:zoek.bouwjaar_van?'vanaf '+zoek.bouwjaar_van:zoek.bouwjaar_tot?'tot '+zoek.bouwjaar_tot:'';var meta=[brandstof,jaren].filter(Boolean).join(' \u00b7 ');var advs=zoek.advertenties||[];var advHtml=advs.length?advs.map(function(adv){var prijs=adv.prijs?'\u20ac'+Number(adv.prijs).toLocaleString('nl-NL'):'Prijs onbekend';var site=adv.site||'';var datum=adv.gevonden_op?new Date(adv.gevonden_op).toLocaleDateString('nl-NL'):'';return'<a href="'+(adv.url||'#')+'" target="_blank" rel="noopener" class="adv-link-rij"><div class="adv-item"><div style="flex:1"><div class="adv-titel">'+(adv.titel||'')+'</div><div class="adv-meta-txt">'+site+(datum?' \u00b7 '+datum:'')+'</div></div><div style="display:flex;align-items:center"><div class="adv-prijs">'+prijs+'</div><div class="adv-arrow">\u203a</div></div></div></a>';}).join(''):'<div class="scanning"><span class="scanning-dot">&#128260;</span> Aan het zoeken \u2014 resultaten verschijnen hier zo</div>';return'<div class="zoek-blok"><div class="zoek-header-blok"><div><div class="zoek-naam">'+(zoek.merk||'')+' '+(zoek.type_model||'')+'</div>'+(meta?'<div class="zoek-meta">'+meta+'</div>':'')+' </div><div><div class="zoek-count">'+advs.length+'</div><div class="zoek-count-lbl">resultaten</div></div></div>'+advHtml+'</div>';}).join('');reslist.innerHTML=html;}
function renderZoekLijst(){var list=document.getElementById('zoek-list');if(!list)return;if(!dashboardData.length){list.innerHTML='';return;}list.innerHTML=dashboardData.map(function(zoek){var jaren=zoek.bouwjaar_van&&zoek.bouwjaar_tot?zoek.bouwjaar_van+'\u2013'+zoek.bouwjaar_tot:'Alle jaren';return'<div class="zoek-item"><div class="zoek-item-header"><div><div class="zoek-item-merk">'+(zoek.merk||'')+' '+(zoek.type_model||'')+'</div><div class="zoek-item-detail">'+(zoek.brandstof||'-')+' \u00b7 '+jaren+'</div></div><span class="badge badge-groen">Actief</span></div><div class="zoek-item-actions"><button class="btn-sm btn-del" onclick="verwijderZoek(&quot;'+zoek.id+'&quot;)">Verwijderen</button></div></div>';}).join('');}
function startZoek(){var merk=document.getElementById('f-merk').value,type=document.getElementById('f-type').value;if(!merk&&!type){alert('Vul minimaal een merk of type in');return;}var brandstof=document.getElementById('f-brandstof').value,jaarVan=document.getElementById('f-jaar-van').value,jaarTot=document.getElementById('f-jaar-tot').value,btn=document.getElementById('start-btn');btn.disabled=true;btn.textContent='&#128269; Zoeken gestart...';fetch(API+'/api/zoekopdrachten',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:huidigEmail,merk:merk||null,type_model:type||null,brandstof:brandstof?brandstof.toLowerCase():null,bouwjaar_van:jaarVan?parseInt(jaarVan):null,bouwjaar_tot:jaarTot?parseInt(jaarTot):null})}).then(function(r){return r.json();}).then(function(){btn.disabled=false;btn.textContent='&#128269; Zoekopdracht starten';showTab('resultaten',document.querySelectorAll('.tab')[0]);laadDashboard();startAutoRefresh();}).catch(function(){btn.disabled=false;btn.textContent='&#128269; Zoekopdracht starten';alert('Er ging iets mis. Probeer opnieuw.');});}
function verwijderZoek(id){if(!confirm('Zoekopdracht verwijderen?'))return;fetch(API+'/api/zoekopdrachten/'+id,{method:'DELETE'}).then(function(){laadDashboard();}).catch(function(){});}
function laadHotlist(){var list=document.getElementById('hotlist-list');if(!list)return;var fallback=[{merk:'BMW',type_model:'5-serie 530i',brandstof:'benzine',bouwjaar_van:2016,bouwjaar_tot:2021,aantal_zoekers:147},{merk:'Volkswagen',type_model:'Golf GTI',brandstof:'benzine',bouwjaar_van:2018,bouwjaar_tot:2022,aantal_zoekers:121},{merk:'BMW',type_model:'540i',brandstof:'benzine',bouwjaar_van:1994,bouwjaar_tot:2000,aantal_zoekers:89},{merk:'Mercedes-Benz',type_model:'C220d',brandstof:'diesel',bouwjaar_van:2019,bouwjaar_tot:2023,aantal_zoekers:79},{merk:'Audi',type_model:'A4 35 TFSI',brandstof:'benzine',bouwjaar_van:2017,bouwjaar_tot:2021,aantal_zoekers:56},{merk:'Toyota',type_model:'Yaris Hybrid',brandstof:'hybride',bouwjaar_van:2019,bouwjaar_tot:2023,aantal_zoekers:48},{merk:'Porsche',type_model:'911',brandstof:'benzine',bouwjaar_van:1998,bouwjaar_tot:2005,aantal_zoekers:41},{merk:'Renault',type_model:'Trafic',brandstof:'diesel',bouwjaar_van:2015,bouwjaar_tot:2022,aantal_zoekers:38},{merk:'Ford',type_model:'Mustang GT',brandstof:'benzine',bouwjaar_van:2015,bouwjaar_tot:2020,aantal_zoekers:33},{merk:'Volkswagen',type_model:'Transporter T6',brandstof:'diesel',bouwjaar_van:2016,bouwjaar_tot:2021,aantal_zoekers:29}];fetch(API+'/api/hotlist').then(function(r){return r.json();}).then(function(data){renderHotlist(data&&data.length?data:fallback);}).catch(function(){renderHotlist(fallback);});}
function renderHotlist(data){var list=document.getElementById('hotlist-list');list.innerHTML=data.map(function(item,i){var rank=i+1,jaarStr=item.bouwjaar_van&&item.bouwjaar_tot?item.bouwjaar_van+'\u2013'+item.bouwjaar_tot:'';return'<div class="hot-item" onclick="zoekVanHotlist(&quot;'+item.merk+'&quot;,&quot;'+(item.type_model||'')+'&quot;)">'+'<div class="hot-rank'+(rank<=3?' top':'')+'">'+rank+'</div>'+'<div class="hot-body"><div class="hot-merk">'+item.merk+' '+(item.type_model||'')+'</div><div class="hot-detail">'+(item.brandstof||'')+' \u00b7 '+jaarStr+'</div></div>'+'<div class="hot-count"><div class="hot-num">'+item.aantal_zoekers+'</div><div class="hot-lbl">zoekers</div></div>'+(rank<=3?'<span style="font-size:14px">&#128293;</span>':'')+' </div>';}).join('');}
function zoekVanHotlist(merk,type){showTab('zoeken',document.querySelectorAll('.tab')[1]);setTimeout(function(){var el=document.getElementById('f-merk');for(var i=0;i<el.options.length;i++){if(el.options[i].value===merk){el.selectedIndex=i;break;}}document.getElementById('f-type').value=type||'';},100);}
function selectPlan(plan){gekozenPlan=plan;document.getElementById('plan-dag').classList.toggle('selected',plan==='dag');document.getElementById('plan-maand').classList.toggle('selected',plan==='maand');}
function betalen(){alert('Mollie betaling wordt binnenkort geactiveerd.');}
function gegevensOpvragen(){alert('Je gegevens worden verstuurd naar: '+huidigEmail);}
function bijzonderPlaatsen(){var o=prompt('Beschrijf de auto die je zoekt:');if(o)alert('Geplaatst!');}
vulJaren();
if(huidigEmail){toonApp();}
</script>
</body>
</html>"""


def trigger_github_scraper():
    if not GITHUB_TOKEN:
        print("Geen GitHub token")
        return
    try:
        r = httpx.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/scraper.yml/dispatches",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
            json={"ref": "main"}, timeout=15
        )
        print(f"GitHub trigger: {r.status_code}")
    except Exception as e:
        print(f"GitHub trigger fout: {e}")


def supabase_get(path):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, timeout=15)
    return r.json() if r.status_code < 300 else []

def supabase_post_raw(path, data):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json", "Prefer": "return=representation"}
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, json=data, timeout=15)
    return r.json() if r.status_code < 300 else []

def marktplaats_url(item):
    vip = item.get("vipUrl", "")
    if vip:
        return f"https://www.marktplaats.nl{vip}" if vip.startswith("/") else vip
    item_id = item.get("itemId", "")
    return f"https://www.marktplaats.nl/v/m{item_id.lstrip('m')}" if item_id else ""

def normaliseer_merk(merk):
    if not merk:
        return ""
    mapping = {"vw":"volkswagen","mercedes":"mercedes-benz","bmw":"bmw","audi":"audi","ford":"ford",
               "opel":"opel","toyota":"toyota","honda":"honda","renault":"renault","peugeot":"peugeot",
               "skoda":"skoda","seat":"seat","kia":"kia","hyundai":"hyundai","nissan":"nissan",
               "mazda":"mazda","volvo":"volvo","fiat":"fiat","dacia":"dacia","mitsubishi":"mitsubishi",
               "suzuki":"suzuki","porsche":"porsche","tesla":"tesla","citroen":"citroën","citroën":"citroën"}
    return mapping.get(merk.strip().lower(), merk.strip().lower())

def scrape_marktplaats(merk, model, bouwjaar_van, bouwjaar_tot, brandstof):
    resultaten = []
    try:
        for pagina in range(3):
            params = {"query": f"{merk} {model}".strip(), "categoryId": "91", "l1CategoryId": "91",
                      "limit": "30", "offset": str(pagina * 30)}
            if bouwjaar_van: params["constructionYearFrom"] = str(bouwjaar_van)
            if bouwjaar_tot: params["constructionYearTo"] = str(bouwjaar_tot)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json"}
            r = httpx.get("https://www.marktplaats.nl/lrp/api/search", params=params, headers=headers, timeout=20, follow_redirects=True)
            if r.status_code != 200: break
            listings = r.json().get("listings", [])
            if not listings: break
            for item in listings:
                titel = item.get("title", "")
                prijs_cents = item.get("priceInfo", {}).get("priceCents", 0)
                prijs_int = prijs_cents // 100 if prijs_cents else None
                adv_url = marktplaats_url(item)
                if titel and adv_url:
                    resultaten.append({"titel": titel, "prijs": prijs_int, "url": adv_url, "bron": "Marktplaats.nl"})
    except Exception as e:
        print(f"Marktplaats fout: {e}")
    return resultaten

def zoek_matcht(zoek, titel):
    titel_l = titel.lower()
    merk = (zoek.get("merk") or "").lower()
    model = (zoek.get("type_model") or "").lower()
    if merk and merk not in titel_l and normaliseer_merk(merk) not in titel_l:
        return False
    if model and not any(w in titel_l for w in model.split() if len(w) > 2):
        return False
    return True

def scrape_voor_zoekopdracht(zoek):
    alle = scrape_marktplaats(zoek.get("merk",""), zoek.get("type_model",""),
                               zoek.get("bouwjaar_van"), zoek.get("bouwjaar_tot"), zoek.get("brandstof"))
    nieuwe = 0
    for r in alle:
        if not zoek_matcht(zoek, r["titel"]): continue
        url_hash = hashlib.md5(r["url"].encode()).hexdigest()
        if supabase_get(f"advertenties?url_hash=eq.{url_hash}&zoekopdracht_id=eq.{zoek['id']}"): continue
        insert = {"zoekopdracht_id": zoek["id"], "titel": r["titel"], "url": r["url"],
                  "url_hash": url_hash, "site": r["bron"], "merk": zoek.get("merk",""),
                  "type_model": zoek.get("type_model",""), "status": "actief",
                  "gevonden_op": datetime.utcnow().isoformat()}
        if r.get("prijs") is not None: insert["prijs"] = r["prijs"]
        if supabase_post_raw("advertenties", insert): nieuwe += 1
    print(f"Directe scan: {nieuwe} nieuwe advertenties voor {zoek.get('merk','')} {zoek.get('type_model','')}")


class ZoekopdachtModel(BaseModel):
    email: EmailStr
    merk: Optional[str] = None
    type_model: Optional[str] = None
    brandstof: Optional[str] = None
    bouwjaar_van: Optional[int] = None
    bouwjaar_tot: Optional[int] = None


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=HTML, media_type="text/html; charset=utf-8",
                        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"})

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
            "email": email, "avg_akkoord": True,
            "avg_akkoord_op": datetime.utcnow().isoformat(),
            "gratis_periode_tot": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }).execute()
        return {"status": "aangemaakt", "gebruiker": nieuw.data[0]}
    except Exception:
        return {"status": "aangemaakt", "gebruiker": {"id": "test", "email": email}}

@app.get("/api/gebruikers/{email}/dashboard")
async def get_dashboard(email: str):
    if not supabase: return {"zoekopdrachten": []}
    try:
        gebruiker = supabase.table("gebruikers").select("id").eq("email", email).execute()
        if not gebruiker.data: return {"zoekopdrachten": []}
        gebruiker_id = gebruiker.data[0]["id"]
        zoekopdrachten = supabase.table("zoekopdrachten").select("*").eq("gebruiker_id", gebruiker_id).eq("status", "actief").execute().data
        resultaat = []
        for zoek in zoekopdrachten:
            advertenties = supabase.table("advertenties").select("id,titel,prijs,url,site,gevonden_op").eq("zoekopdracht_id", zoek["id"]).eq("status", "actief").order("gevonden_op", desc=True).limit(100).execute().data
            resultaat.append({"id": zoek["id"], "merk": zoek.get("merk",""), "type_model": zoek.get("type_model",""),
                               "brandstof": zoek.get("brandstof",""), "bouwjaar_van": zoek.get("bouwjaar_van"),
                               "bouwjaar_tot": zoek.get("bouwjaar_tot"), "advertenties": advertenties})
        return {"zoekopdrachten": resultaat}
    except Exception as e:
        print(f"Dashboard fout: {e}")
        return {"zoekopdrachten": []}

@app.post("/api/zoekopdrachten")
async def maak_zoekopdracht(data: ZoekopdachtModel, background_tasks: BackgroundTasks):
    if not supabase: return {"status": "aangemaakt", "zoekopdracht": {"id": "test"}}
    try:
        gebruiker = supabase.table("gebruikers").select("id").eq("email", data.email).execute()
        if not gebruiker.data: raise HTTPException(404, "Registreer eerst")
        zoek = supabase.table("zoekopdrachten").insert({
            "gebruiker_id": gebruiker.data[0]["id"], "merk": data.merk, "type_model": data.type_model,
            "brandstof": data.brandstof, "bouwjaar_van": data.bouwjaar_van,
            "bouwjaar_tot": data.bouwjaar_tot, "status": "actief"
        }).execute()
        zoek_data = zoek.data[0]
        background_tasks.add_task(scrape_voor_zoekopdracht, zoek_data)
        background_tasks.add_task(trigger_github_scraper)
        return {"status": "aangemaakt", "zoekopdracht": zoek_data}
    except HTTPException: raise
    except Exception as e:
        print(f"Zoekopdracht fout: {e}")
        return {"status": "aangemaakt", "zoekopdracht": {"id": "test"}}

@app.delete("/api/zoekopdrachten/{zoek_id}")
async def verwijder_zoekopdracht(zoek_id: str):
    if not supabase: return {"status": "gestopt"}
    try:
        supabase.table("zoekopdrachten").update({"status": "gestopt"}).eq("id", zoek_id).execute()
        return {"status": "gestopt"}
    except Exception as e:
        return {"status": "fout", "melding": str(e)}

@app.get("/api/advertenties/{zoekopdracht_id}")
async def get_advertenties(zoekopdracht_id: str):
    if not supabase: return []
    try:
        return supabase.table("advertenties").select("*").eq("zoekopdracht_id", zoekopdracht_id).eq("status", "actief").order("gevonden_op", desc=True).execute().data
    except Exception: return []

@app.get("/api/hotlist")
async def get_hotlist():
    if not supabase: return []
    try:
        return supabase.table("hotlist_statistieken").select("*").order("aantal_zoekers", desc=True).limit(10).execute().data
    except Exception: return []

handler = Mangum(app)
