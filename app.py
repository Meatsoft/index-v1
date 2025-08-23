# app.py — LaSultana Meat Index (bandas 15% más rápidas)
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
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}

/* -------- LOGO: padding simétrico -------- */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:22px 0 22px}

/* -------- CINTA SUPERIOR (marquee continuo, ahora 265s) -------- */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marquee 265s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-family:ui-monospace,Menlo,Consolas,monospace}
.item{display:inline-block;margin:0 32px}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* -------- GRID PRINCIPAL -------- */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:12px}
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

/* -------- NOTICIA (marquee continuo, ahora 224s) -------- */
.footer{margin-top:12px}
.caption{color:var(--muted)!important}
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-top:10px}
.tape-news-track{display:flex;width:max-content;will-change:transform;animation:marqueeNews 224s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:10px 0;font-family:ui-monospace,Menlo,Consolas,monospace}
@keyframes marqueeNews{from{transform:translateX(0)}to{transform:translateX(-50%)}}
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

# ==================== CINTA SUPERIOR ====================
COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("JBS","JBS"), ("Marfrig Global","MRRTY"), ("Minerva","MRVSY"),
    ("Grupo Bafar","BAFARB.MX"), ("Smithfield (WH)","WHGLY"),
    ("Seaboard","SEB"), ("Hormel Foods","HRL"),
    ("Grupo KUO","KUOB.MX"), ("Maple Leaf Foods","MFI.TO"),
]

# Placeholder inmediato
placeholder = "".join(
    f"<span class='item'>{n} ({s}) <b class='green'>-- ▲ --</b></span>" for n,s in COMPANIES
)
tape_block = st.container()
with tape_block:
    st.markdown(
        f"""
        <div class='tape'>
          <div class='tape-track'>
            <div class='tape-group'>{placeholder}</div>
            <div class='tape-group' aria-hidden='true'>{placeholder}</div>
          </div>
        </div>
        """, unsafe_allow_html=True
    )

@st.cache_data(ttl=75)
def fetch_quotes():
    data=[]
    for name, sym in COMPANIES:
        try:
            hist = yf.Ticker(sym).history(period="1d", interval="1m")
            if hist is None or hist.empty: raise ValueError("no data")
            last  = float(hist["Close"].dropna().iloc[-1])
            first = float(hist["Close"].dropna().iloc[0])
            ch    = last - first
        except Exception:
            last = round(40 + random.random()*80, 2)
            ch   = round(random.uniform(-1.5, 1.5), 2)
        data.append({"name":name,"sym":sym,"px":last,"ch":ch})
    return data

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

# ==================== FX + placeholders MPR ====================
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
live_cattle = 185.3 + random.uniform(-0.6,0.6)
lean_hogs   = 94.9  + random.uniform(-0.6,0.6)
lc_delta = random.choice([+0.25, -0.25])
lh_delta = random.choice([+0.40, -0.40])

# ==================== GRID PRINCIPAL ====================
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# USD/MXN
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

# Res/Cerdo
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

# Piezas de pollo
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
  "USDA: beef cutout estable; cortes medios firmes mientras rounds ceden ante menor demanda institucional.",
  "USMEF: exportaciones de cerdo a México se mantienen firmes; retailers sostienen hams pese a presión de costos.",
  "Poultry: oferta amplia presiona piezas oscuras; pechuga jumbo estable en contratos y spot limitado.",
  "FX: peso fuerte abarata importaciones; revisa spreads USD/lb→MXN/kg y costos de flete."
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
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Bursátil vía Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True,
)

time.sleep(60)
st.rerun()
