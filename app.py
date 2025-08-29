# LaSultana Meat Index — v1 con:
# - Cinta bursátil (yfinance)
# - USD/MXN, Res (LE=F), Cerdo (HE=F) (yfinance)
# - KPI: Livestock Health Watch (US/BR/MX) — GDELT JSON + IA opcional (OPENAI_API_KEY)
# - KPI: Frozen Meat Industry Monitor — señales reales + rotador con fade
# - Sin cinta inferior; sin autorefresh (anti-parpadeo)

import os, re, json, time, datetime as dt
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

/* Health Watch */
.hw-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.hw-col{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.hw-title{font-size:16px;color:var(--muted);margin-bottom:8px}
.hw-item{margin:8px 0;padding:8px 10px;border:1px solid var(--line);border-radius:10px}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}
.dot.red{background:var(--down)} .dot.amb{background:#f0ad4e} .dot.green{background:#3cb371}
.hw-meta{color:var(--muted);font-size:12px;margin-top:4px}

/* Industry Monitor (rotador) */
.im-card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;min-height:110px;display:flex;align-items:center;justify-content:center}
.im-wrap{position:relative;height:90px;overflow:hidden}
.im-item{position:absolute;left:0;right:0;top:0;opacity:0;animation:fade 12s linear infinite}
.im-item:nth-child(1){animation-delay:0s}
.im-item:nth-child(2){animation-delay:4s}
.im-item:nth-child(3){animation-delay:8s}
@keyframes fade{
  0% {opacity:0; transform:translateY(5px)}
  5% {opacity:1; transform:translateY(0)}
  30% {opacity:1}
  33% {opacity:0; transform:translateY(-5px)}
  100% {opacity:0}
}
.im-num{font-size:40px;font-weight:900;letter-spacing:.2px;margin-bottom:6px;text-align:center}
.im-sub{font-size:16px;color:var(--muted);text-align:center}
.im-badge{display:inline-block;margin-left:8px;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px}
.caption{color:var(--muted)!important;margin-top:8px}
</style>
""", unsafe_allow_html=True)

# ==================== HELPERS ====================
def fmt2(x: float | None) -> str:
    if x is None: return "—"
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def fmt4(x: float | None) -> str:
    if x is None: return "—"
    s = f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def humanize_delta(minutes: float) -> str:
    if minutes < 1: return "hace segundos"
    if minutes < 60: return f"hace {int(minutes)} min"
    hours = minutes/60
    if hours < 24: return f"hace {int(hours)} h"
    days = int(hours//24)
    return f"hace {days} d"

# ==================== LOGO ====================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== CINTA SUPERIOR (USD firmes) ====================
COMPANIES_USD = [
    ("Tyson Foods","TSN"), ("Pilgrim’s Pride","PPC"), ("JBS","JBS"), ("BRF","BRFS"),
    ("Hormel Foods","HRL"), ("Seaboard","SEB"), ("Minerva","MRVSY"),
    ("Cal-Maine Foods","CALM"), ("Vital Farms","VITL"), ("WH Group","WHGLY"),
    ("Wingstop","WING"), ("Yum! Brands","YUM"), ("Restaurant Brands Intl.","QSR"),
    ("Sysco","SYY"), ("US Foods","USFD"), ("Performance Food Group","PFGC"), ("Walmart","WMT"),
]

@st.cache_data(ttl=75)
def quote_last_and_change(sym: str):
    try:
        t = yf.Ticker(sym); fi = t.fast_info
        last = fi.get("last_price"); prev = fi.get("previous_close")
        if last is not None:
            return float(last), (float(last)-float(prev)) if prev is not None else None
    except: pass
    try:
        inf = yf.Ticker(sym).info or {}
        last = inf.get("regularMarketPrice"); prev = inf.get("regularMarketPreviousClose")
        if last is not None:
            return float(last), (float(last)-float(prev)) if prev is not None else None
    except: pass
    try:
        d = yf.Ticker(sym).history(period="10d", interval="1d")
        if d is None or d.empty: return None, None
        c = d["Close"].dropna(); last = float(c.iloc[-1]); prev = float(c.iloc[-2]) if c.shape[0]>=2 else None
        return last, (last-prev) if prev is not None else None
    except: return None, None

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
st.markdown(f"""
<div class='tape'><div class='tape-track'>
  <div class='tape-group'>{ticker_line}</div>
  <div class='tape-group' aria-hidden='true'>{ticker_line}</div>
</div></div>
""", unsafe_allow_html=True)

# ==================== FX & FUTUROS (Yahoo) ====================
@st.cache_data(ttl=75)
def get_yahoo(sym: str):
    return quote_last_and_change(sym)

fx, fx_chg = get_yahoo("MXN=X")
lc, lc_chg = get_yahoo("LE=F")
lh, lh_chg = get_yahoo("HE=F")

def kpi_fx(title, value, chg):
    if value is None:
        val_html = "<div class='big'>N/D</div>"; delta_html=""
    else:
        val_html = f"<div class='big'>{fmt4(value)}</div>"
        if chg is None: delta_html=""
        else:
            cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
            delta_html=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"""<div class="card"><div class="kpi">
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
    return f"""<div class="card"><div class="kpi">
      <div><div class="title">{title}</div>{price_html}</div>{delta_html}
    </div></div>"""

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(kpi_fx("USD/MXN", fx, fx_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Res en pie", lc, lc_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Cerdo en pie", lh, lh_chg), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== IA opcional ====================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

def ai_summarize_health(groups):
    """groups: {country:[{title, url, datetime, species, severity}]}"""
    if not OPENAI_API_KEY:
        out={}
        for c,items in groups.items():
            bullets=[]
            for it in items[:2]:
                t=it.get("title","").strip()
                sev=it.get("severity","amb")
                s = "🔴" if sev=="red" else ("🟠" if sev=="amb" else "🟢")
                when = it.get("when_txt","")
                src = it.get("domain","")
                species = it.get("species","")
                bullets.append(f"{s} {species} — {t} ({src} · {when})")
            out[c]=bullets
        return out
    try:
        sys = (
            "Eres un analista sanitario agropecuario. Resume en español, "
            "sin inventar datos. Máx 2 bullets por país. Incluye especie, acción/estado, "
            "y fuente+edad (ej. 'hace 2 h'). Si no hay severidad alta, usa 🟢."
        )
        user_parts=[]
        for c,items in groups.items():
            for it in items[:4]:
                user_parts.append({
                    "country": c,
                    "title": it.get("title",""),
                    "species": it.get("species",""),
                    "severity": it.get("severity","amb"),
                    "when": it.get("when_txt",""),
                    "source": it.get("domain",""),
                })
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role":"system","content":sys},
                {"role":"user","content": json.dumps(user_parts, ensure_ascii=False)}
            ],
            "temperature": 0.2,
            "response_format": {"type":"json_object"}
        }
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"},
            json=payload, timeout=15
        )
        j = r.json()
        txt = j["choices"][0]["message"]["content"]
        data = json.loads(txt)
        return data if isinstance(data, dict) else {}
    except Exception:
        return ai_summarize_health({k:v for k,v in groups.items() if v})

def ai_summarize_metrics(items):
    if not OPENAI_API_KEY:
        return items
    try:
        sys = ("Eres un editor financiero. Devuelve una lista JSON de objetos "
               "{num, sub, badge}. No inventes. num breve (ej '+6.7%' o '$7,837M'). sub con país/periodo.")
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role":"system","content":sys},
                {"role":"user","content": json.dumps(items, ensure_ascii=False)}
            ],
            "temperature": 0.2,
            "response_format": {"type":"json_object"}
        }
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"},
            json=payload, timeout=15
        )
        out = r.json()["choices"][0]["message"]["content"]
        data = json.loads(out)
        if isinstance(data, list): return data
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            return data["items"]
        return items
    except Exception:
        return items

# ==================== GDELT Fetchers ====================
GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
COMMON_HEADERS = {"User-Agent":"Mozilla/5.0"}

DISEASE_Q = "(avian%20influenza%20OR%20HPAI%20OR%20bird%20flu%20OR%20African%20swine%20fever%20OR%20ASF%20OR%20foot-and-mouth%20OR%20FMD%20OR%20PRRS)"
COUNTRY_MAP = {"US":"Estados Unidos","BR":"Brasil","MX":"México"}

SPECIES_REGEX = [
    (r"\b(pollo|aves|broiler|chicken)\b", "Pollo"),
    (r"\b(pavo|turkey)\b", "Pavo"),
    (r"\b(cerdo|swine|hog|pork)\b", "Cerdo"),
    (r"\b(res|bovine|cattle)\b", "Res"),
]

def detect_species(text:str)->str:
    u = text.lower()
    for pat,label in SPECIES_REGEX:
        if re.search(pat, u): return label
    return "Ganado"

def severity_from_title(t:str)->str:
    u = t.lower()
    hard = any(k in u for k in ["confirmed","confirmado","quarantine","cuarentena","culling","sacrificio","outbreak","brote","emergency"])
    med  = any(k in u for k in ["detected","detección","suspected","sospecha","cases","casos","alert"])
    if hard: return "red"
    if med:  return "amb"
    return "green"

@st.cache_data(ttl=600)
def gdelt_search(country_code:str, timespan="10d", maxrecords=40):
    try:
        params = {
            "query": f"{DISEASE_Q} sourcecountry:{country_code}",
            "mode": "ArtList",
            "format": "json",
            "timespan": timespan,
            "maxrecords": str(maxrecords)
        }
        r = requests.get(GDELT_DOC, params=params, headers=COMMON_HEADERS, timeout=12)
        if r.status_code != 200: return []
        j = r.json()
        arts = j.get("articles", []) or []
        out=[]
        now = dt.datetime.utcnow()
        for a in arts:
            title = a.get("title","").strip()
            url   = a.get("url","")
            dom   = a.get("domain","")
            seen  = a.get("seendate","")  # 'YYYYMMDDHHMMSS'
            when_txt = ""
            try:
                d = dt.datetime.strptime(seen, "%Y%m%d%H%M%S")
                minutes = (now - d).total_seconds()/60.0
                when_txt = humanize_delta(minutes)
            except Exception:
                pass
            species = detect_species(title)
            sev = severity_from_title(title)
            out.append({"title":title,"url":url,"domain":dom,"when_txt":when_txt,"species":species,"severity":sev})
        return out[:maxrecords]
    except Exception:
        return []

# ==================== KPI: Livestock Health Watch ====================
def order_items(items):
    rank={"red":0,"amb":1,"green":2}
    return sorted(items, key=lambda x: rank.get(x.get("severity","amb"),1))

US_items = order_items(gdelt_search("US"))[:6]
BR_items = order_items(gdelt_search("BR"))[:6]
MX_items = order_items(gdelt_search("MX"))[:6]

groups = {"US": US_items, "BR": BR_items, "MX": MX_items}
summ = ai_summarize_health(groups)

st.markdown("<div class='card'><div class='kpi'><div class='title'>Livestock Health Watch</div></div></div>", unsafe_allow_html=True)
st.markdown("<div class='hw-grid'>", unsafe_allow_html=True)
for cc in ["US","BR","MX"]:
    bullets = summ.get(cc, [])
    country_name = COUNTRY_MAP.get(cc, cc)
    st.markdown(f"<div class='hw-col'><div class='hw-title'>{country_name}</div>", unsafe_allow_html=True)
    if bullets:
        for b in bullets[:2]:
            color = "amb"
            if "🔴" in b: color="red"
            elif "🟢" in b: color="green"
            st.markdown(f"<div class='hw-item'><span class='dot {color}'></span>{b}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='hw-item'><span class='dot green'></span>Sin novedades significativas (última revisión reciente).</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== KPI: Frozen Meat Industry Monitor ====================
@st.cache_data(ttl=300)
def pct_30d(sym:str):
    try:
        d = yf.Ticker(sym).history(period="45d", interval="1d")
        if d is None or d.empty or d["Close"].dropna().shape[0] < 5:
            return None
        c = d["Close"].dropna()
        last = float(c.iloc[-1]); prev = float(c.iloc[0])
        return (last/prev - 1.0) * 100.0
    except Exception:
        return None

live_signals = []
for label, sym in [("Res (LE=F)", "LE=F"), ("Cerdo (HE=F)","HE=F"), ("USD/MXN", "MXN=X"), ("Maíz (ZC=F)","ZC=F")]:
    p = pct_30d(sym)
    if p is not None:
        sgn = "▲" if p>=0 else "▼"
        live_signals.append({"num": f"{p:+.1f}%", "sub": f"{label} · cambio 30D {sgn}", "badge":"mercado vivo"})

@st.cache_data(ttl=43200)
def gdelt_numbers(query:str, timespan="30d", maxrecords=30):
    try:
        r = requests.get(GDELT_DOC, params={
            "query": query, "mode":"ArtList", "format":"json",
            "timespan": timespan, "maxrecords": str(maxrecords)
        }, headers=COMMON_HEADERS, timeout=12)
        if r.status_code != 200: return []
        arts = (r.json() or {}).get("articles", []) or []
        out=[]
        for a in arts:
            t = a.get("title","")
            m_pct = re.search(r"([+-]?\d{1,2}(?:\.\d+)?\s?%)", t)
            m_usd = re.search(r"\$[\d,]+(\.\d+)?\s?(?:B|M|million|billion)", t, re.I)
            if not (m_pct or m_usd): 
                continue
            num = m_pct.group(1) if m_pct else m_usd.group(0)
            dom = a.get("domain","")
            out.append({"num": num, "sub": t, "badge": dom})
        return out[:8]
    except Exception:
        return []

news_metrics = []
news_metrics += gdelt_numbers("(Brazil%20poultry%20exports%20OR%20ABPA%20frango)")
news_metrics += gdelt_numbers("(USMEF%20pork%20exports%20OR%20USMEF%20beef%20exports)")
news_metrics += gdelt_numbers("(frozen%20chicken%20market%20growth%20OR%20frozen%20poultry%20market)")
news_metrics += gdelt_numbers("(Mexico%20chicken%20imports%20OR%20México%20importaciones%20pollo)")

items_im = (live_signals[:4] + news_metrics[:4])[:3]
items_im = ai_summarize_metrics(items_im)

st.markdown("<div class='card im-card'><div class='im-wrap'>", unsafe_allow_html=True)
if not items_im:
    st.markdown("<div class='im-item' style='opacity:1'><div class='im-num'>—</div><div class='im-sub'>Sin datos recientes</div></div>", unsafe_allow_html=True)
else:
    for it in items_im[:3]:
        num = it.get("num","—")
        sub = it.get("sub","")
        badge = it.get("badge","")
        extra = f" <span class='im-badge'>{badge}</span>" if badge else ""
        st.markdown(f"<div class='im-item'><div class='im-num'>{num}</div><div class='im-sub'>{sub}{extra}</div></div>", unsafe_allow_html=True)
st.markdown("</div></div>", unsafe_allow_html=True)

# ==================== PIE ====================
st.markdown(
    f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · "
    "Fuentes: Yahoo Finance (~15 min), GDELT (prensa global). IA opcional con OPENAI_API_KEY.</div>",
    unsafe_allow_html=True,
)

time.sleep(60)
st.rerun()
