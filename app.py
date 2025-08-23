import streamlit as st
import random, datetime as dt

st.set_page_config(page_title="LaSultana Meat Index®", layout="wide")

# --- LOGO ---
st.image("ILSMeatIndex.png", width=180)
st.markdown("# LaSultana Meat Index®")

# --- MOCK DATA (luego conectamos APIs) ---
fx = 18.53 + random.uniform(-0.1, 0.1)
cattle = 185 + random.uniform(-2, 2)
hogs = 95 + random.uniform(-1, 1)
turkey = 1.22
chicken_live = 1.10
parts = {
    "Pechuga": 2.65,
    "Ala": 1.98,
    "Pierna": 1.32,
    "Muslo": 1.29
}

# --- TICKER (demo con empresas) ---
companies = [
    ("Tyson", "TSN", 91.5, +0.3),
    ("Pilgrim’s", "PPC", 26.4, -0.2),
    ("BRF", "BRFS", 2.8, +0.1),
    ("Cal-Maine", "CALM", 55.3, -0.4),
    ("Vital Farms", "VITL", 15.2, +0.2)
]
ticker = " | ".join([f"{n} {s} {p:.2f} {'▲' if ch>=0 else '▼'}{abs(ch):.2f}" for n,s,p,ch in companies])
st.markdown(f"<marquee>{ticker}</marquee>", unsafe_allow_html=True)

# --- SNAPSHOT ---
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("USD/MXN")
    st.metric("Dólar", f"{fx:.4f}", "+0.02")
with col2:
    st.subheader("Live Cattle")
    st.metric("USD/cwt", f"{cattle:.2f}", "-0.25")
with col3:
    st.subheader("Lean Hogs")
    st.metric("USD/cwt", f"{hogs:.2f}", "-0.40")

col4, col5, col6 = st.columns(3)
with col4:
    st.subheader("Pavo vivo")
    st.metric("USD/lb", f"{turkey:.2f}")
with col5:
    st.subheader("Pollo vivo")
    st.metric("USD/lb", f"{chicken_live:.2f}")
with col6:
    st.subheader("Piezas de Pollo")
    for k,v in parts.items():
        st.write(f"{k}: {v:.2f} USD/lb")

# --- MENSAJES ---
msgs = [
    "USMEF: exportaciones de cerdo a México continúan firmes.",
    "USDA: beef cutout estable; middle meats firmes.",
    "Mayor oferta de pollo presiona piezas oscuras."
]
st.info(random.choice(msgs) + f" | Última actualización {dt.datetime.now().strftime('%H:%M:%S')}")
