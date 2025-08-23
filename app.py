# app.py — LaSultana Meat Index (layout igual a mock)
import time, datetime as dt, random, requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ======= ESTILO =======
st.markdown("""
<style>
:root{
  --bg:#0a0f14; --panel:#0e151b; --line:#1f2b3a; --txt:#e9f3ff;
  --up:#25d07d; --down:#ff6b6b; --muted:#a9c7e4;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important}
.block-container{max-width:1400px;padding-top:8px}
h1{font-size:44px;margin:0 0 10px 4px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px}
.kpi{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:46px;font-weight:800}
.kpi .delta{font-size:18px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}
.grid{display:grid;grid-template-columns: 1.1fr 1fr 1fr; gap:12px}
.centerstack .box{margin-bottom:12px}
.table{width:100%}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line)}
.table th{text-align:left;color:var(--muted);font-weight:600}
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden}
.tape-inner{display:inline-block;white-space:nowrap;padding:8px 0;
            font-family:ui-monospace,Menlo,Consolas,monospace;
            animation:scroll 45s linear infinite}
.item{display:inline-block;margin:0 28px}
@keyframes scroll{0%{transform:translateX(100%)}100%{transform:translateX(-100%)}}
.footer{margin-top:12px}
</style>
""", unsafe_allow_html=True)

# ======= TÍTULO =======
st.markdown("<h1>LaSultana Meat Index®</h1>", unsafe_allow_html=True)

# ======= EMPRESAS =======
COMPANIES = [
    ("Tyson Foods","TSN"),
    ("Pilgrim’s Pride","PPC"),
    ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"),
    ("Vital Farms","VITL"),
    ("JBS","JBS"),                
    ("Marfrig Global","MRRTY"),   
    ("Minerva","MRVSY"),          
    ("Grupo Bafar","BAFARB.MX"),
    ("Smithfield (WH)","WHGLY"),  
    ("Seaboard","SEB"),
    ("Hormel Foods","HRL"),
    ("Grupo KUO","KUOB.MX"),
    ("Maple Leaf Foods","MFI.TO"),
]

@st.cache_data(ttl=60)
def quotes():
    rows=[]
    for name,sym in COMPANIES:
        try:
            h=yf.Ticker(sym).history(period="1d",interval="1m")
            last=float(h["Close"].dropna().iloc[-1])
            first=float(h["Close"].dropna().iloc[0])
            ch=last-first
        except Exception:
            last=round(40+random.random()*80,2)
            ch=round(random.uniform(-1.5,1.5),2)
        rows.append({"name":name,"sym":sym,"px":last,"ch":ch})
    return rows

# ======= CINTA BURSÁTIL =======
eq=quotes()
line=""
for _ in range(2):  # duplicamos para loop
    for r in eq:
        cls="green" if r["ch"]>=0 else "red"
        arrow="▲" if r["ch"]>=0 else "▼"
        line += (
            f"<span class='item'>{r['name']} ({r['sym']}) "
            f"<b class='{cls}'>{r['px']:.2f} {arrow} {abs(r['ch']):.2f}</b></span>"
        )
st.markdown(f"<div class='tape'><div class='tape-inner'>{line}</div></div>", unsafe_allow_html=True)

# ======= FX =======
@st.cache_data(ttl=60)
def usdmxn():
    try:
        j=requests.get("https://api.exchangerate.host/latest",
                       params={"base":"USD","symbols":"MXN"},timeout=8).json()
        return float(j["rates"]["MXN"])
    except Exception:
        return 18.50+random.uniform(-0.2,0.2)

fx=usdmxn()
live_cattle=185.32+random.uniform(-0.6,0.6)
lean_hogs=94.86+random.uniform(-0.6,0.6)
fx_d=random.choice([+0.02,-0.02])
lc_d=random.choice([+0.25,-0.25])
lh_d=random.choice([+0.40,-0.40])

# ======= LAYOUT PRINCIPAL =======
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# USD/MXN
st.markdown(f"""
<div class="card kpi">
  <div class="title">USD/MXN</div>
  <div class="big">{fx:,.4f}</div>
  <div class="delta {'green' if fx_d>=0 else 'red'}">{'▲' if fx_d>=0 else '▼'} {abs(fx_d):.02f}</div>
</div>
""", unsafe_allow_html=True)

# Centro: Live Cattle / Lean Hogs
st.markdown(f"""
<div class="centerstack">
  <div class="card box kpi">
    <div class="title">Live Cattle</div>
    <div class="big">{live_cattle:,.2f} <span class="muted">USD/cwt</span></div>
    <div class="delta {'green' if lc_d>=0 else 'red'}">{'▲' if lc_d>=0 else '▼'} {abs(lc_d):.02f}</div>
  </div>
  <div class="card box kpi">
    <div class="title">Lean Hogs</div>
    <div class="big">{lean_hogs:,.2f} <span class="muted">USD/cwt</span></div>
    <div class="delta {'green' if lh_d>=0 else 'red'}">{'▲' if lh_d>=0 else '▼'} {abs(lh_d):.02f}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Derecha: Piezas de Pollo
parts={"Pechuga":2.65,"Ala":1.98,"Pierna":1.32,"Muslo":1.29}
rows="".join([f"<tr><td>{k}</td><td style='text-align:right'>{v:,.2f}</td></tr>" for k,v in parts.items()])
st.markdown(f"""
<div class="card">
  <div class="title" style="font-size:18px;color:var(--txt);margin-bottom:6px">Piezas de Pollo</div>
  <table class="table">
    <thead><tr><th>Producto</th><th style="text-align:right">USD/lb</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # cierre grid

# ======= BANDA DE NOTICIAS =======
news=[
 "USMEF: exportaciones de cerdo a México continúan firmes; demanda retail sostiene hams.",
 "USDA: beef cutout estable; middle meats firmes, rounds suaves.",
 "Poultry: oferta amplia presiona piezas oscuras; pechuga jumbo estable.",
 "FX: fortaleza del peso abarata importaciones; revisar spreads USD/lb → MXN/kg."
]
i=int(time.time()//30)%len(news)
j=(i+1)%len(news)
st.markdown(f"""
<div class="card footer">
  <div>{news[i]}</div>
  <div class="muted">{news[j]}</div>
</div>
""", unsafe_allow_html=True)

st.caption(f"Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Cotizaciones Yahoo Finance (pueden venir con ~15 min de retraso).")

time.sleep(60)
st.rerun()
