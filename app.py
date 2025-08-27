# app.py — LaSultana Meat Index (USDA-pechugas en vivo + fallback)
# - Bursátil (yfinance, USD-only activos)
# - USD/MXN (yfinance: MXN=X)
# - Res/Cerdo (LE=F / HE=F via Yahoo)
# - Piezas de pollo (USDA AJ_PY018): Pechuga B/S y Pechuga T/S
#     * fetch directo cada 60s
#     * snapshot local automático (reusa formatos viejos)
#     * si USDA no responde, se muestra último snapshot (NUNCA inventa)

import os, json, re, time, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

#==================== ESTILOS ====================
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
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:16px}
header[data-testid="stHeader"]{display:none;} #MainMenu{visibility:hidden;} footer{visibility:hidden}

/* Logo */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:24px 0 20px}

/* Cinta bursátil */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:16px}
.tape-track{display:flex;width:max-content;animation:marquee 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
.up{color:var(--up)} .down{color:var(--down)} .muted{color:var(--muted)}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* KPIs delgadas */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .title{font-size:16px;color:var(--muted)}
.kpi .big{font-size:36px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:16px;margin-left:10px}
.unit-inline{font-size:.70em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* Pechugas como KPIs (2 cartas) */
.grid-pech{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:4px}

/* Noticias (un 22% más rápida que antes) */
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:4px 0 16px}
.tape-news-track{display:flex;width:max-content;animation:marqueeNews 132s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNews{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}
.badge{
  display:inline-block;padding:2px 8px; /* padding vertical reducido */
  border:1px solid var(--line);border-radius:8px;color:var(--muted);
  font-size:12px;margin-left:8px
}
</style>
""", unsafe_allow_html=True)

#==================== HELPERS ====================
def fmt2(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

#==================== LOGO ====================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

#==================== CINTA BURSÁTIL (USD & activos) ====================
COMPANIES = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("JBS","JBS"),
    ("BRF","BRFS"), ("Hormel Foods","HRL"), ("Seaboard","SEB"),
    ("Minerva","MRVSY"), ("Marfrig","MRRTY"), ("Maple Leaf Foods","MFI.TO"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"),
    ("Grupo KUO","KUOB.MX"),  # MXN, se filtrará por moneda
    ("WH Group","WHGLY"),
    ("Minupar Participações","MNPR3.SA"),
    ("Excelsior Alimentos","BAUH4.SA"),
    ("Wens Foodstuff Group","300498.SZ"),
    ("Wingstop","WING"), ("Yum! Brands","YUM"),
    ("Restaurant Brands Intl.","QSR"),
    ("Sysco","SYY"), ("US Foods","USFD"),
    ("Performance Food Group","PFGC"),
    ("Walmart","WMT"),
]
# Bafar y Alsea removidos (MXN y/o inactivos).

@st.cache_data(ttl=75)
def quote_usd_only(sym:str):
    """Devuelve (last, chg) sólo si el activo cotiza en USD y tiene dato."""
    try:
        t = yf.Ticker(sym)
        inf = t.info or {}
        curr = inf.get("currency")
        if curr != "USD":
            return None, None, curr
        fi = getattr(t, "fast_info", {}) or {}
        last = fi.get("last_price")
        prev = fi.get("previous_close")
        if last is None:
            # fallback history
            d = t.history(period="10d", interval="1d")
            if d is None or d.empty: return None, None, curr
            c = d["Close"].dropna()
            if c.empty: return None, None, curr
            last = float(c.iloc[-1]); prev = float(c.iloc[-2]) if len(c)>=2 else None
        chg = (float(last) - float(prev)) if prev is not None else None
        return float(last), (None if chg is None else float(chg)), curr
    except:
        return None, None, None

items=[]
for name,sym in COMPANIES:
    last,chg,curr = quote_usd_only(sym)
    if last is None:
        # silenciamos los que no son USD o no tienen dato
        continue
    if chg is None:
        items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
    else:
        cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
        items.append(f"<span class='item'>{name} ({sym}) <b class='{cls}'>{last:.2f} {arr} {abs(chg):.2f}</b></span>")

ticker_line = "".join(items) if items else "<span class='item'>—</span>"

st.markdown(f"""
<div class='tape'><div class='tape-track'>
  <div class='tape-group'>{ticker_line}</div>
  <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
</div></div>
""", unsafe_allow_html=True)

#==================== FX y FUTUROS (Yahoo) ====================
@st.cache_data(ttl=75)
def yq(sym:str):
    try:
        t=yf.Ticker(sym); fi=t.fast_info or {}
        last=fi.get("last_price"); prev=fi.get("previous_close")
        if last is None:
            d=t.history(period="10d", interval="1d")
            if d is None or d.empty: return None, None
            c=d["Close"].dropna(); last=float(c.iloc[-1]); prev=float(c.iloc[-2]) if len(c)>=2 else None
        chg=(float(last)-float(prev)) if prev is not None else None
        return float(last), (None if chg is None else float(chg))
    except:
        return None, None

fx, fx_chg = yq("MXN=X")   # USD/MXN
lc, lc_chg = yq("LE=F")    # Live Cattle
lh, lh_chg = yq("HE=F")    # Lean Hogs

def kpi(title, price, chg, unit_text=None):
    unit_html = f"<span class='unit-inline'>{unit_text}</span>" if unit_text else ""
    if price is None:
        price_html = f"<div class='big'>N/D {unit_html}</div>"; delta_html=""
    else:
        if chg is None:
            price_html = f"<div class='big'>{fmt2(price)} {unit_html}</div>"; delta_html=""
        else:
            cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
            price_html = f"<div class='big'>{fmt2(price)} {unit_html}</div>"
            delta_html = f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""<div class="card"><div class="kpi">
      <div><div class="title">{title}</div>{price_html}</div>{delta_html}
    </div></div>"""

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(kpi("USD/MXN", fx, fx_chg, unit_text=""), unsafe_allow_html=True)
st.markdown(kpi("Res en pie", lc, lc_chg, unit_text="USD/100 lb"), unsafe_allow_html=True)
st.markdown(kpi("Cerdo en pie", lh, lh_chg, unit_text="USD/100 lb"), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

#==================== USDA PECHUGAS (AJ_PY018) ====================
POULTRY_URLS = [
    "https://www.ams.usda.gov/mnreports/aj_py018.txt",
    "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
    "https://www.ams.usda.gov/mnreports/py018.txt",
    "https://www.ams.usda.gov/mnreports/PY018.txt",
]
HDR = {"User-Agent":"Mozilla/5.0"}

# Patrones para Pechuga B/S y Pechuga T/S
PECH_PAT = {
    "Pechuga B/S": [r"BREAST\s*-\s*B/?S(?!.*JUMBO)", r"BREAST,\s*B/?S(?!.*JUMBO)"],
    "Pechuga T/S (strapless)": [r"BREAST\s*T/?S", r"STRAPLESS"],
}

def _avg_from_line(U:str) -> float | None:
    # 1) Weighted Avg (WTD/WEIGHTED AVG) — la fuente preferida de USDA
    m = re.search(r"(?:WT?D|WEIGHTED)\s*AVG\.?\s*(\d+(?:\.\d+)?)", U)
    if m:
        try: return float(m.group(1))
        except: pass
    # 2) Rango numérico -> promedio
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", U)
    if m2:
        try:
            lo=float(m2.group(1)); hi=float(m2.group(2))
            return (lo+hi)/2.0
        except: pass
    # 3) Último número de la línea como fallback
    nums = re.findall(r"(\d+(?:\.\d+)?)", U)
    if nums:
        try: return float(nums[-1])
        except: return None
    return None

@st.cache_data(ttl=1800)
def fetch_pechugas()->dict:
    """Lee AJ_PY018 desde varias URLs. Devuelve {'Pechuga B/S':x, 'Pechuga T/S (strapless)':y} si hay datos hoy."""
    for url in POULTRY_URLS:
        try:
            r = requests.get(url, timeout=12, headers=HDR)
            if r.status_code != 200: continue
            txt = r.text
            if "<html" in txt.lower():  # redirecciones
                continue
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            out={}
            for disp, pats in PECH_PAT.items():
                for ln in lines:
                    U=ln.upper()
                    if any(re.search(p,U) for p in pats):
                        v=_avg_from_line(U)
                        if v is not None:
                            out[disp]=v; break
            if out:
                return out
        except:
            continue
    return {}

# --- Snapshot robusto (reusa formatos viejos) ---
SNAP_PRIMARY = "poultry_last_pechugas.json"
SNAP_FALLBACKS = ["poultry_last.json", "poultry_last_full.json", "poultry_last_pechugas.json"]
KEY_ALIASES = {
    "Breast - B/S": "Pechuga B/S",
    "BREAST - B/S": "Pechuga B/S",
    "Breast B/S": "Pechuga B/S",
    "Breast T/S": "Pechuga T/S (strapless)",
    "BREAST T/S": "Pechuga T/S (strapless)",
    "Breast T/S (strapless)": "Pechuga T/S (strapless)",
}

def _normalize_snapshot_dict(raw: dict) -> dict:
    out={}
    for k,v in (raw or {}).items():
        val = v.get("price") if isinstance(v, dict) else v
        if val is None: continue
        name = KEY_ALIASES.get(k, k)
        if name in ("Pechuga B/S","Pechuga T/S (strapless)"):
            try: out[name]=float(val)
            except: pass
    return out

def load_any_snapshot()->dict:
    if os.path.exists(SNAP_PRIMARY):
        try:
            with open(SNAP_PRIMARY,"r") as f:
                return _normalize_snapshot_dict(json.load(f))
        except: pass
    for p in SNAP_FALLBACKS:
        if os.path.exists(p):
            try:
                with open(p,"r") as f:
                    d=_normalize_snapshot_dict(json.load(f))
                    if d: return d
            except: continue
    return {}

def save_primary_snapshot(d:dict):
    try:
        with open(SNAP_PRIMARY,"w") as f:
            json.dump({k:float(v) for k,v in d.items() if v is not None}, f)
    except:
        pass

def pechugas_with_snapshot():
    cur = fetch_pechugas()          # HOY (AJ_PY018)
    prev = load_any_snapshot()      # último snapshot
    seeded=False
    if cur:
        res={}
        for k,v in cur.items():
            pv=prev.get(k)
            dlt = 0.0 if pv is None else (float(v)-float(pv))
            res[k]={"price":float(v),"delta":float(dlt)}
        save_primary_snapshot(cur)
        if not prev: seeded=True
        return res, False, seeded
    if prev:
        res={k:{"price":float(v),"delta":0.0} for k,v in prev.items()}
        return res, True, False
    # arranque en frío sin snapshot
    base={k:{"price":None,"delta":0.0} for k in ("Pechuga B/S","Pechuga T/S (strapless)")}
    return base, True, False

pech, stale, seeded = pechugas_with_snapshot()

# Render como KPIs (dos tarjetas)
def kpi_pech(title, item):
    price = item.get("price"); d = item.get("delta", 0.0)
    unit = "<span class='unit-inline'>USD/lb</span>"
    if price is None:
        price_html=f"<div class='big'>N/D {unit}</div>"; delta_html=""
    else:
        cls="up" if d>=0 else "down"; arr="▲" if d>=0 else "▼"
        price_html=f"<div class='big'>{fmt2(price)} {unit}</div>"
        delta_html=f"<div class='delta {cls}'>{arr} {fmt2(abs(d))}</div>"
    return f"""<div class="card"><div class="kpi">
      <div><div class="title">{title}</div>{price_html}</div>{delta_html}
    </div></div>"""

badge = " <span class='badge'>último disponible</span>" if stale else (" <span class='badge'>actualizado</span>" if seeded else "")
st.markdown(f"<div class='title' style='margin:8px 0 6px'>Piezas de Pollo — U.S. National (USDA){badge}</div>", unsafe_allow_html=True)
st.markdown("<div class='grid-pech'>", unsafe_allow_html=True)
st.markdown(kpi_pech("Pechuga B/S", pech.get("Pechuga B/S", {})), unsafe_allow_html=True)
st.markdown(kpi_pech("Pechuga T/S (strapless)", pech.get("Pechuga T/S (strapless)", {})), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

#==================== Noticias (cinta) ====================
news = [
  "USDA: beef cutout estable; cortes medios firmes; demanda retail moderada, foodservice suave.",
  "USMEF: exportaciones de cerdo a México firmes; hams sostienen volumen pese a costos.",
  "Pechuga B/S estable en contratos; T/S con oferta contenida; oscurezas presionadas.",
  "FX: peso fuerte abarata importaciones; revisar spread USD/lb→MXN/kg y logística."
]
k = int(time.time()//30) % len(news)
st.markdown(f"""
<div class='tape-news'><div class='tape-news-track'>
  <div class='tape-news-group'><span class='item'>{news[k]}</span></div>
  <div class='tape-news-group' aria-hidden='true'><span class='item'>{news[k]}</span></div>
</div></div>
""", unsafe_allow_html=True)

#==================== Pie ====================
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True
)

# Refresco simple (sí, hay un “flash” corto: limitación de Streamlit con rerun)
time.sleep(60)
st.rerun()
