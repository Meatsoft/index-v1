# LaSultana Meat Index — v2.1 (layout fijo y sin vacíos)
import os, re, json, time, datetime as dt
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")
try: st.cache_data.clear()
except: pass

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

/* === Zona News KPIs (2 columnas) === */
.sec-grid{display:grid;grid-template-columns:1.6fr 1fr;gap:12px}
@media (max-width:1100px){ .sec-grid{grid-template-columns:1fr} }

/* Health Watch */
.hw-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.hw-title{font-size:18px;color:var(--muted)}
.hw-badges .tag{display:inline-block;margin-left:6px;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px}
.hw-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.hw-box{border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.hw-box h4{margin:0 0 6px 0;font-size:15px;color:var(--muted)}
.hw-item{margin:6px 0;padding:8px 10px;border:1px solid var(--line);border-radius:10px}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}
.dot.red{background:var(--down)} .dot.amb{background:#f0ad4e} .dot.green{background:#3cb371}

/* Industry Monitor (rotador) */
.im-card{min-height:150px}
.im-wrap{position:relative;height:130px;overflow:hidden;width:100%}
.im-item{position:absolute;left:0;right:0;top:0;opacity:0;animation:fade 12s linear infinite}
.im-item:nth-child(1){animation-delay:0s}
.im-item:nth-child(2){animation-delay:4s}
.im-item:nth-child(3){animation-delay:8s}
/* Arranca visible (nada de pantalla en blanco) */
@keyframes fade{
  0% {opacity:1; transform:translateY(0)}
  30% {opacity:1}
  33% {opacity:0; transform:translateY(-5px)}
  100% {opacity:0}
}
.im-num{font-size:44px;font-weight:900;letter-spacing:.2px;margin-bottom:8px;text-align:center}
.im-sub{font-size:16px;color:var(--muted);text-align:center}
.im-badge{display:inline-block;margin-left:8px;padding:3px 8px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px}

.caption{color:var(--muted)!important;margin-top:8px}
</style>
""", unsafe_allow_html=True)

# ==================== HELPERS ====================
def fmt2(x): 
    if x is None: return "—"
    s=f"{x:,.2f}"; return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x):
    if x is None: return "—"
    s=f"{x:,.4f}"; return s.replace(",", "X").replace(".", ",").replace("X", ".")
def humanize_delta(minutes: float) -> str:
    if minutes < 1: return "hace segundos"
    if minutes < 60: return f"hace {int(minutes)} min"
    hours = minutes/60
    if hours < 24: return f"hace {int(hours)} h"
    days = int(hours//24); return f"hace {days} d"

# ==================== LOGO ====================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if os.path.exists("ILSMeatIndex.png"):
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== CINTA SUPERIOR ====================
COMPANIES_USD=[("Tyson Foods","TSN"),("Pilgrim’s Pride","PPC"),("JBS","JBS"),("BRF","BRFS"),
               ("Hormel Foods","HRL"),("Seaboard","SEB"),("Minerva","MRVSY"),
               ("Cal-Maine Foods","CALM"),("Vital Farms","VITL"),("WH Group","WHGLY"),
               ("Wingstop","WING"),("Yum! Brands","YUM"),("Restaurant Brands Intl.","QSR"),
               ("Sysco","SYY"),("US Foods","USFD"),("Performance Food Group","PFGC"),("Walmart","WMT")]

@st.cache_data(ttl=75)
def quote_last_and_change(sym:str):
    try:
        t=yf.Ticker(sym); fi=t.fast_info
        last=fi.get("last_price"); prev=fi.get("previous_close")
        if last is not None: return float(last),(float(last)-float(prev)) if prev is not None else None
    except: pass
    try:
        inf=yf.Ticker(sym).info or {}
        last=inf.get("regularMarketPrice"); prev=inf.get("regularMarketPreviousClose")
        if last is not None: return float(last),(float(last)-float(prev)) if prev is not None else None
    except: pass
    try:
        d=yf.Ticker(sym).history(period="10d", interval="1d")
        if d is None or d.empty: return None,None
        c=d["Close"].dropna(); last=float(c.iloc[-1]); prev=float(c.iloc[-2]) if c.shape[0]>=2 else None
        return last,(last-prev) if prev is not None else None
    except: return None,None

items=[]
for name,sym in COMPANIES_USD:
    last,chg=quote_last_and_change(sym)
    if last is None: continue
    if chg is None: items.append(f"<span class='item'>{name} ({sym}) <b>{last:.2f}</b></span>")
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

# ==================== FX & FUTUROS ====================
@st.cache_data(ttl=75)
def get_yahoo(sym:str): return quote_last_and_change(sym)

fx,fx_chg=get_yahoo("MXN=X"); lc,lc_chg=get_yahoo("LE=F"); lh,lh_chg=get_yahoo("HE=F")

def kpi_fx(title,val,chg):
    if val is None: val_html="<div class='big'>N/D</div>"; delta=""
    else:
        val_html=f"<div class='big'>{fmt4(val)}</div>"
        if chg is None: delta=""
        else:
            cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
            delta=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"<div class='card'><div class='kpi'><div><div class='title'>{title}</div>{val_html}</div>{delta}</div></div>"

def kpi_cme(title,price,chg):
    unit="USD/100 lb"
    if price is None: price_html=f"<div class='big'>N/D <span class='unit-inline'>{unit}</span></div>"; delta=""
    else:
        price_html=f"<div class='big'>{fmt2(price)} <span class='unit-inline'>{unit}</span></div>"
        if chg is None: delta=""
        else:
            cls="up" if chg>=0 else "down"; arr="▲" if chg>=0 else "▼"
            delta=f"<div class='delta {cls}'>{arr} {fmt2(abs(chg))}</div>"
    return f"<div class='card'><div class='kpi'><div><div class='title'>{title}</div>{price_html}</div>{delta}</div></div>"

st.markdown("<div class='grid'>", unsafe_allow_html=True)
st.markdown(kpi_fx("USD/MXN",fx,fx_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Res en pie",lc,lc_chg), unsafe_allow_html=True)
st.markdown(kpi_cme("Cerdo en pie",lh,lh_chg), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ==================== IA opcional ====================
OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY","").strip()

def ai_health(groups):
    def fallback():
        out={}
        for c,its in groups.items():
            bullets=[]
            for it in its[:2]:
                s="🔴" if it.get("severity")=="red" else ("🟠" if it.get("severity")=="amb" else "🟢")
                bullets.append(f"{s} {it.get('species','Ganado')} — {it.get('title','').strip()} ({it.get('domain','')} · {it.get('when_txt','')})")
            out[c]=bullets or ["🟢 Sin novedades relevantes."]
        return out
    if not OPENAI_API_KEY: return fallback()
    try:
        payload={"model":"gpt-4o-mini",
                 "messages":[
                    {"role":"system","content":"Resume en español, máx 2 bullets por país, sin inventar; incluye especie y antigüedad."},
                    {"role":"user","content":json.dumps(groups,ensure_ascii=False)}
                 ],
                 "temperature":0.2,"response_format":{"type":"json_object"}}
        r=requests.post("https://api.openai.com/v1/chat/completions",
                        headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
                        json=payload, timeout=15)
        txt=r.json()["choices"][0]["message"]["content"]
        data=json.loads(txt)
        return data if isinstance(data,dict) else fallback()
    except Exception:
        return fallback()

def ai_metrics(items):
    if not OPENAI_API_KEY: return items
    try:
        payload={"model":"gpt-4o-mini",
                 "messages":[
                    {"role":"system","content":"Devuelve lista JSON de objetos {num, sub, badge}. No inventes."},
                    {"role":"user","content":json.dumps(items,ensure_ascii=False)}
                 ],
                 "temperature":0.2,"response_format":{"type":"json_object"}}
        r=requests.post("https://api.openai.com/v1/chat/completions",
                        headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
                        json=payload, timeout=15)
        data=json.loads(r.json()["choices"][0]["message"]["content"])
        if isinstance(data,list): return data
        if isinstance(data,dict) and "items" in data and isinstance(data["items"],list): return data["items"]
        return items
    except Exception:
        return items

# ==================== GDELT ====================
GDELT_DOC="https://api.gdeltproject.org/api/v2/doc/doc"
COMMON_HEADERS={"User-Agent":"Mozilla/5.0"}
DISEASE_Q=("("
           "avian%20influenza%20OR%20HPAI%20OR%20bird%20flu%20OR%20African%20swine%20fever%20"
           "OR%20ASF%20OR%20foot-and-mouth%20OR%20FMD%20OR%20PRRS)")
COUNTRY_MAP={"US":"Estados Unidos","BR":"Brasil","MX":"México"}
SPECIES_REGEX=[(r"\b(pollo|aves|broiler|chicken)\b","Pollo"),
               (r"\b(pavo|turkey)\b","Pavo"),
               (r"\b(cerdo|swine|hog|pork)\b","Cerdo"),
               (r"\b(res|bovine|cattle)\b","Res")]
def detect_species(text:str)->str:
    u=text.lower()
    for pat,label in SPECIES_REGEX:
        if re.search(pat,u): return label
    return "Ganado"
def severity(title:str)->str:
    u=title.lower()
    if any(k in u for k in ["confirmed","confirmado","quarantine","cuarentena","culling","sacrificio","outbreak","brote","emergency"]): return "red"
    if any(k in u for k in ["detected","detección","suspected","sospecha","cases","casos","alert"]): return "amb"
    return "green"

@st.cache_data(ttl=600)
def gdelt_search(cc:str, timespan="30d", maxrecords=50):
    try:
        r=requests.get(GDELT_DOC, params={
            "query":f"{DISEASE_Q} sourcecountry:{cc}",
            "mode":"ArtList","format":"json","timespan":timespan,
            "maxrecords":str(maxrecords),"sort":"DateDesc"
        }, headers=COMMON_HEADERS, timeout=12)
        if r.status_code!=200: return []
        arts=(r.json() or {}).get("articles",[]) or []
        now=dt.datetime.utcnow(); out=[]
        for a in arts:
            t=a.get("title","").strip()
            if not t: continue
            dom=a.get("domain",""); seen=a.get("seendate","")
            when=""
            try:
                d=dt.datetime.strptime(seen,"%Y%m%d%H%M%S")
                minutes=(now-d).total_seconds()/60.0
                when=humanize_delta(minutes)
            except: pass
            out.append({"title":t,"url":a.get("url",""),"domain":dom,"when_txt":when,
                        "species":detect_species(t),"severity":severity(t)})
        rank={"red":0,"amb":1,"green":2}
        out=sorted(out, key=lambda x: rank.get(x.get("severity","amb"),1))
        return out[:maxrecords]
    except Exception:
        return []

# ==================== SECCIÓN: Health Watch + Industry Monitor ====================
US_items=gdelt_search("US"); BR_items=gdelt_search("BR"); MX_items=gdelt_search("MX")
counts={"US":len(US_items),"BR":len(BR_items),"MX":len(MX_items)}
groups={"US":US_items[:6],"BR":BR_items[:6],"MX":MX_items[:6]}
summary=ai_health(groups)

# Señales vivas (30D)
@st.cache_data(ttl=300)
def pct_30d(sym:str):
    try:
        d=yf.Ticker(sym).history(period="45d", interval="1d")
        if d is None or d.empty or d["Close"].dropna().shape[0]<5: return None
        c=d["Close"].dropna(); last=float(c.iloc[-1]); prev=float(c.iloc[0])
        return (last/prev-1.0)*100.0
    except: return None

live_signals=[]
for label,sym in [("Res (LE=F)","LE=F"),("Cerdo (HE=F)","HE=F"),("USD/MXN","MXN=X"),("Maíz (ZC=F)","ZC=F")]:
    p=pct_30d(sym)
    if p is not None:
        sgn="▲" if p>=0 else "▼"
        live_signals.append({"num": f"{p:+.1f}%", "sub": f"{label} · cambio 30D {sgn}", "badge":"mercado vivo"})

@st.cache_data(ttl=43200)
def gdelt_numbers(query:str, timespan="45d", maxrecords=40):
    try:
        r=requests.get(GDELT_DOC, params={
            "query":query,"mode":"ArtList","format":"json","timespan":timespan,
            "maxrecords":str(maxrecords),"sort":"DateDesc"
        }, headers=COMMON_HEADERS, timeout=12)
        if r.status_code!=200: return []
        arts=(r.json() or {}).get("articles",[]) or []
        out=[]
        for a in arts:
            t=a.get("title","")
            m_pct=re.search(r"([+-]?\d{1,3}(?:\.\d+)?\s?%)", t)
            m_usd=re.search(r"\$[\d,]+(?:\.\d+)?\s?(?:B|M|million|billion)", t, re.I)
            if not (m_pct or m_usd): continue
            num=m_pct.group(1) if m_pct else m_usd.group(0)
            out.append({"num":num,"sub":t,"badge":a.get("domain","")})
        return out[:8]
    except Exception:
        return []

news_metrics=[]
news_metrics += gdelt_numbers("(Brazil%20poultry%20exports%20OR%20ABPA%20frango)")
news_metrics += gdelt_numbers("(USMEF%20pork%20exports%20OR%20USMEF%20beef%20exports)")
news_metrics += gdelt_numbers("(frozen%20chicken%20market%20growth%20OR%20frozen%20poultry%20market)")
news_metrics += gdelt_numbers("(Mexico%20chicken%20imports%20OR%20México%20importaciones%20pollo)")
items_im=(live_signals[:4]+news_metrics[:4])[:3]
items_im=ai_metrics(items_im)
if not items_im:
    items_im=[{"num":"—","sub":"Sin datos recientes","badge":""}]*3
while len(items_im)<3:
    items_im += items_im

# Render 2 columnas
hw_html = []
hw_html.append(
    f"<div class='hw-head'><div class='hw-title'>Livestock Health Watch</div>"
    f"<div class='hw-badges'><span class='tag'>US {counts['US']}</span>"
    f"<span class='tag'>BR {counts['BR']}</span><span class='tag'>MX {counts['MX']}</span></div></div>"
)
hw_html.append("<div class='hw-grid'>")
for cc in ["US","BR","MX"]:
    bullets=summary.get(cc,[]) or ["🟢 Sin novedades significativas (última revisión reciente)."]
    country={"US":"Estados Unidos","BR":"Brasil","MX":"México"}[cc]
    hw_html.append("<div class='hw-box'>")
    hw_html.append(f"<h4>{country}</h4>")
    for b in bullets[:2]:
        color="amb"
        if "🔴" in b: color="red"
        elif "🟢" in b: color="green"
        hw_html.append(f"<div class='hw-item'><span class='dot {color}'></span>{b}</div>")
    hw_html.append("</div>")
hw_html.append("</div>")
hw_html_str = "".join(hw_html)

im_html = ["<div class='card im-card'><div class='im-wrap'>"]
for i,it in enumerate(items_im[:3],1):
    num=it.get("num","—"); sub=it.get("sub",""); badge=it.get("badge","")
    extra=f" <span class='im-badge'>{badge}</span>" if badge else ""
    im_html.append(f"<div class='im-item'><div class='im-num'>{num}</div><div class='im-sub'>{sub}{extra}</div></div>")
im_html.append("</div></div>")
im_html_str="".join(im_html)

st.markdown(f"<div class='sec-grid'><div class='card'>{hw_html_str}</div>{im_html_str}</div>", unsafe_allow_html=True)

# ==================== PIE ====================
st.markdown(
    f"<div class='caption'>Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · "
    "Fuentes: Yahoo Finance (~15 min), GDELT (prensa global). IA opcional con OPENAI_API_KEY.</div>",
    unsafe_allow_html=True,
)

time.sleep(60)
st.rerun()
