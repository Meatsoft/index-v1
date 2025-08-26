# app.py — LaSultana Meat Index (sin parpadeo, cinta completa, 3 pechugas)
# Fuentes:
# - Yahoo Finance: MXN=X (USD/MXN), LE=F (Res), HE=F (Cerdo), Acciones
# - USDA AJ_PY018 (piezas pollo) con snapshot local (sin inventar)

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
.grid .card:last-child{margin-bottom:0}

header[data-testid="stHeader"]{display:none;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}

/* LOGO */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:32px 0 28px}

/* CINTA SUPERIOR (stocks) */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
.muted{color:var(--muted)}
.up{color:var(--up)} .down{color:var(--down)}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* GRID */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:18px}

.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
.unit-inline{font-size:0.7em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* TABLA POLLO (3 pechugas) */
.poultry-table{width:100%}
.poultry-table table{width:100%;border-collapse:collapse}
.poultry-table th,.poultry-table td{padding:10px;border-bottom:1px solid var(--line);vertical-align:middle}
.poultry-table th{text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px}
.poultry-table td:first-child{font-size:110%;}
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
# Base (ya teníamos):
base_companies = [
    ("Tyson Foods","TSN"),
    ("Pilgrim’s Pride","PPC"),
    ("JBS","JBS"),
    ("BRF","BRFS"),
    ("Hormel Foods","HRL"),
    ("Seaboard","SEB"),
    ("Minerva","MRVSY"),
    ("Marfrig Global","MRRTY"),
    ("Maple Leaf Foods","MFI.TO"),
    ("Cal-Maine Foods","CALM"),
    ("Vital Farms","VITL"),
    ("Grupo KUO","KUOB.MX"),
    ("Grupo Bafar","BAFARB.MX"),
    ("WH Group (Smithfield)","WHGLY"),  # SFD ya no cotiza, usamos la matriz
]

# Nuevas del listado (solo las que no estaban):
extras = [
    ("Minupar Participações","MNPR3.SA"),     # B3: MNPR3
    ("Excelsior Alimentos","BAUH4.SA"),      # B3: BAUH4
    ("Wens Foodstuff Group","300498.SZ"),    # SZSE: 300498
    ("Wingstop","WING"),
    ("Yum! Brands","YUM"),
    ("Restaurant Brands Intl.","QSR"),
    ("Sysco","SYY"),
    ("US Foods","USFD"),
    ("Performance Food Group","PFGC"),
    ("Walmart","WMT"),
    ("Alsea","ALSEA.MX"),
]

# Unir sin duplicados por símbolo
seen = set(sym for _, sym in base_companies)
COMPANIES = base_companies + [(n,s) for (n,s) in extras if s not in seen]

@st.cache_data(ttl=75)
def yahoo_quote(sym: str):
    """Devuelve (last, chg) desde Yahoo; chg puede ser None si no hay prev_close."""
    try:
        t = yf.Ticker(sym)
        # 1) fast_info
        try:
            fi = t.fast_info
            last = fi.get("last_price", None)
            prev = fi.get("previous_close", None)
            if last is not None:
                chg = (float(last) - float(prev)) if prev is not None else None
                return float(last), chg
        except Exception:
            pass
        # 2) info
        try:
            inf = t.info or {}
            last = inf.get("regularMarketPrice", None)
            prev = inf.get("regularMarketPreviousClose", None)
            if last is not None:
                chg = (float(last) - float(prev)) if prev is not None else None
                return float(last), chg
        except Exception:
            pass
        # 3) history diario
        d = t.history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna()
        if c.shape[0] == 0: return None, None
        last = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if c.shape[0] >= 2 else None
        chg  = (last - prev) if prev is not None else None
        return last, chg
    except Exception:
        return None, None

# Construir SIEMPRE todas (si no hay dato → “—”)
line_items = []
for name, sym in COMPANIES:
    last, chg = yahoo_quote(sym)
    if last is None:
        line_items.append(f"<span class='item'>{name} ({sym}) <b class='muted'>—</b></span>")
    else:
        if chg is None:
            line_items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
        else:
            cls = "up" if chg >= 0 else "down"
            arr = "▲" if chg >= 0 else "▼"
            line_items.append(
                f"<span class='item'>{name} ({sym}) <b class='{cls}'>{last:.2f} {arr} {abs(chg):.2f}</b></span>"
            )
ticker_line = "".join(line_items)

st.markdown(f"""
<div class='tape'>
  <div class='tape-track'>
    <div class='tape-group'>{ticker_line}</div>
    <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ==================== FX (Yahoo Finance: MXN=X) ====================
@st.cache_data(ttl=75)
def get_fx_yahoo():
    try:
        t = yf.Ticker("MXN=X")
        # fast_info
        try:
            fi = t.fast_info
            last = fi.get("last_price", None)
            prev = fi.get("previous_close", None)
            if last is not None:
                chg = (float(last) - float(prev)) if prev is not None else None
                return float(last), chg
        except Exception:
            pass
        # info
        try:
            inf = t.info or {}
            last = inf.get("regularMarketPrice", None)
            prev = inf.get("regularMarketPreviousClose", None)
            if last is not None:
                chg = (float(last) - float(prev)) if prev is not None else None
                return float(last), chg
        except Exception:
            pass
        # history diario
        d = t.history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna()
        if c.shape[0] == 0: return None, None
        last = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if c.shape[0] >= 2 else None
        chg  = (last - prev) if prev is not None else None
        return last, chg
    except Exception:
        return None, None

# ==================== CME (Yahoo) ====================
@st.cache_data(ttl=75)
def get_yahoo_last(sym: str):
    try:
        t = yf.Ticker(sym)
        # fast_info
        try:
            fi = t.fast_info
            last = fi.get("last_price", None)
            prev = fi.get("previous_close", None)
            if last is not None:
                chg = (float(last) - float(prev)) if prev is not None else None
                return float(last), chg
        except Exception:
            pass
        # info
        try:
            inf = t.info or {}
            last = inf.get("regularMarketPrice", None)
            prev = inf.get("regularMarketPreviousClose", None)
            if last is not None:
                chg = (float(last) - float(prev)) if prev is not None else None
                return last, chg
        except Exception:
            pass
        # history diario
        d = t.history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna()
        if c.shape[0] == 0: return None, None
        last = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if c.shape[0] >= 2 else None
        chg  = (last - prev) if prev is not None else None
        return last, chg
    except Exception:
        return None, None

# ==================== USDA — 3 pechugas ====================
POULTRY_URLS = [
    "https://www.ams.usda.gov/mnreports/aj_py018.txt",
    "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
    "https://www.ams.usda.gov/mnreports/py018.txt",
    "https://www.ams.usda.gov/mnreports/PY018.txt",
]
HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"}

PECHUGAS_MAP = {
    "Pechuga B/S Jumbo":   [r"BREAST.*B/?S.*JUMBO", r"JUMBO.*BREAST.*B/?S"],
    "Pechuga B/S":         [r"BREAST\\s*-\\s*B/?S(?!.*JUMBO)", r"BREAST,\\s*B/?S(?!.*JUMBO)"],
    "Pechuga T/S":         [r"BREAST\\s*T/?S", r"STRAPLESS"],
}

def _avg_from_line(U: str):
    m = re.search(r"(?:WT?D|WEIGHTED)\\s*AVG\\.?\\s*(\\d+(?:\\.\\d+)?)", U)
    if m:
        try: return float(m.group(1))
        except: pass
    m2 = re.search(r"(\\d+(?:\\.\\d+)?)\\s*-\\s*(\\d+(?:\\.\\d+)?)", U)
    if m2:
        try: return (float(m2.group(1)) + float(m2.group(2)))/2.0
        except: pass
    nums = re.findall(r"(\\d+(?:\\.\\d+)?)", U)
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
            txt = r.text
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            found = {}
            for disp, pats in PECHUGAS_MAP.items():
                for ln in lines:
                    U = ln.upper()
                    if any(re.search(p, U) for p in pats):
                        val = _avg_from_line(U)
                        if val is not None:
                            found[disp] = val
                            break
            if found:
                return found
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
    # primera vida
    base = {k:{"price":None,"delta":0.0} for k in PECHUGAS_MAP.keys()}
    return base, True, False

# ==================== UI ESTÁTICA ====================
st.markdown("<div class='grid'>", unsafe_allow_html=True)
fx_ph     = st.empty()
res_ph    = st.empty()
cerdo_ph  = st.empty()
st.markdown("</div>", unsafe_allow_html=True)

pollo_ph  = st.container()
news_ph   = st.empty()
footer_ph = st.empty()

# ==================== RENDER HELPERS ====================
def render_fx(ph, fx, chg):
    if fx is None:
        rate_html = "<div class='big'>N/D</div>"; delta_html = ""
    else:
        if chg is None:
            rate_html = f"<div class='big'>{fmt4(fx)}</div>"; delta_html = ""
        else:
            cls = "up" if chg >= 0 else "down"; arr = "▲" if chg >= 0 else "▼"
            rate_html = f"<div class='big {cls}'>{fmt4(fx)}</div>"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    ph.markdown(f"""
    <div class="card"><div class="kpi"><div class="left">
      <div class="title">USD/MXN</div>
      {rate_html}
      {delta_html}
    </div></div></div>
    """, unsafe_allow_html=True)

def render_kpi(ph, titulo, price, chg):
    unit = "USD/100 lb"
    if price is None:
        price_html = f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"; delta_html = ""
    else:
        if chg is None:
            price_html = f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"; delta_html = ""
        else:
            cls = "up" if chg >= 0 else "down"; arr = "▲" if chg >= 0 else "▼"
            price_html = f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    ph.markdown(f"""
    <div class="card box"><div class="kpi">
      <div class="left"><div class="title">{titulo}</div>{price_html}</div>
      {delta_html}
    </div></div>
    """, unsafe_allow_html=True)

def render_pechugas(ph_container, data, stale, seeded):
    order = ["Pechuga B/S Jumbo", "Pechuga B/S", "Pechuga T/S"]
    rows = []; any_val=False
    for name in order:
        it = data.get(name, {"price":None,"delta":0.0})
        price, delta = it["price"], it["delta"]
        if price is not None: any_val=True
        cls = "up" if (delta or 0)>=0 else "down"; arr = "▲" if (delta or 0)>=0 else "▼"
        price_txt = fmt2(price) if price is not None else "—"
        delta_txt = (f"{arr} {fmt2(abs(delta))}" if price is not None else "—")
        rows.append(
            f"<tr><td>{name}</td>"
            f"<td><span class='price-lg'>{price_txt} <span class='unit-inline--poultry'>USD/lb</span></span> "
            f"<span class='price-delta {cls}'>{delta_txt}</span></td></tr>"
        )
    badge = ""
    if stale and any_val: badge = " <span class='badge'>último disponible</span>"
    elif seeded:          badge = " <span class='badge'>actualizado</span>"
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
    <div class='tape-news'><div class='tape-news-track'>
      <div class='tape-news-group'><span class='item'>{text}</span></div>
      <div class='tape-news-group' aria-hidden='true'><span class='item'>{text}</span></div>
    </div></div>
    """, unsafe_allow_html=True)

# ==================== LOOP SIN PARPADEO ====================
while True:
    try:
        # FX y Futuros (Yahoo)
        fx, fx_chg = get_fx_yahoo()
        lc, lc_chg = get_yahoo_last("LE=F")
        lh, lh_chg = get_yahoo_last("HE=F")

        # USDA pechugas (3)
        pechugas, stale, seeded = get_pechugas_with_snapshot()

        # Pintar
        render_fx(fx_ph, fx, fx_chg)
        render_kpi(res_ph,   "Res en pie",   lc, lc_chg)
        render_kpi(cerdo_ph, "Cerdo en pie", lh, lh_chg)
        render_pechugas(pollo_ph, pechugas, stale, seeded)
        render_news(news_ph)

        footer_ph.markdown(
            f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
            unsafe_allow_html=True,
        )
    except Exception:
        pass
    time.sleep(60)
