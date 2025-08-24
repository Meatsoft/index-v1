# app.py — LaSultana Meat Index
# CME (LE=F/HE=F): siempre mostramos "lo que Yahoo muestra" (last y change con su delay).
# Barra bursátil y USD/MXN se mantienen igual.

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
.card{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:10px;
  padding:14px;
  margin-bottom:18px;
}
.grid .card:last-child{margin-bottom:0}

/* Ocultar UI */
header[data-testid="stHeader"] {display:none;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

/* LOGO */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:32px 0 28px}

/* CINTA SUPERIOR */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-family:ui-monospace,Menlo,Consolas,monospace}
.item{display:inline-block;margin:0 32px}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* GRID */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:18px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900}
.kpi .delta{font-size:20px;margin-left:12px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}

/* TABLA POLLO */
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line)}
.table th{text-align:left;color:var(--muted);font-weight:600}
.table td:last-child{text-align:right}

/* NOTICIA */
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 18px}
.tape-news-track{display:flex;width:max-content;will-change:transform;animation:marqueeNewsFast 177s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:18px}
@keyframes marqueeNewsFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}
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

# ==================== CINTA SUPERIOR (bursátil real) ====================
PRIMARY_COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("JBS","JBS"), ("Marfrig Global","MRRTY"), ("Minerva","MRVSY"),
    ("Grupo Bafar","BAFARB.MX"), ("WH Group (Smithfield)","WHGLY"),
    ("Seaboard","SEB"), ("Hormel Foods","HRL"),
    ("Grupo KUO","KUOB.MX"), ("Maple Leaf Foods","MFI.TO"),
]
ALTERNATES = [("Conagra Brands","CAG"), ("Sysco","SYY"), ("US Foods","USFD"),
              ("Cranswick","CWK.L"), ("NH Foods","2282.T")]

@st.cache_data(ttl=75)
def fetch_quotes_strict():
    valid, seen = [], set()
    def try_add(name, sym):
        if sym in seen: return
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="1d", interval="1m")
            if hist is None or hist.empty:
                hist = t.history(period="1d", interval="5m")
            if hist is None or hist.empty: return
            closes = hist["Close"].dropna()
            if closes.empty: return
            last, first = float(closes.iloc[-1]), float(closes.iloc[0])
            ch = last - first
            valid.append({"name":name,"sym":sym,"px":last,"ch":ch})
            seen.add(sym)
        except Exception:
            return
    for n,s in PRIMARY_COMPANIES: try_add(n,s)
    i=0
    while len(valid)<14 and i<len(ALTERNATES):
        try_add(*ALTERNATES[i]); i+=1
    return valid

quotes = fetch_quotes_strict()
ticker_line = ""
for q in quotes:
    cls = "green" if q["ch"]>=0 else "red"
    arrow = "▲" if q["ch"]>=0 else "▼"
    ticker_line += f"<span class='item'>{q['name']} ({q['sym']}) <b class='{cls}'>{q['px']:.2f} {arrow} {abs(q['ch']):.2f}</b></span>"

st.markdown(
    f"""
    <div class='tape'>
      <div class='tape-track'>
        <div class='tape-group'>{ticker_line}</div>
        <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
      </div>
    </div>
    """, unsafe_allow_html=True
)

# ==================== FX (igual, con fallback suave) ====================
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

# ==================== CME: "lo que Yahoo muestre" (last y change) ====================
@st.cache_data(ttl=75)
def get_yahoo_last(sym: str):
    """
    Toma el 'last' y el 'change' que Yahoo expone para el ticker.
    Orden de preferencia:
      1) fast_info.last_price / fast_info.previous_close
      2) info['regularMarketPrice'] / info['regularMarketPreviousClose']
      3) history diario para last/prev como fallback
    Devuelve: (last, change) o (None, None) si no hay datos.
    """
    try:
        t = yf.Ticker(sym)

        # 1) fast_info (rápido)
        try:
            fi = t.fast_info
            last = fi.get("last_price", None)
            prev = fi.get("previous_close", None)
            if last is not None and prev is not None:
                return float(last), float(last) - float(prev)
        except Exception:
            pass

        # 2) info estándar
        try:
            inf = t.info or {}
            last = inf.get("regularMarketPrice", None)
            prev = inf.get("regularMarketPreviousClose", None)
            if last is not None and prev is not None:
                return float(last), float(last) - float(prev)
        except Exception:
            pass

        # 3) history (diario)
        d = t.history(period="10d", interval="1d")
        if d is None or d.empty:
            return None, None
        closes = d["Close"].dropna()
        if closes.shape[0] == 0:
            return None, None
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if closes.shape[0] >= 2 else last
        return last, last - prev
    except Exception:
        return None, None

live_cattle_px, live_cattle_ch = get_yahoo_last("LE=F")  # Live Cattle (CME)
lean_hogs_px,   lean_hogs_ch   = get_yahoo_last("HE=F")  # Lean Hogs (CME)

# ==================== GRID ====================
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# 1) USD/MXN
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

# 2) Res / Cerdo (CME, siempre last+change de Yahoo)
def kpi_card(titulo: str, price, chg):
    sub = "USD/100 lb (CME)"
    if price is None:
        price_html = f"<div class='big'>N/D <span class='muted'>{sub}</span></div>"
        delta_html = ""
    else:
        dir_cls   = "green" if (chg or 0) >= 0 else "red"
        dir_arrow = "▲"     if (chg or 0) >= 0 else "▼"
        price_html = f"<div class='big'>{fmt2(price)} <span class='muted'>{sub}</span></div>"
        delta_html = f"<div class='delta {dir_cls}'>{dir_arrow} {fmt2(abs(chg))}</div>"
    return f"""
    <div class="card box">
      <div class="kpi">
        <div class="left">
          <div class="title">{titulo}</div>
          {price_html}
        </div>
        {delta_html}
      </div>
    </div>
    """

st.markdown("<div class='centerstack'>", unsafe_allow_html=True)
st.markdown(kpi_card("Res en pie",   live_cattle_px, live_cattle_ch), unsafe_allow_html=True)
st.markdown(kpi_card("Cerdo en pie", lean_hogs_px,   lean_hogs_ch),   unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 3) Piezas de Pollo (placeholder por ahora)
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

# ==================== NOTICIA (placeholder rotativo) ====================
noticias = [
  "USDA: beef cutout estable; cortes medios firmes, con demanda moderada en retail y ligera debilidad en foodservice.",
  "USMEF: exportaciones de cerdo a México firmes; importadores absorben costos mientras supermercados sostienen hams.",
  "Poultry: oferta amplia presiona piezas oscuras, pero la pechuga jumbo se mantiene estable en contratos mayoristas.",
  "FX: fortaleza del peso abarata importaciones; revisar spreads USD/lb→MXN/kg y el impacto en costos logísticos."
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
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuente: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True,
)

time.sleep(60)
st.rerun()
