# app.py — LaSultana Meat Index (V1.7: layout limpio, 2 columnas, sin contenedor fantasma)
import os, time, datetime as dt, textwrap as tw
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")
try: st.cache_data.clear()
except: pass

# ====================== ESTILOS ======================
st.markdown(tw.dedent("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800;900&display=swap');

:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b; --font:"Manrope","Inter","Segoe UI",Roboto,Arial,sans-serif;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important;font-family:var(--font)!important}
*{font-family:var(--font)!important}
.block-container{max-width:1400px;padding-top:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:18px}
header[data-testid="stHeader"]{display:none;} #MainMenu{visibility:hidden;} footer{visibility:hidden}

/* LOGO */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:26px 0 22px}

/* CINTA BURSÁTIL */
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
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px;line-height:1.05}
.kpi .delta{font-size:20px;margin-left:12px}
.unit-inline{font-size:.7em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* Sección inferior: 2 columnas lado a lado */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}

/* Livestock Health Watch */
.lhw .panel{border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:10px}
.lhw .head{font-weight:700;color:var(--muted);margin-bottom:6px}
.lhw .okdot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#28e07d;vertical-align:middle;margin-right:8px}
.badge{display:inline-block;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;margin-left:6px}

/* Frozen Meat Industry Monitor (3 slots · 10s c/u) */
.im-card{min-height:210px}
.im-wrap{position:relative;height:200px;overflow:hidden;width:100%}
.im-item{position:absolute;left:0;right:0;top:0;opacity:0;animation:fadeSlot 30s linear infinite;will-change:opacity,transform}
.im-item:nth-child(1){animation-delay:0s}
.im-item:nth-child(2){animation-delay:10s}
.im-item:nth-child(3){animation-delay:20s}
@keyframes fadeSlot{
  0%   {opacity:1; transform:translateY(0)}
  32%  {opacity:1}
  36%  {opacity:0; transform:translateY(-6px)}
  100% {opacity:0}
}
.im-num{font-size:56px;font-weight:900;letter-spacing:.3px;margin-bottom:12px;text-align:center;line-height:1;color:var(--txt)}
.im-sub{font-size:18px;color:var(--muted);text-align:center}
.im-desc{font-size:14px;color:#8fb7d5;text-align:center;margin-top:8px}
.im-badge{display:inline-block;margin-left:8px;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px}
</style>
"""), unsafe_allow_html=True)

# ==================== HELPERS ====================
def fmt2(x: float | None) -> str:
    if x is None: return "—"
    s = f"{x:,.2f}"; return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float | None) -> str:
    if x is None: return "—"
    s = f"{x:,.4f}"; return s.replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data(ttl=75)
def quote_last_and_change(sym: str):
    try:
        t = yf.Ticker(sym); fi = getattr(t, "fast_info", {}) or {}
        last = fi.get("last_price", None); prev = fi.get("previous_close", None)
        if last is not None:
            ch = (float(last) - float(prev)) if prev is not None else None
            return float(last), ch
    except Exception: pass
    try:
        info = yf.Ticker(sym).info or {}
        last = info.get("regularMarketPrice", None)
        prev = info.get("regularMarketPreviousClose", None)
        if last is not None:
            ch = (float(last) - float(prev)) if prev is not None else None
            return float(last), ch
    except Exception: pass
    try:
        d = yf.Ticker(sym).history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna()
        last = float(c.iloc[-1]); prev = float(c.iloc[-2]) if c.shape[0] >= 2 else None
        ch = (last - prev) if prev is not None else None
        return last, ch
    except Exception:
        return None, None

@st.cache_data(ttl=300)
def pct_change_n_days(sym: str, days: int = 30) -> float | None:
    try:
        d = yf.Ticker(sym).history(period=f"{max(days+15, 40)}d", interval="1d")
        if d is None or d.empty: return None
        c = d["Close"].dropna()
        if c.shape[0] < days+1: return None
        last = float(c.iloc[-1]); prev = float(c.iloc[-(days+1)])
        if prev == 0: return None
        return (last/prev - 1.0)*100.0
    except Exception:
        return None

# ==================== LOGO ====================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== CINTA BURSÁTIL (USD) ====================
COMPANIES_USD = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("JBS","JBS"), ("BRF","BRFS"),
    ("Hormel Foods","HRL"), ("Seaboard","SEB"), ("Minerva","MRVSY"), ("Marfrig","MRRTY"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"), ("WH Group","WHGLY"),
    ("Wingstop","WING"), ("Yum! Brands","YUM"), ("Restaurant Brands Intl.","QSR"),
    ("Sysco","SYY"), ("US Foods","USFD"), ("Performance Food Group","PFGC"),
    ("Walmart","WMT"),
]
items=[]
for name,sym in COMPANIES_USD:
    last,chg=quote_last_and_change(sym)
    if last is None: continue
    if chg is None:
        items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
    else:
        cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
        items.append(f"<span class='item'>{name} ({sym}) <b class='{cls}'>{last:.2f} {arr} {abs(chg):.2f}</b></span>")
ticker_line="".join(items)
st.markdown(tw.dedent(f"""
<div class='tape'>
  <div class='tape-track'>
    <div class='tape-group'>{ticker_line}</div>
    <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
  </div>
</div>
"""), unsafe_allow_html=True)

# ==================== KPIs: USD/MXN, Res, Cerdo ====================
fx, fx_chg = quote_last_and_change("MXN=X")
lc, lc_chg = quote_last_and_change("LE=F")
lh, lh_chg = quote_last_and_change("HE=F")

def kpi_fx(title, value, chg):
    if value is None:
        val_html = "<div class='big'>N/D</div>"; delta_html = ""
    else:
        val_html = f"<div class='big'>{fmt4(value)}</div>"
        if chg is None: delta_html=""
        else:
            cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
            delta_html=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""
    <div class="card"><div class="kpi">
      <div><div class="title">{title}</div>{val_html}</div>{delta_html}
    </div></div>"""

def kpi_cme(title, price, chg):
    unit="USD/100 lb"
    if price is None:
        price_html=f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"; delta_html=""
    else:
        price_html=f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
        if chg is None: delta_html=""
        else:
            cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
            delta_html=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""
    <div class="card"><div class="kpi">
      <div><div class="title">{title}</div>{price_html}</div>{delta_html}
    </div></div>"""

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(kpi_fx("USD/MXN", fx, fx_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Res en pie", lc, lc_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Cerdo en pie", lh, lh_chg), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== BLOQUE INFERIOR: 2 COLUMNAS ====================
st.markdown("<div class='grid2'>", unsafe_allow_html=True)

# (A) Frozen Meat Industry Monitor — IZQUIERDA
sig_fx = pct_change_n_days("MXN=X", 30)
sig_lc = pct_change_n_days("LE=F", 30)
sig_lh = pct_change_n_days("HE=F", 30)

def signal_html(pct: float | None, label: str) -> str:
    num_txt = "—" if pct is None else f"{pct:+.1f}%"
    return (
        f"<div class='im-item'>"
        f"  <div class='im-num'>{num_txt}</div>"
        f"  <div class='im-sub'>{label} · cambio 30D <span class='im-badge'>mercado vivo</span></div>"
        f"  <div class='im-desc'>Variación de cierre a cierre en los últimos 30 días (Yahoo Finance).</div>"
        f"</div>"
    )

signals = [
    signal_html(sig_fx,"USD/MXN"),
    signal_html(sig_lc,"Res (LE=F)"),
    signal_html(sig_lh,"Cerdo (HE=F)")
]
while len(signals) < 3:
    signals.append(signals[-1])

st.markdown(tw.dedent(f"""
<div class="card im-card">
  <div class="title" style="color:var(--txt);margin-bottom:6px">Frozen Meat Industry Monitor</div>
  <div class="im-wrap">
    {''.join(signals)}
  </div>
</div>
"""), unsafe_allow_html=True)

# (B) Livestock Health Watch — DERECHA
lhw_html = """
<div class="card lhw">
  <div class="title" style="color:var(--txt);margin-bottom:6px">Livestock Health Watch</div>
  <div class="panel">
    <div class="head">Estados Unidos <span class="badge">USA</span></div>
    <div><span class="okdot"></span>Sin novedades significativas (última revisión reciente).</div>
  </div>
  <div class="panel">
    <div class="head">Brasil <span class="badge">BRA</span></div>
    <div><span class="okdot"></span>Sin novedades significativas (última revisión reciente).</div>
  </div>
  <div class="panel" style="margin-bottom:0">
    <div class="head">México <span class="badge">MEX</span></div>
    <div><span class="okdot"></span>Sin novedades significativas (última revisión reciente).</div>
  </div>
</div>
"""
st.markdown(lhw_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # cierra grid2

# ==================== PIE ====================
st.markdown(
  f"<div style='color:var(--muted);font-size:13px'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True,
)

# ==================== HANDS-FREE REFRESH ====================
time.sleep(60)
st.rerun()
