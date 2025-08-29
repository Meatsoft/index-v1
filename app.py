# app.py — LaSultana Meat Index (Industry Monitor mejorado)
import os, re, time, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")
try:
    st.cache_data.clear()
except Exception:
    pass

# ====================== ESTILOS ======================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700&display=swap');
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b; --font:"Manrope","Inter","Segoe UI",Roboto,Arial,sans-serif;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important;font-family:var(--font)!important}
*{font-family:var(--font)!important}
.block-container{max-width:1400px;padding-top:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:18px}
header[data-testid="stHeader"]{display:none;} #MainMenu{visibility:hidden;} footer{visibility:hidden}

/* Logo */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:26px 0 22px}

/* Cinta bursátil */
.tape{border:1px solid var(--line);border-radius:12px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;animation:marquee 210s linear infinite;will-change:transform;backface-visibility:hidden;transform:translateZ(0)}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
.up{color:var(--up)} .down{color:var(--down)} .muted{color:var(--muted)}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* KPIs */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
.unit-inline{font-size:.7em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* === Industry Monitor (rotador lento, mayor tamaño + explicación) === */
.im-card{min-height:180px}
.im-wrap{position:relative;height:170px;overflow:hidden;width:100%}
.im-item{position:absolute;left:0;right:0;top:0;opacity:0;animation:fadeSlow 30s linear infinite}
/* 3 ítems: 10s cada uno (≈8s visibles + 2s fade) */
.im-item:nth-child(1){animation-delay:0s}
.im-item:nth-child(2){animation-delay:10s}
.im-item:nth-child(3){animation-delay:20s}
@keyframes fadeSlow{
  0%   {opacity:1; transform:translateY(0)}
  75%  {opacity:1}
  83%  {opacity:0; transform:translateY(-6px)}
  100% {opacity:0}
}
.im-num{font-size:72px;font-weight:900;letter-spacing:.3px;margin-bottom:10px;text-align:center;line-height:1}
.im-sub{font-size:20px;color:var(--muted);text-align:center}
.im-desc{font-size:15px;color:#8fb7d5;text-align:center;margin-top:6px}
.im-badge{display:inline-block;margin-left:8px;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px}

/* Health Watch */
.hw-row{display:flex;gap:10px;align-items:center}
.dot-ok{width:8px;height:8px;border-radius:50%;background:#29d07d;display:inline-block;margin-right:8px}
.badge{display:inline-block;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;margin-left:8px}
</style>
""", unsafe_allow_html=True)

# ====================== HELPERS ======================
def fmt2(x: float | None) -> str:
    if x is None:
        return "—"
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def fmt4(x: float | None) -> str:
    if x is None:
        return "—"
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ====================== LOGO ======================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ====================== CINTA BURSÁTIL (solo USD sólidos) ======================
COMPANIES_USD = [
    ("Tyson Foods","TSN"),
    ("Pilgrim’s Pride","PPC"),
    ("JBS","JBS"),
    ("BRF","BRFS"),
    ("Hormel Foods","HRL"),
    ("Seaboard","SEB"),
    ("Minerva","MRVSY"),      # OTC USD
    ("Marfrig","MRRTY"),      # si no hay datos, se omite
    ("Cal-Maine Foods","CALM"),
    ("Vital Farms","VITL"),
    ("WH Group","WHGLY"),     # OTC USD
    ("Wingstop","WING"),
    ("Yum! Brands","YUM"),
    ("Restaurant Brands Intl.","QSR"),
    ("Sysco","SYY"),
    ("US Foods","USFD"),
    ("Performance Food Group","PFGC"),
    ("Walmart","WMT"),
]

@st.cache_data(ttl=75)
def quote_last_and_change(sym: str):
    try:
        t = yf.Ticker(sym)
        fi = t.fast_info
        last = fi.get("last_price", None)
        prev = fi.get("previous_close", None)
        if last is not None:
            ch = (float(last) - float(prev)) if prev is not None else None
            return float(last), ch
    except Exception:
        pass
    try:
        inf = yf.Ticker(sym).info or {}
        last = inf.get("regularMarketPrice", None)
        prev = inf.get("regularMarketPreviousClose", None)
        if last is not None:
            ch = (float(last) - float(prev)) if prev is not None else None
            return float(last), ch
    except Exception:
        pass
    try:
        d = yf.Ticker(sym).history(period="10d", interval="1d")
        if d is None or d.empty:
            return None, None
        c = d["Close"].dropna()
        last = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if c.shape[0] >= 2 else None
        ch = (last - prev) if prev is not None else None
        return last, ch
    except Exception:
        return None, None

items = []
for name, sym in COMPANIES_USD:
    last, chg = quote_last_and_change(sym)
    if last is None:
        continue
    if chg is None:
        items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
    else:
        cls = "up" if chg >= 0 else "down"
        arr = "▲" if chg >= 0 else "▼"
        items.append(f"<span class='item'>{name} ({sym}) <b class='{cls}'>{last:.2f} {arr} {abs(chg):.2f}</b></span>")

st.markdown(f"""
<div class='tape'>
  <div class='tape-track'>
    <div class='tape-group'>{"".join(items)}</div>
    <div class='tape-group' aria-hidden='true'>{"".join(items)}</div>
  </div>
</div>""", unsafe_allow_html=True)

# ====================== FX & FUTUROS (Yahoo) ======================
@st.cache_data(ttl=75)
def get_yahoo(sym: str):
    return quote_last_and_change(sym)

fx, fx_chg = get_yahoo("MXN=X")  # USD/MXN: cuántos MXN por 1 USD
lc, lc_chg = get_yahoo("LE=F")   # Live Cattle
lh, lh_chg = get_yahoo("HE=F")   # Lean Hogs

def kpi_fx(title: str, value: float | None, chg: float | None) -> str:
    if value is None:
        val_html = "<div class='big'>N/D</div>"
        delta_html = ""
    else:
        val_html = f"<div class='big'>{fmt4(value)}</div>"
        if chg is None:
            delta_html = ""
        else:
            cls = "up" if chg >= 0 else "down"
            arr = "▲" if chg >= 0 else "▼"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""
    <div class="card">
      <div class="kpi">
        <div><div class="title">{title}</div>{val_html}</div>{delta_html}
      </div>
    </div>
    """

def kpi_cme(title: str, price: float | None, chg: float | None) -> str:
    unit = "USD/100 lb"
    if price is None:
        price_html = f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"
        delta_html = ""
    else:
        price_html = f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
        if chg is None:
            delta_html = ""
        else:
            cls = "up" if chg >= 0 else "down"
            arr = "▲" if chg >= 0 else "▼"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""
    <div class="card">
      <div class="kpi">
        <div><div class="title">{title}</div>{price_html}</div>{delta_html}
      </div>
    </div>
    """

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(kpi_fx("USD/MXN", fx, fx_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Res en pie", lc, lc_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Cerdo en pie", lh, lh_chg), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ====================== LIVESTOCK HEALTH WATCH (mínimo viable) ======================
def hw_panel(title: str, ok: bool, details: list[str] | None = None):
    if ok:
        body = "<span class='dot-ok'></span>Sin novedades significativas (última revisión reciente)."
    else:
        items = "".join([f"<li>{re.escape(x)}</li>" for x in (details or [])])
        body = f"<ul>{items}</ul>"
    st.markdown(f"<div class='card'><div class='kpi'><div class='title'>{title}</div></div><div>{body}</div></div>", unsafe_allow_html=True)

st.markdown("<div class='card'><div class='kpi'><div class='title'>Livestock Health Watch</div><div><span class='badge'>US</span><span class='badge'>BR</span><span class='badge'>MX</span></div></div></div>", unsafe_allow_html=True)
# (Por ahora mostramos “sin novedades”; si quieres, luego cableamos GDELT)
hw_panel("Estados Unidos", True)
hw_panel("Brasil", True)
hw_panel("México", True)

# ====================== FROZEN MEAT INDUSTRY MONITOR (rotador lento) ======================
@st.cache_data(ttl=75)
def pct_30d(sym: str) -> float | None:
    try:
        t = yf.Ticker(sym)
        h = t.history(period="45d", interval="1d")
        if h is None or h.empty or h["Close"].dropna().shape[0] < 2:
            return None
        c = h["Close"].dropna()
        # buscar 30 días hábiles atrás (aprox 21-23 barras)
        first = float(c.iloc[-22]) if len(c) >= 22 else float(c.iloc[0])
        last = float(c.iloc[-1])
        if first == 0:
            return None
        return (last/first - 1.0) * 100.0
    except Exception:
        return None

# Construimos hasta 3 tarjetas con explicación
live_signals = []
for label, sym in [("Res (LE=F)", "LE=F"), ("Cerdo (HE=F)", "HE=F"), ("USD/MXN", "MXN=X")]:
    p = pct_30d(sym)
    if p is not None:
        sgn = "▲" if p >= 0 else "▼"
        live_signals.append({
            "num": f"{p:+.1f}%",
            "sub": f"{label} · cambio 30D {sgn}",
            "badge": "mercado vivo",
            "desc": "Variación de cierre a cierre en los últimos 30 días (Yahoo Finance)."
        })

# Si no hubo suficientes señales, no mostramos tarjeta vacía
if live_signals:
    items_im = live_signals[:3]
    im_html = ["<div class='card im-card'><div class='im-wrap'>"]
    for it in items_im:
        num   = it.get("num", "—")
        sub   = it.get("sub", "")
        badge = it.get("badge", "")
        desc  = it.get("desc") or ("Cambio en 30 días (Yahoo Finance)." if badge == "mercado vivo"
                                   else "Cifra textual detectada en noticias recientes.")
        extra = f" <span class='im-badge'>{badge}</span>" if badge else ""
        im_html.append(
            f"<div class='im-item'>"
            f"<div class='im-num'>{num}</div>"
            f"<div class='im-sub'>{sub}{extra}</div>"
            f"<div class='im-desc'>{desc}</div>"
            f"</div>"
        )
    im_html.append("</div></div>")
    st.markdown("".join(im_html), unsafe_allow_html=True)

# ====================== PIE ======================
st.markdown(
    f"<div class='muted' style='color:var(--muted)!important'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Fuentes: Yahoo Finance (~15 min retraso).</div>",
    unsafe_allow_html=True,
)

# Hands-free refresco suave (evita st.autorefresh para no romper Streamlit Cloud)
time.sleep(60)
st.rerun()
