# LaSultana Meat Index — v2.8 (rotador fijo + Health híbrido + spacing unificado)
import os, re, json, time, threading, datetime as dt
from zoneinfo import ZoneInfo
from pathlib import Path
import requests, streamlit as st, yfinance as yf

st.set_page_config(page_title="LaSultana Meat Index", layout="wide")

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

/* === Unificar spacing entre TODOS los bloques (A=B=C) === */
.element-container{margin-bottom:12px !important;}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
header[data-testid="stHeader"]{display:none;} #MainMenu{visibility:hidden;} footer{visibility:hidden}

/* Logo */
.logo-row{width:100%;display:flex;justify-content:center;align-items:center;margin:26px 0 22px}

/* Cinta bursátil */
.tape{border:1px solid var(--line);border-radius:12px;background:#0d141a;overflow:hidden;min-height:44px}
.tape-track{display:flex;width:max-content;animation:marquee 210s linear infinite;will-change:transform;backface-visibility:hidden;transform:translateZ(0)}
.tape-group{display:inline-block;white-space:nowrap;padding:10px 0;font-size:112%}
.item{display:inline-block;margin:0 32px}
.up{color:var(--up)} .down{color:var(--down)} .muted{color:var(--muted)}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* KPIs */
.grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:12px}
.kpi{display:flex;justify-content:space-between;align-items:flex-start}
.kpi .title{font-size:18px;color:var(--muted)}
.kpi .big{font-size:52px;font-weight:900;letter-spacing:.2px;line-height:1.0;margin:10px 0 8px}
.kpi .delta{font-size:20px;margin-left:12px}
.kpi .delta{margin-left:auto}          /* pega la flecha a la derecha */
.kpi .right{display:flex;align-items:flex-start}
.unit-inline{font-size:.7em;color:var(--muted);font-weight:600;letter-spacing:.3px}

/* Unidad abajo del número (USD/lb) */
.unit-bottom{
  display:block; margin-top:8px; font-size:1.05em; font-weight:600; color:var(--muted);
}

/* 2 columnas: Health (izq) + Insights (der) */
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

/* Market Insights (rotador, sin superposición ni “espejo”) */
.im-card{min-height:190px}
.im-wrap{
  position:relative; width:100%; height:178px;
  overflow:hidden; border:1px solid var(--line); border-radius:12px;
  padding:10px; display:flex; align-items:center; justify-content:center;
  isolation:isolate; contain:content;
}
.im-item{
  position:absolute; inset:0;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  opacity:0; transform:translateY(10px);
  animation:imCycle 40.5s ease-in-out infinite; /* 35% más largo: 30s -> 40.5s */
  will-change:opacity,transform; pointer-events:none;
}
.im-item:nth-child(1){animation-delay:0s}
.im-item:nth-child(2){animation-delay:13.5s}
.im-item:nth-child(3){animation-delay:27s}
/* 40% transición más suave: ventanas más largas de blend */
@keyframes imCycle{
  0%, 6%   {opacity:0; transform:translateY(10px)}
  10%, 36% {opacity:1; transform:translateY(0)}
  40%, 100%{opacity:0; transform:translateY(-6px)}
}
.im-num{font-size:60px;font-weight:900;letter-spacing:.2px;line-height:1.0;margin:0 0 10px 0;text-align:center}
.im-sub{font-size:18px;color:var(--txt);opacity:.95;line-height:1.25;margin:2px 0 8px 0;text-align:center}
.im-desc{font-size:16px;color:var(--muted);line-height:1.35;margin:0 14px;text-align:center}

/* Footer */
.caption{color:var(--muted)!important;margin-top:8px}
</style>
""", unsafe_allow_html=True)

# ====================== HELPERS ======================
def fmt2(x):
    if x is None: return "—"
    s=f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def fmt4(x):
    if x is None: return "—"
    s=f"{x:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
def humanize_delta(minutes: float) -> str:
    if minutes < 1: return "hace segundos"
    if minutes < 60: return f"hace {int(minutes)} min"
    hours = minutes/60
    if hours < 24: return f"hace {int(hours)} h"
    days = int(hours//24); return f"hace {days} d"

def load_json(path: Path, default):
    try:
        if path.exists(): return json.loads(path.read_text(encoding="utf-8"))
    except: pass
    return default
def save_json(path: Path, data):
    try: path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except: pass
def is_stale(payload: dict, max_age_sec: int) -> bool:
    try:
        ts = payload.get("updated"); 
        if not ts: return True
        t = dt.datetime.fromisoformat(ts)
        return (dt.datetime.utcnow() - t).total_seconds() > max_age_sec
    except: return True

# ====================== LOGO ======================
st.markdown("<div class='logo-row'>", unsafe_allow_html=True)
if Path("ILSMeatIndex.png").exists():
    st.image("ILSMeatIndex.png", width=440)
st.markdown("</div>", unsafe_allow_html=True)

# ====================== CINTA ======================
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

# ====================== FX & FUTUROS ======================
SHOW_PER_LB = True   # si True, divide futuros entre 100 y muestra USD/lb

@st.cache_data(ttl=75)
def get_yahoo(sym:str): return quote_last_and_change(sym)

fx,fx_chg=get_yahoo("MXN=X")
lc,lc_chg=get_yahoo("LE=F")
lh,lh_chg=get_yahoo("HE=F")

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
    if price is None:
        num="N/D"; unit="USD/100 lb" if not SHOW_PER_LB else "USD/lb"
        price_html=f"<div class='big'>{num}<span class='unit-bottom'>{unit}</span></div>"; delta=""
    else:
        p = price/100.0 if SHOW_PER_LB else price
        unit="USD/lb" if SHOW_PER_LB else "USD/100 lb"
        price_html=f"<div class='big'>{fmt2(p)}<span class='unit-bottom'>{unit}</span></div>"
        if chg is None: delta=""
        else:
            # si mostramos por libra, el delta también por libra (aprox escala/100)
            d = chg/100.0 if SHOW_PER_LB else chg
            cls="up" if d>=0 else "down"; arr="▲" if d>=0 else "▼"
            delta=f"<div class='delta {cls}'>{arr} {fmt2(abs(d))}</div>"
    return f"<div class='card'><div class='kpi'><div><div class='title'>{title}</div>{price_html}</div>{delta}</div></div>"

kpi_html = "".join([
    kpi_fx("USD/MXN",fx,fx_chg),
    kpi_cme("Res en pie",lc,lc_chg),
    kpi_cme("Cerdo en pie",lh,lh_chg),
])
st.markdown(f"<div class='grid'>{kpi_html}</div>", unsafe_allow_html=True)

# ====================== IA opcional ======================
OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY","").strip()

def ai_health(groups):
    """Resume en máx 2 bullets por país; si no hay, devuelve fallback."""
    def fallback():
        out={}
        for c,its in groups.items():
            bullets=[]
            for it in its[:2]:
                s="🔴" if it.get("severity")=="red" else ("🟠" if it.get("severity")=="amb" else "🟢")
                bullets.append(f"{s} {it.get('species','Ganado')} — {it.get('title','').strip()} ({it.get('domain','')} · {it.get('when_txt','')})")
            out[c]=bullets or ["🟢 Sin novedades significativas (última revisión reciente)."]
        return out
    if not OPENAI_API_KEY: return fallback()
    try:
        payload={"model":"gpt-4o-mini",
                 "messages":[
                    {"role":"system","content":"Devuelve JSON por país con hasta 2 bullets concisos en español. No inventes."},
                    {"role":"user","content":json.dumps(groups,ensure_ascii=False)}
                 ],
                 "temperature":0.2,"response_format":{"type":"json_object"}}
        r=requests.post("https://api.openai.com/v1/chat/completions",
                        headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
                        json=payload, timeout=10)
        txt=r.json()["choices"][0]["message"]["content"]
        data=json.loads(txt)
        return data if isinstance(data,dict) else fallback()
    except Exception:
        return fallback()

# ====================== GDELT ======================
GDELT_DOC="https://api.gdeltproject.org/api/v2/doc/doc"
COMMON_HEADERS={"User-Agent":"Mozilla/5.0"}
DISEASE_Q=("("
           "avian%20influenza%20OR%20HPAI%20OR%20bird%20flu%20OR%20African%20swine%20fever%20"
           "OR%20ASF%20OR%20foot-and-mouth%20OR%20FMD%20OR%20PRRS)")
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

def _gdelt(country_code:str, timespan="30d", maxrecords=40):
    try:
        r=requests.get(GDELT_DOC, params={
            "query":f"{DISEASE_Q} sourcecountry:{country_code}",
            "mode":"ArtList","format":"json","timespan":timespan,
            "maxrecords":str(maxrecords),"sort":"DateDesc"
        }, headers=COMMON_HEADERS, timeout=7)
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

@st.cache_data(ttl=900)
def gdelt_recent(cc:str): return _gdelt(cc, "30d", 30)

@st.cache_data(ttl=3600)
def gdelt_history(cc:str): return _gdelt(cc, "180d", 60)

@st.cache_data(ttl=43200)
def gdelt_numbers(query:str, timespan="45d", maxrecords=30):
    try:
        r=requests.get(GDELT_DOC, params={
            "query":query,"mode":"ArtList","format":"json","timespan":timespan,
            "maxrecords":str(maxrecords),"sort":"DateDesc"
        }, headers=COMMON_HEADERS, timeout=7)
        if r.status_code!=200: return []
        arts=(r.json() or {}).get("articles",[]) or []
        out=[]
        for a in arts:
            t=a.get("title","")
            m_pct=re.search(r"([+-]?\d{1,3}(?:\.\d+)?\s?%)", t)
            m_usd=re.search(r"\$[\d,]+(?:\.\d+)?\s?(?:B|M|million|billion)", t, re.I)
            if not (m_pct or m_usd): continue
            num=m_pct.group(1) if m_pct else m_usd.group(0)
            out.append({"num":num,"sub":t,"desc":a.get("domain","")})
        return out[:6]
    except Exception:
        return []

# ====================== SNAPSHOTS + REFRESCO EN 2° PLANO ======================
DATA_DIR = Path(".")
HW_FILE = DATA_DIR / "hw_snapshot.json"
IM_FILE = DATA_DIR / "im_snapshot.json"

def default_hw():
    return {
        "updated": dt.datetime.utcnow().isoformat(),
        "counts": {"US":0,"BR":0,"MX":0},
        "summary": {
            "US": ["🟢 Sin novedades significativas (última revisión reciente)."],
            "BR": ["🟢 Sin novedades significativas (última revisión reciente)."],
            "MX": ["🟢 Sin novedades significativas (última revisión reciente)."],
        }
    }

def default_im():
    return {
        "updated": dt.datetime.utcnow().isoformat(),
        "items": [
            {"num":"—","sub":"Sin datos recientes","desc":"—"},
            {"num":"—","sub":"Sin datos recientes","desc":"—"},
            {"num":"—","sub":"Sin datos recientes","desc":"—"},
        ]
    }

hw_payload = load_json(HW_FILE, default_hw())
im_payload = load_json(IM_FILE, default_im())

def refresh_hw_async():
    def run():
        try:
            # Modo híbrido: primero 30d, si vacío completar con 180d
            data={}
            counts={}
            for cc in ["US","BR","MX"]:
                recent = gdelt_recent(cc)
                hist   = gdelt_history(cc) if not recent else []
                counts[cc]=len(recent)
                bullets=[]
                # prioridad: rojas/ámbar recientes
                for it in recent:
                    if it.get("severity") in ("red","amb"):
                        s="🔴" if it["severity"]=="red" else "🟠"
                        bullets.append(f"{s} {it['species']} — {it['title']} ({it['domain']} · {it['when_txt']})")
                        if len(bullets)>=2: break
                # si no hay, muestra el último evento histórico (atenuado)
                if not bullets and hist:
                    it=hist[0]
                    bullets.append(f"🟢 Último evento: {it['species']} — {it['title']} ({it['domain']} · {it['when_txt']})")
                if not bullets:
                    bullets=["🟢 Sin novedades significativas (última revisión reciente)."]
                data[cc]=bullets[:2]
            payload={"updated": dt.datetime.utcnow().isoformat(), "counts": counts, "summary": data}
            save_json(HW_FILE, payload)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()

def refresh_im_async():
    def run():
        try:
            @st.cache_data(ttl=600)
            def pct_30d(sym:str):
                try:
                    d=yf.Ticker(sym).history(period="45d", interval="1d")
                    if d is None or d.empty or d["Close"].dropna().shape[0] < 5: return None
                    c=d["Close"].dropna(); first=float(c.iloc[0]); last=float(c.iloc[-1])
                    return (last/first - 1.0)*100.0
                except: return None

            live=[]
            for label,sym in [("USD/MXN","MXN=X"),("Res (LE=F)","LE=F"),("Cerdo (HE=F)","HE=F")]:
                p=pct_30d(sym)
                if p is not None:
                    sign="+" if p>=0 else ""
                    live.append({"num":f"{sign}{p:.1f}%", "sub":f"{label} · cambio 30D",
                                 "desc":"Variación de cierre a cierre en los últimos 30 días (Yahoo Finance)."})

            news=[]
            news += gdelt_numbers("(Brazil%20poultry%20exports%20OR%20ABPA%20frango)")
            news += gdelt_numbers("(USMEF%20pork%20exports%20OR%20USMEF%20beef%20exports)")
            news += gdelt_numbers("(Mexico%20chicken%20imports%20OR%20México%20importaciones%20pollo)")

            items = (live[:3] + news[:3])[:3]
            if OPENAI_API_KEY:
                try:
                    payload={"model":"gpt-4o-mini",
                             "messages":[
                                {"role":"system","content":"Devuelve lista JSON de objetos {num, sub, desc}. Reduce títulos largos y no inventes."},
                                {"role":"user","content":json.dumps(items,ensure_ascii=False)}
                             ],
                             "temperature":0.2,"response_format":{"type":"json_object"}}
                    r=requests.post("https://api.openai.com/v1/chat/completions",
                                    headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
                                    json=payload, timeout=10)
                    parsed=json.loads(r.json()["choices"][0]["message"]["content"])
                    if isinstance(parsed,list): items=parsed
                    elif isinstance(parsed,dict) and "items" in parsed: items=parsed["items"]
                except Exception:
                    pass

            if not items: items = default_im()["items"]
            while len(items) < 3: items += items

            payload={"updated": dt.datetime.utcnow().isoformat(), "items": items[:3]}
            save_json(IM_FILE, payload)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()

# Disparar refresh en bg si está viejo
if is_stale(hw_payload, 15*60):  # 15 min
    refresh_hw_async()
if is_stale(im_payload, 10*60):  # 10 min
    refresh_im_async()

# ====================== RENDER: HEALTH + INSIGHTS ======================
counts = hw_payload.get("counts", {"US":0,"BR":0,"MX":0})
summary = hw_payload.get("summary", default_hw()["summary"])

hw_html=[]
hw_html.append(
  f"<div class='hw-head'><div class='hw-title'>Livestock Health Watch</div>"
  f"<div class='hw-badges'><span class='tag'>US {counts.get('US',0)}</span>"
  f"<span class='tag'>BR {counts.get('BR',0)}</span><span class='tag'>MX {counts.get('MX',0)}</span></div></div>"
)
hw_html.append("<div class='hw-grid'>")
for cc,label in [("US","Estados Unidos"),("BR","Brasil"),("MX","México")]:
    bullets=summary.get(cc,[]) or ["🟢 Sin novedades significativas (última revisión reciente)."]
    hw_html.append("<div class='hw-box'>")
    hw_html.append(f"<h4>{label}</h4>")
    for b in bullets[:2]:
        color="amb"
        if "🔴" in b: color="red"
        elif "🟢" in b: color="green"
        hw_html.append(f"<div class='hw-item'><span class='dot {color}'></span>{b}</div>")
    hw_html.append("</div>")
hw_html.append("</div>")
hw_html_str="".join(hw_html)

items_im = im_payload.get("items", default_im()["items"])[:3]
im_parts = ["<div class='card im-card'><div class='im-wrap'>"]
for it in items_im:
    num=it.get("num","—"); sub=it.get("sub",""); desc=it.get("desc","")
    # No escapar como texto: imprimimos HTML directo
    im_parts.append(f"""
      <div class="im-item">
        <div class="im-num">{num}</div>
        <div class="im-sub">{sub}</div>
        <div class="im-desc">{desc if desc else "&nbsp;"}</div>
      </div>
    """)
im_parts.append("</div></div>")
im_html_str="".join(im_parts)

st.markdown(f"<div class='sec-grid'><div class='card'>{hw_html_str}</div>{im_html_str}</div>", unsafe_allow_html=True)

# ====================== FOOTER (hora Monterrey) ======================
local_now = dt.datetime.now(ZoneInfo("America/Monterrey"))
st.markdown(
    f"<div class='caption'>Actualizado: {local_now.strftime('%Y-%m-%d %H:%M:%S')}</div>",
    unsafe_allow_html=True,
)

# Refresco gentle
time.sleep(60)
st.rerun()
