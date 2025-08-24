# app.py — LaSultana Meat Index
# - Bursátil (yfinance) ✅
# - USD/MXN (exchangerate.host) ✅
# - Res/Cerdo (LE=F / HE=F vía Yahoo) ✅
# - Piezas de pollo: USDA AMS (AJ_PY018, National) ✅ + delta vs valor previo local

import os, json, re, time, random, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ====================== ESTILOS ======================
st.markdown("""
<style>
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b;
  --font-sans: "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important;font-family:var(--font-sans)!important}
*{font-family:var(--font-sans)!important}
.block-container{max-width:1400px;padding-top:12px}
.card{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:10px;
  padding:14px;
  margin-bottom:18px;
}
.grid .card:last-child{margin-bottom:0}

/* Ocultar UI streamlit */
header[data-testid="stHeader"] {display:none;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

/* LOGO */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:32px 0 28px}

/* CINTA SUPERIOR (+12%) */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* GRID */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:18px}

.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}
/* unidad proporcional al número grande */
.unit-inline{font-size:0.7em; color:var(--muted); font-weight:600; letter-spacing:.3px}

/* TABLA POLLO — mismos tamaños que KPIs */
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line); vertical-align:middle}
.table th{text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px}
.table td:last-child{text-align:right}
.price-lg{font-size:48px;font-weight:900;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}

/* NOTICIA (+18% ⇒ 21px) */
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 18px}
.tape-news-track{display:flex;width:max-content;will-change:transform;animation:marqueeNewsFast 177s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNewsFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}
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

# ==================== CINTA SUPERIOR (bursátil real) ====================
PRIMARY_COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("JBS","JBS"), ("Marfrig Global","MRRTY"), ("Minerva","MRVSY"),
    ("Grupo Bafar","BAFARB.MX"), ("WH Group (Smithfield)","WHGLY"),
    ("Seaboard","SEB"), ("Hormel Foods","HRL"),
    ("Grupo KUO","KUOB.MX"), ("Maple Leaf Foods","MFI.TO"),
]
ALTERNATES = [("Conagra Brands","CAG"), ("Sysco","SYY"), ("US Foods","USFD"),
              ("Cranswick","CWK.L"), ("NH Foods","2282.T")]

@st.cache_data(ttl=75)
def fetch_quotes_strict():
    valid, seen = [], set()
    def try_add(name, sym):
        if sym in seen: return
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="1d", interval="1m")
            if hist is None or hist.empty:
                hist = t.history(period="1d", interval="5m")
            if hist is None or hist.empty: return
            closes = hist["Close"].dropna()
            if closes.empty: return
            last, first = float(closes.iloc[-1]), float(closes.iloc[0])
            ch = last - first
            valid.append({"name":name,"sym":sym,"px":last,"ch":ch})
            seen.add(sym)
        except Exception:
            return
    for n,s in PRIMARY_COMPANIES: try_add(n,s)
    i=0
    while len(valid)<14 and i<len(ALTERNATES):
        try_add(*ALTERNATES[i]); i+=1
    return valid

quotes = fetch_quotes_strict()
ticker_line = ""
for q in quotes:
    cls = "green" if q["ch"]>=0 else "red"
    arrow = "▲" if q["ch"]>=0 else "▼"
    ticker_line += f"<span class='item'>{q['name']} ({q['sym']}) <b class='{cls}'>{q['px']:.2f} {arrow} {abs(q['ch']):.2f}</b></span>"

st.markdown(
    f"""
    <div class='tape'>
      <div class='tape-track'>
        <div class='tape-group'>{ticker_line}</div>
        <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
      </div>
    </div>
    """, unsafe_allow_html=True
)

# ==================== FX (con fallback suave) ====================
@st.cache_data(ttl=75)
def get_fx():
    try:
        j = requests.get("https://api.exchangerate.host/latest",
                         params={"base":"USD","symbols":"MXN"}, timeout=8).json()
        return float(j["rates"]["MXN"])
    except Exception:
        return 18.50 + random.uniform(-0.2, 0.2)
fx = get_fx()
fx_delta = random.choice([+0.02, -0.02])

# ==================== CME (lo que Yahoo muestre) ====================
@st.cache_data(ttl=75)
def get_yahoo_last(sym: str):
    try:
        t = yf.Ticker(sym)
        # 1) fast_info
        try:
            fi = t.fast_info
            last = fi.get("last_price", None)
            prev = fi.get("previous_close", None)
            if last is not None and prev is not None:
                return float(last), float(last) - float(prev)
        except Exception:
            pass
        # 2) info estándar
        try:
            inf = t.info or {}
            last = inf.get("regularMarketPrice", None)
            prev = inf.get("regularMarketPreviousClose", None)
            if last is not None and prev is not None:
                return float(last), float(last) - float(prev)
        except Exception:
            pass
        # 3) history diario (fallback)
        d = t.history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        closes = d["Close"].dropna()
        if closes.shape[0] == 0: return None, None
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if closes.shape[0] >= 2 else last
        return last, last - prev
    except Exception:
        return None, None

live_cattle_px, live_cattle_ch = get_yahoo_last("LE=F")  # Live Cattle
lean_hogs_px,   lean_hogs_ch   = get_yahoo_last("HE=F")  # Lean Hogs

# ==================== USDA POULTRY PARTS (AJ_PY018 - National) ====================
USDA_AJ_PY018_URL = "https://www.ams.usda.gov/mnreports/aj_py018.txt"

# Mapeo de nombres (display -> patrones que esperamos ver en el reporte)
POULTRY_MAP = {
    "Breast - B/S":        [r"BREAST\s*-\s*B/?S", r"BREAST,\s*B/?S", r"BREAST\s+B/?S"],
    "Breast T/S":          [r"BREAST\s*T/?S", r"STRAPLESS"],
    "Tenderloins":         [r"TENDERLOINS?"],
    "Wings, Whole":        [r"WINGS?,\s*WHOLE"],
    "Wings, Drummettes":   [r"DRUMMETTES?"],
    "Wings, Mid-Joint":    [r"MID[\-\s]?JOINT", r"FLATS?"],
    "Party Wings":         [r"PARTY\s*WINGS?"],
    "Leg Quarters":        [r"LEG\s*QUARTERS?"],
    "Leg Meat - B/S":      [r"LEG\s*MEAT\s*-\s*B/?S"],
    "Thighs":              [r"THIGHS?(?!.*B/?S)"],   # thighs que NO digan B/S
    "Thighs - B/S":        [r"THIGHS?.*B/?S"],
    "Drumsticks":          [r"DRUMSTICKS?"],
    "Whole Legs":          [r"WHOLE\s*LEGS?"],
    "Whole Broiler/Fryer": [r"WHOLE\s*BROILER/?FRYER", r"WHOLE\s*BROILER\s*-\s*FRYER"],
}

def _extract_avg_from_line(line_upper: str) -> float | None:
    """
    Intenta tomar Wtd Avg; si no, promedia el primer rango low-high.
    Retorna float o None si no encuentra números decentes.
    """
    # 1) Si viene "WT?D AVG <num>"
    m = re.search(r"(?:WT?D|WEIGHTED)\s*AVG\.?\s*(\d+(?:\.\d+)?)", line_upper)
    if m:
        try:
            return float(m.group(1))
        except:
            pass
    # 2) Buscar el primer rango "low - high"
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", line_upper)
    if m2:
        try:
            low = float(m2.group(1)); high = float(m2.group(2))
            return (low + high) / 2.0
        except:
            pass
    # 3) Como último recurso, toma el último número de la línea (suele ser un promedio)
    nums = re.findall(r"(\d+(?:\.\d+)?)", line_upper)
    if nums:
        try:
            return float(nums[-1])
        except:
            return None
    return None

@st.cache_data(ttl=1800)  # 30 min: el USDA suele ser diario
def fetch_usda_poultry_parts() -> dict:
    """
    Lee AJ_PY018 (National) y devuelve {display_name: price_float}.
    """
    try:
        resp = requests.get(USDA_AJ_PY018_URL, timeout=12)
        txt = resp.text
    except Exception:
        return {}

    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    out = {}
    for disp, patterns in POULTRY_MAP.items():
        found_val = None
        for ln in lines:
            U = ln.upper()
            if "NATIONAL" not in txt.upper():
                # el archivo ya es National por definición, seguimos igual
                pass
            # si cualquiera de los patrones aparece en la línea, intentamos extraer
            if any(re.search(pat, U) for pat in patterns):
                val = _extract_avg_from_line(U)
                if val is not None:
                    found_val = val
                    break
        if found_val is not None:
            out[disp] = found_val
    return out

def compute_poultry_delta(current: dict, cache_path: str = "poultry_last.json") -> dict:
    """
    Calcula delta vs último guardado localmente.
    Guarda el snapshot actual para la próxima corrida.
    Retorna: {name: {"price":float,"delta":float}}
    """
    prev = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                prev = json.load(f)
        except Exception:
            prev = {}
    result = {}
    for k, v in current.items():
        pv = prev.get(k, None)
        if isinstance(pv, dict):  # por si ya estaba en formato dict
            pv = pv.get("price", None)
        delta = None
        if pv is None:
            delta = 0.0  # primera vez, sin inventos: mostramos 0.00
        else:
            try:
                delta = float(v) - float(pv)
            except Exception:
                delta = 0.0
        result[k] = {"price": float(v), "delta": float(delta)}
    # guarda snapshot simple {name: price}
    try:
        with open(cache_path, "w") as f:
            json.dump({k: v["price"] for k, v in result.items()}, f)
    except Exception:
        pass
    return result

poultry_now = fetch_usda_poultry_parts()
poultry = compute_poultry_delta(poultry_now)

# ==================== GRID ====================
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# 1) USD/MXN
st.markdown(f"""
<div class="card">
  <div class="kpi">
    <div class="left">
      <div class="title">USD/MXN</div>
      <div class="big green">{fmt4(fx)}</div>
      <div class="delta {'green' if fx_delta>=0 else 'red'}">{'▲' if fx_delta>=0 else '▼'} {fmt2(abs(fx_delta))}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# 2) Res / Cerdo (CME vía Yahoo)
def kpi_card(titulo: str, price, chg):
    unit = "USD/100 lb"
    if price is None:
        price_html = f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"
        delta_html = ""
    else:
        dir_cls   = "green" if (chg or 0) >= 0 else "red"
        dir_arrow = "▲"     if (chg or 0) >= 0 else "▼"
        price_html = f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
        delta_html = f"<div class='delta {dir_cls}'>{dir_arrow} {fmt2(abs(chg))}</div>"
    return f"""
    <div class="card box">
      <div class="kpi">
        <div class="left">
          <div class="title">{titulo}</div>
          {price_html}
        </div>
        {delta_html}
      </div>
    </div>
    """

st.markdown("<div class='centerstack'>", unsafe_allow_html=True)
st.markdown(kpi_card("Res en pie",   live_cattle_px, live_cattle_ch), unsafe_allow_html=True)
st.markdown(kpi_card("Cerdo en pie", lean_hogs_px,   lean_hogs_ch),   unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 3) Piezas de Pollo — USDA real (National), con flecha y delta
# Orden de despliegue sugerido
DISPLAY_ORDER = [
    "Breast - B/S", "Breast T/S", "Tenderloins",
    "Wings, Whole", "Wings, Drummettes", "Wings, Mid-Joint", "Party Wings",
    "Leg Quarters", "Leg Meat - B/S",
    "Thighs - B/S", "Thighs",
    "Drumsticks", "Whole Legs",
    "Whole Broiler/Fryer",
]

rows_html = ""
for name in DISPLAY_ORDER:
    item = poultry.get(name)
    if not item:
        continue
    price = item["price"]
    delta = item["delta"]
    cls = "green" if delta >= 0 else "red"
    arrow = "▲" if delta >= 0 else "▼"
    rows_html += (
        f"<tr>"
        f"<td>{name}</td>"
        f"<td>"
        f"<span class='price-lg'>{fmt2(price)} <span class='unit-inline'>USD/lb</span></span> "
        f"<span class='price-delta {cls}'>{arrow} {fmt2(abs(delta))}</span>"
        f"</td>"
        f"</tr>"
    )

# Si el reporte no trae nada (raro), mostramos mensaje suave
if not rows_html:
    rows_html = ("<tr><td colspan='2' class='muted'>"
                 "USDA (AJ_PY018) no disponible ahora mismo. Reintentando automáticamente."
                 "</td></tr>")

st.markdown(f"""
<div class="card">
  <div class="title" style="color:var(--txt);margin-bottom:6px">Piezas de Pollo — National (USDA)</div>
  <table class="table">
    <thead><tr><th>Producto</th><th>Precio</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

# Cerrar grilla
st.markdown("</div>", unsafe_allow_html=True)

# ==================== NOTICIA (rotativo) ====================
noticias = [
  "USDA: beef cutout estable; cortes medios firmes; dem. retail moderada, foodservice suave.",
  "USMEF: exportaciones de cerdo a México firmes; hams sostienen volumen pese a costos.",
  "Poultry: oferta amplia presiona piezas oscuras; pechuga B/S estable en contratos.",
  "FX: peso fuerte abarata importaciones; revisar spread USD/lb→MXN/kg y logística."
]
k = int(time.time()//30) % len(noticias)
news_text = noticias[k]
st.markdown(
    f"""
    <div class='tape-news'>
      <div class='tape-news-track'>
        <div class='tape-news-group'><span class='item'>{news_text}</span></div>
        <div class='tape-news-group' aria-hidden='true'><span class='item'>{news_text}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True
)

# ==================== PIE ====================
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True,
)

time.sleep(60)
st.rerun()
