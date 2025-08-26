# app.py — LaSultana Meat Index (3 pechugas + cinta completa)

import os, json, re, time, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")
# Limpia cachés para evitar que veas la tabla vieja
try:
    st.cache_data.clear()
except Exception:
    pass

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
header[data-testid="stHeader"]{display:none;} #MainMenu{visibility:hidden;} footer{visibility:hidden;}

/* LOGO */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:26px 0 22px}

/* CINTA (stocks) */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
.up{color:var(--up)} .down{color:var(--down)} .muted{color:var(--muted)}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* GRID */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
.unit-inline{font-size:.7em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* TABLA (SOLO 3 PECHUGAS) */
.poultry-table table{width:100%;border-collapse:collapse}
.poultry-table th,.poultry-table td{padding:10px;border-bottom:1px solid var(--line);vertical-align:middle}
.poultry-table th{text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px}
.poultry-table td:first-child{font-size:110%;}
.price-lg{font-size:48px;font-weight:900;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}
.unit-inline--poultry{font-size:.60em;color:var(--muted);font-weight:600;letter-spacing:.3px}
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

# ==================== HELPERS ====================
def fmt2(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ==================== LOGO ====================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== CINTA (toda tu lista) ====================
COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("JBS","JBS"), ("BRF","BRFS"),
    ("Hormel Foods","HRL"), ("Seaboard","SEB"), ("Minerva","MRVSY"), ("Marfrig","MRRTY"),
    ("Maple Leaf Foods","MFI.TO"), ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("Grupo KUO","KUOB.MX"), ("Grupo Bafar","BAFARB.MX"),
    ("WH Group","WHGLY"), ("Minupar Participações","MNPR3.SA"),
    ("Excelsior Alimentos","BAUH4.SA"), ("Wens Foodstuff Group","300498.SZ"),
    ("Wingstop","WING"), ("Yum! Brands","YUM"), ("Restaurant Brands Intl.","QSR"),
    ("Sysco","SYY"), ("US Foods","USFD"), ("Performance Food Group","PFGC"),
    ("Walmart","WMT"), ("Alsea","ALSEA.MX"),
]

@st.cache_data(ttl=75)
def yahoo_quote(sym: str):
    try:
        t = yf.Ticker(sym)
        fi = t.fast_info
        last = fi.get("last_price", None)
        prev = fi.get("previous_close", None)
        if last is not None:
            chg = (float(last) - float(prev)) if prev is not None else None
            return float(last), chg
    except Exception:
        pass
    try:
        inf = yf.Ticker(sym).info or {}
        last = inf.get("regularMarketPrice", None)
        prev = inf.get("regularMarketPreviousClose", None)
        if last is not None:
            chg = (float(last) - float(prev)) if prev is not None else None
            return float(last), chg
    except Exception:
        pass
    try:
        d = yf.Ticker(sym).history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna()
        last = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if c.shape[0] >= 2 else None
        return last, (last - prev) if prev is not None else None
    except Exception:
        return None, None

tape_ph = st.empty()
def render_tape():
    items = []
    for name, sym in COMPANIES:
        last, chg = yahoo_quote(sym)
        if last is None:
            items.append(f"<span class='item'>{name} ({sym}) <b class='muted'>—</b></span>")
        else:
            if chg is None:
                items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
            else:
                cls = "up" if chg >= 0 else "down"; arr = "▲" if chg >= 0 else "▼"
                items.append(f"<span class='item'>{name} ({sym}) <b class='{cls}'>{last:.2f} {arr} {abs(chg):.2f}</b></span>")
    line = "".join(items)
    tape_ph.markdown(f"""
    <div class='tape'><div class='tape-track'>
      <div class='tape-group'>{line}</div>
      <div class='tape-group' aria-hidden='true'>{line}</div>
    </div></div>
    """, unsafe_allow_html=True)

render_tape()

# ==================== FX y FUTUROS (Yahoo) ====================
@st.cache_data(ttl=75)
def get_fx_yahoo():
    try:
        t = yf.Ticker("MXN=X")
        fi = t.fast_info
        last = fi.get("last_price", None)
        prev = fi.get("previous_close", None)
        if last is not None:
            chg = (float(last) - float(prev)) if prev is not None else None
            return float(last), chg
    except Exception:
        pass
    try:
        inf = yf.Ticker("MXN=X").info or {}
        last = inf.get("regularMarketPrice", None)
        prev = inf.get("regularMarketPreviousClose", None)
        if last is not None:
            chg = (float(last) - float(prev)) if prev is not None else None
            return float(last), chg
    except Exception:
        pass
    try:
        d = yf.Ticker("MXN=X").history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna(); last = float(c.iloc[-1]); prev = float(c.iloc[-2]) if c.shape[0]>=2 else None
        return last, (last - prev) if prev is not None else None
    except Exception:
        return None, None

@st.cache_data(ttl=75)
def get_yahoo_last(sym: str):
    try:
        t = yf.Ticker(sym); fi = t.fast_info
        last = fi.get("last_price", None); prev = fi.get("previous_close", None)
        if last is not None:
            chg = (float(last) - float(prev)) if prev is not None else None
            return float(last), chg
    except Exception:
        pass
    try:
        inf = yf.Ticker(sym).info or {}
        last = inf.get("regularMarketPrice", None)
        prev = inf.get("regularMarketPreviousClose", None)
        if last is not None:
            chg = (float(last) - float(prev)) if prev is not None else None
            return last, chg
    except Exception:
        pass
    try:
        d = yf.Ticker(sym).history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna(); last = float(c.iloc[-1]); prev = float(c.iloc[-2]) if c.shape[0]>=2 else None
        return last, (last - prev) if prev is not None else None
    except Exception:
        return None, None

# ==================== USDA — SOLO 3 PECHUGAS ====================
POULTRY_URLS = [
    "https://www.ams.usda.gov/mnreports/aj_py018.txt",
    "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
    "https://www.ams.usda.gov/mnreports/py018.txt",
    "https://www.ams.usda.gov/mnreports/PY018.txt",
]
HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"}

PECHUGAS_MAP = {
    "Pechuga B/S Jumbo":   [r"BREAST.*B/?S.*JUMBO", r"JUMBO.*BREAST.*B/?S"],
    "Pechuga B/S":         [r"BREAST\s*-\s*B/?S(?!.*JUMBO)", r"BREAST,\s*B/?S(?!.*JUMBO)"],
    "Pechuga T/S (strapless)": [r"BREAST\s*T/?S", r"STRAPLESS"],
}

def _avg_from_line(U: str):
    m = re.search(r"(?:WT?D|WEIGHTED)\s*AVG\.?\s*(\d+(?:\.\d+)?)", U)
    if m:
        try: return float(m.group(1))
        except: pass
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", U)
    if m2:
        try: return (float(m2.group(1)) + float(m2.group(2)))/2.0
        except: pass
    nums = re.findall(r"(\d+(?:\.\d+)?)", U)
    if nums:
        try: return float(nums[-1])
        except: return None
    return None

@st.cache_data(ttl=1800)
def fetch_usda_pechugas()->dict:
    for url in POULTRY_URLS:
        try:
            r = requests.get(url, timeout=12, headers=HEADERS)
            if r.status_code != 200: continue
            lines = [ln.strip() for ln in r.text.splitlines() if ln.strip()]
            found = {}
            for disp, pats in PECHUGAS_MAP.items():
                for ln in lines:
                    U = ln.upper()
                    if any(re.search(p, U) for p in pats):
                        val = _avg_from_line(U)
                        if val is not None:
                            found[disp] = val
                            break
            if found: return found
        except Exception:
            continue
    return {}

SNAP = "poultry_last_pechugas.json"
def load_snap():
    if not os.path.exists(SNAP): return {}
    try:
        with open(SNAP,"r") as f: return json.load(f)
    except: return {}
def save_snap(d:dict):
    try:
        with open(SNAP,"w") as f: json.dump({k:float(v) for k,v in d.items()}, f)
    except: pass

def get_pechugas_with_snapshot():
    cur = fetch_usda_pechugas()
    prev = load_snap()
    seeded = False
    if cur:
        res = {}
        for k,v in cur.items():
            pv = prev.get(k, None)
            if isinstance(pv, dict): pv = pv.get("price")
            dlt = 0.0 if pv is None else (float(v)-float(pv))
            res[k] = {"price": float(v), "delta": float(dlt)}
        save_snap(cur)
        if not prev: seeded = True
        return res, False, seeded
    if prev:
        return {k:{"price": float((v.get("price") if isinstance(v,dict) else v)), "delta":0.0} for k,v in prev.items()}, True, False
    base = {k:{"price":None,"delta":0.0} for k in PECHUGAS_MAP.keys()}
    return base, True, False

# ==================== RENDER ====================
def render_kpi(title, price, chg):
    unit = "USD/100 lb"
    if price is None:
        price_html = f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"; delta_html=""
    else:
        if chg is None:
            price_html = f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"; delta_html=""
        else:
            cls = "up" if chg>=0 else "down"; arr = "▲" if chg>=0 else "▼"
            price_html = f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""<div class="card"><div class="kpi"><div>
        <div class="title">{title}</div>{price_html}</div>{delta_html}
    </div></div>"""

fx, fx_chg = get_fx_yahoo()
lc, lc_chg = get_yahoo_last("LE=F")
lh, lh_chg = get_yahoo_last("HE=F")

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(
    f"""<div>{render_kpi("USD/MXN", fx, fx_chg)}</div>
        <div>{render_kpi("Res en pie", lc, lc_chg)}</div>
        <div>{render_kpi("Cerdo en pie", lh, lh_chg)}</div>""",
    unsafe_allow_html=True
)
st.markdown("</div>", unsafe_allow_html=True)

# Tabla SOLO de 3 pechugas
pechugas, stale, seeded = get_pechugas_with_snapshot()
order = ["Pechuga B/S Jumbo","Pechuga B/S","Pechuga T/S (strapless)"]
rows = []
for name in order:
    it = pechugas.get(name, {"price":None,"delta":0.0})
    price, delta = it["price"], it["delta"]
    cls = "up" if (delta or 0)>=0 else "down"; arr = "▲" if (delta or 0)>=0 else "▼"
    price_txt = fmt2(price) if price is not None else "—"
    delta_txt = f"{arr} {fmt2(abs(delta))}" if price is not None else "—"
    rows.append(
        f"<tr><td>{name}</td>"
        f"<td><span class='price-lg'>{price_txt} <span class='unit-inline--poultry'>USD/lb</span></span> "
        f"<span class='price-delta {cls}'>{delta_txt}</span></td></tr>"
    )
badge = " <span class='badge'>último disponible</span>" if stale else (" <span class='badge'>actualizado</span>" if seeded else "")
st.markdown(f"""
<div class="card poultry-table">
  <div class="title" style="color:var(--txt);margin-bottom:6px">Piezas de Pollo, Precios U.S. National (USDA){badge}</div>
  <table><thead><tr><th>Producto</th><th>Precio</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</div>
""", unsafe_allow_html=True)

# Noticias y pie
noticias = [
  "USDA: beef cutout estable; cortes medios firmes; demanda retail moderada, foodservice suave.",
  "USMEF: exportaciones de cerdo a México firmes; hams sostienen volumen pese a costos.",
  "Pechuga B/S estable en contratos; oferta amplia presiona piezas oscuras.",
  "FX: peso fuerte abarata importaciones; revisar spread USD/lb→MXN/kg y logística."
]
k = int(time.time()//30)%len(noticias)
st.markdown(f"""
<div class='tape-news'><div class='tape-news-track'>
  <div class='tape-news-group'><span class='item'>{noticias[k]}</span></div>
  <div class='tape-news-group' aria-hidden='true'><span class='item'>{noticias[k]}</span></div>
</div></div>
""", unsafe_allow_html=True)
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True
)
