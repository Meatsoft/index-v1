# app.py — LaSultana Meat Index (Banxico FIX con fallback a Spot)
import os, json, re, time, random, datetime as dt
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

.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:32px 0 28px}

/* Cinta superior */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* Grid */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:18px}

.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}
.unit-inline{font-size:0.7em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* Tabla Pollo */
.poultry-table{width:100%}
.poultry-table table{width:100%;border-collapse:collapse}
.poultry-table th,.poultry-table td{padding:10px;border-bottom:1px solid var(--line);vertical-align:middle}
.poultry-table th{text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px}
.poultry-table td:first-child{font-size:110%;}
.unit-inline--poultry{font-size:0.60em;color:var(--muted);font-weight:600;letter-spacing:.3px}
.price-lg{font-size:48px;font-weight:900;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}
.poultry-table td:last-child{text-align:right}

/* Noticias */
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 18px}
.tape-news-track{display:flex;width:max-content;will-change:transform;animation:marqueeNewsFast 150s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNewsFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}
.badge{display:inline-block;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;margin-left:8px}
</style>
""", unsafe_allow_html=True)

# ============== HELPERS
def fmt2(x): return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x): return f"{x:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ============== LOGO
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ============== USD/MXN Banxico FIX con fallback Spot
BANXICO_SERIES = "SF43718"
BANXICO_TOKEN = os.getenv("BANXICO_TOKEN", "").strip()
FX_FILE = "fx_last.json"

def load_fx():
    if os.path.exists(FX_FILE):
        try: return json.load(open(FX_FILE))
        except: return None
def save_fx(val, src):
    try: json.dump({"val":val,"src":src,"ts":dt.datetime.now().isoformat()}, open(FX_FILE,"w"))
    except: pass

def get_fx():
    # 1. Banxico FIX
    if BANXICO_TOKEN:
        try:
            url=f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{BANXICO_SERIES}/datos/oportuno"
            r=requests.get(url,headers={"Bmx-Token":BANXICO_TOKEN},timeout=10).json()
            dato=r["bmx"]["series"][0]["datos"][0]
            val=float(dato["dato"])
            save_fx(val,"Banxico FIX")
            return val,"Banxico FIX"
        except: pass
    # 2. Fallback Spot
    try:
        r=requests.get("https://api.exchangerate.host/latest?base=USD&symbols=MXN",timeout=8).json()
        val=float(r["rates"]["MXN"])
        save_fx(val,"Spot")
        return val,"Spot"
    except: pass
    # 3. Snapshot
    snap=load_fx()
    if snap: return snap["val"], snap["src"]+" (último)"
    return None,""

# ============== Render USD/MXN
fx_val,fx_src=get_fx()
cls="green" if fx_val else "muted"
price_html=f"<div class='big'>{fmt4(fx_val) if fx_val else 'N/D'} <span class='unit-inline'>FIX</span></div>"
st.markdown(f"""
<div class="card">
  <div class="kpi">
    <div class="left">
      <div class="title">USD/MXN ({fx_src})</div>
      {price_html}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
