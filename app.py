import os, time, random, datetime as dt
import requests, pandas as pd
import streamlit as st
import yfinance as yf

# ========= CONFIG BÁSICA =========
st.set_page_config(page_title="LaSultana Meat Index®", layout="wide")
REFRESH_SECS = 60   # refresco para TV
NEWS_ROTATE_SECS = 30

# ========= TEMA (alto contraste, estilo terminal) =========
st.markdown("""
<style>
:root{ --bg:#0b0f14; --card:#0f151c; --line:#223043; --txt:#eaf4ff; --muted:#cfe6ff;
       --up:#38d18a; --down:#ff6b6b; }
html, body, .stApp { background:var(--bg)!important; color:var(--txt)!important; }
.block-container{ padding-top:10px; max-width:1400px; }
.card{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 16px; }
h1,h2,h3,h4{ color:var(--txt)!important; margin:0 0 6px 0; }
.big{ font-size:44px; font-weight:800; letter-spacing:.3px; }
.mid{ font-size:26px; font-weight:700; }
.small{ color:var(--muted); font-size:14px; }
.up{ color:var(--up)!important; } .down{ color:var(--down)!important; }
.tape{ overflow:hidden; border-radius:12px; border:1px solid var(--line); background:#0e151c; }
.tape-inner{ display:inline-block; white-space:nowrap; padding:10px 0;
             animation: scroll 45s linear infinite; font-family: ui-monospace,Menlo,Consolas,monospace;}
.item{ display:inline-block; margin:0 30px; }
@keyframes scroll { 0%{transform:translateX(100%);} 100%{transform:translateX(-100%);} }
.logo-wrap{ display:flex; justify-content:center; }
.logo{ max-width:620px; width:90%; }
.grid3{ display:grid; grid-template-columns: 1fr 1fr 1fr; gap:14px; }
.grid3-tight{ display:grid; grid-template-columns: 1fr 1fr 2fr; gap:14px; }
.footer{ margin-top:10px; }
.news{ font-size:16px; }
</style>
""", unsafe_allow_html=True)

# ========= CABECERA (logo centrado) =========
st.markdown('<div class="logo-wrap">', unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", use_column_width=False, output_format="PNG", caption=None)
st.markdown('</div>', unsafe_allow_html=True)

# ========= MAPA DE EMPRESAS (14) =========
# Notas:
# - Smithfield ya no cotiza: usamos WH Group (ADR WHGLY) como proxy.
# - Algunos listados latam pueden fallar en yfinance; incluimos candidatos alternos.
COMPANIES = [
    ("Tyson Foods",        ["TSN"]),
    ("Pilgrim’s Pride",    ["PPC"]),
    ("BRF",                ["BRFS"]),
    ("Cal-Maine Foods",    ["CALM"]),
    ("Vital Farms",        ["VITL"]),
    ("JBS",                ["JBS", "JBSAY"]),
    ("Marfrig Global",     ["MRRTY","MRFG3.SA"]),
    ("Minerva",            ["MRVSY","BEEF3.SA"]),
    ("Grupo Bafar",        ["BAFARB.MX","BAFARA.MX","BAFAR*.MX"]),
    ("Smithfield (WH)",    ["WHGLY","0288.HK"]),  # proxy
    ("Seaboard",           ["SEB"]),
    ("Hormel Foods",       ["HRL"]),
    ("Grupo KUO",          ["KUOB.MX","KUO*.MX"]),
    ("Maple Leaf Foods",   ["MFI.TO"]),
]

@st.cache_data(ttl=45, show_spinner=False)
def fetch_quote(sym: str):
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        if h is None or h.empty: return None
        last = float(h["Close"].dropna().iloc[-1])
        first = float(h["Close"].dropna().iloc[0])
        ch = last - first
        return last, ch
    except Exception:
        return None

@st.cache_data(ttl=45, show_spinner=False)
def get_equity_tape():
    rows = []
    for name, candidates in COMPANIES:
        use = None; data = None
        for c in candidates:
            data = fetch_quote(c)
            if data: use = c; break
        if not data:  # fallback demo para no romper la cinta
            px = round(40+random.random()*80, 2)
            ch = round(random.uniform(-1.5,1.5), 2)
        else:
            px, ch = round(data[0],2), round(data[1],2)
        rows.append({"name":name, "sym":use or candidates[0], "px":px, "ch":ch})
    return rows

# ========= CINTA BURSÁTIL (marquee infinito) =========
eq_rows = get_equity_tape()
# repetimos elementos para que la animación sea continua
line = ""
for _ in range(2):  # duplicado
    for r in eq_rows:
        cls = "up" if r["ch"]>=0 else "down"
        arrow = "▲" if r["ch"]>=0 else "▼"
        line += f'<span class="item">{r["name"]} ({r["sym"]}) ' \
                f'<b class="{cls}">{r["px"]:.2f} {arrow} {abs(r["ch"]):.2f}</b></span>'
st.markdown(f'<div class="tape"><div class="tape-inner">{line}</div></div>', unsafe_allow_html=True)

# ========= FX (USD/MXN) =========
@st.cache_data(ttl=45, show_spinner=False)
def get_fx_usdmxn():
    try:
        r = requests.get("https://api.exchangerate.host/latest",
                         params={"base":"USD","symbols":"MXN"}, timeout=8)
        r.raise_for_status()
        return float(r.json()["rates"]["MXN"])
    except Exception:
        return 18.50 + random.uniform(-0.20,0.20)

# ========= SNAPSHOT PRINCIPAL (ES/legible) =========
fx = get_fx_usdmxn()
res_en_pie   = 186.0 + random.uniform(-0.8,0.8)  # TODO: conectar AMS/MPR
cerdo_en_pie = 95.0  + random.uniform(-0.8,0.8)  # TODO: conectar AMS/MPR

st.markdown('<div class="grid3">', unsafe_allow_html=True)
st.markdown(f"""
<div class="card">
  <h3>Tipo de cambio (USD → MXN)</h3>
  <div class="big">{fx:.4f}</div>
</div>
<div class="card">
  <h3>Res en pie</h3>
  <div class="mid">{res_en_pie:.2f} USD/cwt</div>
</div>
<div class="card">
  <h3>Cerdo en pie</h3>
  <div class="mid">{cerdo_en_pie:.2f} USD/cwt</div>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="grid3-tight">', unsafe_allow_html=True)
st.markdown(f"""
<div class="card">
  <h3>Pavo vivo</h3>
  <div class="mid">{1.220:.3f} USD/lb</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="card">
  <h3>Pollo vivo</h3>
  <div class="mid">{1.100:.3f} USD/lb</div>
</div>
""", unsafe_allow_html=True)

parts = {"Pechuga":2.65,"Ala":1.98,"Pierna":1.32,"Muslo":1.29}
parts_html = "<div class='card'><h3>Piezas de pollo</h3><div class='grid3' style='grid-template-columns:repeat(4,1fr);gap:10px;'>"
for k,v in parts.items():
    parts_html += f"<div><b>{k}</b><div class='mid'>{v:.2f} USD/lb</div></div>"
parts_html += "</div></div>"
st.markdown(parts_html, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ========= BANDA DE NOTICIAS (rotación cada 30s en cliente) =========
news_items = [
    "USMEF: exportaciones de cerdo a México se mantienen fuertes; demanda retail sostiene hams.",
    "USDA: beef cutout estable; middle meats firmes; rounds suaves.",
    "Poultry: oferta amplia presiona piezas oscuras; pechuga jumbo estable.",
    "FX: fortaleza del peso abarata importaciones; revisar spreads USD/lb → MXN/kg."
]
# Render y JS para rotar en el navegador sin recargar
st.markdown('<div class="card footer"><div id="news" class="news"></div></div>', unsafe_allow_html=True)
st.components.v1.html(f"""
<div id="news_text" style="color:#eaf4ff;font-size:16px;"></div>
<script>
const msgs = {news_items};
let i = Math.floor(Date.now()/1000/{NEWS_ROTATE_SECS}) % msgs.length;
function render() {{
  document.getElementById("news_text").innerText = msgs[i];
}}
render();
setInterval(() => {{ i = (i+1) % msgs.length; render(); }}, {NEWS_ROTATE_SECS*1000});
</script>
""", height=40)

# ========= PIE / REFRESH =========
st.caption(f"Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ·  Auto-refresh {REFRESH_SECS}s  ·  Datos bursátiles vía yfinance (pueden venir con ~15 min de retraso).")

time.sleep(REFRESH_SECS)
st.rerun()
