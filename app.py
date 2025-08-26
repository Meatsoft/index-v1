# app.py — LaSultana Meat Index (cinta extendida, sin parpadeo)
# Incluye: 
# - Bursátil (25 empresas de Yahoo Finance)
# - USD/MXN (MXN=X en Yahoo Finance)
# - Res/Cerdo (LE=F / HE=F via Yahoo)
# - Piezas de Pollo (USDA AJ_PY018, snapshot)
# - Noticias scroll
# - Logo

import os, json, re, time, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ====================== ESTILOS ======================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700&display=swap');
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b;
  --font-sans:"Manrope","Inter","Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important;font-family:var(--font-sans)!important}
*{font-family:var(--font-sans)!important}
.block-container{max-width:1400px;padding-top:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:18px}
header[data-testid="stHeader"]{display:none;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:32px 0 28px}
/* CINTA */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.green{color:var(--up)} .red{color:var(--down)}
/* GRID */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:18px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
/* POLLO */
.poultry-table{width:100%}
.poultry-table table{width:100%;border-collapse:collapse}
.poultry-table th,.poultry-table td{padding:10px;border-bottom:1px solid var(--line)}
.poultry-table th{text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px}
.poultry-table td:first-child{font-size:110%;}
.unit-inline{font-size:0.7em;color:var(--muted);font-weight:600;letter-spacing:.3px}
.unit-inline--poultry{font-size:0.60em;color:var(--muted);font-weight:600;letter-spacing:.3px}
.price-lg{font-size:48px;font-weight:900;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}
.poultry-table td:last-child{text-align:right}
/* NOTICIAS */
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 18px}
.tape-news-track{display:flex;width:max-content;will-change:transform;animation:marqueeNewsFast 150s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNewsFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}
.badge{display:inline-block;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;margin-left:8px}
</style>
""", unsafe_allow_html=True)

def fmt2(x: float) -> str:
    s = f"{x:,.2f}"; return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"; return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ==================== LOGO ====================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== CINTA EXTENDIDA ====================
COMPANIES = [
    ("Tyson Foods","TSN"),("Pilgrim’s Pride","PPC"),("JBS","JBS"),("BRF","BRFS"),
    ("Smithfield (WH Group)","WHGLY"),("Hormel Foods","HRL"),("Seaboard","SEB"),
    ("Minerva","MRVSY"),("Marfrig","MRRTY"),("Maple Leaf Foods","MFI.TO"),
    ("Cal-Maine Foods","CALM"),("Vital Farms","VITL"),("Grupo KUO","KUOB.MX"),
    ("Grupo Bafar","BAFARB.MX"),("Minupar Part.","MNPR3.SA"),("Excelsior Alim.","BAUH4.SA"),
    ("Wens Foodstuff","300498.SZ"),("Wingstop","WING"),("Yum! Brands","YUM"),
    ("Restaurant Brands","QSR"),("Sysco","SYY"),("US Foods","USFD"),
    ("Performance Food Gr.","PFGC"),("Walmart","WMT"),("Alsea","ALSEA.MX"),
]

@st.cache_data(ttl=90)
def fetch_quotes(companies):
    out=[]
    for name,sym in companies:
        try:
            t=yf.Ticker(sym); d=t.history(period="1d", interval="5m")
            if d.empty: continue
            last=float(d["Close"].iloc[-1]); first=float(d["Close"].iloc[0])
            ch=last-first; out.append({"name":name,"sym":sym,"px":last,"ch":ch})
        except: continue
    return out

quotes=fetch_quotes(COMPANIES)
ticker_line=""
for q in quotes:
    cls="green" if q["ch"]>=0 else "red"; arrow="▲" if q["ch"]>=0 else "▼"
    ticker_line+=f"<span class='item'>{q['name']} ({q['sym']}) <b class='{cls}'>{q['px']:.2f} {arrow} {abs(q['ch']):.2f}</b></span>"
st.markdown(f"""
<div class='tape'>
  <div class='tape-track'>
    <div class='tape-group'>{ticker_line}</div>
    <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ==================== FX (USD/MXN Yahoo) ====================
@st.cache_data(ttl=75)
def get_fx_yahoo():
    try:
        t=yf.Ticker("MXN=X")
        fi=t.fast_info
        last=fi.get("last_price"); prev=fi.get("previous_close")
        if last and prev: return float(last), float(last)-float(prev)
        d=t.history(period="10d", interval="1d")
        if d.empty: return None,None
        last=float(d["Close"].iloc[-1]); prev=float(d["Close"].iloc[-2])
        return last,last-prev
    except: return None,None

# ==================== CME (Res/Cerdo) ====================
@st.cache_data(ttl=75)
def get_yahoo_last(sym):
    try:
        t=yf.Ticker(sym); fi=t.fast_info
        last=fi.get("last_price"); prev=fi.get("previous_close")
        if last and prev: return float(last), float(last)-float(prev)
        d=t.history(period="10d", interval="1d")
        if d.empty: return None,None
        last=float(d["Close"].iloc[-1]); prev=float(d["Close"].iloc[-2])
        return last,last-prev
    except: return None,None

# ==================== USDA POULTRY ====================
POULTRY_URLS=["https://www.ams.usda.gov/mnreports/aj_py018.txt"]
POULTRY_MAP={"Breast - B/S":["BREAST","B/S"],"Wings, Whole":["WINGS","WHOLE"],"Leg Quarters":["LEG","QUARTERS"],"Thighs":["THIGHS"]}

def _extract_avg_from_line(line):
    m=re.search(r"(\d+\.\d+)", line)
    return float(m.group(1)) if m else None

@st.cache_data(ttl=1800)
def fetch_poultry():
    for url in POULTRY_URLS:
        try:
            r=requests.get(url,timeout=12)
            if r.status_code!=200: continue
            txt=r.text.upper(); out={}
            for k,pats in POULTRY_MAP.items():
                for ln in txt.splitlines():
                    if all(p in ln for p in pats):
                        v=_extract_avg_from_line(ln)
                        if v: out[k]=v; break
            return out
        except: continue
    return {}

def load_snapshot(path="poultry.json"):
    if not os.path.exists(path): return {}
    try: return json.load(open(path))
    except: return {}
def save_snapshot(data,path="poultry.json"):
    try: json.dump(data,open(path,"w")); 
    except: pass

def get_poultry():
    cur=fetch_poultry(); prev=load_snapshot()
    if cur: save_snapshot(cur); return cur,False
    return prev,True

# ==================== RENDER ====================
fx_ph=st.empty(); res_ph=st.empty(); cerdo_ph=st.empty()
pollo_ph=st.empty(); news_ph=st.empty(); footer_ph=st.empty()

def render_fx(ph,fx,chg):
    cls="green" if (chg or 0)>=0 else "red"; arr="▲" if (chg or 0)>=0 else "▼"
    if fx: 
        ph.markdown(f"<div class='card'><div class='title'>USD/MXN</div><div class='big {cls}'>{fmt4(fx)}</div><div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div></div>",unsafe_allow_html=True)

def render_kpi(ph,title,px,chg):
    if not px: 
        ph.markdown(f"<div class='card'><div class='title'>{title}</div><div class='big'>N/D</div></div>",unsafe_allow_html=True); return
    cls="green" if (chg or 0)>=0 else "red"; arr="▲" if (chg or 0)>=0 else "▼"
    ph.markdown(f"<div class='card'><div class='title'>{title}</div><div class='big'>{fmt2(px)} <span class='unit-inline'>USD/100 lb</span></div><div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div></div>",unsafe_allow_html=True)

def render_poultry(ph,data,stale):
    rows="".join([f"<tr><td>{k}</td><td><span class='price-lg'>{fmt2(v)} <span class='unit-inline--poultry'>USD/lb</span></span></td></tr>" for k,v in data.items()])
    badge="<span class='badge'>último disponible</span>" if stale else ""
    ph.markdown(f"<div class='card poultry-table'><div class='title'>Piezas de Pollo, Precios U.S. National (USDA){badge}</div><table><thead><tr><th>Producto</th><th>Precio</th></tr></thead><tbody>{rows}</tbody></table></div>",unsafe_allow_html=True)

def render_news(ph):
    noticias=["USDA: beef cutout estable.","USMEF: exportaciones firmes.","Poultry: pechuga estable.","FX: peso fuerte."]
    k=int(time.time()//30)%len(noticias); text=noticias[k]
    ph.markdown(f"<div class='tape-news'><div class='tape-news-track'><div class='tape-news-group'><span class='item'>{text}</span></div><div class='tape-news-group' aria-hidden='true'><span class='item'>{text}</span></div></div></div>",unsafe_allow_html=True)

# ==================== LOOP ====================
while True:
    fx,fx_chg=get_fx_yahoo()
    res_px,res_chg=get_yahoo_last("LE=F"); cerdo_px,cerdo_chg=get_yahoo_last("HE=F")
    poultry,stale=get_poultry()
    render_fx(fx_ph,fx,fx_chg)
    render_kpi(res_ph,"Res en pie",res_px,res_chg)
    render_kpi(cerdo_ph,"Cerdo en pie",cerdo_px,cerdo_chg)
    render_poultry(pollo_ph,poultry,stale)
    render_news(news_ph)
    footer_ph.markdown(f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15m retraso).</div>",unsafe_allow_html=True)
    time.sleep(60)
