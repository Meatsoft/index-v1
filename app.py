# app.py — LaSultana Meat Index (2 pechugas + USD tickers limpios + JK_PY001)
import os, json, re, time, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")
try:
    st.cache_data.clear()
except:
    pass

# ====================== ESTILOS ======================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700&display=swap');
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b; --font:"Manrope","Inter","Segoe UI",Roboto,Arial,sans-serif;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important;font-family:var(--font)!important}
*{font-family:var(--font)!important}
.block-container{max-width:1400px;padding-top:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:18px}
header[data-testid="stHeader"]{display:none;} #MainMenu{visibility:hidden;} footer{visibility:hidden}

/* Logo */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:26px 0 22px}

/* Cinta bursátil */
.tape{border:1px solid var(--line);border-radius:12px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{
  display:flex;width:max-content;animation:marquee 210s linear infinite;
  will-change:transform;backface-visibility:hidden;transform:translateZ(0);
}
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

/* === Tabla de pollo (un solo marco, esquinas limpias) === */
.card.pechugas{border:1px solid var(--line);border-radius:12px;overflow:hidden;padding:0;margin-bottom:18px}
.pechugas table{width:100%;border-collapse:separate;border-spacing:0;margin:0}
.pechugas th,.pechugas td{
  padding:12px 14px; vertical-align:middle;
  border-bottom:1px solid var(--line)!important;
  border-left:0!important;border-right:0!important;border-top:0!important;
}
.pechugas thead th{
  text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px;
  border-bottom:1px solid var(--line)!important;
}
.pechugas tbody tr:last-child td{
  border-bottom:0!important;
  padding-bottom:10px;
}
.pechugas td:first-child{font-size:110%}
.pechugas td:last-child{text-align:right}
.price-lg{font-size:48px;font-weight:900;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}
.unit-inline--p{font-size:.60em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* Noticias (22% más rápida + anti-ghosting) */
.tape-news{border:1px solid var(--line);border-radius:12px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 18px}
.tape-news-track{
  display:flex;width:max-content;animation:marqueeNews 117s linear infinite;
  will-change:transform;backface-visibility:hidden;transform:translateZ(0);
}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px;line-height:28px}
@keyframes marqueeNews{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}
.badge{display:inline-block;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;margin-left:8px}
</style>
""",
    unsafe_allow_html=True,
)

# ==================== HELPERS ====================
def fmt2(x: float | None) -> str:
    if x is None:
        return "—"
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def fmt4(x: float | None) -> str:
    if x is None:
        return "—"
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ==================== LOGO ====================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== CINTA SUPERIOR (solo USD sólidos) ====================
# Si no hay datos del ticker, se omite (no se muestra en gris)
COMPANIES_USD = [
    ("Tyson Foods","TSN"),
    ("Pilgrim’s Pride","PPC"),
    ("JBS","JBS"),
    ("BRF","BRFS"),
    ("Hormel Foods","HRL"),
    ("Seaboard","SEB"),
    ("Minerva","MRVSY"),          # OTC USD
    ("Marfrig","MRRTY"),          # si no hay datos, se omite
    ("Cal-Maine Foods","CALM"),
    ("Vital Farms","VITL"),
    ("WH Group","WHGLY"),         # OTC USD
    ("Wingstop","WING"),
    ("Yum! Brands","YUM"),
    ("Restaurant Brands Intl.","QSR"),
    ("Sysco","SYY"),
    ("US Foods","USFD"),
    ("Performance Food Group","PFGC"),
    ("Walmart","WMT"),
]

@st.cache_data(ttl=75)
def quote_last_and_change(sym: str):
    try:
        t = yf.Ticker(sym)
        fi = t.fast_info
        last = fi.get("last_price", None)
        prev = fi.get("previous_close", None)
        if last is not None:
            ch = (float(last) - float(prev)) if prev is not None else None
            return float(last), ch
    except Exception:
        pass
    try:
        inf = yf.Ticker(sym).info or {}
        last = inf.get("regularMarketPrice", None)
        prev = inf.get("regularMarketPreviousClose", None)
        if last is not None:
            ch = (float(last) - float(prev)) if prev is not None else None
            return float(last), ch
    except Exception:
        pass
    try:
        d = yf.Ticker(sym).history(period="10d", interval="1d")
        if d is None or d.empty:
            return None, None
        c = d["Close"].dropna()
        last = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if c.shape[0] >= 2 else None
        ch = (last - prev) if prev is not None else None
        return last, ch
    except Exception:
        return None, None

items = []
for name, sym in COMPANIES_USD:
    last, chg = quote_last_and_change(sym)
    if last is None:
        continue
    if chg is None:
        items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
    else:
        cls = "up" if chg >= 0 else "down"
        arr = "▲" if chg >= 0 else "▼"
        items.append(f"<span class='item'>{name} ({sym}) <b class='{cls}'>{last:.2f} {arr} {abs(chg):.2f}</b></span>")

ticker_line = "".join(items)
st.markdown(
    f"""
    <div class='tape'>
      <div class='tape-track'>
        <div class='tape-group'>{ticker_line}</div>
        <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==================== FX & FUTUROS (Yahoo) ====================
@st.cache_data(ttl=75)
def get_yahoo(sym: str):
    return quote_last_and_change(sym)

fx, fx_chg = get_yahoo("MXN=X")  # USD/MXN (MXN por 1 USD)
lc, lc_chg = get_yahoo("LE=F")   # Live Cattle
lh, lh_chg = get_yahoo("HE=F")   # Lean Hogs

def kpi_fx(title: str, value: float | None, chg: float | None) -> str:
    if value is None:
        val_html = "<div class='big'>N/D</div>"
        delta_html = ""
    else:
        val_html = f"<div class='big'>{fmt4(value)}</div>"
        if chg is None:
            delta_html = ""
        else:
            cls = "up" if chg >= 0 else "down"
            arr = "▲" if chg >= 0 else "▼"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""
    <div class="card">
      <div class="kpi">
        <div><div class="title">{title}</div>{val_html}</div>{delta_html}
      </div>
    </div>
    """

def kpi_cme(title: str, price: float | None, chg: float | None) -> str:
    unit = "USD/100 lb"
    if price is None:
        price_html = f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"
        delta_html = ""
    else:
        price_html = f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
        if chg is None:
            delta_html = ""
        else:
            cls = "up" if chg >= 0 else "down"
            arr = "▲" if chg >= 0 else "▼"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""
    <div class="card">
      <div class="kpi">
        <div><div class="title">{title}</div>{price_html}</div>{delta_html}
      </div>
    </div>
    """

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(kpi_fx("USD/MXN", fx, fx_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Res en pie", lc, lc_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Cerdo en pie", lh, lh_chg), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== USDA POULTRY (B/S y T/S con JK_PY001 + respaldo AJ_PY018) ====================
POULTRY_URLS = [
    # 1) Atlanta Daily Broiler/Fryer Parts (USDA AMS): suele traer Wtd Avg de B/S y T/S
    "https://www.ams.usda.gov/mnreports/jk_py001.txt",
    "https://www.ams.usda.gov/mnreports/JK_PY001.txt",
    "https://mymarketnews.ams.usda.gov/filerepo/JK_PY001.TXT",
    # 2) Respaldo: a veces no tiene B/S o T/S
    "https://www.ams.usda.gov/mnreports/aj_py018.txt",
    "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
    "https://www.ams.usda.gov/mnreports/py018.txt",
    "https://www.ams.usda.gov/mnreports/PY018.txt",
]
HDR = {"User-Agent": "Mozilla/5.0"}

PECH_PATTERNS = {
    "Pechuga B/S": [r"BREAST\s*-\s*B/?S(?!.*JUMBO)", r"BREAST,\s*B/?S(?!.*JUMBO)"],
    "Pechuga T/S (strapless)": [r"BREAST\s*T/?S", r"STRAPLESS"],
}

def _extract_avg(U: str) -> float | None:
    # Captura "WTD AVG", "WTD. AVG", "WEIGHTED AVG", y si no, el último número de un rango 123.45 - 125.00
    m = re.search(r"(?:WT?D|WEIGHTED)\s*AVG\.?\s*(\d+(?:\.\d+)?)", U)
    if m:
        try:
            return float(m.group(1))
        except:
            pass
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", U)
    if m2:
        try:
            return (float(m2.group(1)) + float(m2.group(2))) / 2.0
        except:
            pass
    nums = re.findall(r"(\d+(?:\.\d+)?)", U)
    if nums:
        try:
            return float(nums[-1])
        except:
            return None
    return None

@st.cache_data(ttl=1800)
def fetch_usda_pechugas() -> dict:
    for url in POULTRY_URLS:
        try:
            r = requests.get(url, timeout=12, headers=HDR)
            if r.status_code != 200:
                continue
            txt = r.text
            if "<html" in txt.lower():
                # evita proxys/redirects que regresan HTML
                continue
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            out = {}
            for disp, pats in PECH_PATTERNS.items():
                for ln in lines:
                    U = ln.upper()
                    if any(re.search(p, U) for p in pats):
                        v = _extract_avg(U)
                        if v is not None:
                            out[disp] = v
                            break
            if out:
                return out
        except Exception:
            continue
    return {}

SNAP = "poultry_last_minimal.json"

def load_snap() -> dict:
    if not os.path.exists(SNAP):
        return {}
    try:
        with open(SNAP, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_snap(data: dict):
    try:
        with open(SNAP, "w") as f:
            json.dump({k: float(v) for k, v in data.items()}, f)
    except Exception:
        pass

def get_pechugas_with_snapshot():
    cur = fetch_usda_pechugas()
    prev = load_snap()
    seeded = False
    if cur:
        res = {}
        for k, v in cur.items():
            pv = prev.get(k, None)
            if isinstance(pv, dict):
                pv = pv.get("price")
            dlt = 0.0 if pv is None else (float(v) - float(pv))
            res[k] = {"price": float(v), "delta": float(dlt)}
        save_snap(cur)
        if not prev:
            seeded = True
        return res, False, seeded
    if prev:
        res = {
            k: {"price": float((v.get("price") if isinstance(v, dict) else v)), "delta": 0.0}
            for k, v in prev.items()
        }
        return res, True, False
    # Primera corrida sin snapshot ni fetch
    return {k: {"price": None, "delta": 0.0} for k in PECH_PATTERNS.keys()}, True, False

pech, stale, seeded = get_pechugas_with_snapshot()

order = ["Pechuga B/S", "Pechuga T/S (strapless)"]
rows = []
for name in order:
    it = pech.get(name, {"price": None, "delta": 0.0})
    price, delta = it["price"], it["delta"]
    cls = "up" if (delta or 0) >= 0 else "down"
    arr = "▲" if (delta or 0) >= 0 else "▼"
    price_txt = fmt2(price) if price is not None else "—"
    delta_txt = f"{arr} {fmt2(abs(delta))}" if price is not None else "—"
    rows.append(
        f"<tr><td>{name}</td>"
        f"<td><span class='price-lg'>{price_txt} <span class='unit-inline--p'>USD/lb</span></span> "
        f"<span class='price-delta {cls}'>{delta_txt}</span></td></tr>"
    )

badge = " <span class='badge'>último disponible</span>" if stale else (
    " <span class='badge'>actualizado</span>" if seeded else "")

st.markdown(
    f"""
<div class="card pechugas">
  <div class="title" style="color:var(--txt);margin:12px 14px 6px 14px">
    Piezas de Pollo, U.S. National (USDA){badge}
  </div>
  <table>
    <thead><tr><th>Producto</th><th>Precio</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>
""",
    unsafe_allow_html=True,
)

# ==================== NOTICIAS (cinta inferior) ====================
noticias = [
  "MXN/Kg y logística.",
  "Pechuga B/S y T/S estables; revisar spreads USD/lb → MXN/kg y logística.",
  "USDA: beef cutout estable; cortes medios firmes; demanda retail moderada.",
  "USMEF: exportaciones de cerdo a México firmes; hams sostienen volumen."
]
k = int(time.time() // 30) % len(noticias)
news_text = noticias[k]
st.markdown(
    f"""
    <div class='tape-news'>
      <div class='tape-news-track'>
        <div class='tape-news-group'><span class='item'>{news_text}</span></div>
        <div class='tape-news-group' aria-hidden='true'><span class='item'>{news_text}</span></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==================== PIE ====================
st.markdown(
    f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · "
    "Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
    unsafe_allow_html=True,
)

# ==================== REFRESCO SUAVE (sin parpadeo) ====================
st.autorefresh(interval=60_000, key="autor")
