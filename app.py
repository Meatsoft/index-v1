# app.py — LaSultana Meat Index (KPIs delgados + 2 pechugas + ajustes de cintas)
import os, json, re, time, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ========= ESTILOS =========
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
/* Oculta el widget de estado para minimizar parpadeo visual del auto-rerun */
div[data-testid="stStatusWidget"]{display:none!important}

/* Tarjetas / KPIs (25% más delgados) */
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

/* Cinta bursátil (superior) */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:14px}
.tape-track{display:flex;width:max-content;animation:marquee 210s linear infinite;will-change:transform}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
.up{color:var(--up)} .down{color:var(--down)} .muted{color:var(--muted)}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* Cinta de noticias (inferior) — ~29% más rápida ≈ 110s + 5% extra ya aplicado */
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 14px}
.tape-news-track{display:flex;width:max-content;animation:marqueeNews 110s linear infinite;will-change:transform}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNews{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}

/* Badge con 60% menos padding vertical */
.badge{
  display:inline-block;
  padding:1px 8px;           /* antes 3px 8px */
  border:1px solid var(--line);
  border-radius:8px;
  color:var(--muted);
  font-size:12px;
  line-height:1.1;
  vertical-align:middle;
  margin-left:8px;
}

/* Micro-padding (abajo) para el encabezado de Piezas de Pollo */
.section-title{font-size:20px;color:var(--txt);margin:0 0 6px 0}  /* << tantitito padding abajo */
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

# ========= CINTA BURSÁTIL (filtra a USD y maneja delistados) =========
RAW_COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("JBS","JBS"), ("BRF","BRFS"),
    ("Hormel Foods","HRL"), ("Seaboard","SEB"), ("Minerva","MRVSY"), ("Marfrig","MRRTY"),
    ("Maple Leaf Foods","MFI.TO"), ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("Grupo KUO","KUOB.MX"), ("Grupo Bafar","BAFARB.MX"),
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
        # Filtra por divisa USD
        cur = None
        try:
            cur = (t.fast_info or {}).get("currency", None)
        except Exception:
            pass
        if not cur:
            try:
                cur = (t.info or {}).get("currency", None)
            except Exception:
                pass
        if cur != "USD":
            return None  # descarta si no es USD

        # Último precio con cadena de respaldos
        last, chg = None, None
        try:
            fi = t.fast_info or {}
            lp = fi.get("last_price", None)
            pc = fi.get("previous_close", None)
            if lp is not None:
                last = float(lp)
                chg = (float(lp) - float(pc)) if pc is not None else None
        except Exception:
            pass

        if last is None:
            try:
                inf = t.info or {}
                lp = inf.get("regularMarketPrice", None)
                pc = inf.get("regularMarketPreviousClose", None)
                if lp is not None:
                    last = float(lp)
                    chg = (float(lp) - float(pc)) if pc is not None else None
            except Exception:
                pass

        if last is None:
            d = t.history(period="10d", interval="1d")
            if d is not None and not d.empty:
                c = d["Close"].dropna()
                if not c.empty:
                    last = float(c.iloc[-1])
                    chg = (last - float(c.iloc[-2])) if c.shape[0] >= 2 else None

        if last is None:
            return None
        return {"name": name, "sym": sym, "last": last, "chg": chg}
    except Exception:
        return None

@st.cache_data(ttl=75)
def build_ticker_line():
    items = []
    for n, s in RAW_COMPANIES:
        q = quote_usd_only(n, s)
        if not q:
            continue
        if q["chg"] is None:
            items.append(f"<span class='item'>{q['name']} ({q['sym']}) <b>{q['last']:.2f}</b></span>")
        else:
            cls = "up" if q["chg"] >= 0 else "down"
            arr = "▲" if q["chg"] >= 0 else "▼"
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

# ========= COTIZACIONES PRINCIPALES =========
@st.cache_data(ttl=75)
def get_last_from_yahoo(symbol: str):
    """Regresa (last, chg) con cadena de respaldos sin inventar."""
    try:
        t = yf.Ticker(symbol)
        # fast_info
        try:
            fi = t.fast_info or {}
            lp = fi.get("last_price", None)
            pc = fi.get("previous_close", None)
            if lp is not None:
                lp = float(lp)
                return lp, (lp - float(pc)) if pc is not None else None
        except Exception:
            pass
        # info
        try:
            inf = t.info or {}
            lp = inf.get("regularMarketPrice", None)
            pc = inf.get("regularMarketPreviousClose", None)
            if lp is not None:
                lp = float(lp)
                return lp, (lp - float(pc)) if pc is not None else None
        except Exception:
            pass
        # history
        d = t.history(period="10d", interval="1d")
        if d is not None and not d.empty:
            c = d["Close"].dropna()
            if not c.empty:
                last = float(c.iloc[-1])
                prev = float(c.iloc[-2]) if c.shape[0] >= 2 else None
                return last, (last - prev) if prev is not None else None
        return None, None
    except Exception:
        return None, None

# USD/MXN desde Yahoo
fx, fx_chg   = get_last_from_yahoo("MXN=X")
# Futuros CME
lc, lc_chg   = get_last_from_yahoo("LE=F")  # Live Cattle
lh, lh_chg   = get_last_from_yahoo("HE=F")  # Lean Hogs

def kpi_card(title: str, price, chg, unit: str|None):
    if price is None:
        price_html = f"<div class='big'>N/D{f' <span class=\"unit-inline\">{unit}</span>' if unit else ''}</div>"
        delta_html = ""
    else:
        if chg is None:
            price_html = f"<div class='big'>{fmt2(price)}{f' <span class=\"unit-inline\">{unit}</span>' if unit else ''}</div>"
            delta_html = ""
        else:
            cls  = "up" if chg >= 0 else "down"
            arr  = "▲" if chg >= 0 else "▼"
            price_html = f"<div class='big'>{fmt2(price)}{f' <span class=\"unit-inline\">{unit}</span>' if unit else ''}</div>"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""
    <div class="card"><div class="kpi">
      <div><div class="title">{title}</div>{price_html}</div>{delta_html}
    </div></div>
    """

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(kpi_card("USD/MXN",   fx, fx_chg, None),            unsafe_allow_html=True)
st.markdown(kpi_card("Res en pie", lc, lc_chg, "USD/100 lb"),   unsafe_allow_html=True)
st.markdown(kpi_card("Cerdo en pie", lh, lh_chg, "USD/100 lb"), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ========= USDA — 2 PECHUGAS COMO KPI =========
POULTRY_URLS = [
    "https://www.ams.usda.gov/mnreports/aj_py018.txt",
    "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
    "https://www.ams.usda.gov/mnreports/py018.txt",
    "https://www.ams.usda.gov/mnreports/PY018.txt",
]
HDR = {"User-Agent": "Mozilla/5.0"}
PECH_PAT = {
    "Pechuga B/S":             [r"BREAST\s*-\s*B/?S(?!.*JUMBO)", r"BREAST,\s*B/?S(?!.*JUMBO)"],
    "Pechuga T/S (strapless)": [r"BREAST\s*T/?S", r"STRAPLESS"],
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
    for url in POULTRY_URLS:
        try:
            r = requests.get(url, timeout=12, headers=HDR)
            if r.status_code != 200:
                continue
            if "<html" in r.text.lower():
                continue
            lines = [ln.strip() for ln in r.text.splitlines() if ln.strip()]
            out = {}
            for disp, pats in PECH_PAT.items():
                for ln in lines:
                    U = ln.upper()
                    if any(re.search(p, U) for p in pats):
                        v = _avg(U)
                        if v is not None:
                            out[disp] = v
                            break
            if out:
                return out
        except Exception:
            continue
    return {}

SNAP = "poultry_last_pechugas.json"
def load_snap():
    if not os.path.exists(SNAP): return {}
    try:
        with open(SNAP, "r") as f: return json.load(f)
    except Exception:
        return {}
def save_snap(d: dict):
    try:
        with open(SNAP, "w") as f: json.dump({k: float(v) for k,v in d.items()}, f)
    except Exception:
        pass

def pechugas_with_snapshot():
    cur = fetch_pechugas()
    prev = load_snap()
    seeded = False
    if cur:
        res = {}
        for k,v in cur.items():
            pv = prev.get(k, None)
            if isinstance(pv, dict): pv = pv.get("price")
            dlt = 0.0 if pv is None else (float(v) - float(pv))
            res[k] = {"price": float(v), "delta": float(dlt)}
        save_snap(cur)
        if not prev: seeded = True
        return res, False, seeded
    if prev:
        res = {k: {"price": float((v.get("price") if isinstance(v,dict) else v)), "delta": 0.0}
               for k,v in prev.items()}
        return res, True, False
    base = {k: {"price": None, "delta": 0.0} for k in PECH_PAT.keys()}
    return base, True, False

pech, stale, seeded = pechugas_with_snapshot()

def kpi_pechuga(nombre: str, info: dict) -> str:
    price = info.get("price")
    delta = info.get("delta", 0.0)
    unit = "USD/lb"
    if price is None:
        price_html = f"<div class='big'>— <span class='unit-inline'>{unit}</span></div>"
        delta_html = ""
    else:
        cls = "up" if (delta or 0) >= 0 else "down"
        arr = "▲" if (delta or 0) >= 0 else "▼"
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

# ========= PIE + AUTOREFRESH SUAVE =========
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True
)

# Re-run programático cada 60s (se oculta el widget de estado para minimizar el 'blink')
time.sleep(60)
st.rerun()
