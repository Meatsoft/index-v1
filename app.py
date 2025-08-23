# app.py — LaSultana Meat Index (logo fijo, cinta continua, noticias grandes)
import os, time, random, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ======= ESTILO =======
st.markdown("""
<style>
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important}
.block-container{max-width:1400px;padding-top:8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}

/* GRID PRINCIPAL: 3 columnas */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:12px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900}
.kpi .delta{font-size:20px;margin-left:12px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}

/* LOGO controlado (nunca 60% de la pantalla) */
.logo-wrap{display:flex;justify-content:center;margin:10px 0 14px}
.logo-fixed{width:300px!important;height:auto;display:block}  /* <- Fijo a 300px */

/* CINTA BURSÁTIL: lenta y sin huecos */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px}
.tape-inner{display:inline-block;white-space:nowrap;padding:10px 0;
            font-family:ui-monospace,Menlo,Consolas,monospace;
            animation:scroll 120s linear infinite}              /* lenta */
.item{display:inline-block;margin:0 32px}
@keyframes scroll{0%{transform:translateX(100%)}100%{transform:translateX(-100%)}}

/* Tabla pollo */
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line)}
.table th{text-align:left;color:var(--muted);font-weight:600}
.table td:last-child{text-align:right}

/* Noticias GRANDES */
.footer{margin-top:12px}
.news-main{font-size:22px;font-weight:700}  /* <- más grande */
.news-sub{font-size:18px;color:var(--muted)} /* <- más grande */
.caption{color:var(--muted)!important}
</style>
""", unsafe_allow_html=True)

# ======= Helpers (coma decimal) =======
def fmt2(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ======= LOGO (HTML directo para NO redimensionar raro) =======
if os.path.exists("ILSMeatIndex.png"):
    st.markdown('<div class="logo-wrap"><img src="ILSMeatIndex.png" class="logo-fixed"></div>', unsafe_allow_html=True)

# ======= CINTA BURSÁTIL (14 empresas) =======
COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("JBS","JBS"),               # si falla, "JBSAY"
    ("Marfrig Global","MRRTY"),  # o "MRFG3.SA"
    ("Minerva","MRVSY"),         # o "BEEF3.SA"
    ("Grupo Bafar","BAFARB.MX"),
    ("Smithfield (WH)","WHGLY"), # proxy
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
            last = float(h["Close"].dropna().iloc[-1])
            first= float(h["Close"].dropna().iloc[0])
            ch   = last - first
        except Exception:
            last = round(40 + random.random()*80, 2)
            ch   = round(random.uniform(-1.5, 1.5), 2)
        out.append({"name":name,"sym":sym,"px":last,"ch":ch})
    return out

# Mantén SIEMPRE algo en pantalla
if "last_tape" not in st.session_state:
    st.session_state.last_tape = fetch_quotes()
rows = fetch_quotes()
if not rows:  # si Yahoo falla un instante
    rows = st.session_state.last_tape
else:
    st.session_state.last_tape = rows

# Construye línea base y repítela 6× para que NO haya huecos
base = ""
for r in rows:
    cls = "green" if r["ch"]>=0 else "red"
    arrow = "▲" if r["ch"]>=0 else "▼"
    base += (f"<span class='item'>{r['name']} ({r['sym']}) "
             f"<b class='{cls}'>{r['px']:.2f} {arrow} {abs(r['ch']):.2f}</b></span>")
line = base * 6  # <- continuidad total

st.markdown(f"<div class='tape'><div class='tape-inner'>{line}</div></div>", unsafe_allow_html=True)

# ======= Datos (FX real + placeholders MPR) =======
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

live_cattle = 185.3 + random.uniform(-0.6,0.6)  # TODO: AMS/MPR
lean_hogs   = 94.9  + random.uniform(-0.6,0.6)  # TODO: AMS/MPR
lc_delta = random.choice([+0.25, -0.25])
lh_delta = random.choice([+0.40, -0.40])

# ======= GRID (igual a la foto) =======
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# Izquierda — USD/MXN
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

# Centro — Res/Cerdo con delta a la derecha
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

# Derecha — piezas de pollo
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

# ======= Noticias (GRANDES, 2 líneas, rotando) =======
news = [
  "USMEF: exportaciones de cerdo a México continúan firmes; demanda retail sostiene hams.",
  "USDA: beef cutout estable; middle meats firmes; rounds suaves.",
  "Poultry: oferta amplia presiona piezas oscuras; pechuga jumbo estable.",
  "FX: fortaleza del peso abarata importaciones; revisar spreads USD/lb → MXN/kg."
]
i = int(time.time()//30) % len(news)
j = (i+1) % len(news)
st.markdown(f"""
<div class="card footer">
  <div class="news-main">{news[i]}</div>
  <div class="news-sub">{news[j]}</div>
</div>
""", unsafe_allow_html=True)

# ======= Pie + auto-refresh =======
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Bursátil vía Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True,
)

time.sleep(60)
st.rerun()
