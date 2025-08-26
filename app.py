# app.py — LaSultana Meat Index (cinta extendida SIEMPRE visible, sin parpadeo)
# - Cinta bursátil: 25 empresas, con fallback robusto (intradía -> diario -> mensual)
# - USD/MXN (Yahoo Finance: MXN=X)
# - Res/Cerdo (LE=F / HE=F via Yahoo)
# - Piezas de pollo (USDA AJ_PY018) con snapshot
# - Noticias scroll
# - Sin st.rerun(): placeholders + loop => sin parpadeo

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

/* LOGO */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:32px 0 28px}

/* CINTA SUPERIOR */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}

/* GRID */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:18px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
.unit-inline{font-size:0.7em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* TABLA POLLO */
.poultry-table{width:100%}
.poultry-table table{width:100%;border-collapse:collapse}
.poultry-table th,.poultry-table td{padding:10px;border-bottom:1px solid var(--line);vertical-align:middle}
.poultry-table th{text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px}
.poultry-table td:first-child{font-size:110%;}
.unit-inline--poultry{font-size:0.60em;color:var(--muted);font-weight:600;letter-spacing:.3px}
.price-lg{font-size:48px;font-weight:900;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}
.poultry-table td:last-child{text-align:right}

/* NOTICIAS (15% más rápida ≈ 150s) */
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

# ==================== CINTA EXTENDIDA (25 empresas, fallback robusto) ====================
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
def fetch_quote_one(sym: str):
    """
    Devuelve (last, change) o (None, None).
    Orden de intentos:
      1) fast_info (last_price, previous_close)
      2) info (regularMarketPrice, regularMarketPreviousClose)
      3) history intradía: 1d/5m
      4) history diario: 5d/1d
      5) history mensual: max/1mo
    """
    try:
        t = yf.Ticker(sym)
        # 1) fast_info
        try:
            fi = t.fast_info
            lp = fi.get("last_price"); pc = fi.get("previous_close")
            if lp is not None and pc is not None:
                return float(lp), float(lp) - float(pc)
        except Exception:
            pass
        # 2) info
        try:
            inf = t.info or {}
            lp = inf.get("regularMarketPrice"); pc = inf.get("regularMarketPreviousClose")
            if lp is not None and pc is not None:
                lp = float(lp); pc = float(pc); return lp, lp - pc
        except Exception:
            pass
        # 3) intradía
        try:
            d = t.history(period="1d", interval="5m")
            if d is not None and not d.empty:
                c = d["Close"].dropna()
                if c.shape[0] >= 1:
                    last = float(c.iloc[-1])
                    first = float(c.iloc[0])
                    return last, last - first
        except Exception:
            pass
        # 4) diario
        try:
            d = t.history(period="5d", interval="1d")
            if d is not None and not d.empty:
                c = d["Close"].dropna()
                if c.shape[0] >= 2:
                    last = float(c.iloc[-1])
                    prev = float(c.iloc[-2])
                    return last, last - prev
        except Exception:
            pass
        # 5) mensual
        try:
            d = t.history(period="max", interval="1mo")
            if d is not None and not d.empty:
                c = d["Close"].dropna()
                if c.shape[0] >= 2:
                    last = float(c.iloc[-1])
                    prev = float(c.iloc[-2])
                    return last, last - prev
        except Exception:
            pass
    except Exception:
        pass
    return None, None

@st.cache_data(ttl=90)
def fetch_quotes_all(companies):
    """
    Devuelve lista con todas las compañías preservando orden,
    cada una como dict {name,sym,last,chg}. Si no hay datos, last=None.
    """
    out = []
    for name, sym in companies:
        last, chg = fetch_quote_one(sym)
        out.append({"name": name, "sym": sym, "px": last, "ch": chg})
    return out

quotes = fetch_quotes_all(COMPANIES)

def build_ticker_html(items):
    segs = []
    for q in items:
        if q["px"] is None:
            segs.append(f"<span class='item'>{q['name']} ({q['sym']}) <b class='muted'>N/D</b></span>")
        else:
            cls = "green" if (q['ch'] or 0) >= 0 else "red"
            arrow = "▲" if (q['ch'] or 0) >= 0 else "▼"
            segs.append(
                f"<span class='item'>{q['name']} ({q['sym']}) "
                f"<b class='{cls}'>{q['px']:.2f} {arrow} {abs(q['ch']):.2f}</b></span>"
            )
    line = "".join(segs)
    return f"""
    <div class='tape'>
      <div class='tape-track'>
        <div class='tape-group'>{line}</div>
        <div class='tape-group' aria-hidden='true'>{line}</div>
      </div>
    </div>
    """

st.markdown(build_ticker_html(quotes), unsafe_allow_html=True)

# ==================== FX (USD/MXN Yahoo: MXN=X) ====================
@st.cache_data(ttl=75)
def get_fx_yahoo():
    try:
        t = yf.Ticker("MXN=X")
        # fast_info
        try:
            fi = t.fast_info
            last = fi.get("last_price"); prev = fi.get("previous_close")
            if last is not None and prev is not None:
                return float(last), float(last) - float(prev)
        except Exception: pass
        # info
        try:
            inf = t.info or {}
            last = inf.get("regularMarketPrice"); prev = inf.get("regularMarketPreviousClose")
            if last is not None and prev is not None:
                last = float(last); prev = float(prev); return last, last - prev
        except Exception: pass
        # diario
        d = t.history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna()
        if c.shape[0] == 0: return None, None
        last = float(c.iloc[-1]); prev = float(c.iloc[-2]) if c.shape[0] >= 2 else last
        return last, last - prev
    except Exception:
        return None, None

# ==================== Futuros CME (Res/Cerdo) ====================
@st.cache_data(ttl=75)
def get_yahoo_last(sym: str):
    try:
        t = yf.Ticker(sym)
        try:
            fi = t.fast_info
            last = fi.get("last_price"); prev = fi.get("previous_close")
            if last is not None and prev is not None:
                return float(last), float(last) - float(prev)
        except Exception: pass
        d = t.history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna()
        if c.shape[0] == 0: return None, None
        last = float(c.iloc[-1]); prev = float(c.iloc[-2]) if c.shape[0] >= 2 else last
        return last, last - prev
    except Exception:
        return None, None

# ==================== USDA POULTRY (AJ_PY018) ====================
POULTRY_URLS = [
    "https://www.ams.usda.gov/mnreports/aj_py018.txt",
    "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
    "https://www.ams.usda.gov/mnreports/py018.txt",
    "https://www.ams.usda.gov/mnreports/PY018.txt",
]
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
    "Thighs - B/S":        [r"THIGHS?.*B/?S"],
    "Thighs":              [r"THIGHS?(?!.*B/?S)"],
    "Drumsticks":          [r"DRUMSTICKS?"],
    "Whole Legs":          [r"WHOLE\s*LEGS?"],
    "Whole Broiler/Fryer": [r"WHOLE\s*BROILER/?FRYER", r"WHOLE\s*BROILER\s*-\s*FRYER"],
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

def _extract_avg_from_line(line_upper: str) -> float | None:
    m = re.search(r"(?:WT?D|WEIGHTED)\s*AVG\.?\s*(\d+(?:\.\d+)?)", line_upper)
    if m:
        try: return float(m.group(1))
        except: pass
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", line_upper)
    if m2:
        try:
            low = float(m2.group(1)); high = float(m2.group(2))
            return (low + high)/2.0
        except: pass
    nums = re.findall(r"(\d+(?:\.\d+)?)", line_upper)
    if nums:
        try: return float(nums[-1])
        except: return None
    return None

@st.cache_data(ttl=1800)
def fetch_usda_poultry_parts_try_all() -> dict:
    for url in POULTRY_URLS:
        try:
            r = requests.get(url, timeout=12)
            if r.status_code != 200: continue
            txt = r.text
            if "<html" in txt.lower():  # proxy/redirección
                continue
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            out = {}
            for disp, patterns in POULTRY_MAP.items():
                for ln in lines:
                    U = ln.upper()
                    if any(re.search(pat, U) for pat in patterns):
                        val = _extract_avg_from_line(U)
                        if val is not None:
                            out[disp] = val
                            break
            if out:
                return out
        except Exception:
            continue
    return {}

def load_snapshot(path="poultry_last.json") -> dict:
    if not os.path.exists(path): return {}
    try:
        with open(path, "r") as f: return json.load(f)
    except Exception:
        return {}

def save_snapshot(data: dict, path="poultry_last.json"):
    try:
        with open(path, "w") as f:
            json.dump({k: float(v) for k,v in data.items()}, f)
    except Exception:
        pass

def get_poultry_with_snapshot():
    current = fetch_usda_poultry_parts_try_all()
    prev = load_snapshot()
    seeded = False
    if current:
        result = {}
        for k,v in current.items():
            pv = prev.get(k, None)
            if isinstance(pv, dict): pv = pv.get("price")
            dlt = 0.0 if pv is None else (float(v) - float(pv))
            result[k] = {"price": float(v), "delta": float(dlt)}
        save_snapshot(current)
        if not prev: seeded = True
        return result, False, seeded
    if prev:
        res = {k: {"price": float((v.get("price") if isinstance(v,dict) else v)), "delta": 0.0}
               for k,v in prev.items() if (v if not isinstance(v,dict) else v.get("price")) is not None}
        return res, True, False
    placeholders = {k: {"price": None, "delta": 0.0} for k in POULTRY_MAP.keys()}
    return placeholders, True, False

# ==================== PLACEHOLDERS (UI sin parpadeo) ====================
grid_top = st.container()
with grid_top:
    st.markdown("<div class='grid'>", unsafe_allow_html=True)
    fx_ph     = st.empty()
    res_ph    = st.empty()
    cerdo_ph  = st.empty()
    st.markdown("</div>", unsafe_allow_html=True)

pollo_ph  = st.container()
news_ph   = st.empty()
footer_ph = st.empty()

# ==================== RENDER HELPERS ====================
def render_fx(ph, fx, fx_delta):
    if fx is None:
        rate_html = "<div class='big'>N/D</div>"; delta_html = ""
    else:
        cls = "green" if (fx_delta or 0) >= 0 else "red"
        arr = "▲" if (fx_delta or 0) >= 0 else "▼"
        rate_html  = f"<div class='big {cls}'>{fmt4(fx)}</div>"
        delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(fx_delta))}</div>"
    ph.markdown(f"""
    <div class="card">
      <div class="kpi">
        <div class="left">
          <div class="title">USD/MXN</div>
          {rate_html}
          {delta_html}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_kpi(ph, titulo, price, chg):
    unit = "USD/100 lb"
    if price is None:
        price_html = f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"
        delta_html = ""
    else:
        cls = "green" if (chg or 0) >= 0 else "red"
        arrow = "▲" if (chg or 0) >= 0 else "▼"
        price_html = f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
        delta_html = f"<div class='delta {cls}'>{arrow} {fmt2(abs(chg))}</div>"
    ph.markdown(f"""
    <div class="card box">
      <div class="kpi">
        <div class="left"><div class="title">{titulo}</div>{price_html}</div>
        {delta_html}
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_poultry(ph_container, poultry, poultry_stale, poultry_seeded_now):
    DISPLAY_ORDER = [
        "Breast - B/S","Breast T/S","Tenderloins","Wings, Whole","Wings, Drummettes",
        "Wings, Mid-Joint","Party Wings","Leg Quarters","Leg Meat - B/S",
        "Thighs - B/S","Thighs","Drumsticks","Whole Legs","Whole Broiler/Fryer",
    ]
    rows = []
    has_val = False
    for k in DISPLAY_ORDER:
        it = poultry.get(k)
        if not it: continue
        price, delta = it["price"], it["delta"]
        if price is not None: has_val = True
        cls = "green" if (delta or 0) >= 0 else "red"
        arrow = "▲" if (delta or 0) >= 0 else "▼"
        price_txt = f"{fmt2(price)}" if price is not None else "—"
        delta_txt = f"{arrow} {fmt2(abs(delta))}" if price is not None else "—"
        rows.append(
          f"<tr><td>{LABELS_ES.get(k,k)}</td>"
          f"<td><span class='price-lg'>{price_txt} <span class='unit-inline--poultry'>USD/lb</span></span> "
          f"<span class='price-delta {cls}'>{delta_txt}</span></td></tr>"
        )
    if not rows:
        rows = ["<tr><td colspan='2' class='muted'>Preparando primeros datos de USDA…</td></tr>"]
    badge = ""
    if poultry_stale and has_val: badge = " <span class='badge'>último disponible</span>"
    elif poultry_seeded_now:      badge = " <span class='badge'>actualizado</span>"
    ph_container.markdown(f"""
    <div class="card poultry-table">
      <div class="title" style="color:var(--txt);margin-bottom:6px">
        Piezas de Pollo, Precios U.S. National (USDA){badge}
      </div>
      <table>
        <thead><tr><th>Producto</th><th>Precio</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)

def render_news(ph):
    noticias = [
      "USDA: beef cutout estable; cortes medios firmes; dem. retail moderada, foodservice suave.",
      "USMEF: exportaciones de cerdo a México firmes; hams sostienen volumen pese a costos.",
      "Poultry: oferta amplia presiona piezas oscuras; pechuga B/S estable en contratos.",
      "FX: peso fuerte abarata importaciones; revisar spread USD/lb→MXN/kg y logística."
    ]
    k = int(time.time()//30) % len(noticias)
    text = noticias[k]
    ph.markdown(f"""
    <div class='tape-news'>
      <div class='tape-news-track'>
        <div class='tape-news-group'><span class='item'>{text}</span></div>
        <div class='tape-news-group' aria-hidden='true'><span class='item'>{text}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ==================== LOOP SIN PARPADEO ====================
while True:
    try:
        # FX
        fx, fx_chg = get_fx_yahoo()
        # Futuros
        lc_px, lc_ch = get_yahoo_last("LE=F")
        lh_px, lh_ch = get_yahoo_last("HE=F")
        # USDA pollo
        poultry, poultry_stale, poultry_seeded_now = get_poultry_with_snapshot()

        # Pintar
        render_fx(fx_ph, fx, fx_chg)
        render_kpi(res_ph,   "Res en pie",   lc_px, lc_ch)
        render_kpi(cerdo_ph, "Cerdo en pie", lh_px, lh_ch)
        render_poultry(pollo_ph, poultry, poultry_stale, poultry_seeded_now)
        render_news(news_ph)

        footer_ph.markdown(
            f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
            unsafe_allow_html=True,
        )
    except Exception:
        # Silencioso: siguiente tick reintenta
        pass

    time.sleep(60)
