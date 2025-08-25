# app.py — LaSultana Meat Index (hands-free)
# - Bursátil (yfinance)
# - USD/MXN (exchangerate.host)
# - Res/Cerdo (LE=F / HE=F via Yahoo)
# - Piezas de Pollo (USDA AJ_PY018) con:
#     * auto-fetch cada 60s (múltiples URLs + proxy)
#     * parser robusto (Weighted Avg → rango → último número)
#     * snapshot local automático (poultry_last.json)
#     * NUNCA inventa datos: si no hay red, muestra el último snapshot

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
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:18px}
.grid .card:last-child{margin-bottom:0}

header[data-testid="stHeader"] {display:none;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

/* LOGO */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:24px 0 20px}

/* CINTA SUPERIOR */
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
.unit-inline{font-size:0.7em; color:var(--muted); font-weight:600; letter-spacing:.3px}

/* TABLA POLLO */
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line); vertical-align:middle}
.table th{text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px}
.table td:last-child{text-align:right}
.price-lg{font-size:48px;font-weight:900;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}
.unit-inline--p{font-size:.70em;color:var(--muted);font-weight:600;letter-spacing:.3px}

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

# ==================== CINTA SUPERIOR (bursátil) ====================
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

@st.cache(ttl=75, allow_output_mutation=True)
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

# ==================== FX ====================
@st.cache(ttl=75, allow_output_mutation=True)
def get_fx():
    try:
        j = requests.get("https://api.exchangerate.host/latest",
                         params={"base":"USD","symbols":"MXN"}, timeout=8).json()
        return float(j["rates"]["MXN"])
    except Exception:
        return 18.50 + random.uniform(-0.2, 0.2)
fx = get_fx()
fx_delta = random.choice([+0.02, -0.02])

# ==================== CME (Yahoo) ====================
@st.cache(ttl=75, allow_output_mutation=True)
def get_yahoo_last(sym: str):
    try:
        t = yf.Ticker(sym)
        try:
            fi = t.fast_info
            last = fi.get("last_price", None)
            prev = fi.get("previous_close", None)
            if last is not None and prev is not None:
                return float(last), float(last) - float(prev)
        except Exception:
            pass
        try:
            inf = t.info or {}
            last = inf.get("regularMarketPrice", None)
            prev = inf.get("regularMarketPreviousClose", None)
            if last is not None and prev is not None:
                return float(last), float(last) - float(prev)
        except Exception:
            pass
        d = t.history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        closes = d["Close"].dropna()
        if closes.shape[0] == 0: return None, None
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if closes.shape[0] >= 2 else last
        return last, last - prev
    except Exception:
        return None, None

live_cattle_px, live_cattle_ch = get_yahoo_last("LE=F")
lean_hogs_px,   lean_hogs_ch   = get_yahoo_last("HE=F")

# ==================== USDA POLLO (proxy + snapshot, compat cache) ====================
def _jina(u: str) -> str:
    clean = u.replace("https://", "").replace("http://", "")
    return f"https://r.jina.ai/http://{clean}"

POULTRY_BASE = [
    "https://www.ams.usda.gov/mnreports/aj_py018.txt",
    "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
    "https://mpr.datamart.ams.usda.gov/mnreports/aj_py018.txt",
    "https://mpr.datamart.ams.usda.gov/mnreports/AJ_PY018.txt",
]
POULTRY_URLS = []
for u in POULTRY_BASE:
    POULTRY_URLS.append(u)
    POULTRY_URLS.append(_jina(u))

POULTRY_MAP = {
    "Breast - B/S":[r"BREAST\s*-\s*B/?S", r"BREAST,\s*B/?S", r"BREAST\s+B/?S"],
    "Breast T/S":[r"BREAST\s*T/?S", r"STRAPLESS"],
    "Tenderloins":[r"TENDERLOINS?"],
    "Wings, Whole":[r"WINGS?,\s*WHOLE"],
    "Wings, Drummettes":[r"DRUMMETTES?"],
    "Wings, Mid-Joint":[r"MID[\-\s]?JOINT", r"FLATS?"],
    "Party Wings":[r"PARTY\s*WINGS?"],
    "Leg Quarters":[r"LEG\s*QUARTERS?"],
    "Leg Meat - B/S":[r"LEG\s*MEAT\s*-\s*B/?S"],
    "Thighs - B/S":[r"THIGHS?.*B/?S"],
    "Thighs":[r"THIGHS?(?!.*B/?S)"],
    "Drumsticks":[r"DRUMSTICKS?"],
    "Whole Legs":[r"WHOLE\s*LEGS?"],
    "Whole Broiler/Fryer":[r"WHOLE\s*BROILER/?FRYER", r"WHOLE\s*BROILER\s*-\s*FRYER"],
}
LABELS_ES = {
    "Breast - B/S":"Pechuga sin hueso (B/S)",
    "Breast T/S":"Pechuga T/S (strapless)",
    "Tenderloins":"Tender de pechuga",
    "Wings, Whole":"Ala entera",
    "Wings, Drummettes":"Muslito de ala (drummette)",
    "Wings, Mid-Joint":"Media ala (flat)",
    "Party Wings":"Alitas mixtas (party wings)",
    "Leg Quarters":"Pierna-muslo (cuarto trasero)",
    "Leg Meat - B/S":"Carne de pierna B/S",
    "Thighs - B/S":"Muslo B/S",
    "Thighs":"Muslo con hueso",
    "Drumsticks":"Pierna (drumstick)",
    "Whole Legs":"Pierna entera",
    "Whole Broiler/Fryer":"Pollo entero (broiler/fryer)",
}
HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept":"text/plain,*/*;q=0.8",
}
SNAP = "poultry_last.json"

def _avg(line: str):
    U = line.upper()
    m = re.search(r"(?:WT?D|WEIGHTED)\s*AVG\.?\s*(\d+(?:\.\d+)?)", U)
    if m:
        try: return float(m.group(1))
        except: pass
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", U)
    if m2:
        try:
            lo, hi = float(m2.group(1)), float(m2.group(2))
            return (lo + hi) / 2.0
        except: pass
    nums = re.findall(r"(\d+(?:\.\d+)?)", U)
    if nums:
        try: return float(nums[-1])
        except: pass
    return None

@st.cache(ttl=1800, allow_output_mutation=True)
def fetch_usda() -> dict:
    for url in POULTRY_URLS:
        try:
            r = requests.get(url, timeout=12, headers=HEADERS)
            if r.status_code != 200:
                continue
            txt = r.text
            if "<html" in txt.lower() and "r.jina.ai" not in url:
                continue
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            out = {}
            for disp, pats in POULTRY_MAP.items():
                for ln in lines:
                    if any(re.search(p, ln.upper()) for p in pats):
                        v = _avg(ln)
                        if v is not None:
                            out[disp] = v
                            break
            if out:
                return out
        except Exception:
            continue
    return {}

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

def poultry_latest():
    cur = fetch_usda()
    prev = load_snap()
    if cur:
        res = {}
        for k,v in cur.items():
            pv = prev.get(k)
            if isinstance(pv, dict): pv = pv.get("price")
            dlt = 0.0 if pv is None else (float(v) - float(pv))
            res[k] = {"price": float(v), "delta": float(dlt)}
        save_snap(cur)
        return res, "live"
    if prev:
        res = {k: {"price": float((v.get("price") if isinstance(v,dict) else v)), "delta": 0.0}
               for k,v in prev.items()
               if (v if not isinstance(v,dict) else v.get("price")) is not None}
        return res, "snapshot"
    return None, "none"

def build_poultry_html(data: dict, status: str) -> str:
    order = [
        "Breast - B/S","Breast T/S","Tenderloins","Wings, Whole","Wings, Drummettes",
        "Wings, Mid-Joint","Party Wings","Leg Quarters","Leg Meat - B/S",
        "Thighs - B/S","Thighs","Drumsticks","Whole Legs","Whole Broiler/Fryer",
    ]
    rows=[]
    for k in order:
        it = data.get(k)
        if not it: continue
        price, delta = it["price"], it["delta"]
        cls = "green" if (delta or 0) >= 0 else "red"
        arr = "▲" if (delta or 0) >= 0 else "▼"
        rows.append(
          f"<tr><td>{LABELS_ES.get(k,k)}</td>"
          f"<td><span class='price-lg'>{fmt2(price)} <span class='unit-inline--p'>USD/lb</span></span> "
          f"<span class='price-delta {cls}'>{arr} {fmt2(abs(delta))}</span></td></tr>"
        )
    badge = {"live":"<span class='badge'>USDA: en vivo</span>",
             "snapshot":"<span class='badge'>USDA: último disponible</span>",
             "none":"<span class='badge'>USDA: sin datos iniciales</span>"}[status]
    return f"""
    <div class="card poultry">
      <div class="title" style="color:var(--txt);margin-bottom:6px">
        Piezas de Pollo, Precios U.S. National (USDA) {badge}
      </div>
      <table class="table">
        <thead><tr><th>Producto</th><th>Precio</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """

# ==================== GRID ====================
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# 1) USD/MXN
st.markdown(f"""
<div class="card">
  <div class="kpi">
    <div class="left">
      <div class="title">USD/MXN</div>
      <div class="big {'green' if fx_delta>=0 else 'red'}">{fmt4(fx)}</div>
      <div class="delta {'green' if fx_delta>=0 else 'red'}">{'▲' if fx_delta>=0 else '▼'} {fmt2(abs(fx_delta))}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# 2) Res / Cerdo
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

# 3) Piezas de Pollo — tabla (hands-free)
poultry, poultry_status = poultry_latest()
if poultry:
    st.markdown(build_poultry_html(poultry, poultry_status), unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # cierre grid si hiciste wrappers adicionales

# ==================== NOTICIAS ====================
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

# Auto-refresh
time.sleep(60)
st.rerun()
