# LaSultana Meat Index — v2.8 (USD/lb -30%, Insights full width)
import os, re, json, time, threading, datetime as dt
from zoneinfo import ZoneInfo
from pathlib import Path
import requests, streamlit as st, yfinance as yf

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

/* Unificar spacing entre TODOS los bloques (A/B/C iguales) */
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

/* KPIs */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:54px;font-weight:900;letter-spacing:.2px;line-height:1.0;margin:10px 0 8px 0}
.kpi .delta{font-size:20px;margin-left:12px}
.unit-bottom{font-size:.70em;color:var(--muted);font-weight:700;letter-spacing:.3px;margin-top:6px} /* -30% */

/* Market Insights (rotador suave a todo lo ancho) */
.im-card{display:flex; align-items:center; justify-content:center;}
.im-wrap{
  position:relative; width:100%; height:176px;
  overflow:hidden; border:1px solid var(--line); border-radius:12px;
  padding:8px 10px 10px 10px; display:flex; align-items:center; justify-content:center;
  isolation:isolate; contain:content;
}
.im-item{
  position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center;
  opacity:0; transform:translateY(10px);
  animation:imCycle 40.5s ease-in-out infinite;    /* +35% duración total */
  will-change:opacity,transform; pointer-events:none;
}
.im-item:nth-child(1){animation-delay:0s}
.im-item:nth-child(2){animation-delay:13.5s}
.im-item:nth-child(3){animation-delay:27s}
/* +40% transición (más tiempo en fade) */
@keyframes imCycle{
  0%,   8%   {opacity:0; transform:translateY(10px)}
  12%,  32%  {opacity:1; transform:translateY(2px)}
  36%, 100%  {opacity:0; transform:translateY(-4px)}
}
.im-num{font-size:64px;font-weight:900;letter-spacing:.2px;line-height:1.0;margin:0 0 8px 0;text-align:center}
.im-sub{font-size:18px;color:var(--txt);opacity:.92;line-height:1.25;margin:2px 0 6px 0;text-align:center}
.im-desc{font-size:16px;color:var(--muted);line-height:1.35;margin:2px 14px 0;text-align:center}

/* Footer */
.caption{color:var(--muted)!important;margin-top:8px}
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
        ts = payload.get("updated"); 
        if not ts: return True
        t = dt.datetime.fromisoformat(ts)
        return (dt.datetime.utcnow() - t).total_seconds() > max_age_sec
    except: return True

# ====================== LOGO ======================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if Path("ILSMeatIndex.png").exists():
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ====================== CINTA ======================
COMPANIES_USD=[("Tyson Foods","TSN"),("Pilgrim’s Pride","PPC"),("JBS","JBS"),("BRF","BRFS"),
               ("Hormel Foods","HRL"),("Seaboard","SEB"),("Minerva","MRVSY"),
               ("Cal-Maine Foods","CALM"),("Vital Farms","VITL"),("WH Group","WHGLY"),
               ("Wingstop","WING"),("Yum! Brands","YUM"),("Restaurant Brands Intl.","QSR"),
               ("Sysco","SYY"),("US Foods","USFD"),("Performance Food Group","PFGC"),("Walmart","WMT")]

@st.cache_data(ttl=75)
def quote_last_and_change(sym:str):
    try:
        t=yf.Ticker(sym); fi=t.fast_info
        last=fi.get("last_price"); prev=fi.get("previous_close")
        if last is not None: return float(last),(float(last)-float(prev)) if prev is not None else None
    except: pass
    try:
        inf=yf.Ticker(sym).info or {}
        last=inf.get("regularMarketPrice"); prev=inf.get("regularMarketPreviousClose")
        if last is not None: return float(last),(float(last)-float(prev)) if prev is not None else None
    except: pass
    try:
        d=yf.Ticker(sym).history(period="10d", interval="1d")
        if d is None or d.empty: return None,None
        c=d["Close"].dropna(); last=float(c.iloc[-1]); prev=float(c.iloc[-2]) if c.shape[0]>=2 else None
        return last,(last-prev) if prev is not None else None
    except: return None,None

items=[]
for name,sym in COMPANIES_USD:
    last,chg=quote_last_and_change(sym)
    if last is None: continue
    if chg is None: items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
    else:
        cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
        items.append(f"<span class='item'>{name} ({sym}) <b class='{cls}'>{last:.2f} {arr} {abs(chg):.2f}</b></span>")
ticker_line="".join(items)
st.markdown(f"""
<div class='tape'><div class='tape-track'>
  <div class='tape-group'>{ticker_line}</div>
  <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
</div></div>
""", unsafe_allow_html=True)

# ====================== FX & FUTUROS ======================
@st.cache_data(ttl=75)
def get_yahoo(sym:str): return quote_last_and_change(sym)

SHOW_PER_LB = True   # Mostrar USD/lb (divide por 100 los futuros de LE=F y HE=F)

fx,fx_chg=get_yahoo("MXN=X")
lc,lc_chg=get_yahoo("LE=F")
lh,lh_chg=get_yahoo("HE=F")

def adjust_per_lb(price, chg):
    if not SHOW_PER_LB or price is None: return price, chg
    p = price/100.0
    c = (chg/100.0) if chg is not None else None
    return p, c

lc, lc_chg = adjust_per_lb(lc, lc_chg)
lh, lh_chg = adjust_per_lb(lh, lh_chg)

def kpi_fx(title,val,chg):
    if val is None: val_html="<div class='big'>N/D</div>"; delta=""
    else:
        val_html=f"<div class='big'>{fmt4(val)}</div>"
        if chg is None: delta=""
        else:
            cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
            delta=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"<div class='card'><div class='kpi'><div><div class='title'>{title}</div>{val_html}</div>{delta}</div></div>"

def kpi_cme(title,price,chg):
    unit="USD/lb" if SHOW_PER_LB else "USD/100 lb"
    if price is None:
        price_html=f"<div class='big'>N/D</div><div class='unit-bottom'>{unit}</div>"; delta=""
    else:
        price_html=f"<div class='big'>{fmt2(price)}</div><div class='unit-bottom'>{unit}</div>"
        if chg is None: delta=""
        else:
            cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
            delta=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"<div class='card'><div class='kpi'><div><div class='title'>{title}</div>{price_html}</div>{delta}</div></div>"

# Render
kpi_html = "".join([
    kpi_fx("USD/MXN",fx,fx_chg),
    kpi_cme("Res en pie",lc,lc_chg),
    kpi_cme("Cerdo en pie",lh,lh_chg),
])
st.markdown(f"<div class='grid'>{kpi_html}</div>", unsafe_allow_html=True)

# ====================== IA opcional (para Insights) ======================
OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY","").strip()

def ai_metrics(items):
    if not OPENAI_API_KEY: return items
    try:
        payload={"model":"gpt-4o-mini",
                 "messages":[
                    {"role":"system","content":"Devuelve lista JSON de objetos {num, sub, desc}. No inventes; resume desc en 1 línea."},
                    {"role":"user","content":json.dumps(items,ensure_ascii=False)}
                 ],
                 "temperature":0.2,"response_format":{"type":"json_object"}}
        r=requests.post("https://api.openai.com/v1/chat/completions",
                        headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
                        json=payload, timeout=12)
        data=json.loads(r.json()["choices"][0]["message"]["content"])
        if isinstance(data,list): return data
        if isinstance(data,dict) and "items" in data and isinstance(data["items"],list): return data["items"]
        return items
    except Exception:
        return items

# ====================== GDELT p/ “números” ======================
GDELT_DOC="https://api.gdeltproject.org/api/v2/doc/doc"
COMMON_HEADERS={"User-Agent":"Mozilla/5.0"}

@st.cache_data(ttl=43200)
def gdelt_numbers(query:str, timespan="45d", maxrecords=30):
    try:
        r=requests.get(GDELT_DOC, params={
            "query":query,"mode":"ArtList","format":"json","timespan":timespan,
            "maxrecords":str(maxrecords),"sort":"DateDesc"
        }, headers=COMMON_HEADERS, timeout=8)
        if r.status_code!=200: return []
        arts=(r.json() or {}).get("articles",[]) or []
        out=[]
        for a in arts:
            t=a.get("title","")
            m_pct=re.search(r"([+-]?\d{1,3}(?:\.\d+)?\s?%)", t)
            m_usd=re.search(r"\$[\d,]+(?:\.\d+)?\s?(?:B|M|million|billion)", t, re.I)
            if not (m_pct or m_usd): continue
            num=m_pct.group(1) if m_pct else m_usd.group(0)
            out.append({"num":num,"sub":t,"desc":a.get("domain","")})
        return out[:6]
    except Exception:
        return []

# ====================== SNAPSHOTS + REFRESCO EN 2° PLANO ======================
DATA_DIR = Path(".")
IM_FILE = DATA_DIR / "im_snapshot.json"

def default_im():
    return {
        "updated": dt.datetime.utcnow().isoformat(),
        "items": [
            {"num":"—","sub":"Sin datos recientes","desc":"—"},
            {"num":"—","sub":"Sin datos recientes","desc":"—"},
            {"num":"—","sub":"Sin datos recientes","desc":"—"},
        ]
    }

im_payload = load_json(IM_FILE, default_im())

def refresh_im_async():
    def run():
        try:
            @st.cache_data(ttl=600)
            def pct_30d(sym:str):
                try:
                    d=yf.Ticker(sym).history(period="45d", interval="1d")
                    if d is None or d.empty or d["Close"].dropna().shape[0] < 5: return None
                    c=d["Close"].dropna(); first=float(c.iloc[0]); last=float(c.iloc[-1])
                    return (last/first - 1.0)*100.0
                except: return None

            live=[]
            for label,sym in [("USD/MXN","MXN=X"),("Res (LE=F)","LE=F"),("Cerdo (HE=F)","HE=F")]:
                p=pct_30d(sym)
                if p is not None:
                    sign="+" if p>=0 else ""
                    suffix=" (per lb)" if (SHOW_PER_LB and sym in ["LE=F","HE=F"]) else ""
                    live.append({"num":f"{sign}{p:.1f}%", "sub":f"{label}{suffix} · cambio 30D",
                                 "desc":"Variación de cierre a cierre en los últimos 30 días (Yahoo Finance)."})

            news=[]
            news += gdelt_numbers("(Brazil%20poultry%20exports%20OR%20ABPA%20frango)")
            news += gdelt_numbers("(USMEF%20pork%20exports%20OR%20USMEF%20beef%20exports)")
            news += gdelt_numbers("(Mexico%20chicken%20imports%20OR%20México%20importaciones%20pollo)")

            items = (live[:3] + news[:3])[:3]
            items = ai_metrics(items)
            if not items: items = default_im()["items"]
            while len(items) < 3: items += items

            payload={"updated": dt.datetime.utcnow().isoformat(), "items": items[:3]}
            save_json(IM_FILE, payload)
        except: pass
    threading.Thread(target=run, daemon=True).start()

def is_stale(payload: dict, max_age_sec: int) -> bool:
    try:
        ts = payload.get("updated"); 
        if not ts: return True
        t = dt.datetime.fromisoformat(ts)
        return (dt.datetime.utcnow() - t).total_seconds() > max_age_sec
    except: return True

if is_stale(im_payload, 10*60):
    refresh_im_async()

# ====================== RENDER: INSIGHTS FULL WIDTH ======================
items_im = im_payload.get("items", default_im()["items"])[:3]
im_html = ["<div class='card im-card'><div class='im-wrap'>"]
for it in items_im:
    num=it.get("num","—"); sub=it.get("sub",""); desc=it.get("desc","")
    im_html.append(f"""
      <div class="im-item">
        <div class="im-num">{num}</div>
        <div class="im-sub">{sub}</div>
        <div class="im-desc">{desc if desc else "&nbsp;"}</div>
      </div>
    """)
im_html.append("</div></div>")
st.markdown("".join(im_html), unsafe_allow_html=True)

# ====================== FOOTER (hora Monterrey) ======================
local_now = dt.datetime.now(ZoneInfo("America/Monterrey"))
st.markdown(f"<div class='caption'>Actualizado: {local_now.strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

time.sleep(60)
st.rerun()
