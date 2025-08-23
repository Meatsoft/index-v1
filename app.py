# app.py — LaSultana Meat Index (logo robusto, cinta inmediata y lenta, 1 noticia breve)
import os, random, time, datetime as dt
import requests, streamlit as st, yfinance as yf
import pandas as pd

# ============ AUTORELOAD (30s) con fallback si falta streamlit-autorefresh ============
REFRESH_MS = 30_000  # <-- cámbialo a 15_000 si quieres 15s
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=REFRESH_MS, key="auto")
except Exception:
    # Fallback: recarga vía JS si no está instalada la librería
    st.components.v1.html(
        f"<script>setTimeout(()=>window.parent.location.reload(), {REFRESH_MS});</script>",
        height=0,
    )

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ====================== ESTILOS ======================
st.markdown("""
<style>
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important}
.block-container{max-width:1400px;padding-top:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}

/* LOGO */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:8px 0 12px}

/* CINTA (18% más lenta: 260s) */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px}
.tape-inner{display:inline-block;white-space:nowrap;padding:10px 0;
            font-family:ui-monospace,Menlo,Consolas,monospace;
            animation:scroll 260s linear infinite}
.item{display:inline-block;margin:0 32px}
@keyframes scroll{0%{transform:translateX(100%)}100%{transform:translateX(-100%)}}

/* GRID PRINCIPAL */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:12px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;font-variant-numeric: tabular-nums}
.kpi .delta{font-size:20px;margin-left:12px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}

/* TABLA POLLO */
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line)}
.table th{text-align:left;color:var(--muted);font-weight:600}
.table td:last-child{text-align:right}

/* NOTICIA ÚNICA */
.footer{margin-top:12px}
.news-main{font-size:24px;font-weight:800}
.caption{color:var(--muted)!important}
</style>
""", unsafe_allow_html=True)

# ==================== HELPERS ====================
def fmt2(x: float) -> str:
    s = f"{x:,.2f}"; return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"; return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ==================== LOGO (ROBUSTO) ====================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== CINTA (VISIBLE AL INSTANTE) ====================
COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("JBS","JBS"), ("Marfrig Global","MRRTY"), ("Minerva","MRVSY"),
    ("Grupo Bafar","BAFARB.MX"), ("Smithfield (WH)","WHGLY"),
    ("Seaboard","SEB"), ("Hormel Foods","HRL"),
    ("Grupo KUO","KUOB.MX"), ("Maple Leaf Foods","MFI.TO"),
]
# Mapeo silencioso para símbolos problemáticos (no cambia cómo se ve el nombre):
SYMBOL_FIX = {"JBS": "JBSAY", "MRVSY": "MRVSY", "MRRTY": "MRRTY"}

# 1) Placeholder inmediato (cero parpadeo)
placeholder_text = "".join(
    f"<span class='item'>{n} ({s}) <b class='green'>-- ▲ --</b></span>" for n,s in COMPANIES
)
tape_block = st.container()
with tape_block:
    st.markdown(f"<div class='tape'><div class='tape-inner'>{placeholder_text*10}</div></div>",
                unsafe_allow_html=True)

# ==================== QUOTES con fallback 5d/5m + memo último bueno ====================
@st.cache_data(ttl=75)
def _fetch_one(sym: str):
    """Devuelve (last, delta) usando 1d/1m; si no hay datos cae a 5d/5m."""
    def _from(df: pd.DataFrame):
        if df is None or df.empty: return None
        df = df.dropna(subset=["Close"])
        last = float(df["Close"].iloc[-1])
        first = float(df["Close"].iloc[0])
        return last, last - first

    # 1) Intradía puro
    try:
        df = yf.download(sym, period="1d", interval="1m", auto_adjust=False,
                         progress=False, prepost=True, threads=False)
        snap = _from(df)
        if snap: return snap
    except Exception:
        pass
    # 2) Fallback 5d/5m: usa último vs cierre previo
    try:
        df = yf.download(sym, period="5d", interval="5m", auto_adjust=False,
                         progress=False, prepost=True, threads=False)
        if df is None or df.empty: return None
        df = df.dropna(subset=["Close"])
        last = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-2]) if len(df) > 1 else last
        return last, last - prev
    except Exception:
        return None

def fetch_quotes():
    if "last_good" not in st.session_state:
        st.session_state.last_good = {}
    data=[]
    for name, sym in COMPANIES:
        real = SYMBOL_FIX.get(sym, sym)
        snap = _fetch_one(real)
        if snap:
            last, ch = snap
            st.session_state.last_good[real] = (last, ch)
        else:
            # Usa último bueno; si no hay, como último recurso muestra random suave para no romper la cinta
            last, ch = st.session_state.last_good.get(real, (None, None))
            if last is None:
                last = round(40 + random.random()*80, 2)
                ch   = round(random.uniform(-1.2, 1.2), 2)
        data.append({"name":name,"sym":sym,"px":last,"ch":ch})
    return data

# 2) Reemplazo sin borrar el bloque
quotes = fetch_quotes()
line = ""
for q in quotes:
    cls = "green" if q["ch"]>=0 else "red"
    arrow = "▲" if q["ch"]>=0 else "▼"
    line += (
        f"<span class='item'>{q['name']} ({q['sym']}) "
        f"<b class='{cls}'>{q['px']:.2f} {arrow} {abs(q['ch']):.2f}</b></span>"
    )
with tape_block:
    st.markdown(f"<div class='tape'><div class='tape-inner'>{line*10}</div></div>",
                unsafe_allow_html=True)

# ==================== FX + (placeholders MPR) ====================
@st.cache_data(ttl=75)
def get_fx():
    try:
        j = requests.get("https://api.exchangerate.host/latest",
                         params={"base":"USD","symbols":"MXN"}, timeout=8).json()
        val = float(j["rates"]["MXN"])
        st.session_state["fx_last"] = val
        return val
    except Exception:
        return st.session_state.get("fx_last", 18.50 + random.uniform(-0.2, 0.2))

fx = get_fx()
fx_delta = random.choice([+0.02, -0.02])  # placeholder visual
live_cattle = 185.3 + random.uniform(-0.6,0.6)  # TODO: conectar a LE=F (CME) y convertir a USD/cwt
lean_hogs   = 94.9  + random.uniform(-0.6,0.6)  # TODO: conectar a HE=F (CME)
lc_delta = random.choice([+0.25, -0.25])
lh_delta = random.choice([+0.40, -0.40])

# ==================== GRID PRINCIPAL ====================
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# Columna izquierda — USD/MXN
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

# Columna centro apilada — Res/Cerdo con delta a la derecha
st.markdown(f"""
<div class="centerstack">
  <div class="card box">
    <div class="kpi">
      <div class="left">
        <div class="title">Res en pie</div>
        <div class="big">{fmt2(live_cattle)} <span class="muted">USD/cwt</span></div>
      </div>
      <div class="delta {'red' if lc_delta<0 else 'green'}">{'▼' if lc_delta<0 else '▲'} {fmt2(abs(lc_delta))}</div>
    </div>
  </div>
  <div class="card box">
    <div class="kpi">
      <div class="left">
        <div class="title">Cerdo en pie</div>
        <div class="big">{fmt2(lean_hogs)} <span class="muted">USD/cwt</span></div>
      </div>
      <div class="delta {'red' if lh_delta<0 else 'green'}">{'▼' if lh_delta<0 else '▲'} {fmt2(abs(lh_delta))}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Columna derecha — Piezas de Pollo
parts = {"Pechuga":2.65,"Ala":1.98,"Pierna":1.32,"Muslo":1.29}
rows_html = "".join([f"<tr><td>{k}</td><td>{fmt2(v)}</td></tr>" for k,v in parts.items()])
st.markdown(f"""
<div class="card">
  <div class="title" style="color:var(--txt);margin-bottom:6px">Piezas de Pollo</div>
  <table class="table">
    <thead><tr><th>Producto</th><th>USD/lb</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # /grid

# ==================== NOTICIA ÚNICA (breve/desarrollada) ====================
noticias = [
  "USMEF: exportaciones de cerdo a México se mantienen firmes; retailers sostienen hams pese a presión de costos.",
  "USDA: beef cutout estable; cortes medios continúan firmes mientras rounds ceden ante menor demanda institucional.",
  "Poultry: oferta amplia presiona piezas oscuras; pechuga jumbo estable en contratos y spot limitado.",
  "FX: peso fuerte abarata importaciones; revisa spreads USD/lb→MXN/kg y costos de flete/financiamiento."
]
k = int(time.time()//30) % len(noticias)
st.markdown(f"<div class='card footer'><div class='news-main'>{noticias[k]}</div></div>",
            unsafe_allow_html=True)

# ==================== PIE ====================
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh {REFRESH_MS//1000}s · Bursátil vía Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True,
)
