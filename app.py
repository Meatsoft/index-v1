# app.py — LaSultana Meat Index (fix pollo: usa último snapshot aunque cambien etiquetas)
import os, json, re, time, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ========= ESTILOS (idénticos a la versión anterior) =========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&display=swap');
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b; --font:"Manrope","Inter","Segoe UI",Roboto,Arial,sans-serif;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important;font-family:var(--font)!important}
*{font-family:var(--font)!important}
.block-container{max-width:1400px;padding-top:12px}
header[data-testid="stHeader"]{display:none;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
div[data-testid="stStatusWidget"]{display:none!important}

/* Tarjetas / KPIs delgados (25%) */
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:14px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .title{font-size:14px;color:var(--muted)}
.kpi .big{font-size:36px;font-weight:800;letter-spacing:.2px}
.kpi .delta{font-size:15px;margin-left:10px}
.unit-inline{font-size:.70em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* Grid */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}

/* Logo */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:24px 0 18px}

/* Cinta bursátil */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:14px}
.tape-track{display:flex;width:max-content;animation:marquee 210s linear infinite;will-change:transform}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
.up{color:var(--up)} .down{color:var(--down)} .muted{color:var(--muted)}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* Cinta de noticias (más rápida) */
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 14px}
.tape-news-track{display:flex;width:max-content;animation:marqueeNews 110s linear infinite;will-change:transform}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNews{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}

/* Badge con 60% menos padding vertical */
.badge{display:inline-block;padding:1px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);
       font-size:12px;line-height:1.1;vertical-align:middle;margin-left:8px}

/* Título de Piezas (micro-padding abajo) */
.section-title{font-size:20px;color:var(--txt);margin:0 0 6px 0}
</style>
""", unsafe_allow_html=True)

# ========= HELPERS =========
def fmt2(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ========= LOGO =========
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ========= CINTA BURSÁTIL (filtra USD) =========
RAW_COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("JBS","JBS"), ("BRF","BRFS"),
    ("Hormel Foods","HRL"), ("Seaboard","SEB"), ("Minerva","MRVSY"), ("Marfrig","MRRTY"),
    ("Maple Leaf Foods","MFI.TO"), ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("Grupo KUO","KUOB.MX"),
    ("WH Group","WHGLY"), ("Minupar Participações","MNPR3.SA"),
    ("Excelsior Alimentos","BAUH4.SA"), ("Wens Foodstuff Group","300498.SZ"),
    ("Wingstop","WING"), ("Yum! Brands","YUM"), ("Restaurant Brands Intl.","QSR"),
    ("Sysco","SYY"), ("US Foods","USFD"), ("Performance Food Group","PFGC"),
    ("Walmart","WMT"),
]

@st.cache_data(ttl=75)
def quote_usd_only(name: str, sym: str):
    try:
        t = yf.Ticker(sym)
        cur = None
        try: cur = (t.fast_info or {}).get("currency", None)
        except: pass
        if not cur:
            try: cur = (t.info or {}).get("currency", None)
            except: pass
        if cur != "USD":
            return None
        last, chg = None, None
        try:
            fi = t.fast_info or {}
            lp = fi.get("last_price", None); pc = fi.get("previous_close", None)
            if lp is not None:
                last = float(lp); chg = (last - float(pc)) if pc is not None else None
        except: pass
        if last is None:
            try:
                inf = t.info or {}
                lp = inf.get("regularMarketPrice", None); pc = inf.get("regularMarketPreviousClose", None)
                if lp is not None:
                    last = float(lp); chg = (last - float(pc)) if pc is not None else None
            except: pass
        if last is None:
            d = t.history(period="10d", interval="1d")
            if d is not None and not d.empty:
                c = d["Close"].dropna()
                if not c.empty:
                    last = float(c.iloc[-1])
                    chg = (last - float(c.iloc[-2])) if c.shape[0] >= 2 else None
        if last is None: return None
        return {"name":name, "sym":sym, "last":last, "chg":chg}
    except: 
        return None

@st.cache_data(ttl=75)
def build_ticker_line():
    items=[]
    for n,s in RAW_COMPANIES:
        q = quote_usd_only(n,s)
        if not q: continue
        if q["chg"] is None:
            items.append(f"<span class='item'>{q['name']} ({q['sym']}) <b>{q['last']:.2f}</b></span>")
        else:
            cls="up" if q["chg"]>=0 else "down"; arr="▲" if q["chg"]>=0 else "▼"
            items.append(f"<span class='item'>{q['name']} ({q['sym']}) "
                         f"<b class='{cls}'>{q['last']:.2f} {arr} {abs(q['chg']):.2f}</b></span>")
    return "".join(items)

ticker_html = build_ticker_line()
st.markdown(f"""
<div class='tape'>
  <div class='tape-track'>
    <div class='tape-group'>{ticker_html}</div>
    <div class='tape-group' aria-hidden='true'>{ticker_html}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ========= QUOTES PRINCIPALES (USD/MXN, LE=F, HE=F) =========
@st.cache_data(ttl=75)
def get_last_from_yahoo(symbol: str):
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info or {}
        lp = fi.get("last_price", None); pc = fi.get("previous_close", None)
        if lp is not None:
            lp = float(lp); return lp, (lp - float(pc)) if pc is not None else None
        inf = t.info or {}
        lp = inf.get("regularMarketPrice", None); pc = inf.get("regularMarketPreviousClose", None)
        if lp is not None:
            lp = float(lp); return lp, (lp - float(pc)) if pc is not None else None
        d = t.history(period="10d", interval="1d")
        if d is not None and not d.empty:
            c = d["Close"].dropna()
            if not c.empty:
                last = float(c.iloc[-1])
                prev = float(c.iloc[-2]) if c.shape[0] >= 2 else None
                return last, (last - prev) if prev is not None else None
        return None, None
    except:
        return None, None

fx, fx_chg = get_last_from_yahoo("MXN=X")
lc, lc_chg = get_last_from_yahoo("LE=F")   # Live Cattle (USD/100 lb)
lh, lh_chg = get_last_from_yahoo("HE=F")   # Lean Hogs  (USD/100 lb)

def kpi_card(title, price, chg, unit):
    if price is None:
        price_html = f"<div class='big'>N/D{(' <span class=\"unit-inline\">'+unit+'</span>') if unit else ''}</div>"
        delta_html = ""
    else:
        if chg is None:
            price_html = f"<div class='big'>{fmt2(price)}{(' <span class=\"unit-inline\">'+unit+'</span>') if unit else ''}</div>"
            delta_html = ""
        else:
            cls = "up" if chg>=0 else "down"; arr = "▲" if chg>=0 else "▼"
            price_html = f"<div class='big'>{fmt2(price)}{(' <span class=\"unit-inline\">'+unit+'</span>') if unit else ''}</div>"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""<div class="card"><div class="kpi">
      <div><div class="title">{title}</div>{price_html}</div>{delta_html}
    </div></div>"""

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(kpi_card("USD/MXN", fx, fx_chg, None),              unsafe_allow_html=True)
st.markdown(kpi_card("Res en pie", lc, lc_chg, "USD/100 lb"),   unsafe_allow_html=True)
st.markdown(kpi_card("Cerdo en pie", lh, lh_chg, "USD/100 lb"), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ========= USDA — 2 PECHUGAS (fix: snapshot normalizado) =========
POULTRY_URLS = [
  "https://www.ams.usda.gov/mnreports/aj_py018.txt",
  "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
  "https://www.ams.usda.gov/mnreports/py018.txt",
  "https://www.ams.usda.gov/mnreports/PY018.txt",
]
HDR = {"User-Agent":"Mozilla/5.0", "Cache-Control":"no-cache"}

# Etiquetas “de pantalla” que mostramos
LAB_BS = "Pechuga B/S"
LAB_TS = "Pechuga T/S (strapless)"

# Sinónimos que pueden existir en snapshots viejos / reportes
SNAP_KEYS_MAP = {
    LAB_BS: [r"PECHUGA\s*B/?S", r"BREAST\s*-\s*B/?S(?!.*JUMBO)", r"BREAST,\s*B/?S(?!.*JUMBO)", r"BREAST B/S(?!.*JUMBO)"],
    LAB_TS: [r"PECHUGA\s*T/?S", r"BREAST\s*T/?S", r"STRAPLESS"]
}

def _avg(U: str) -> float|None:
    m = re.search(r"(?:WT?D|WEIGHTED)\s*AVG\.?\s*(\d+(?:\.\d+)?)", U)
    if m:
        try: return float(m.group(1))
        except: pass
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", U)
    if m2:
        try: return (float(m2.group(1)) + float(m2.group(2))) / 2.0
        except: pass
    nums = re.findall(r"(\d+(?:\.\d+)?)", U)
    if nums:
        try: return float(nums[-1])
        except: return None
    return None

@st.cache_data(ttl=1800)
def fetch_pechugas()->dict:
    """Intenta traer B/S y T/S del USDA; si no hay, regresa {} (no se cachea nada más)."""
    for url in POULTRY_URLS:
        try:
            r = requests.get(url, timeout=15, headers=HDR)
            if r.status_code != 200: 
                continue
            txt = r.text
            if "<html" in txt.lower():  # redirección/proxy
                continue
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            out = {}
            for ln in lines:
                U = ln.upper()
                # T/S
                if any(re.search(p, U) for p in SNAP_KEYS_MAP[LAB_TS]):
                    v = _avg(U)
                    if v is not None:
                        out[LAB_TS] = v
                # B/S (no Jumbo)
                if any(re.search(p, U) for p in SNAP_KEYS_MAP[LAB_BS]):
                    v = _avg(U)
                    if v is not None:
                        out[LAB_BS] = v
            if out:
                return out
        except:
            continue
    return {}

SNAP = "poultry_last_pechugas.json"

def load_snap() -> dict:
    if not os.path.exists(SNAP): return {}
    try:
        with open(SNAP,"r") as f: return json.load(f)
    except:
        return {}

def save_snap(d: dict):
    try:
        with open(SNAP,"w") as f:
            json.dump({k: float(v) for k,v in d.items()}, f)
    except:
        pass

def _normalize_from_snapshot(raw: dict) -> dict:
    """Toma cualquier snapshot (con etiquetas viejas o en inglés) y devuelve un dict con nuestras 2 claves estándar."""
    if not raw: 
        return {}
    norm = {}
    upper_items = [(k, raw[k]["price"] if isinstance(raw[k], dict) else raw[k]) for k in raw]
    for target, pats in SNAP_KEYS_MAP.items():
        # Busca el primer match por regex dentro de las claves existentes
        for k,val in upper_items:
            U = str(k).upper()
            if any(re.search(p, U) for p in pats):
                try:
                    if val is not None:
                        norm[target] = float(val)
                        break
                except:
                    continue
    return norm

def pechugas_with_snapshot():
    """Regresa (result_dict, stale, seeded).
       result_dict: {label: {price, delta}} para B/S y T/S."""
    cur = fetch_pechugas()
    prev_raw = load_snap()

    # Normaliza el snapshot por si las etiquetas viejas no coinciden
    prev_norm = _normalize_from_snapshot(prev_raw)

    # Caso 1: hoy sí obtuvimos datos
    if cur:
        res = {}
        for k, v in cur.items():
            pv = prev_norm.get(k, None)
            dlt = 0.0 if pv is None else (float(v) - float(pv))
            res[k] = {"price": float(v), "delta": float(dlt)}
        # guarda snapshot SOLO si hay datos
        save_snap(cur)
        seeded = True if not prev_norm else False
        return res, False, seeded

    # Caso 2: no hay datos nuevos, usamos snapshot normalizado si existe
    if prev_norm:
        res = {k: {"price": float(prev_norm[k]), "delta": 0.0} for k in prev_norm}
        return res, True, False

    # Caso 3: primera vida sin snapshot
    base = {LAB_BS: {"price": None, "delta": 0.0},
            LAB_TS: {"price": None, "delta": 0.0}}
    return base, True, False

pech, stale, seeded = pechugas_with_snapshot()

def kpi_pechuga(nombre: str, info: dict) -> str:
    price = info.get("price"); delta = info.get("delta", 0.0)
    unit = "USD/lb"
    if price is None:
        price_html = f"<div class='big'>— <span class='unit-inline'>{unit}</span></div>"
        delta_html = ""
    else:
        cls  = "up" if (delta or 0) >= 0 else "down"
        arr  = "▲" if (delta or 0) >= 0 else "▼"
        price_html = f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
        delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(delta))}</div>"
    return f"""<div class="card"><div class="kpi">
        <div><div class="title">{nombre}</div>{price_html}</div>{delta_html}
    </div></div>"""

badge = " <span class='badge'>último disponible</span>" if stale else (" <span class='badge'>actualizado</span>" if seeded else "")
st.markdown(f"<div class='section-title'>Piezas de Pollo — U.S. National (USDA){badge}</div>", unsafe_allow_html=True)

colA, colB = st.columns(2)
with colA:
    st.markdown(kpi_pechuga("Pechuga B/S", pech.get("Pechuga B/S", {})), unsafe_allow_html=True)
with colB:
    st.markdown(kpi_pechuga("Pechuga T/S (strapless)", pech.get("Pechuga T/S (strapless)", {})), unsafe_allow_html=True)

# ========= CINTA DE NOTICIAS =========
news = [
  "USDA: beef cutout estable; cortes medios firmes; demanda retail moderada, foodservice suave.",
  "USMEF: exportaciones de cerdo a México firmes; hams sostienen volumen pese a costos.",
  "Pechuga B/S y T/S estables; revisar spreads USD/lb → MXN/kg y logística.",
  "FX: peso fuerte abarata importaciones; monitorear costos de flete refrigerado."
]
k = int(time.time()//30) % len(news)
st.markdown(f"""
<div class='tape-news'><div class='tape-news-track'>
  <div class='tape-news-group'><span class='item'>{news[k]}</span></div>
  <div class='tape-news-group' aria-hidden='true'><span class='item'>{news[k]}</span></div>
</div></div>
""", unsafe_allow_html=True)

# ========= PIE + RERUN =========
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True
)

time.sleep(60)
st.rerun()
