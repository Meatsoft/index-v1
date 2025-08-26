# app.py — LaSultana Meat Index (USD-only tickers, refresh suave)
import os, json, re, time, datetime as dt
import requests, streamlit as st, yfinance as yf
import pandas as pd

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# Oculta el widget de estado (“Running / Reset”) para evitar parpadeo visible
st.markdown("""
<script>
const mo=new MutationObserver(()=>{const s=document.querySelector('[data-testid="stStatusWidget"]'); if(s) s.style.display='none';});
mo.observe(document.body,{subtree:true,childList:true});
</script>
""", unsafe_allow_html=True)

# ================= ESTILOS =================
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
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:18px}
header[data-testid="stHeader"]{display:none;} #MainMenu{visibility:hidden;} footer{visibility:hidden}

/* Logo */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:26px 0 22px}

/* Cinta bursátil */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;animation:marquee 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
.up{color:var(--up)} .down{color:var(--down)} .muted{color:var(--muted)}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* KPIs */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
.unit-inline{font-size:.7em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* Tabla SOLO 3 pechugas — con esquinas redondeadas internas */
.pechugas{border-radius:10px}
.pechugas .tbl{border-radius:10px; overflow:hidden;}   /* recorta las esquinas */
.pechugas table{width:100%;border-collapse:separate;border-spacing:0}
.pechugas th,.pechugas td{padding:10px;border-bottom:1px solid var(--line);vertical-align:middle;background:transparent}
.pechugas th{text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px}
.pechugas td:first-child{font-size:110%}
.price-lg{font-size:48px;font-weight:900;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}
.unit-inline--p{font-size:.60em;color:var(--muted);font-weight:600;letter-spacing:.3px}
.pechugas td:last-child{text-align:right}

/* Noticias — 22% más rápida (122s -> ~95s) */
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 18px}
.tape-news-track{display:flex;width:max-content;animation:marqueeNews 95s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNews{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}
.badge{display:inline-block;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;margin-left:8px}
</style>
""", unsafe_allow_html=True)

def fmt2(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ================= LOGO =================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ================= CINTA (solo USD + reciente) =================
COMPANIES_USD = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("JBS","JBS"),
    ("BRF","BRFS"), ("Hormel Foods","HRL"), ("Seaboard","SEB"),
    ("Minerva","MRVSY"), ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("WH Group","WHGLY"), ("Wingstop","WING"), ("Yum! Brands","YUM"),
    ("Restaurant Brands Intl.","QSR"), ("Sysco","SYY"), ("US Foods","USFD"),
    ("Performance Food Group","PFGC"), ("Walmart","WMT"),
]
RECENCY_DAYS = 30

@st.cache_data(ttl=90)
def yahoo_meta_and_price(sym:str):
    try:
        t = yf.Ticker(sym)
        curr = None
        try: curr = t.fast_info.get("currency")
        except: pass
        if not curr:
            try: curr = (t.info or {}).get("currency")
            except: pass

        last, delta = None, None
        try:
            fi = t.fast_info
            last = fi.get("last_price")
            prev = fi.get("previous_close")
            if last is not None and prev is not None:
                last = float(last); delta = float(last) - float(prev)
        except: pass
        if last is None:
            try:
                inf = t.info or {}
                last = inf.get("regularMarketPrice")
                prev = inf.get("regularMarketPreviousClose")
                if last is not None and prev is not None:
                    last = float(last); delta = float(last) - float(prev)
            except: pass

        last_ts = None
        try:
            hist = t.history(period="2mo", interval="1d")
            if hist is not None and not hist.empty:
                last_ts = pd.to_datetime(hist.index[-1]).to_pydatetime()
                if last is None:
                    close = hist["Close"].dropna()
                    if not close.empty:
                        last = float(close.iloc[-1])
                        if close.shape[0] >= 2:
                            delta = last - float(close.iloc[-2])
        except: pass

        if last is None:
            return None
        return {"last": last, "delta": delta, "currency": curr, "last_ts": last_ts}
    except:
        return None

def is_fresh_usd(meta:dict)->bool:
    if not meta: return False
    if meta.get("currency") != "USD": return False
    ts = meta.get("last_ts")
    if not ts: return True
    return (dt.datetime.utcnow() - ts.replace(tzinfo=None)).days <= RECENCY_DAYS

items=[]
for name, sym in COMPANIES_USD:
    meta = yahoo_meta_and_price(sym)
    if not is_fresh_usd(meta): 
        continue
    last = meta["last"]; chg = meta["delta"]
    if chg is None:
        items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
    else:
        cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
        items.append(f"<span class='item'>{name} ({sym}) <b class='{cls}'>{last:.2f} {arr} {abs(chg):.2f}</b></span>")
line="".join(items)
st.markdown(f"""
<div class='tape'><div class='tape-track'>
  <div class='tape-group'>{line}</div>
  <div class='tape-group' aria-hidden='true'>{line}</div>
</div></div>""", unsafe_allow_html=True)

# ================= FX & FUTUROS (Yahoo) =================
@st.cache_data(ttl=75)
def q(sym:str):
    meta = yahoo_meta_and_price(sym)
    if not meta: return None, None
    return meta["last"], meta["delta"]

fx,fx_chg = q("MXN=X")
lc,lc_chg = q("LE=F")    # Live Cattle front month
lh,lh_chg = q("HE=F")    # Lean Hogs  front month

def kpi(title, price, chg):
    unit="USD/100 lb"
    if price is None:
        price_html=f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"; delta_html=""
    else:
        if chg is None:
            price_html=f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"; delta_html=""
        else:
            cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
            price_html=f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
            delta_html=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""<div class="card"><div class="kpi">
      <div><div class="title">{title}</div>{price_html}</div>{delta_html}
    </div></div>"""

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(kpi("USD/MXN", fx, fx_chg), unsafe_allow_html=True)
st.markdown(kpi("Res en pie", lc, lc_chg), unsafe_allow_html=True)
st.markdown(kpi("Cerdo en pie", lh, lh_chg), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ================= USDA — SOLO 3 PECHUGAS =================
POULTRY_URLS=[
 "https://www.ams.usda.gov/mnreports/aj_py018.txt",
 "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
 "https://www.ams.usda.gov/mnreports/py018.txt",
 "https://www.ams.usda.gov/mnreports/PY018.txt",
]
HDR={"User-Agent":"Mozilla/5.0"}
PECHUGAS_PAT={
 "Pechuga B/S Jumbo":[r"BREAST.*B/?S.*JUMBO", r"JUMBO.*BREAST.*B/?S"],
 "Pechuga B/S":[r"BREAST\\s*-\\s*B/?S(?!.*JUMBO)", r"BREAST,\\s*B/?S(?!.*JUMBO)"],
 "Pechuga T/S (strapless)":[r"BREAST\\s*T/?S", r"STRAPLESS"],
}
def _avg(U:str):
    m=re.search(r"(?:WT?D|WEIGHTED)\\s*AVG\\.?\\s*(\\d+(?:\\.\\d+)?)",U)
    if m:
        try:return float(m.group(1))
        except: pass
    m2=re.search(r"(\\d+(?:\\.\\d+)?)\\s*-\\s*(\\d+(?:\\.\\d+)?)",U)
    if m2:
        try: return (float(m2.group(1))+float(m2.group(2)))/2.0
        except: pass
    nums=re.findall(r"(\\d+(?:\\.\\d+)?)",U)
    if nums:
        try:return float(nums[-1])
        except: return None
    return None

@st.cache_data(ttl=1800)
def fetch_pechugas()->dict:
    for url in POULTRY_URLS:
        try:
            r=requests.get(url,timeout=12,headers=HDR)
            if r.status_code!=200: continue
            lines=[ln.strip() for ln in r.text.splitlines() if ln.strip()]
            out={}
            for disp,pats in PECHUGAS_PAT.items():
                for ln in lines:
                    U=ln.upper()
                    if any(re.search(p,U) for p in pats):
                        v=_avg(U)
                        if v is not None:
                            out[disp]=v; break
            if out: return out
        except: continue
    return {}

SNAP="poultry_last_pechugas.json"
def load_snap():
    if not os.path.exists(SNAP): return {}
    try:
        with open(SNAP,"r") as f: return json.load(f)
    except: return {}
def save_snap(d:dict):
    try:
        with open(SNAP,"w") as f: json.dump({k:float(v) for k,v in d.items()},f)
    except: pass

def pechugas_with_snapshot():
    cur=fetch_pechugas(); prev=load_snap(); seeded=False
    if cur:
        res={}
        for k,v in cur.items():
            pv=prev.get(k,None)
            if isinstance(pv,dict): pv=pv.get("price")
            dlt=0.0 if pv is None else (float(v)-float(pv))
            res[k]={"price":float(v),"delta":float(dlt)}
        save_snap(cur)
        if not prev: seeded=True
        return res,False,seeded
    if prev:
        res={k:{"price":float((v.get("price") if isinstance(v,dict) else v)),"delta":0.0} for k,v in prev.items()}
        return res,True,False
    base={k:{"price":None,"delta":0.0} for k in PECHUGAS_PAT.keys()}
    return base,True,False

pech, stale, seeded = pechugas_with_snapshot()
order=["Pechuga B/S Jumbo","Pechuga B/S","Pechuga T/S (strapless)"]
rows=[]
for name in order:
    it=pech.get(name, {"price":None,"delta":0.0})
    price,delta=it["price"], it["delta"]
    cls="up" if (delta or 0)>=0 else "down"; arr="▲" if (delta or 0)>=0 else "▼"
    price_txt=fmt2(price) if price is not None else "—"
    delta_txt=f"{arr} {fmt2(abs(delta))}" if price is not None else "—"
    rows.append(
        f"<tr><td>{name}</td>"
        f"<td><span class='price-lg'>{price_txt} <span class='unit-inline--p'>USD/lb</span></span> "
        f"<span class='price-delta {cls}'>{delta_txt}</span></td></tr>"
    )
badge=" <span class='badge'>último disponible</span>" if stale else (" <span class='badge'>actualizado</span>" if seeded else "")
st.markdown(f"""
<div class="card pechugas">
  <div class="title" style="color:var(--txt);margin-bottom:6px">Piezas de Pollo, Precios U.S. National (USDA){badge}</div>
  <div class="tbl">
    <table>
      <thead><tr><th>Producto</th><th>Precio</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</div>
""", unsafe_allow_html=True)

# ===== Noticias + pie =====
news=[
  "USDA: beef cutout estable; cortes medios firmes; demanda retail moderada, foodservice suave.",
  "USMEF: exportaciones de cerdo a México firmes; hams sostienen volumen pese a costos.",
  "Pechuga B/S estable en contratos; oferta amplia presiona piezas oscuras.",
  "FX: peso fuerte abarata importaciones; revisar spread USD/lb→MXN/kg y logística."
]
k=int(time.time()//30)%len(news)
st.markdown(f"""
<div class='tape-news'><div class='tape-news-track'>
  <div class='tape-news-group'><span class='item'>{news[k]}</span></div>
  <div class='tape-news-group' aria-hidden='true'><span class='item'>{news[k]}</span></div>
</div></div>""", unsafe_allow_html=True)

st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True
)

# Refresh suave (sin st.autorefresh, evita parpadeos)
time.sleep(60)
st.rerun()
