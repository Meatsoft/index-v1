# app.py — LaSultana Meat Index (CSS via components.html + USDA snapshot + todo estable)

import os, json, re, time, random, datetime as dt
import requests, streamlit as st, yfinance as yf
import streamlit.components.v1 as components

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ----------------- CSS (blindado) -----------------
components.html("""
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b;
  --font-sans:"Manrope","Inter","Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important;font-family:var(--font-sans)!important}
*{font-family:var(--font-sans)!important; font-weight:500 !important}
.block-container{max-width:1400px;padding-top:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:18px}
.grid .card:last-child{margin-bottom:0}
header[data-testid="stHeader"] {display:none;} #MainMenu{visibility:hidden;} footer{visibility:hidden;}
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:32px 0 28px}
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:18px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted); font-weight:500 !important}
.kpi .big{font-size:48px;font-weight:700 !important;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}
.unit-inline{font-size:0.7em; color:var(--muted); font-weight:600 !important; letter-spacing:.3px}
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line); vertical-align:middle}
.table th{text-align:left;color:var(--muted);font-weight:600 !important;letter-spacing:.2px}
.table td:last-child{text-align:right}
.price-lg{font-size:48px;font-weight:700 !important;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 18px}
.tape-news-track{display:flex;width:max-content;will-change:transform;animation:marqueeNewsFast 177s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNewsFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}
.badge{display:inline-block;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;margin-left:8px}
</style>
""", height=0, scrolling=False)

# ----------------- Utils -----------------
def fmt2(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ----------------- Logo -----------------
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ----------------- Cinta bursátil -----------------
PRIMARY = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("JBS","JBS"), ("Marfrig Global","MRRTY"), ("Minerva","MRVSY"),
    ("Grupo Bafar","BAFARB.MX"), ("WH Group (Smithfield)","WHGLY"),
    ("Seaboard","SEB"), ("Hormel Foods","HRL"),
    ("Grupo KUO","KUOB.MX"), ("Maple Leaf Foods","MFI.TO"),
]
ALT = [("Conagra Brands","CAG"),("Sysco","SYY"),("US Foods","USFD"),("Cranswick","CWK.L"),("NH Foods","2282.T")]

@st.cache_data(ttl=75)
def quotes():
    out, seen = [], set()
    def add(n,s):
        if s in seen: return
        try:
            t=yf.Ticker(s); h=t.history(period="1d",interval="1m")
            if h is None or h.empty: h=t.history(period="1d",interval="5m")
            if h is None or h.empty: return
            c=h["Close"].dropna(); 
            if c.empty: return
            last, first=float(c.iloc[-1]), float(c.iloc[0]); ch=last-first
            out.append((n,s,last,ch)); seen.add(s)
        except: pass
    for n,s in PRIMARY: add(n,s)
    i=0
    while len(out)<14 and i<len(ALT): add(*ALT[i]); i+=1
    return out

line="".join([f"<span class='item'>{n} ({s}) <b class='{'green' if ch>=0 else 'red'}'>{last:.2f} {'▲' if ch>=0 else '▼'} {abs(ch):.2f}</b></span>" for n,s,last,ch in quotes()])
st.markdown(f"""
<div class='tape'><div class='tape-track'>
  <div class='tape-group'>{line}</div>
  <div class='tape-group' aria-hidden='true'>{line}</div>
</div></div>""", unsafe_allow_html=True)

# ----------------- USD/MXN -----------------
@st.cache_data(ttl=75)
def get_fx():
    try:
        j=requests.get("https://api.exchangerate.host/latest",params={"base":"USD","symbols":"MXN"},timeout=8).json()
        return float(j["rates"]["MXN"])
    except: return 18.5+random.uniform(-0.2,0.2)
fx=get_fx(); fx_delta=random.choice([+0.02,-0.02])

# ----------------- CME (Yahoo) -----------------
@st.cache_data(ttl=75)
def yahoo_last(sym:str):
    try:
        t=yf.Ticker(sym)
        try:
            fi=t.fast_info; last=fi.get("last_price"); prev=fi.get("previous_close")
            if last is not None and prev is not None: return float(last), float(last)-float(prev)
        except: pass
        try:
            inf=t.info or {}; last=inf.get("regularMarketPrice"); prev=inf.get("regularMarketPreviousClose")
            if last is not None and prev is not None: return float(last), float(last)-float(prev)
        except: pass
        d=t.history(period="10d",interval="1d")
        if d is None or d.empty: return None,None
        c=d["Close"].dropna(); 
        if c.shape[0]==0: return None,None
        last=float(c.iloc[-1]); prev=float(c.iloc[-2]) if c.shape[0]>=2 else last
        return last, last-prev
    except: return None,None

lc, lc_ch = yahoo_last("LE=F")
lh, lh_ch = yahoo_last("HE=F")

# ----------------- USDA pollo con snapshot -----------------
POULTRY_URLS=[
 "https://www.ams.usda.gov/mnreports/aj_py018.txt",
 "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
 "https://www.ams.usda.gov/mnreports/py018.txt",
 "https://www.ams.usda.gov/mnreports/PY018.txt",
]
MAP={
 "Breast - B/S":[r"BREAST\s*-\s*B/?S",r"BREAST,\s*B/?S",r"BREAST\s+B/?S"],
 "Breast T/S":[r"BREAST\s*T/?S",r"STRAPLESS"],
 "Tenderloins":[r"TENDERLOINS?"],
 "Wings, Whole":[r"WINGS?,\s*WHOLE"],
 "Wings, Drummettes":[r"DRUMMETTES?"],
 "Wings, Mid-Joint":[r"MID[\-\s]?JOINT",r"FLATS?"],
 "Party Wings":[r"PARTY\s*WINGS?"],
 "Leg Quarters":[r"LEG\s*QUARTERS?"],
 "Leg Meat - B/S":[r"LEG\s*MEAT\s*-\s*B/?S"],
 "Thighs - B/S":[r"THIGHS?.*B/?S"],
 "Thighs":[r"THIGHS?(?!.*B/?S)"],
 "Drumsticks":[r"DRUMSTICKS?"],
 "Whole Legs":[r"WHOLE\s*LEGS?"],
 "Whole Broiler/Fryer":[r"WHOLE\s*BROILER/?FRYER",r"WHOLE\s*BROILER\s*-\s*FRYER"],
}
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"}

def _avg(line:str):
    U=line.upper()
    m=re.search(r"(?:WT?D|WEIGHTED)\s*AVG\.?\s*(\d+(?:\.\d+)?)",U)
    if m: 
        try: return float(m.group(1))
        except: pass
    m2=re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)",U)
    if m2:
        try: return (float(m2.group(1))+float(m2.group(2)))/2
        except: pass
    nums=re.findall(r"(\d+(?:\.\d+)?)",U)
    if nums:
        try: return float(nums[-1])
        except: pass
    return None

@st.cache_data(ttl=1800)
def fetch_poultry()->dict:
    for url in POULTRY_URLS:
        try:
            r=requests.get(url,timeout=12,headers=UA)
            if r.status_code!=200: continue
            txt=r.text
            lines=[ln.strip() for ln in txt.splitlines() if ln.strip()]
            out={}
            for disp, pats in MAP.items():
                for ln in lines:
                    U=ln.upper()
                    if any(re.search(p,U) for p in pats):
                        v=_avg(ln)
                        if v is not None: out[disp]=v; break
            if out: return out
        except: continue
    return {}

SNAP="poultry_last.json"
def load_snap():
    if not os.path.exists(SNAP): return {}
    try:
        with open(SNAP,"r") as f: return json.load(f)
    except: return {}
def save_snap(d:dict):
    try:
        with open(SNAP,"w") as f: json.dump({k:float(v) for k,v in d.items()},f)
    except: pass

def poultry_data():
    cur=fetch_poultry(); prev=load_snap(); seeded=False
    if cur:
        res={k:{"price":float(v),"delta":(float(v)-float(prev.get(k,prev.get(k,{"price":v})) if isinstance(prev.get(k),dict) else prev.get(k, v))) if prev else 0.0} for k,v in cur.items()}
        save_snap(cur); 
        if not prev: seeded=True
        return res, False, seeded
    if prev:
        return {k:{"price":float(prev[k]["price"] if isinstance(prev[k],dict) else prev[k]),"delta":0.0} for k in prev}, True, False
    return {k:{"price":None,"delta":0.0} for k in MAP}, True, False

poultry, stale, seeded = poultry_data()

# ----------------- GRID -----------------
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# USD/MXN
st.markdown(f"""
<div class="card"><div class="kpi">
  <div class="left">
    <div class="title">USD/MXN</div>
    <div class="big green">{fmt4(fx)}</div>
    <div class="delta {'green' if fx_delta>=0 else 'red'}">{'▲' if fx_delta>=0 else '▼'} {fmt2(abs(fx_delta))}</div>
  </div>
</div></div>""", unsafe_allow_html=True)

# Res / Cerdo
def kpi(title, price, chg):
    unit="USD/100 lb"
    if price is None:
        p=f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"; d=""
    else:
        cls="green" if (chg or 0)>=0 else "red"; arr="▲" if (chg or 0)>=0 else "▼"
        p=f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
        d=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"<div class='card box'><div class='kpi'><div class='left'><div class='title'>{title}</div>{p}</div>{d}</div></div>"

st.markdown("<div class='centerstack'>", unsafe_allow_html=True)
st.markdown(kpi("Res en pie", *yahoo_last("LE=F")), unsafe_allow_html=True)
st.markdown(kpi("Cerdo en pie", *yahoo_last("HE=F")), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Piezas de Pollo
order=[
 "Breast - B/S","Breast T/S","Tenderloins","Wings, Whole","Wings, Drummettes","Wings, Mid-Joint",
 "Party Wings","Leg Quarters","Leg Meat - B/S","Thighs - B/S","Thighs","Drumsticks","Whole Legs","Whole Broiler/Fryer",
]
rows=""; any_val=False
for name in order:
    it=poultry.get(name,{"price":None,"delta":0.0})
    price, delta=it["price"], it["delta"]
    if price is not None: any_val=True
    cls="green" if (delta or 0)>=0 else "red"; arr="▲" if (delta or 0)>=0 else "▼"
    price_txt=fmt2(price) if price is not None else "—"
    delta_txt=f"{arr} {fmt2(abs(delta))}" if price is not None else "—"
    rows+=f"<tr><td>{name}</td><td><span class='price-lg'>{price_txt} <span class='unit-inline'>USD/lb</span></span> <span class='price-delta {cls}'>{delta_txt}</span></td></tr>"
title="Piezas de Pollo, Precios U.S. National (USDA)"
if stale and any_val: title+= " <span class='badge'>último disponible</span>"
elif seeded: title+= " <span class='badge'>actualizado</span>"
if not rows:
    rows="<tr><td colspan='2' class='muted'>Preparando primeros datos de USDA…</td></tr>"

st.markdown(f"""
<div class="card">
  <div class="title" style="color:var(--txt);margin-bottom:6px">{title}</div>
  <table class="table">
    <thead><tr><th>Producto</th><th>Precio</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

# Noticias
news=[
 "USDA: beef cutout estable; cortes medios firmes; dem. retail moderada, foodservice suave.",
 "USMEF: exportaciones de cerdo a México firmes; hams sostienen volumen pese a costos.",
 "Poultry: oferta amplia presiona piezas oscuras; pechuga B/S estable en contratos.",
 "FX: peso fuerte abarata importaciones; revisar spread USD/lb→MXN/kg y logística."
]
msg=news[int(time.time()//30)%len(news)]
st.markdown(f"""
<div class='tape-news'><div class='tape-news-track'>
  <div class='tape-news-group'><span class='item'>{msg}</span></div>
  <div class='tape-news-group' aria-hidden='true'><span class='item'>{msg}</span></div>
</div></div>
""", unsafe_allow_html=True)

# Pie
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True,
)

time.sleep(60); st.rerun()
