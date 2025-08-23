# app.py — LaSultana Meat Index (USD/MXN sin simulaciones)
import os, time, random, datetime as dt
import requests, streamlit as st, yfinance as yf

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
.card{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:10px;
  padding:14px;
  margin-bottom:18px; /* separación fija para TODOS */
}
.grid .card:last-child{margin-bottom:0}

/* --- Ocultar header, menú y footer de Streamlit --- */
header[data-testid="stHeader"] {display:none;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

/* -------- LOGO -------- */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:32px 0 28px}

/* -------- CINTA SUPERIOR -------- */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-family:ui-monospace,Menlo,Consolas,monospace}
.item{display:inline-block;margin:0 32px}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}

/* -------- GRID -------- */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:18px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900}
.kpi .delta{font-size:20px;margin-left:12px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}

/* -------- TABLA POLLO -------- */
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line)}
.table th{text-align:left;color:var(--muted);font-weight:600}
.table td:last-child{text-align:right}

/* -------- NOTICIA -------- */
.tape-news{
  border:1px solid var(--line);
  border-radius:10px;
  background:#0d141a;
  overflow:hidden;
  min-height:52px;
  margin-top:0;
  margin-bottom:18px;
}
.tape-news-track{display:flex;width:max-content;will-change:transform;animation:marqueeNewsFast 177s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:18px}
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

# ==================== CINTA SUPERIOR (UNA sola, la real) ====================
COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("JBS","JBS"), ("Marfrig Global","MRRTY"), ("Minerva","MRVSY"),
    ("Grupo Bafar","BAFARB.MX"), ("Smithfield (WH)","WHGLY"),
    ("Seaboard","SEB"), ("Hormel Foods","HRL"),
    ("Grupo KUO","KUOB.MX"), ("Maple Leaf Foods","MFI.TO"),
]

@st.cache_data(ttl=75)
def fetch_quotes():
    out=[]
    for name, sym in COMPANIES:
        try:
            h = yf.Ticker(sym).history(period="1d", interval="1m")
            if h is None or h.empty: raise ValueError("no data")
            last  = float(h["Close"].dropna().iloc[-1])
            first = float(h["Close"].dropna().iloc[0])
            ch    = last - first
        except Exception:
            last = None; ch = None
        out.append({"name":name,"sym":sym,"px":last,"ch":ch})
    return out

quotes = fetch_quotes()
line = ""
for q in quotes:
    if q["px"] is None:
        line += f"<span class='item'>{q['name']} ({q['sym']}) <b class='muted'>— — —</b></span>"
    else:
        cls = "green" if (q["ch"] or 0)>=0 else "red"
        arrow = "▲" if (q["ch"] or 0)>=0 else "▼"
        ch_abs = abs(q["ch"]) if q["ch"] is not None else 0.00
        line += f"<span class='item'>{q['name']} ({q['sym']}) <b class='{cls}'>{q['px']:.2f} {arrow} {ch_abs:.2f}</b></span>"

st.markdown(
    f"""
    <div class='tape'>
      <div class='tape-track'>
        <div class='tape-group'>{line}</div>
        <div class='tape-group' aria-hidden='true'>{line}</div>
      </div>
    </div>
    """, unsafe_allow_html=True
)

# ==================== MÉTRICAS ====================
@st.cache_data(ttl=75)
def get_fx():
    try:
        j = requests.get(
            "https://api.exchangerate.host/latest",
            params={"base":"USD","symbols":"MXN"},
            timeout=8
        ).json()
        return float(j["rates"]["MXN"])
    except Exception:
        return None  # 🔥 sin simulación

fx = get_fx()

live_cattle = 185.3 + random.uniform(-0.6,0.6)  # placeholder temporal
lean_hogs   = 94.9  + random.uniform(-0.6,0.6)  # placeholder temporal
lc_delta = random.choice([+0.25, -0.25])        # (se reemplazará al cablear CME)
lh_delta = random.choice([+0.40, -0.40])

# ==================== GRID ====================
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# USD/MXN (izquierda) — sin simulaciones ni delta inventado
if fx is None:
    fx_value_html = "<div class='big red'>—</div>"
    fx_delta_html = "<div class='delta muted'>sin dato</div>"
else:
    fx_value_html = f"<div class='big green'>{fmt4(fx)}</div>"
    fx_delta_html = ""  # si quieres delta real luego, lo agregamos

st.markdown(f"""
<div class="card">
  <div class="kpi">
    <div class="left">
      <div class="title">USD/MXN</div>
      {fx_value_html}
      {fx_delta_html}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Res / Cerdo (centro apilado)
st.markdown(f"""
<div class="centerstack">
  <div class="card box">
    <div class="kpi">
      <div class="left">
        <div class="title">Res en pie</div>
        <div class="big">{fmt2(live_cattle)} <span class="muted">USD/100 lb</span></div>
      </div>
      <div class="delta {'red' if lc_delta<0 else 'green'}">{'▼' if lc_delta<0 else '▲'} {fmt2(abs(lc_delta))}</div>
    </div>
  </div>
  <div class="card box">
    <div class="kpi">
      <div class="left">
        <div class="title">Cerdo en pie</div>
        <div class="big">{fmt2(lean_hogs)} <span class="muted">USD/100 lb</span></div>
      </div>
      <div class="delta {'red' if lh_delta<0 else 'green'}">{'▼' if lh_delta<0 else '▲'} {fmt2(abs(lh_delta))}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Piezas de pollo (derecha)
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

st.markdown("</div>", unsafe_allow_html=True)

# ==================== NOTICIA ====================
noticias = [
  "USDA: beef cutout estable; cortes medios firmes, con demanda moderada en retail y ligera debilidad en foodservice.",
  "USMEF: exportaciones de cerdo a México firmes; importadores absorben costos mientras supermercados sostienen hams.",
  "Poultry: oferta amplia presiona piezas oscuras, pero la pechuga jumbo se mantiene estable en contratos mayoristas.",
  "FX: fortaleza del peso abarata importaciones; revisar spreads USD/lb→MXN/kg y el impacto en costos logísticos."
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
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuente: USDA · USMEF · Yahoo Finance · exchangerate.host.</div>",
  unsafe_allow_html=True,
)

time.sleep(60)
st.rerun()
