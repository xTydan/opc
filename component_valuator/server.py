from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
from engine import parse_import,build_report,search_query,olx_url,infer_specs,money,extract_components
ROOT=Path(__file__).resolve().parent; DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
LF=DATA/"source-listings.json"; OF=DATA/"olx-offers.json"
def load(p):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return []
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")
class H(BaseHTTPRequestHandler):
    def reply(self,x,code=200):
        b=json.dumps(x,ensure_ascii=False).encode(); self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(b)
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Access-Control-Allow-Headers","Content-Type"); self.send_header("Access-Control-Allow-Methods","POST, OPTIONS"); self.end_headers()
    def do_GET(self):
        p=urlparse(self.path).path
        if p=="/":
            b=(ROOT/"index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b); return
        if p=="/app.js":
            b=(ROOT/"app.js").read_bytes(); self.send_response(200); self.send_header("Content-Type","text/javascript; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b); return
        if p=="/api/state":
            listings=load(LF); offers=load(OF); comps=[]; seen=set()
            for listing in listings:
                for c in listing.get("components",[]):
                    k=(c["category"],c["model"].lower())
                    if k not in seen:
                        seen.add(k); q=search_query(c); comps.append({**c,"search_query":q,"search_url":olx_url(q)})
            return self.reply({"listings":len(listings),"offers":len(offers),"components":comps,"report":build_report(listings,offers)})
        self.send_error(404)
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0"))
        if n>20000000: return self.send_error(413)
        try: body=json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError: return self.send_error(400)
        p=urlparse(self.path).path
        if p=="/api/import":
            rows=parse_import(body); save(LF,rows); return self.reply({"ok":True,"listings":len(rows),"components":sum(len(x["components"]) for x in rows)})
        if p=="/api/collect":
            old=load(OF); indexed={x.get("url"):x for x in old if x.get("url")}
            for x in body.get("offers",[]):
                if not isinstance(x,dict) or not x.get("url") or not money(x.get("price")): continue
                cat=x.get("category")
                if cat not in ("cpu","gpu","ram","motherboard","storage","psu","cooling","case"): continue
                x["price"]=money(x["price"]); parsed=next((c for c in extract_components(x.get("title","")) if c["category"]==cat),None); x["model"]=parsed["model"] if parsed else x.get("title",""); x["specs"]=parsed["specs"] if parsed else infer_specs(cat,x.get("title",""))
                indexed[x["url"]]=x
            save(OF,list(indexed.values())); return self.reply({"ok":True,"received":len(body.get("offers",[])),"stored":len(indexed)})
        self.send_error(404)
if __name__=="__main__":
    print("PC Component Valuator: http://127.0.0.1:8766"); ThreadingHTTPServer(("127.0.0.1",8766),H).serve_forever()
