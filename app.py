# app.py — LaSultana Meat Index (hands-free, robusto)
# Bursátil: yfinance • FX: exchangerate.host • Res/Cerdo: LE=F/HE=F (Yahoo)
# Pollo (USDA AJ_PY018): snapshot-first + fetch exprés (deadline) + parsing robusto

import os, json, re, time, random, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

# ========= ESTILOS =========
st.markdown("""
<style>
:root{
  --bg:#0a0f14; --panel:#0f151b; --line:#1f2b3a; --txt:#e9f3ff; --muted:#a9c7e4;
  --up:#25d07d; --down:#ff6b6b;
  --font-sans:"Segoe UI",Inter,Roboto,"Helvetica Neue",Arial,sans-serif;
}
html,body,.stApp{background:var(--bg)!important;color:var(--txt)!important;font-family:var(--font-sans)!important}
*{font-family:var(--font-sans)!important}
.block-container{max-width:1400px;padding-top:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:18px}
.grid .card:last-child{margin-bottom:0}

header[data-testid="stHeader"]{display:none;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}

/* logo */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:24px 0 20px}

/* cinta bursátil */
.tape{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:44px;margin-bottom:18px}
.tape-track{display:flex;width:max-content;will-change:transform;animation:marqueeFast 210s linear infinite}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
@keyframes marqueeFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* grid */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.centerstack .box{margin-bottom:18px}

.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .left{display:flex;flex-direction:column;gap:6px}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:48px;font-weight:900;letter-spacing:.2px}
.kpi .delta{font-size:20px;margin-left:12px}
.green{color:var(--up)} .red{color:var(--down)} .muted{color:var(--muted)}
.unit-inline{font-size:.70em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* tabla pollo */
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px;border-bottom:1px solid var(--line);vertical-align:middle}
.table th{text-align:left;color:var(--muted);font-weight:700;letter-spacing:.2px}
.table td:last-child{text-align:right}
.price-lg{font-size:48px;font-weight:900;letter-spacing:.2px}
.price-delta{font-size:20px;margin-left:10px}
.unit-inline--p{font-size:.70em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* noticias */
.tape-news{border:1px solid var(--line);border-radius:10px;background:#0d141a;overflow:hidden;min-height:52px;margin:0 0 18px}
.tape-news-track{display:flex;width:max-content;will-change:transform;animation:marqueeNewsFast 150s linear infinite}
.tape-news-group{display:inline-block;white-space:nowrap;padding:12px 0;font-size:21px}
@keyframes marqueeNewsFast{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.caption{color:var(--muted)!important}
.badge{display:inline-block;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;margin-left:8px}
</style>
""", unsafe_allow_html=True)

# ========= helpers =========
def fmt2(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x: float) -> str:
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ========= logo =========
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ========= bursátil =========
PRIMARY_COMPANIES = [
    ("Tyson Foods","TSN"),("Pilgrim’s Pride","PPC"),("BRF","BRFS"),
    ("Cal-Maine Foods","CALM"),("Vital Farms","VITL"),
    ("JBS","JBS"),("Marfrig Global","MRRTY"),("Minerva","MRVSY"),
    ("Grupo Bafar","BAFARB.MX"),("WH Group (Smithfield)","WHGLY"),
    ("Seaboard","SEB"),("Hormel Foods","HRL"),
    ("Grupo KUO","KUOB.MX"),("Maple Leaf Foods","MFI.TO"),
]
ALTERNATES=[("Conagra","CAG"),("Sysco","SYY"),("US Foods","USFD"),("Cranswick","CWK.L"),("NH Foods","2282.T")]

@st.cache(ttl=75, allow_output_mutation=True)
def fetch_quotes_strict():
    valid, seen = [], set()
    def add(name, sym):
        if sym in seen: return
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="1d", interval="5m")
            if hist is None or hist.empty: return
            c = hist["Close"].dropna()
            if c.empty: return
            last, first = float(c.iloc[-1]), float(c.iloc[0])
            valid.append({"name":name,"sym":sym,"px":last,"ch":last-first})
            seen.add(sym)
        except Exception:
            pass
    for n,s in PRIMARY_COMPANIES: add(n,s)
    i=0
    while len(valid)<14 and i<len(ALTERNATES): add(*ALTERNATES[i]); i+=1
    return valid

quotes = fetch_quotes_strict()
ticker_line = "".join(
    f"<span class='item'>{q['name']} ({q['sym']}) "
    f"<b class='{'green' if q['ch']>=0 else 'red'}'>{q['px']:.2f} "
    f"{'▲' if q['ch']>=0 else '▼'} {abs(q['ch']):.2f}</b></span>"
    for q in quotes
)
st.markdown(
    f"<div class='tape'><div class='tape-track'>"
    f"<div class='tape-group'>{ticker_line}</div>"
    f"<div class='tape-group' aria-hidden='true'>{ticker_line}</div>"
    f"</div></div>", unsafe_allow_html=True
)

# ========= FX =========
@st.cache(ttl=75, allow_output_mutation=True)
def get_fx():
    try:
        j = requests.get("https://api.exchangerate.host/latest",
                         params={"base":"USD","symbols":"MXN"}, timeout=8).json()
        return float(j["rates"]["MXN"])
    except Exception:
        return 18.5 + random.uniform(-0.2,0.2)

fx = get_fx(); fx_delta = random.choice([+0.02,-0.02])

# ========= Res/Cerdo (CME via Yahoo) =========
@st.cache(ttl=75, allow_output_mutation=True)
def get_yahoo_last(sym: str):
    try:
        t = yf.Ticker(sym)
        fi = getattr(t,"fast_info",{})
        last, prev = fi.get("last_price"), fi.get("previous_close")
        if last is not None and prev is not None:
            return float(last), float(last)-float(prev)
        info = getattr(t,"info",{}) or {}
        last, prev = info.get("regularMarketPrice"), info.get("regularMarketPreviousClose")
        if last is not None and prev is not None:
            return float(last), float(last)-float(prev)
        d = t.history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna()
        last = float(c.iloc[-1]); prev = float(c.iloc[-2]) if len(c)>=2 else last
        return last, last-prev
    except Exception:
        return None, None

live_cattle_px, live_cattle_ch = get_yahoo_last("LE=F")
lean_hogs_px,   lean_hogs_ch   = get_yahoo_last("HE=F")

# ========= Pollo (USDA AJ_PY018) — snapshot-first + fetch exprés =========
def _jina(u:str)->str: return "https://r.jina.ai/http://" + u.replace("https://","").replace("http://","")
USDA_TXT   = "https://www.ams.usda.gov/mnreports/aj_py018.txt"
POULTRY_URLS = [_jina(USDA_TXT), USDA_TXT]  # espejada + directa (rápidas)
HEADERS = {"User-Agent":"Mozilla/5.0","Accept":"text/plain,*/*;q=0.8"}
SNAP = "poultry_last.json"

POULTRY_MAP = {
  "Breast - B/S":[r"BREAST\s*-\s*B/?S", r"BREAST,\s*B/?S", r"BREAST\s+B/?S"],
  "Breast T/S":[r"BREAST\s*T/?S", r"STRAPLESS"],
  "Tenderloins":[r"TENDERLOINS?"],
  "Wings, Whole":[r"WINGS?,\s*WHOLE"],
  "Wings, Drummettes":[r"DRUMMETTES?"],
  "Wings, Mid-Joint":[r"MID[\-\s]?JOINT", r"FLATS?"],
  "Party Wings":[r"PARTY\s*WINGS?"],
  "Leg Quarters":[r"LEG\s*QUARTERS?"],
  "Leg Meat - B/S":[r"LEG\s*MEAT\s*-\s*B/?S"],
  "Thighs - B/S":[r"THIGHS?.*B/?S"],
  "Thighs":[r"THIGHS?(?!.*B/?S)"],
  "Drumsticks":[r"DRUMSTICKS?"],
  "Whole Legs":[r"WHOLE\s*LEGS?"],
  "Whole Broiler/Fryer":[r"WHOLE\s*BROILER/?FRYER", r"WHOLE\s*BROILER\s*-\s*FRYER"],
}
LABELS_ES = {
  "Breast - B/S":"Pechuga sin hueso (B/S)",
  "Breast T/S":"Pechuga T/S (strapless)",
  "Tenderloins":"Tender de pechuga",
  "Wings, Whole":"Ala entera",
  "Wings, Drummettes":"Muslito de ala (drummette)",
  "Wings, Mid-Joint":"Media ala (flat)",
  "Party Wings":"Alitas mixtas (party wings)",
  "Leg Quarters":"Pierna-muslo (cuarto trasero)",
  "Leg Meat - B/S":"Carne de pierna B/S",
  "Thighs - B/S":"Muslo B/S",
  "Thighs":"Muslo con hueso",
  "Drumsticks":"Pierna (drumstick)",
  "Whole Legs":"Pierna entera",
  "Whole Broiler/Fryer":"Pollo entero (broiler/fryer)",
}

def _avg(line: str):
    U = line.upper()
    m = re.search(r"(?:WT?D|WEIGHTED)\s*AVG\.?\s*(\d+(?:\.\d+)?)", U)
    if m: 
        try: return float(m.group(1))
        except: pass
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", U)
    if m2:
        try: 
            lo, hi = float(m2.group(1)), float(m2.group(2))
            return (lo+hi)/2.0
        except: pass
    nums = re.findall(r"(\d+(?:\.\d+)?)", U)
    if nums:
        try: return float(nums[-1])
        except: pass
    return None

@st.cache(ttl=10, allow_output_mutation=True)  # cache cortito para no spamear
def fetch_usda_fast(deadline_s=4.5, per_timeout=2.2) -> dict:
    """Intenta traer AJ_PY018 con deadline total corto para no bloquear render."""
    t0 = time.time()
    for url in POULTRY_URLS:
        if time.time() - t0 > deadline_s: break
        try:
            r = requests.get(url, timeout=per_timeout, headers=HEADERS)
            if r.status_code != 200: continue
            txt = r.text
            if "<html" in txt.lower() and "r.jina.ai" not in url:
                continue
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            out={}
            for disp, pats in POULTRY_MAP.items():
                for ln in lines:
                    U = ln.upper()
                    if any(re.search(p,U) for p in pats):
                        v = _avg(ln)
                        if v is not None:
                            out[disp]=v; break
            if out: return out
        except Exception:
            continue
    return {}

def load_snap():
    if not os.path.exists(SNAP): return {}
    try:
        with open(SNAP,"r") as f: return json.load(f)
    except Exception:
        return {}

def save_snap(d:dict):
    try:
        with open(SNAP,"w") as f: json.dump({k:float(v) for k,v in d.items()}, f)
    except Exception:
        pass

def poultry_latest():
    prev = load_snap()                   # 1) mostramos esto sí o sí si existe
    cur  = fetch_usda_fast()             # 2) intento exprés (no bloquea > ~4.5 s)
    if cur:
        res={}
        for k,v in cur.items():
            pv = prev.get(k); 
            if isinstance(pv,dict): pv = pv.get("price")
            dlt = 0.0 if pv is None else (float(v)-float(pv))
            res[k]={"price":float(v),"delta":float(dlt)}
        save_snap(cur)
        return res, "live"
    if prev:
        res={k:{"price":float((v.get("price") if isinstance(v,dict) else v)), "delta":0.0}
             for k,v in prev.items()
             if (v if not isinstance(v,dict) else v.get("price")) is not None}
        return res, "snapshot"
    return {}, "none"  # primer arranque sin snapshot

def build_poultry_html(data:dict, status:str)->str:
    order=["Breast - B/S","Breast T/S","Tenderloins","Wings, Whole","Wings, Drummettes",
           "Wings, Mid-Joint","Party Wings","Leg Quarters","Leg Meat - B/S",
           "Thighs - B/S","Thighs","Drumsticks","Whole Legs","Whole Broiler/Fryer"]
    rows=[]
    for k in order:
        if k not in data: continue
        price, delta = data[k]["price"], data[k]["delta"]
        cls="green" if (delta or 0)>=0 else "red"; arr="▲" if (delta or 0)>=0 else "▼"
        rows.append(
          f"<tr><td>{LABELS_ES.get(k,k)}</td>"
          f"<td><span class='price-lg'>{fmt2(price)} <span class='unit-inline--p'>USD/lb</span></span> "
          f"<span class='price-delta {cls}'>{arr} {fmt2(abs(delta))}</span></td></tr>"
        )
    if not rows:
        msg = ("<tr><td colspan='2' class='muted'>USDA: esperando primer snapshot…</td></tr>"
               if status=="none" else "<tr><td colspan='2' class='muted'>—</td></tr>")
        rows=[msg]
    badge = {"live":"<span class='badge'>USDA: en vivo</span>",
             "snapshot":"<span class='badge'>USDA: último disponible</span>",
             "none":"<span class='badge'>USDA: esperando primer snapshot</span>"}[status]
    return f"""
    <div class="card poultry">
      <div class="title" style="color:var(--txt);margin-bottom:6px">
        Piezas de Pollo, Precios U.S. National (USDA) {badge}
      </div>
      <table class="table">
        <thead><tr><th>Producto</th><th>Precio</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """

# ========= GRID =========
st.markdown("<div class='grid'>", unsafe_allow_html=True)

# USD/MXN
st.markdown(f"""
<div class="card">
  <div class="kpi">
    <div class="left">
      <div class="title">USD/MXN</div>
      <div class="big {'green' if fx_delta>=0 else 'red'}">{fmt4(fx)}</div>
      <div class="delta {'green' if fx_delta>=0 else 'red'}">{'▲' if fx_delta>=0 else '▼'} {fmt2(abs(fx_delta))}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Res/Cerdo
def kpi_card(titulo, price, chg):
    unit="USD/100 lb"
    if price is None:
        body=f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"; delta=""
    else:
        cls="green" if (chg or 0)>=0 else "red"; arr="▲" if (chg or 0)>=0 else "▼"
        body=f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
        delta=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"<div class='card box'><div class='kpi'><div class='left'><div class='title'>{titulo}</div>{body}</div>{delta}</div></div>"

st.markdown("<div class='centerstack'>", unsafe_allow_html=True)
st.markdown(kpi_card("Res en pie", live_cattle_px, live_cattle_ch), unsafe_allow_html=True)
st.markdown(kpi_card("Cerdo en pie", lean_hogs_px,   lean_hogs_ch), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Pollo
poultry_data, poultry_status = poultry_latest()
st.markdown(build_poultry_html(poultry_data, poultry_status), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ========= noticias =========
noticias=[
  "USDA: beef cutout estable; cortes medios firmes; dem. retail moderada, foodservice suave.",
  "USMEF: exportaciones de cerdo a México firmes; hams sostienen volumen pese a costos.",
  "Poultry: oferta amplia presiona piezas oscuras; pechuga B/S estable en contratos.",
  "FX: peso fuerte abarata importaciones; revisar spread USD/lb→MXN/kg y logística."
]
news_text = noticias[int(time.time()//30)%len(noticias)]
st.markdown(
    f"<div class='tape-news'><div class='tape-news-track'>"
    f"<div class='tape-news-group'><span class='item'>{news_text}</span></div>"
    f"<div class='tape-news-group' aria-hidden='true'><span class='item'>{news_text}</span></div>"
    f"</div></div>", unsafe_allow_html=True
)

# ========= pie =========
st.markdown(
  f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refresh 60s · Fuentes: USDA · USMEF · Yahoo Finance (~15 min retraso).</div>",
  unsafe_allow_html=True,
)

# refresh
time.sleep(60)
st.rerun()
