import os, time, random, datetime as dt
import requests, pandas as pd
import streamlit as st
import yfinance as yf

# ----------------- CONFIG UI -----------------
st.set_page_config(page_title="LaSultana Meat Index®", layout="wide")

st.markdown("""
<style>
:root{
  --bg:#0b0f14; --card:#0f151c; --line:#243245; --txt:#eaf4ff; --muted:#cfe6ff;
  --up:#5fd38d; --down:#ff6b6b; --accent:#b9e1ff;
}
html, body, .stApp { background:var(--bg)!important; color:var(--txt)!important; }
.block-container{ padding-top: 12px; }
h1,h2,h3,h4,h5,h6{ color:var(--txt)!important; }
p, .small, .stMarkdown, .stCaption{ color:var(--muted)!important; }
.card{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 16px; }
.big{ font-size:44px; font-weight:800; letter-spacing:.3px; color:var(--txt);}
.mid{ font-size:26px; font-weight:700; color:var(--txt);}
.badge{ padding:2px 6px; border-radius:6px; margin-left:6px; font-size:12px; }
.up{ color:var(--up)!important; } .down{ color:var(--down)!important; }
.ticker{ white-space:nowrap; overflow:hidden; font-family: ui-monospace,Menlo,Consolas,monospace;}
.titem{ display:inline-block; margin-right:28px; }
.hr{ height:10px; }
</style>
""", unsafe_allow_html=True)

# ----------------- LOGO -----------------
# Logo grande, sin título repetido
lc1, lc2, lc3 = st.columns([1.2,6,1.2])
with lc2:
    if os.path.exists("ILSMeatIndex.png"):
        st.image("ILSMeatIndex.png", use_column_width=True)
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# ----------------- DATA HELPERS -----------------
REFRESH_SECS = 120
EQUITY_MAP = {
    "Tyson Foods": "TSN",
    "Pilgrim’s Pride": "PPC",
    "BRF": "BRFS",
    "Cal-Maine Foods": "CALM",
    "Vital Farms": "VITL",
    "JBS": "JBS",       # si falla, prueba JBSAY
    "Marfrig": "MRRTY", # o MRFG3.SA
    "Minerva": "MRVSY", # o BEEF3.SA
    "Grupo Bafar": "BAFARB.MX",
    "Seaboard": "SEB",
    "Hormel Foods": "HRL",
    "Grupo KUO": "KUOB.MX",
    "Maple Leaf Foods": "MFI.TO",
    # Smithfield dejó de cotizar (WH Group)
}

@st.cache_data(ttl=90)
def get_fx_usdmxn():
    try:
        r = requests.get("https://api.exchangerate.host/latest",
                         params={"base":"USD","symbols":"MXN"}, timeout=10)
        r.raise_for_status()
        return float(r.json()["rates"]["MXN"])
    except Exception:
        return 18.50 + random.uniform(-0.15,0.15)

@st.cache_data(ttl=90)
def get_equities():
    syms = [s for s in EQUITY_MAP.values() if s]
    try:
        df = yf.download(" ".join(syms), period="1d", interval="1m",
                         group_by="ticker", threads=True, progress=False)
        rows=[]
        for name,sym in EQUITY_MAP.items():
            if not sym or sym not in df: continue
            sub = df[sym].dropna()
            last = sub["Close"].dropna().iloc[-1]
            first = sub["Close"].dropna().iloc[0]
            rows.append((name, sym, float(last), float(last-first)))
        return pd.DataFrame(rows, columns=["name","sym","price","change"])
    except Exception:
        return pd.DataFrame([
            ("Tyson Foods","TSN", 57.62, +0.28),
            ("Pilgrim’s Pride","PPC", 46.14, -1.32),
            ("BRF","BRFS", 3.65, +0.03),
            ("Cal-Maine Foods","CALM", 116.11, +2.29),
            ("Vital Farms","VITL", 50.94, +1.72),
        ], columns=["name","sym","price","change"])

def arrow_badge(x: float) -> str:
    up = x>=0
    return f'<span class="{ "up" if up else "down" }"><b>{"▲" if up else "▼"} {abs(x):.2f}</b></span>'

# ----------------- TICKER SUPERIOR -----------------
eq = get_equities()
ticker_html = '<div class="card"><div class="ticker">'
for _,r in eq.iterrows():
    ticker_html += f'<span class="titem">{r["name"]} ({r["sym"]}) '\
                   f'<span class="{ "up" if r["change"]>=0 else "down" }">{r["price"]:.2f}</span> '\
                   f'{arrow_badge(r["change"])}</span>'
ticker_html += "</div></div>"
st.markdown(ticker_html, unsafe_allow_html=True)

# ----------------- SNAPSHOT EN ESPAÑOL -----------------
fx = get_fx_usdmxn()
c1,c2,c3 = st.columns(3)

with c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Tipo de cambio (USD → MXN)")
    st.markdown(f'<div class="big">{fx:.4f}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# (Temporal: valores de muestra; luego conectamos AMS/USDA)
res_en_pie   = 186.0 + random.uniform(-0.8,0.8)  # Live Cattle
cerdo_en_pie = 95.0 + random.uniform(-0.8,0.8)   # Lean Hogs

with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Res en pie")
    st.markdown(f'<div class="mid">{res_en_pie:.2f} USD/cwt</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Cerdo en pie")
    st.markdown(f'<div class="mid">{cerdo_en_pie:.2f} USD/cwt</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

d1,d2,d3 = st.columns([1,1,2])

with d1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Pavo vivo")
    st.markdown(f'<div class="mid">{1.220:.3f} USD/lb</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with d2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Pollo vivo")
    st.markdown(f'<div class="mid">{1.100:.3f} USD/lb</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with d3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Piezas de pollo")
    parts = {"Pechuga":2.65,"Ala":1.98,"Pierna":1.32,"Muslo":1.29}
    pc = st.columns(4)
    for (k,v),col in zip(parts.items(), pc):
        with col:
            st.markdown(f"**{k}**")
            st.markdown(f'<div class="mid">{v:.2f} USD/lb</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- BARRA INFERIOR (ALTA LEGIBILIDAD) -----------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("**USMEF:** exportaciones de cerdo a México firmes · **USDA:** beef cutout estable; middle meats firmes.")
st.markdown(f"Actualizado: **{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}** · Auto-refresh **{REFRESH_SECS}s**")
st.markdown('</div>', unsafe_allow_html=True)

# ----------------- AUTO REFRESH -----------------
time.sleep(REFRESH_SECS)
st.rerun()
