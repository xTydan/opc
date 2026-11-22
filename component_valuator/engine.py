from __future__ import annotations
import re, statistics
from datetime import datetime, timezone
from urllib.parse import quote_plus
from typing import Any

CATEGORIES = ("cpu","gpu","ram","motherboard","storage","psu","cooling","case")
def now_iso(): return datetime.now(timezone.utc).isoformat()
def money(v):
    if isinstance(v,(int,float)): return float(v) if v>0 else None
    if isinstance(v,str):
        s=v.replace("\xa0"," ").replace("zł","").replace("PLN","").strip()
        s=re.sub(r"(?<=\d)[ .](?=\d{3}(?:\D|$))","",s).replace(",",".")
        m=re.search(r"\d+(?:\.\d+)?",s); return float(m.group()) if m else None
    return None
def normalize(s): return re.sub(r"[^a-z0-9]+"," ",str(s).lower()).strip()
def infer_specs(category, model):
    s=model.lower().replace(",","."); out={}
    if category=="ram":
        m=re.search(r"\bddr([345])\b",s)
        if m: out["memory_type"]="DDR"+m.group(1)
        m=re.search(r"\b(8|16|24|32|48|64|96|128)\s*gb\b",s)
        if m: out["capacity_gb"]=int(m.group(1))
        m=re.search(r"\b(3[2-9]\d{2}|4\d{3}|5\d{3}|6\d{3}|7\d{3}|8\d{3})\s*mhz\b",s)
        if m: out["speed_mhz"]=int(m.group(1))
    elif category=="storage":
        m=re.search(r"\b(128|240|256|480|500|512|1000|1024|2000|2048|4000)\s*(gb|tb)\b",s)
        if m: out["capacity_gb"]=int(float(m.group(1))*(1024 if m.group(2)=="tb" else 1))
        if "nvme" in s or "m.2" in s: out["interface"]="NVMe"
        elif "sata" in s: out["interface"]="SATA"
        if "hdd" in s: out["drive_type"]="HDD"
        elif "ssd" in s or out.get("interface")=="NVMe": out["drive_type"]="SSD"
    elif category=="gpu":
        m=re.search(r"\b(4|6|8|10|12|16|20|24)\s*gb\b",s)
        if m: out["vram_gb"]=int(m.group(1))
    elif category=="psu":
        m=re.search(r"\b(3\d{2}|4\d{2}|5\d{2}|6\d{2}|7\d{2}|8\d{2}|9\d{2}|1\d{3})\s*w\b",s)
        if m: out["wattage"]=int(m.group(1))
    return out
def extract_components(text):
    patterns=[
    ("cpu",r"\b(?:ryzen\s+[3579]\s+\d{4,5}[a-z]{0,2}|(?:intel\s+)?core\s+i[3579]\s*[- ]?\s*\d{4,5}[a-z]{0,2}|i[3579]\s*[- ]?\s*\d{4,5}[a-z]{0,2})\b"),
    ("gpu",r"\b(?:rtx|gtx)\s*\d{3,4}\s*(?:ti|super)?(?:\s*\d{1,2}\s*gb)?|\bradeon\s+(?:rx\s*)?\d{3,4}\s*(?:xt|xtx)?\b"),
    ("ram",r"\b(?:ddr[345]\s*)?(?:8|16|24|32|48|64|96|128)\s*gb\s*(?:ddr[345])?(?:\s*\d{3,4}\s*mhz)?|\bddr[345]\s*(?:8|16|24|32|48|64|96|128)\s*gb(?:\s*\d{3,4}\s*mhz)?"),
    ("motherboard",r"\b(?:b\d{3,4}|x\d{3,4}|z\d{3,4}|h\d{3,4})[a-z0-9-]*\b"),
    ("storage",r"\b(?:128|240|256|480|500|512|1000|1024|2000|2048|4000)\s*(?:gb|tb)\s*(?:nvme|m\.2|ssd|hdd)?\b"),
    ("psu",r"\b(?:corsair|be\s*quiet|seasonic|chieftec|silentiumpc|endrorfy|cooler master)\b.{0,40}\b\d{3,4}\s*w\b|\b\d{3,4}\s*w\b.{0,35}\b(?:80\s*plus|bronze|gold|platinum|psu|zasilacz)\b")]
    found=[]
    for cat,pat in patterns:
        for m in re.finditer(pat,text,re.I):
            model=re.sub(r"\s+"," ",m.group()).strip(" ,.-")
            if model and not any(x["category"]==cat and normalize(x["model"])==normalize(model) for x in found):
                found.append({"category":cat,"model":model,"source_text":m.group(),"specs":infer_specs(cat,model)})
    return found
def parse_import(payload):
    rows=(payload.get("listings") or payload.get("items") or payload.get("results") or []) if isinstance(payload,dict) else payload if isinstance(payload,list) else []
    out=[]
    for i,row in enumerate(rows):
        if not isinstance(row,dict): continue
        desc=str(row.get("description") or row.get("text") or "")
        comps=row.get("components") or row.get("parsed_components") or extract_components(str(row.get("title") or "")+" "+desc)
        normalized=[]
        for c in comps:
            if not isinstance(c,dict): continue
            cat=str(c.get("category") or c.get("type") or "").lower()
            model=str(c.get("model") or c.get("name") or c.get("raw") or "").strip()
            if cat in CATEGORIES and model: normalized.append({**c,"category":cat,"model":model,"specs":c.get("specs") or infer_specs(cat,model)})
        out.append({"id":str(row.get("id") or row.get("url") or i),"title":str(row.get("title") or ""),"url":row.get("url"),"price":money(row.get("price")),"description":desc,"components":normalized})
    return out
def component_class(c):
    s=c.get("specs") or {}; cat=c.get("category")
    if cat=="ram": return f'{s.get("memory_type","DDR?")} {s.get("capacity_gb","?")}GB {s.get("speed_mhz","dowolne")}MHz'
    if cat=="storage": return f'{s.get("drive_type","dysk")} {s.get("interface","dowolny interfejs")} {s.get("capacity_gb","?")}GB'
    if cat=="gpu": return f'GPU {c.get("performance_tier","benchmark wymagany")} {s.get("vram_gb","?")}GB'
    if cat=="cpu": return f'CPU {c.get("performance_tier","benchmark wymagany")} {c.get("socket","socket nieznany")}'
    if cat=="motherboard": return f'płyta {c.get("socket","socket nieznany")} {s.get("memory_type","RAM nieznany")}'
    if cat=="psu": return f'zasilacz {s.get("wattage","?")}W {c.get("quality_tier","jakość nieznana")}'
    return c.get("model","?")
def search_query(c):
    s=c.get("specs") or {}; cat=c.get("category")
    if cat=="ram": terms=[s.get("memory_type"),f'{s["capacity_gb"]}GB' if s.get("capacity_gb") else None,f'{s["speed_mhz"]}MHz' if s.get("speed_mhz") else None,"RAM"]
    elif cat=="storage": terms=[s.get("drive_type"),s.get("interface"),f'{s["capacity_gb"]}GB' if s.get("capacity_gb") else None]
    else: terms=[c.get("model"),cat]
    return " ".join(str(x) for x in terms if x)
def olx_url(q): return "https://www.olx.pl/oferty/q-"+quote_plus(q).replace("+","-")
def compatibility(a,b):
    if a.get("category")!=b.get("category"): return 0,[]
    cat=a["category"]; x=a.get("specs") or {}; y=b.get("specs") or {}; why=[]
    if cat=="ram":
        if x.get("memory_type") and y.get("memory_type")!=x["memory_type"]: return 0,["inna generacja DDR"]
        if x.get("capacity_gb") and y.get("capacity_gb")!=x["capacity_gb"]: return 0,["inna pojemność"]
        if x.get("speed_mhz") and y.get("speed_mhz") and abs(x["speed_mhz"]-y["speed_mhz"])/x["speed_mhz"]>.12: return 0,["taktowanie poza ±12%"]
        return .92,["ta sama generacja i pojemność","zbliżone taktowanie"]
    if cat=="storage":
        for k in ("drive_type","interface"):
            if x.get(k) and y.get(k)!=x[k]: return 0,[f"niezgodny {k}"]
        if x.get("capacity_gb") and y.get("capacity_gb") and abs(x["capacity_gb"]-y["capacity_gb"])/x["capacity_gb"]>.20: return 0,["inna klasa pojemności"]
        return .82,["zgodny typ/interfejs i zbliżona pojemność"]
    if cat in ("gpu","cpu"):
        sa,sb=a.get("benchmark_score"),b.get("benchmark_score")
        if not sa or not sb or not a.get("benchmark_name") or a.get("benchmark_name")!=b.get("benchmark_name"): return 0,["brak tego samego benchmarku"]
        if abs(sa-sb)/sa>.18: return 0,["wydajność poza ±18%"]
        if cat=="gpu" and x.get("vram_gb") and y.get("vram_gb") and abs(x["vram_gb"]-y["vram_gb"])>4: return 0,["duża różnica VRAM"]
        return .8,["zbliżona wydajność w tym samym benchmarku"]
    if cat=="motherboard":
        for k in ("socket",):
            if a.get(k) and b.get(k)!=a[k]: return 0,[f"niezgodny {k}"]
        if x.get("memory_type") and y.get("memory_type")!=x["memory_type"]: return 0,["inna generacja RAM"]
        return .75,["zgodna platforma"]
    if cat=="psu":
        if x.get("wattage") and y.get("wattage") and abs(x["wattage"]-y["wattage"])/x["wattage"]>.15: return 0,["inna klasa mocy"]
        if a.get("quality_tier") and b.get("quality_tier")!=a["quality_tier"]: return 0,["inna klasa jakości"]
        return .7,["zbliżona moc"]
    return 0,["brak reguły bezpiecznego dopasowania"]
def robust_price(prices):
    if len(prices)<3: return None,[]
    ordered=sorted(prices); q=statistics.quantiles(ordered,n=4,method="inclusive"); q1,q3=q[0],q[2]; iqr=q3-q1
    used=[p for p in ordered if q1-1.5*iqr<=p<=q3+1.5*iqr]
    if len(used)<3: used=ordered
    return round(statistics.median(used),2),used
def value_component(target,offers,min_samples=5):
    matches=[]
    for offer in offers:
        if offer.get("category")!=target.get("category") or not offer.get("price") or offer.get("status")=="inactive": continue
        score,why=compatibility(target,offer)
        if score: matches.append({**offer,"similarity":score,"match_reasons":why})
    exact=[m for m in matches if normalize(m.get("model",""))==normalize(target.get("model",""))]
    selected=exact if len(exact)>=min_samples else matches
    price,used=robust_price([float(x["price"]) for x in selected])
    if len(used)<min_samples: price=None
    conf="wysoka" if price is not None and len(used)>=10 and exact else "średnia" if price is not None else "brak danych"
    return {"category":target["category"],"model":target["model"],"class":component_class(target),"estimated_market_price":price,"sample_count":len(used),"exact_model_count":len(exact),"confidence":conf,"method":"dokładny model" if exact and selected is exact else "odpowiedniki klasy","comparables":selected[:100],"updated_at":now_iso(),"reason":None if price is not None else f"Za mało dopasowanych ofert: {len(used)}/{min_samples}. Cena pozostaje niewyznaczona."}
def build_report(listings,offers):
    targets=[]; seen=set()
    for listing in listings:
        for c in listing.get("components",[]):
            key=(c["category"],normalize(c["model"]))
            if key not in seen: seen.add(key); targets.append(c)
    return {"generated_at":now_iso(),"offer_count":len(offers),"target_count":len(targets),"valuations":[value_component(c,offers) for c in targets]}
