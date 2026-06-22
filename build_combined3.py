"""통합 v3: 500m 격자 인구 배경 + 국토부 경유정류장 노선도 + 카드 OD
입력: uploads의 경유정류장 csv, grid500_population.csv, od_top_20260407.geojson, ulsan_stop_coords_master.csv
출력: ulsan_combined_v3.html, routes_gukto.json
"""
import csv, json, re, glob
from collections import defaultdict

UP = glob.glob("/sessions/jolly-gifted-albattani/mnt/uploads/ulsan_route_stops_20260407*.csv")[-1]

# 좌표 사전 (정류소 위치 master): 이름 -> [모든 좌표] (동명 정류장 다수 대비)
from collections import defaultdict as dd
name2list = dd(list)
for r in csv.DictReader(open("ulsan_stop_coords_master.csv", encoding="utf-8-sig")):
    nm = (r.get("stop_name") or "").strip()
    try:
        name2list[nm].append((float(r["lon"]), float(r["lat"])))
    except Exception:
        pass
norm = lambda s: re.sub(r"[ .()\-]", "", s or "")
nnorm = dd(list)
for k, lst in name2list.items():
    nnorm[norm(k)].extend(lst)

def candidates(nm):
    if nm in name2list: return name2list[nm]
    n = norm(nm)
    if n in nnorm: return nnorm[n]
    res = []
    for mk, lst in nnorm.items():
        if n and (n in mk or mk in n) and abs(len(n) - len(mk)) <= 2:
            res.extend(lst)
    return res

def dist2(a, b):
    return (a[0]-b[0])**2 + (a[1]-b[1])**2

# 경유정류장 → 노선별 순서
routes = defaultdict(list)
names = set()
for r in csv.DictReader(open(UP, encoding="utf-8-sig")):
    routes[r["rte_id"]].append((int(r["sttn_seq"]), r["sttn_nm"]))
    names.add(r["sttn_nm"])
hit = sum(1 for nm in names if candidates(nm))
print(f"노선 {len(routes)} / 고유정류장명 {len(names)} / 좌표매칭 {hit} ({round(hit/len(names)*100)}%)")

JUMP2 = (0.06) ** 2  # 약 5km 이상 점프는 비정상으로 보고 끊음(직선 가로지름 방지)
polylines = []
for rid, lst in routes.items():
    lst.sort()
    pts = []
    prev = None
    for _, nm in lst:
        cands = candidates(nm)
        if not cands:
            continue
        # 직전 정류장과 가장 가까운 동명 후보 선택(먼 점프 방지)
        c = min(cands, key=lambda x: dist2(x, prev)) if prev else cands[0]
        # 그래도 직전과 너무 멀면(매칭 실패 의심) 건너뜀
        if prev and dist2(c, prev) > JUMP2:
            continue
        pts.append([round(c[0], 5), round(c[1], 5)])
        prev = c
    if len(pts) >= 2:
        polylines.append(pts)
json.dump(polylines, open("routes_gukto.json", "w"), separators=(",", ":"))
print(f"그려지는 노선 {len(polylines)} / 평균 점수 {round(sum(len(p) for p in polylines)/len(polylines))}")

# 배경: 500m 격자 인구
cells = []
for r in csv.DictReader(open("grid500_population.csv", encoding="utf-8-sig")):
    cells.append([float(r["lon"]), float(r["lat"]), int(r["pop"])])
vals = sorted(c[2] for c in cells); maxv = vals[int(len(vals)*0.98)]

# OD
od = json.load(open("od_top_20260407.geojson", encoding="utf-8"))["features"]
lines = [{"o": f["geometry"]["coordinates"][0], "d": f["geometry"]["coordinates"][1], "t": f["properties"]["trips"]} for f in od]

allc = cells
B = {"minLon": min(c[0] for c in allc), "maxLon": max(c[0] for c in allc),
     "minLat": min(c[1] for c in allc), "maxLat": max(c[1] for c in allc)}
data = {"cells": cells, "routes": polylines, "od": lines, "maxv": maxv, "bounds": B, "cellM": 500}

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 인구밀도 + 버스 노선도 + OD (통합)</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#070b16;color:#e8eefc;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}canvas{position:absolute;inset:0;width:100%;height:100%}
.panel{position:absolute;background:#0f1830d0;backdrop-filter:blur(6px);border:1px solid #ffffff22;border-radius:12px;padding:12px 14px;font-size:13px}
#title{left:16px;top:16px;max-width:360px}#title h1{margin:0 0 6px;font-size:16px}#title p{margin:3px 0;font-size:12px;color:#bcd0f5;line-height:1.5}
#ctrl{right:16px;top:16px;line-height:1.9}#ctrl label{display:block;cursor:pointer}#ctrl input{margin-right:6px;vertical-align:-1px}
#leg{left:16px;bottom:16px}#leg i{display:inline-block;width:16px;height:10px;margin-right:6px;vertical-align:1px}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:11px;margin-top:6px}</style>
</head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 인구밀도 + 버스 노선도 + OD</h1>
<p>배경: NGII 500m 격자 인구 · 선: 국토부 경유정류장 노선도(360) · 흐름: 카드 OD(2026-04-07)</p>
<span class="tag">전부 실데이터 · 노선·OD 동일 ID</span></div>
<div class="panel" id="ctrl">
<label><input type="checkbox" id="t_pop" checked> 인구 격자(500m)</label>
<label><input type="checkbox" id="t_rte" checked> 버스 노선도</label>
<label><input type="checkbox" id="t_od" checked> 카드 OD 흐름</label></div>
<div class="panel" id="leg"></div></div>
<script>
const D=__DATA__;const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
const B=D.bounds,pad=44,latC=(B.minLat+B.maxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(B.maxLon-B.minLon)*kx,dH=(B.maxLat-B.minLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
function P(lon,lat){return[ox+(lon-B.minLon)*kx*sc,H-(oy+(lat-B.minLat)*sc)];}
function col(v){const t=Math.sqrt(Math.min(1,v/D.maxv));return `rgb(${15+240*t|0},${30+70*t|0},${70-20*t|0})`;}
const S={pop:1,rte:1,od:1};for(const k of ['pop','rte','od'])document.getElementById('t_'+k).onchange=e=>S[k]=e.target.checked?1:0;
(()=>{let h='<b>500m 격자 인구(명)</b><br>';[0,300,800,1500,3000,5000].forEach(v=>h+=`<div><i style="background:${col(v)}"></i>${v.toLocaleString()}</div>`);
 h+='<div style="margin-top:5px"><i style="background:#3a86ff"></i>버스 노선(국토부)</div><div><i style="background:#ffd54f"></i>OD 이동</div>';document.getElementById('leg').innerHTML=h;})();
let t0=performance.now();
function frame(now){fit();const tt=((now-t0)/2600)%1;
 x.fillStyle='#070b16';x.fillRect(0,0,W,H);
 if(S.pop){const px=(D.cellM/111000*sc);for(const[lon,lat,v] of D.cells){const p=P(lon,lat);x.fillStyle=col(v);x.fillRect(p[0]-px/2,p[1]-px/2,px+0.6,px+0.6);}}
 if(S.rte){x.strokeStyle='rgba(58,134,255,0.55)';x.lineWidth=0.8;for(const r of D.routes){x.beginPath();r.forEach((p,i)=>{const q=P(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});x.stroke();}}
 if(S.od){for(const l of D.od){const a=P(l.o[0],l.o[1]),b=P(l.d[0],l.d[1]);const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*0.18;
   x.strokeStyle='rgba(255,213,79,0.22)';x.lineWidth=Math.min(5,1+l.t/40);x.beginPath();x.moveTo(a[0],a[1]);x.quadraticCurveTo(mx,my,b[0],b[1]);x.stroke();
   const k=Math.max(1,Math.round(l.t/40));for(let j=0;j<k;j++){const f=(tt+j/k)%1,u=1-f;const qx=u*u*a[0]+2*u*f*mx+f*f*b[0],qy=u*u*a[1]+2*u*f*my+f*f*b[1];
    x.fillStyle='#ffd54f';x.shadowColor='#ffd54f';x.shadowBlur=6;x.beginPath();x.arc(qx,qy,2.3,0,7);x.fill();}}x.shadowBlur=0;}
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
</script></body></html>"""
out = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_combined_v3.html", "w", encoding="utf-8").write(out)
print("cells", len(cells), "routes", len(polylines), "od", len(lines), "->", round(len(out)/1024), "KB")
