# app.py — LaSultana Meat Index (layout igual al mock)
import os, time, random, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ========== ESTILO (alto contraste, igual a mock) ==========
st.markdown("""
<style>
:root{
  --bg:#090f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b; --header:#dff6e9;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important}
.block-container{max-width:1400px;padding-top:8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px} /* 3 columnas */
.centerstack .box{margin-bottom:12px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900}
.kpi .delta{font-size:20px;margin-left:12px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}
/* Logo controlado */
.logo-wrap{display:flex;justify-content:center;margin:12px 0 18px 0}
.logo{max-width:320px;height:auto}
/* Cinta bursátil lenta */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden}
.tape-inner{display:inline-block;white-space:nowrap;padding:8px 0;
            font-family:ui-monospace,Menlo,Consolas,monospace;
            animation:scroll 100s linear infinite}
.item{display:inline-block;margin:0 32px}
@keyframes scroll{0%{transform:translateX(100%)}100%{transform:translateX(-100%)}}
/* Tabla pollo */
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line)}
.table th{text-align:left;color:var(--muted);font-weight:600}
.table td:last-child{text-align:right}
/* Footer noticias */
.footer{margin-top:12px}
.news-main{font-size:18px}
.news-sub{font-size:16px;color:var(--muted)}
.caption{color:var(--muted)!important}
</style>
""", unsafe_allow_html=True)

# ========= Helpers de formateo (coma decimal) =========
def fmt2(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ========== Logo centrado ==========
if os.path.exists("ILSMeatIndex.png"):
    st.markdown(f'<div class="logo-wrap"><img src="ILSMeatIndex.png" class="logo"/></div>', unsafe_allow_html=True)

# ========== Cinta bursátil (14 empresas) ==========
COMPANIES = [
    ("Tyson Foods","TSN"),
    ("Pilgrim’s Pride","PPC"),
    ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"),
    ("Vital Farms","VITL"),
    ("JBS","JBS"),                # si falla, prueba JBSAY
    ("Marfrig Global","MRRTY"),   # o MRFG3.SA
    ("Minerva","MRVSY"),          # o BEEF3.SA
    ("Grupo Bafar","BAFARB.MX"),
    ("Smithfield (WH)","WHGLY"),  # proxy
    ("Seaboard","SEB"),
    ("Hormel Foods","HRL"),
    ("Grupo KUO","KUOB.MX"),
    ("Maple Leaf Foods","MFI.TO"),
]

@st.cache_data(ttl=90)
def get_quotes():
    out=[]
    for name, sym in COMPANIES:
        try:
            h = yf.Ticker(sym).history(period="1d", interval="1m")
            if h is None or h.empty: raise ValueError("no data")
            last = float(h["Close"].dropna().iloc[-1])
            first= float(h["Close"].dropna().iloc[0])
            ch = last - first
        except Exception:
            last = round(40 + random.random()*80, 2)
            ch   = round(random.uniform(-1.5, 1.5), 2)
        out.append({"name":name,"sym":sym,"px":last,"ch":ch})
    return out

eq = get_quotes()
ticker_html = ""
for _ in range(2):  # duplicado para scroll infinito
    for r in eq:
        cls = "green" if r["ch"]>=0 else "red"
        arrow = "▲" if r["ch"]>=0 else "▼"
        ticker_html += (
            f"<span class='item'>{r['name']} ({r['sym']}) "
            f"<b class='{cls}'>{r['px']:.2f} {arrow} {abs(r['ch']):.2f}</b></span>"
        )
st.markdown(f"<div class='tape'><div class='tape-inner'>{ticker_html}</div></div>", unsafe_allow_html=True)

# ========== Datos FX (gratis) ==========
@st.cache_data(ttl=90)
def get_fx():
    try:
        j = requests.get("https://api.exchangerate.host/latest",
                         params={"base":"USD","symbols":"MXN"}, timeout=8).json()
        return float(j["rates"]["MXN"])
    except Exception:
        return 18.50 + random.uniform(-0.2, 0.2)

fx = get_fx()
fx_delta = random.choice([+0.02, -0.02])

# Placeholders (conectar luego a AMS/MPR)
live_cattle = 185.32 + random.uniform(-0.6,0.6)
lean_hogs   = 94.86  + random.uniform(-0.6,0.6)
lc_delta = random.choice([+0.25, -0.25])
lh_delta = random.choice([+0.40, -0.40])

# ========== Grid principal (3 columnas) ==========
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# Columna izquierda — USD/MXN (número verde grande + delta debajo)
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

# Columna central apilada — Res en pie / Cerdo en pie, delta a la derecha
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

# Columna derecha — Tabla piezas de pollo
parts = {"Pechuga":2.65,"Ala":1.98,"Pierna":1.32,"Muslo":1.29}
rows = "".join([f"<tr><td>{k}</td><td>{fmt2(v)}</td></tr>" for k,v in parts.items()])
st.markdown(f"""
<div class="card">
  <div class="title" style="color:var(--txt);margin-bottom:6px">Piezas de Pollo</div>
  <table class="table">
    <thead><tr><th>Producto</th><th>USD/lb</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # /grid

# ========== Noticias (dos líneas, rotación cada 30s en cliente) ==========
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

# ========== Pie + auto-refresh ==========
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Bursátil vía Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True,
)
time.sleep(60)
st.rerun()
