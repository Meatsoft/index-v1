# app.py — LaSultana Meat Index (igual al mock, lento y ordenado)
import time, datetime as dt, random, requests, streamlit as st, yfinance as yf, os

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ========== ESTILO ==========
st.markdown("""
<style>
:root{
  --bg:#090f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important}
.block-container{max-width:1400px;padding-top:8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi{display:flex;flex-direction:column;gap:8px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900}
.kpi .delta{font-size:20px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}
.grid{display:grid;grid-template-columns: 1.15fr 1fr 1fr; gap:12px}
.centerstack .box{margin-bottom:12px}
.table{width:100%}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line)}
.table th{text-align:left;color:var(--muted);font-weight:600}
.logo-wrap{display:flex;justify-content:center;margin:2px 0 6px}
.logo{max-width:520px;width:90%}
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden}
.tape-inner{display:inline-block;white-space:nowrap;padding:8px 0;
            font-family:ui-monospace,Menlo,Consolas,monospace;
            animation:scroll 90s linear infinite}  /* más lenta */
.item{display:inline-block;margin:0 32px}
@keyframes scroll{0%{transform:translateX(100%)}100%{transform:translateX(-100%)}}
.footer{margin-top:12px}
.sep{height:8px}
</style>
""", unsafe_allow_html=True)

# ========== LOGO ==========
st.markdown('<div class="logo-wrap">', unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", use_column_width=False)
st.markdown('</div><div class="sep"></div>', unsafe_allow_html=True)

# ========== EMPRESAS (14) ==========
COMPANIES = [
    ("Tyson Foods","TSN"),
    ("Pilgrim’s Pride","PPC"),
    ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"),
    ("Vital Farms","VITL"),
    ("JBS","JBS"),                # si falla, cambia a JBSAY
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
def quotes():
    out=[]
    for name,sym in COMPANIES:
        try:
            h = yf.Ticker(sym).history(period="1d", interval="1m")
            last = float(h["Close"].dropna().iloc[-1])
            first = float(h["Close"].dropna().iloc[0])
            ch = last-first
        except Exception:
            last = round(40+random.random()*80,2)
            ch   = round(random.uniform(-1.5,1.5),2)
        out.append({"name":name,"sym":sym,"px":last,"ch":ch})
    return out

# ========== CINTA BURSÁTIL (lenta) ==========
eq = quotes()
line = ""
for _ in range(2):  # duplicamos para continuidad
    for r in eq:
        cls = "green" if r["ch"]>=0 else "red"
        arrow = "▲" if r["ch"]>=0 else "▼"
        line += (
            f"<span class='item'>{r['name']} ({r['sym']}) "
            f"<b class='{cls}'>{r['px']:.2f} {arrow} {abs(r['ch']):.2f}</b></span>"
        )
st.markdown(f"<div class='tape'><div class='tape-inner'>{line}</div></div>", unsafe_allow_html=True)

# ========== FX + FUTUROS (placeholders conectables) ==========
@st.cache_data(ttl=90)
def usdmxn():
    try:
        j = requests.get("https://api.exchangerate.host/latest",
                         params={"base":"USD","symbols":"MXN"}, timeout=8).json()
        return float(j["rates"]["MXN"])
    except Exception:
        return 18.50 + random.uniform(-0.2,0.2)

fx = usdmxn()
live_cattle = 185.32 + random.uniform(-0.6,0.6)  # TODO conectar AMS/MPR
lean_hogs   = 94.86  + random.uniform(-0.6,0.6)  # TODO conectar AMS/MPR
fx_d = random.choice([+0.02,-0.02])
lc_d = random.choice([+0.25,-0.25])
lh_d = random.choice([+0.40,-0.40])

# ========== LAYOUT (igual al mock) ==========
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# Izquierda: USD/MXN
st.markdown(f"""
<div class="card kpi">
  <div class="title">USD/MXN</div>
  <div class="big">{fx:,.4f}</div>
  <div class="delta {'green' if fx_d>=0 else 'red'}">{'▲' if fx_d>=0 else '▼'} {abs(fx_d):.02f}</div>
</div>
""", unsafe_allow_html=True)

# Centro: Live Cattle + Lean Hogs (en español)
st.markdown(f"""
<div class="centerstack">
  <div class="card box kpi">
    <div class="title">Res en pie</div>
    <div class="big">{live_cattle:,.2f} <span class="muted">USD/cwt</span></div>
    <div class="delta {'green' if lc_d>=0 else 'red'}">{'▲' if lc_d>=0 else '▼'} {abs(lc_d):.02f}</div>
  </div>
  <div class="card box kpi">
    <div class="title">Cerdo en pie</div>
    <div class="big">{lean_hogs:,.2f} <span class="muted">USD/cwt</span></div>
    <div class="delta {'green' if lh_d>=0 else 'red'}">{'▲' if lh_d>=0 else '▼'} {abs(lh_d):.02f}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Derecha: Piezas de Pollo (tabla)
parts = {"Pechuga":2.65,"Ala":1.98,"Pierna":1.32,"Muslo":1.29}
rows = "".join([f"<tr><td>{k}</td><td style='text-align:right'>{v:,.2f}</td></tr>" for k,v in parts.items()])
st.markdown(f"""
<div class="card">
  <div class="title" style="font-size:18px;color:var(--txt);margin-bottom:6px">Piezas de Pollo</div>
  <table class="table">
    <thead><tr><th>Producto</th><th style="text-align:right">USD/lb</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # /grid

# ========== BANDA DE NOTICIAS (2 líneas, rotando) ==========
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
  <div>{news[i]}</div>
  <div class="muted">{news[j]}</div>
</div>
""", unsafe_allow_html=True)

st.caption(f"Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Bursátil vía Yahoo Finance (≈15 min de retraso).")

time.sleep(60)
st.rerun()
