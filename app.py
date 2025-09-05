# app.py — LaSultana Meat Index (KPIs + Market Insights + USMEF tape)
import os, re, json, time, threading, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ====================== ESTILOS ======================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700&display=swap');
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b; --font:"Manrope","Inter","Segoe UI",Roboto,Arial,sans-serif;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important;font-family:var(--font)!important}
*{font-family:var(--font)!important}
.block-container{max-width:1400px;padding-top:12px}

/* Unificar espacio vertical entre TODOS los bloques */
.element-container{margin-bottom:12px !important;}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
header[data-testid="stHeader"]{display:none;} #MainMenu{visibility:hidden;} footer{visibility:hidden}

/* Logo */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:26px 0 22px}

/* Cinta bursátil */
.tape{border:1px solid var(--line);border-radius:12px;background:#0d141a;overflow:hidden;min-height:44px}
.tape-track{display:flex;width:max-content;animation:marquee 210s linear infinite;will-change:transform;backface-visibility:hidden;transform:translateZ(0)}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
.up{color:var(--up)} .down{color:var(--down)} .muted{color:var(--muted)}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* KPIs (3 columnas) */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.kpi-wrap{position:relative;min-height:118px;border:1px solid var(--line);border-radius:12px;padding:14px 14px 28px 14px}
.kpi-title{font-size:18px;color:var(--muted);margin-bottom:4px}
.kpi-big{font-size:48px;font-weight:900;letter-spacing:.2px;line-height:1.0;margin:2px 0 0 0}
.kpi-delta{position:absolute;top:10px;right:12px;font-size:20px}
.kpi-unit{position:absolute;left:14px;bottom:8px;font-size:0.70rem;color:var(--muted);font-weight:700;letter-spacing:.25px} /* 30% más pequeño */

/* === Market Insights (a todo lo ancho) === */
.insights-card{min-height:176px}
.im-wrap{
  position:relative; width:100%; height:164px;
  overflow:hidden; border:1px solid var(--line); border-radius:12px;
  padding:10px; display:flex; align-items:center; justify-content:center;
  isolation:isolate; contain:content;
}
.im-item{
  position:absolute; inset:0;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  opacity:0; transform:translateY(10px);
  animation:imCycle 42s ease-in-out infinite; /* 35% más tiempo total (antes ~30s) */
  will-change:opacity,transform; pointer-events:none;
}
/* 3 diapositivas con offsets de 14s */
.im-item:nth-child(1){animation-delay:0s}
.im-item:nth-child(2){animation-delay:14s}
.im-item:nth-child(3){animation-delay:28s}
/* transiciones 40% más largas (fade suave) */
@keyframes imCycle{
  0%   {opacity:0; transform:translateY(8px)}
  6%   {opacity:1; transform:translateY(2px)}
  32%  {opacity:1; transform:translateY(0)}
  38%  {opacity:0; transform:translateY(-3px)}
  100% {opacity:0; transform:translateY(-3px)}
}
.im-num{font-size:62px;font-weight:900;letter-spacing:.2px;line-height:1;margin:0 0 6px 0;text-align:center}
.im-sub{font-size:18px;color:var(--txt);opacity:.95;line-height:1.25;margin:2px 0 6px 0;text-align:center;max-width:980px}
.im-desc{font-size:16px;color:var(--muted);line-height:1.35;margin:2px 14px 0;text-align:center;max-width:980px}

/* === Cinta inferior (USMEF) === */
.tape-news{border:1px solid var(--line);border-radius:12px;background:#0d141a;overflow:hidden;min-height:52px}
.tape-news-track{display:flex;width:max-content;animation:marqueeNews 160s linear infinite;will-change:transform;backface-visibility:hidden;transform:translateZ(0)}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNews{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* Footer */
.caption{color:var(--muted)!important;margin-top:6px}
</style>
""", unsafe_allow_html=True)

# ====================== HELPERS ======================
def fmt2(x):
    if x is None: return "—"
    s=f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x):
    if x is None: return "—"
    s=f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def humanize_delta(minutes: float) -> str:
    if minutes < 1: return "hace segundos"
    if minutes < 60: return f"hace {int(minutes)} min"
    hours = minutes/60
    if hours < 24: return f"hace {int(hours)} h"
    days = int(hours//24); return f"hace {days} d"

def load_json(path: Path, default):
    try:
        if path.exists(): return json.loads(path.read_text(encoding="utf-8"))
    except: pass
    return default
def save_json(path: Path, data):
    try: path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except: pass
def is_stale(payload: dict, max_age_sec: int) -> bool:
    try:
        ts = payload.get("updated")
        if not ts: return True
        t = dt.datetime.fromisoformat(ts)
        return (dt.datetime.utcnow() - t).total_seconds() > max_age_sec
    except: return True

# ====================== LOGO ======================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if Path("ILSMeatIndex.png").exists():
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ====================== CINTA BURSÁTIL ======================
COMPANIES_USD = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("JBS","JBS"), ("BRF","BRFS"),
    ("Hormel Foods","HRL"), ("Seaboard","SEB"), ("Minerva","MRVSY"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"), ("WH Group","WHGLY"),
    ("Wingstop","WING"), ("Yum! Brands","YUM"), ("Restaurant Brands Intl.","QSR"),
    ("Sysco","SYY"), ("US Foods","USFD"), ("Performance Food Group","PFGC"), ("Walmart","WMT"),
]

@st.cache_data(ttl=75)
def quote_last_and_change(sym: str):
    try:
        t = yf.Ticker(sym); fi = t.fast_info
        last = fi.get("last_price"); prev = fi.get("previous_close")
        if last is not None: return float(last), (float(last)-float(prev)) if prev is not None else None
    except: pass
    try:
        inf = yf.Ticker(sym).info or {}
        last = inf.get("regularMarketPrice"); prev = inf.get("regularMarketPreviousClose")
        if last is not None: return float(last), (float(last)-float(prev)) if prev is not None else None
    except: pass
    try:
        d = yf.Ticker(sym).history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna(); last = float(c.iloc[-1]); prev = float(c.iloc[-2]) if c.shape[0]>=2 else None
        return last, (last - prev) if prev is not None else None
    except: return None, None

items=[]
for name,sym in COMPANIES_USD:
    last,chg = quote_last_and_change(sym)
    if last is None: continue
    if chg is None:
        items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
    else:
        cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
        items.append(f"<span class='item'>{name} ({sym}) <b class='{cls}'>{last:.2f} {arr} {abs(chg):.2f}</b></span>")
ticker_line = "".join(items)
st.markdown(f"""
<div class='tape'><div class='tape-track'>
  <div class='tape-group'>{ticker_line}</div>
  <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
</div></div>
""", unsafe_allow_html=True)

# ====================== KPIs (USD/MXN, Res, Cerdo) ======================
@st.cache_data(ttl=75)
def get_yahoo(sym:str): return quote_last_and_change(sym)

def to_per_lb(price, chg):
    if price is None: return None, None
    return price/100.0, (chg/100.0 if chg is not None else None)

fx,fx_chg = get_yahoo("MXN=X")          # USD/MXN (MXN por USD)
lc,lc_chg = get_yahoo("LE=F")           # Live Cattle (USD/100 lb)
lh,lh_chg = get_yahoo("HE=F")           # Lean Hogs (USD/100 lb)
lc,lc_chg = to_per_lb(lc,lc_chg)        # Convertir a USD/lb
lh,lh_chg = to_per_lb(lh,lh_chg)

def kpi_fx(title,val,chg):
    delta_html=""
    if chg is not None:
        cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
        delta_html=f"<div class='kpi-delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""
    <div class='kpi-wrap'>
      <div class='kpi-title'>{title}</div>
      <div class='kpi-big'>{fmt4(val) if val is not None else "N/D"}</div>
      {delta_html}
    </div>"""

def kpi_livestock(title,price,chg):
    delta_html=""
    if chg is not None:
        cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
        delta_html=f"<div class='kpi-delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""
    <div class='kpi-wrap'>
      <div class='kpi-title'>{title}</div>
      <div class='kpi-big'>{fmt2(price) if price is not None else "N/D"}</div>
      <div class='kpi-unit'>USD/lb</div>
      {delta_html}
    </div>"""

kpi_html = "".join([
    kpi_fx("USD/MXN",fx,fx_chg),
    kpi_livestock("Res en pie",lc,lc_chg),
    kpi_livestock("Cerdo en pie",lh,lh_chg),
])
st.markdown(f"<div class='grid'>{kpi_html}</div>", unsafe_allow_html=True)

# ====================== IA opcional ======================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY","").strip()

def ai_summarize_list(items):
    """Formatea/recorta 'sub' y 'desc' con IA (opcional)."""
    if not OPENAI_API_KEY: return items
    try:
        payload = {
            "model":"gpt-4o-mini",
            "messages":[
                {"role":"system","content":"Devuelve lista JSON con los mismos campos num/sub/desc, cortos y claros en español. No inventes datos."},
                {"role":"user","content":json.dumps(items, ensure_ascii=False)}
            ],
            "temperature":0.2,
            "response_format":{"type":"json_object"}
        }
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
            json=payload, timeout=12
        )
        data = json.loads(r.json()["choices"][0]["message"]["content"])
        if isinstance(data, list): return data
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list): return data["items"]
        return items
    except: 
        return items

# ====================== GDELT (para Insights + USMEF) ======================
GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
HDR = {"User-Agent":"Mozilla/5.0"}

@st.cache_data(ttl=600)
def pct_30d(sym:str):
    try:
        d=yf.Ticker(sym).history(period="45d", interval="1d")
        c=d["Close"].dropna()
        if c.shape[0] < 5: return None
        return (float(c.iloc[-1])/float(c.iloc[0]) - 1.0)*100.0
    except: return None

def parse_number_from_title(title:str):
    m_pct=re.search(r"([+-]?\d{1,3}(?:\.\d+)?\s?%)", title)
    if m_pct: return m_pct.group(1)
    m_usd=re.search(r"\$[\d,]+(?:\.\d+)?\s?(?:B|M|billion|million)", title, re.I)
    if m_usd: return m_usd.group(0)
    return "USMEF"

@st.cache_data(ttl=900)
def gdelt_search(query:str, timespan="45d", maxrecords=40):
    try:
        r=requests.get(GDELT_DOC, params={
            "query":query, "mode":"ArtList", "format":"json",
            "timespan":timespan, "maxrecords":str(maxrecords), "sort":"DateDesc"
        }, headers=HDR, timeout=8)
        if r.status_code!=200: return []
        return (r.json() or {}).get("articles",[]) or []
    except: 
        return []

def build_usmef_items():
    arts  = gdelt_search("(USMEF OR \"U.S. Meat Export Federation\")", timespan="60d", maxrecords=60)
    # Filtrar a usmef.org y limpiar duplicados por URL
    seen=set(); out=[]
    for a in arts:
        dom = (a.get("domain") or "").lower()
        if "usmef.org" not in dom: continue
        url = a.get("url","")
        if not url or url in seen: continue
        seen.add(url)
        title = a.get("title","").strip()
        num   = parse_number_from_title(title)
        when  = a.get("seendate","")
        try:
            d=dt.datetime.strptime(when,"%Y%m%d%H%M%S")
            minutes=(dt.datetime.utcnow()-d).total_seconds()/60
            when_txt=humanize_delta(minutes)
        except:
            when_txt=""
        out.append({
            "num": num,
            "sub": title,
            "desc": f"{when_txt} · USMEF" if when_txt else "USMEF"
        })
        if len(out)>=10: break
    return out

# ====================== SNAPSHOTS + REFRESCO (Insights + USMEF tape) ======================
DATA_DIR = Path(".")
IM_FILE   = DATA_DIR / "im_snapshot.json"
TAPE_FILE = DATA_DIR / "usmef_snapshot.json"

def default_im():
    return {"updated": dt.datetime.utcnow().isoformat(),
            "items":[
                {"num":"—","sub":"Sin datos recientes","desc":"—"},
                {"num":"—","sub":"Sin datos recientes","desc":"—"},
                {"num":"—","sub":"Sin datos recientes","desc":"—"},
            ]}

def default_tape():
    return {"updated": dt.datetime.utcnow().isoformat(),
            "lines": ["USMEF: sin novedades recientes."]}

im_payload   = load_json(IM_FILE,   default_im())
tape_payload = load_json(TAPE_FILE, default_tape())

def refresh_insights_async():
    def run():
        try:
            live=[]
            for label,sym in [("USD/MXN","MXN=X"),("Res (LE=F)","LE=F"),("Cerdo (HE=F)","HE=F")]:
                p=pct_30d(sym)
                if p is not None:
                    sign="+" if p>=0 else ""
                    live.append({
                        "num": f"{sign}{p:.1f}%",
                        "sub": f"{label} · cambio 30D",
                        "desc":"Variación de cierre a cierre en los últimos 30 días (Yahoo Finance)."
                    })
            usmef = build_usmef_items()[:3]
            items = (live[:3] + usmef[:3])[:3] or default_im()["items"]
            items = ai_summarize_list(items)
            while len(items)<3: items += items
            save_json(IM_FILE, {"updated": dt.datetime.utcnow().isoformat(), "items": items[:3]})
        except:
            pass
    threading.Thread(target=run, daemon=True).start()

def refresh_tape_async():
    def run():
        try:
            usmef = build_usmef_items()
            if not usmef:
                lines = default_tape()["lines"]
            else:
                lines = [f"{x['sub']}  ·  {x['desc']}" for x in usmef[:8]]
            save_json(TAPE_FILE, {"updated": dt.datetime.utcnow().isoformat(), "lines": lines})
        except:
            pass
    threading.Thread(target=run, daemon=True).start()

# Disparar refrescos en 2º plano cuando estén “viejos”
if is_stale(im_payload,   10*60): refresh_insights_async()
if is_stale(tape_payload, 30*60): refresh_tape_async()

# ====================== RENDER: Market Insights (ancho completo) ======================
items_im = im_payload.get("items", default_im()["items"])[:3]
im_html = ["<div class='card insights-card'><div class='im-wrap'>"]
for it in items_im:
    im_html.append(f"""
      <div class="im-item">
        <div class="im-num">{it.get('num','—')}</div>
        <div class="im-sub">{it.get('sub','')}</div>
        <div class="im-desc">{it.get('desc','')}</div>
      </div>
    """)
im_html.append("</div></div>")
st.markdown("".join(im_html), unsafe_allow_html=True)

# ====================== RENDER: Cinta inferior (USMEF) ======================
lines = tape_payload.get("lines", default_tape()["lines"])
line_html = " · ".join([f"<span class='item'>{st._utils.escape_markdown(l, unsafe_allow_html=True)}</span>" for l in lines])
st.markdown(f"""
<div class='tape-news'><div class='tape-news-track'>
  <div class='tape-news-group'>{line_html}</div>
  <div class='tape-news-group' aria-hidden='true'>{line_html}</div>
</div></div>
""", unsafe_allow_html=True)

# ====================== FOOTER (hora Monterrey) ======================
local_now = dt.datetime.now(ZoneInfo("America/Monterrey"))
st.markdown(f"<div class='caption'>Actualizado: {local_now.strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

# ====================== REFRESH MANUAL CADA 60s ======================
time.sleep(60)
st.rerun()
