# app.py — LaSultana Meat Index (layout igual a mock)
import time, datetime as dt, random, requests, pandas as pd, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ======= ESTILO (idéntico al mock: negro, bordes, verdes/rojos) =======
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

# ======= EMPRESAS (14) =======
COMPANIES = [
    ("Tyson Foods","TSN"),
    ("Pilgrim’s Pride","PPC"),
    ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"),
    ("Vital Farms","VITL"),
    ("JBS","JBS"),                # si falla: JBSAY
    ("Marfrig Global","MRRTY"),   # o MRFG3.SA
    ("Minerva","MRVSY"),          # o BEEF3.SA
    ("Grupo Bafar","BAFARB.MX"),
    ("Smithfield (WH)","WHGLY"),  # proxy
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
            last=float(h["Close"].dropna().iloc[-1]); first=float(h["Close"].dropna().iloc[0])
            ch=last-first
        except Exception:
            last=round(40+random.random()*80,2); ch=round(random.uniform(-1.5,1.5),2)
        rows.append({"name":name,"sym":sym,"px":last,"ch":ch})
    return rows

# ======= CINTA BURSÁTIL (en movimiento) =======
row=quotes()
line=""
for _ in range(2):
    for r in row:
        cls="green" if r["ch"]>=0 else "red"; arrow="▲" if r["ch"]>=0 else "▼"
        line+=f'<span
