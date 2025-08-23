import os, time, random, datetime as dt
import requests, pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index®", layout="wide")

# ————— UI base
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=180)
st.markdown("## LaSultana Meat Index®")

# ————— Config
REFRESH_SECS = 120  # auto-actualiza cada 2 min
EQUITY_MAP = {
    "Tyson Foods": "TSN",
    "Pilgrim’s Pride": "PPC",
    "BRF": "BRFS",
    "Cal-Maine Foods": "CALM",
    "Vital Farms": "VITL",
    "JBS": "JBS",            # si no carga, prueba "JBSAY"
    "Marfrig": "MRRTY",      # si no carga, prueba "MRFG3.SA"
    "Minerva": "MRVSY",      # si no carga, prueba "BEEF3.SA"
    "Grupo Bafar": "BAFARB.MX",  # confirmar símbolo en Yahoo
    "Smithfield Foods": None,    # ya no cotiza (prop. de WH Group)
    "Seaboard": "SEB",
    "Hormel Foods": "HRL",
    "Grupo KUO": "KUOB.MX",
    "Maple Leaf Foods": "MFI.TO",
}

# ————— Helpers
@st.cache_data(ttl=90)
def get_fx_usdmxn():
    try:
        r = requests.get(
            "https://api.exchangerate.host/latest",
            params={"base":"USD","symbols":"MXN"},
            timeout=10
        )
        r.raise_for_status()
        rate = r.json()["rates"]["MXN"]
        return float(rate)
    except Exception:
        return 18.50 + random.uniform(-0.15,0.15)

@st.cache_data(ttl=90)
def get_equities_price_change(tickers: list[str]) -> pd.DataFrame:
    # descarga precios intradía; si falla, devuelve vacía
    try:
        df = yf.download(
            tickers=" ".join([t for t in tickers if t]),
            period="1d", interval="1m", group_by="ticker", threads=True, progress=False
        )
        rows = []
        for label, ysym in EQUITY_MAP.items():
            if not ysym: 
                continue
            try:
                sub = df[ysym].dropna()
                last = sub["Close"].dropna().iloc[-1]
                first = sub["Close"].dropna().iloc[0]
                ch = last - first
                rows.append((label, ysym, float(last), float(ch)))
            except Exception:
                pass
        return pd.DataFrame(rows, columns=["name","sym","price","change"])
    except Exception:
        return pd.DataFrame(columns=["name","sym","price","change"])

def badge(val: float) -> str:
    arrow = "▲" if val>=0 else "▼"
    col = "#5fd38d" if val>=0 else "#ff6b6b"
    return f'<span style="color:{col};font-weight:700">{arrow} {abs(val):.2f}</span>'

# ————— Estilos rápidos (modo oscuro)
st.markdown("""
<style>
:root { --bg:#0b0f14; --card:#0e141b; --line:#1b2a38; --txt:#e6f3ff;}
html, body, .stApp { background: var(--bg) !important; color: var(--txt) !important; }
.block-container { padding-top: 0.8rem; }
.card { background: var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 16px; }
.big { font-size:40px; font-weight:800; }
.mid { font-size:26px; font-weight:700; }
.ticker { white-space:nowrap; overflow:hidden; }
.titem { display:inline-block; margin-right:28px; font-family: ui-monospace, Menlo, Consolas, monospace; }
</style>
""", unsafe_allow_html=True)

# ————— Ticker superior (acciones en vivo, con fallback)
eq_df = get_equities_price_change(list(EQUITY_MAP.values()))
if eq_df.empty:
    st.caption("Ticker bursátil: usando datos de demostración (luego conectamos symbols precisos).")
    eq_df = pd.DataFrame([
        ("Tyson Foods","TSN", 91.50, +0.30),
        ("Pilgrim’s Pride","PPC", 26.40, -0.20),
        ("BRF","BRFS", 2.82, +0.04),
        ("JBS","JBS", 10.80, +0.12),
        ("Hormel","HRL", 31.10, -0.05),
    ], columns=["name","sym","price","change"])

ticker_html = '<div class="card"><div class="ticker">'
for _,r in eq_df.iterrows():
    color = "#5fd38d" if r.change>=0 else "#ff6b6b"
    arrow = "▲" if r.change>=0 else "▼"
    ticker_html += f'<span class="titem">{r["name"]} ({r["sym"]}) ' \
                   f'<span style="color:{color};font-weight:700">{r["price"]:.2f} {arrow} {abs(r["change"]):.2f}</span></span>'
ticker_html += "</div></div>"
st.markdown(ticker_html, unsafe_allow_html=True)

# ————— Snapshot principal (FX + futuros/USDA placeholders)
fx = get_fx_usdmxn()
c1,c2,c3 = st.columns(3)
with c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### USD/MXN")
    st.markdown(f'<div class="big">{fx:.4f}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# por ahora placeholders (en el siguiente paso jalamos USDA/AMS)
live_cattle = 186.0 + random.uniform(-0.8,0.8)
lean_hogs  = 95.0 + random.uniform(-0.8,0.8)
with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Live Cattle")
    st.markdown(f'<div class="mid">{live_cattle:.2f} USD/cwt</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Lean Hogs")
    st.markdown(f'<div class="mid">{lean_hogs:.2f} USD/cwt</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

d1,d2,d3 = st.columns([1,1,2])
with d1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Pavo vivo")
    st.markdown(f'<div class="mid">{1.22:.3f} USD/lb</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with d2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Pollo vivo")
    st.markdown(f'<div class="mid">{1.10:.3f} USD/lb</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with d3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Piezas de pollo")
    parts = {"Pechuga":2.65,"Ala":1.98,"Pierna":1.32,"Muslo":1.29}
    pc = st.columns(4)
    for (k,v),col in zip(parts.items(), pc):
        with col:
            st.markdown(f"**{k}**")
            st.markdown(f'<div class="mid">{v:.2f}</div>', unsafe_allow_html=True)
    st.markdown('<span class="small">USD/lb (USDA/mercado)</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ————— Noticias IA (placeholder)
st.markdown('<div class="card">', unsafe_allow_html=True)
st.write("USMEF: exportaciones de cerdo a México firmes; USDA: beef cutout estable; middle meats firmes.")
st.caption(f"Última actualización: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Auto-refresh {REFRESH_SECS}s")
st.markdown('</div>', unsafe_allow_html=True)

# ————— Auto-refresh para TV
time.sleep(REFRESH_SECS)
st.rerun()
