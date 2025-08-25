# ==================== USDA POLLO (con proxy + snapshot) ====================
def _jina(u: str) -> str:
    # Proxy de solo lectura que devuelve el contenido tal cual
    clean = u.replace("https://", "").replace("http://", "")
    return f"https://r.jina.ai/http://{clean}"

POULTRY_BASE = [
    "https://www.ams.usda.gov/mnreports/aj_py018.txt",
    "https://www.ams.usda.gov/mnreports/AJ_PY018.txt",
    "https://mpr.datamart.ams.usda.gov/mnreports/aj_py018.txt",
    "https://mpr.datamart.ams.usda.gov/mnreports/AJ_PY018.txt",
]
# probamos directo y vía proxy
POULTRY_URLS = []
for u in POULTRY_BASE:
    POULTRY_URLS.append(u)
    POULTRY_URLS.append(_jina(u))

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
HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept":"text/plain,*/*;q=0.8",
}
SNAP = "poultry_last.json"

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
            return (lo + hi) / 2.0
        except: pass
    nums = re.findall(r"(\d+(?:\.\d+)?)", U)
    if nums:
        try: return float(nums[-1])
        except: pass
    return None

@st.cache_data(ttl=1800)
def fetch_usda() -> dict:
    # probamos mirrors y luego los mismos mediante r.jina.ai
    for url in POULTRY_URLS:
        try:
            r = requests.get(url, timeout=12, headers=HEADERS)
            if r.status_code != 200:
                continue
            txt = r.text
            # r.jina.ai trae texto plano; si devuelve html, lo descartamos
            if "<html" in txt.lower() and "r.jina.ai" not in url:
                continue
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            out = {}
            for disp, pats in POULTRY_MAP.items():
                for ln in lines:
                    if any(re.search(p, ln.upper()) for p in pats):
                        v = _avg(ln)
                        if v is not None:
                            out[disp] = v
                            break
            if out:
                return out
        except Exception:
            continue
    return {}

def load_snap():
    if not os.path.exists(SNAP): return {}
    try:
        with open(SNAP, "r") as f: return json.load(f)
    except Exception:
        return {}

def save_snap(d: dict):
    try:
        with open(SNAP, "w") as f: json.dump({k: float(v) for k,v in d.items()}, f)
    except Exception:
        pass

def poultry_latest():
    cur = fetch_usda()
    prev = load_snap()
    if cur:
        res = {}
        for k,v in cur.items():
            pv = prev.get(k)
            if isinstance(pv, dict): pv = pv.get("price")
            dlt = 0.0 if pv is None else (float(v) - float(pv))
            res[k] = {"price": float(v), "delta": float(dlt)}
        save_snap(cur)
        return res, "live"
    if prev:
        res = {k: {"price": float((v.get("price") if isinstance(v,dict) else v)), "delta": 0.0}
               for k,v in prev.items()
               if (v if not isinstance(v,dict) else v.get("price")) is not None}
        return res, "snapshot"
    return None, "none"

def build_poultry_html(data: dict, status: str) -> str:
    order = [
        "Breast - B/S","Breast T/S","Tenderloins","Wings, Whole","Wings, Drummettes",
        "Wings, Mid-Joint","Party Wings","Leg Quarters","Leg Meat - B/S",
        "Thighs - B/S","Thighs","Drumsticks","Whole Legs","Whole Broiler/Fryer",
    ]
    rows=[]
    for k in order:
        it = data.get(k)
        if not it: continue
        price, delta = it["price"], it["delta"]
        cls = "green" if (delta or 0) >= 0 else "red"
        arr = "▲" if (delta or 0) >= 0 else "▼"
        rows.append(
          f"<tr><td>{LABELS_ES.get(k,k)}</td>"
          f"<td><span class='price-lg'>{fmt2(price)} <span class='unit-inline--p'>USD/lb</span></span> "
          f"<span class='price-delta {cls}'>{arr} {fmt2(abs(delta))}</span></td></tr>"
        )
    badge = {"live":"<span class='badge'>USDA: en vivo</span>",
             "snapshot":"<span class='badge'>USDA: último disponible</span>",
             "none":"<span class='badge'>USDA: sin datos iniciales</span>"}[status]
    return f"""
    <div class="card poultry">
      <div class="title" style="color:var(--txt);margin-bottom:6px">
        Piezas de Pollo, Precios U.S. National (USDA) {badge}
      </div>
      <table>
        <thead><tr><th>Producto</th><th>Precio</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """
