"""통합 v2: NGII 500m 격자 인구밀도 배경 + BIS 실노선 + 카드 OD 흐름
입력: grid500/g1..g5/vl_blk.shp (500m 격자 인구), routes_all_encoded.txt, od_top_20260407.geojson
출력: ulsan_combined_grid.html, grid500_population.csv
"""
import json, re, glob
import shapefile
from pyproj import Transformer
T = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

# 1) 500m 격자 인구 (5개 구 합치기) — 중심좌표 + 인구
cells = []
for shp in sorted(glob.glob("grid500/g*/vl_blk.shp")):
    r = shapefile.Reader(shp, encoding="cp949")
    fld = [f[0] for f in r.fields[1:]]
    vi = fld.index("val")
    for sr in r.shapeRecords():
        bb = sr.shape.bbox  # xmin,ymin,xmax,ymax (UTM-K)
        cx, cy = (bb[0]+bb[2])/2, (bb[1]+bb[3])/2
        val = sr.record[vi]
        try:
            val = float(val)
        except Exception:
            continue
        lon, lat = T.transform(cx, cy)
        cells.append([round(lon, 5), round(lat, 5), int(val)])

# 중복 제거(구 경계 겹침 대비): 좌표키로
seen = {}
for lon, lat, v in cells:
    seen[(lon, lat)] = v
cells = [[k[0], k[1], v] for k, v in seen.items()]

# CSV 저장
import csv
with open("grid500_population.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["lon", "lat", "pop"])
    for c in cells: w.writerow(c)

vals = sorted(v for _, _, v in cells)
maxv = vals[int(len(vals)*0.98)]  # 98퍼센타일을 상한으로(이상치 완화)
print("격자 셀:", len(cells), "| 인구 최대:", vals[-1], "| 98%상한:", maxv, "| 총인구합:", sum(vals))

# 2) 노선
def decode(s):
    co, i, lat, lon = [], 0, 0, 0
    while i < len(s):
        for is_lon in (0, 1):
            sh, res = 0, 0
            while True:
                b = ord(s[i]) - 63; i += 1
                res |= (b & 0x1f) << sh; sh += 5
                if b < 0x20: break
            d = ~(res >> 1) if (res & 1) else (res >> 1)
            if is_lon: lon += d
            else: lat += d
        co.append([round(lon/1e5, 5), round(lat/1e5, 5)])
    return co
routes = []
for blk in re.split(r"~(?=\d+\|)", open("routes_all_encoded.txt", encoding="utf-8").read().strip()):
    if "|" not in blk: continue
    no, enc = blk.split("|", 1)
    pts = [p for p in decode(enc) if 35.0 < p[1] < 36.0 and 128.5 < p[0] < 129.9]
    if len(pts) >= 2: routes.append(pts)

# 3) OD
od = json.load(open("od_top_20260407.geojson", encoding="utf-8"))["features"]
lines = [{"o": f["geometry"]["coordinates"][0], "d": f["geometry"]["coordinates"][1], "t": f["properties"]["trips"]} for f in od]

allc = cells
B = {"minLon": min(c[0] for c in allc), "maxLon": max(c[0] for c in allc),
     "minLat": min(c[1] for c in allc), "maxLat": max(c[1] for c in allc)}
data = {"cells": cells, "routes": routes, "od": lines, "maxv": maxv, "bounds": B, "cellM": 500}

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 인구밀도(500m 격자) + 버스 이동</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#070b16;color:#e8eefc;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}canvas{position:absolute;inset:0;width:100%;height:100%}
.panel{position:absolute;background:#0f1830d0;backdrop-filter:blur(6px);border:1px solid #ffffff22;border-radius:12px;padding:12px 14px;font-size:13px}
#title{left:16px;top:16px;max-width:350px}#title h1{margin:0 0 6px;font-size:16px}#title p{margin:3px 0;font-size:12px;color:#bcd0f5;line-height:1.5}
#ctrl{right:16px;top:16px;line-height:1.9}#ctrl label{display:block;cursor:pointer}#ctrl input{margin-right:6px;vertical-align:-1px}
#leg{left:16px;bottom:16px}#leg i{display:inline-block;width:16px;height:10px;margin-right:6px;vertical-align:1px}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:11px;margin-top:6px}</style>
</head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 인구밀도(500m 격자) + 버스 이동</h1>
<p>배경: NGII 국토통계 500m 격자 총인구(2024.10) · 선: BIS 실노선 · 흐름: 카드 OD(2026-04-07)</p>
<span class="tag">전부 실데이터</span></div>
<div class="panel" id="ctrl">
<label><input type="checkbox" id="t_pop" checked> 인구 격자(500m)</label>
<label><input type="checkbox" id="t_rte"> 버스 노선</label>
<label><input type="checkbox" id="t_od" checked> 카드 OD 흐름</label></div>
<div class="panel" id="leg"></div></div>
<script>
const D=__DATA__;const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
const B=D.bounds,pad=44,latC=(B.minLat+B.maxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(B.maxLon-B.minLon)*kx,dH=(B.maxLat-B.minLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
function P(lon,lat){return[ox+(lon-B.minLon)*kx*sc,H-(oy+(lat-B.minLat)*sc)];}
function col(v){const t=Math.sqrt(Math.min(1,v/D.maxv));return `rgb(${15+240*t|0},${30+70*t|0},${70-20*t|0})`;}
const S={pop:1,rte:0,od:1};for(const k of ['pop','rte','od'])document.getElementById('t_'+k).onchange=e=>S[k]=e.target.checked?1:0;
(()=>{let h='<b>500m 격자 인구(명)</b><br>';[0,300,800,1500,3000,5000].forEach(v=>h+=`<div><i style="background:${col(v)}"></i>${v.toLocaleString()}</div>`);
 h+='<div style="margin-top:5px"><i style="background:#3a86ff"></i>버스 노선</div><div><i style="background:#ffd54f"></i>OD 이동</div>';document.getElementById('leg').innerHTML=h;})();
let t0=performance.now();
function frame(now){fit();const tt=((now-t0)/2600)%1;
 x.fillStyle='#070b16';x.fillRect(0,0,W,H);
 if(S.pop){const px=(D.cellM/111000*sc);  // 셀 한 변(위도기준) 화면 px
  for(const[lon,lat,v] of D.cells){const p=P(lon,lat);x.fillStyle=col(v);x.fillRect(p[0]-px/2,p[1]-px/2,px+0.6,px+0.6);}}
 if(S.rte){x.strokeStyle='rgba(58,134,255,0.5)';x.lineWidth=0.8;for(const r of D.routes){x.beginPath();r.forEach((p,i)=>{const q=P(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});x.stroke();}}
 if(S.od){for(const l of D.od){const a=P(l.o[0],l.o[1]),b=P(l.d[0],l.d[1]);const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*0.18;
   x.strokeStyle='rgba(255,213,79,0.22)';x.lineWidth=Math.min(5,1+l.t/40);x.beginPath();x.moveTo(a[0],a[1]);x.quadraticCurveTo(mx,my,b[0],b[1]);x.stroke();
   const k=Math.max(1,Math.round(l.t/40));for(let j=0;j<k;j++){const f=(tt+j/k)%1,u=1-f;const qx=u*u*a[0]+2*u*f*mx+f*f*b[0],qy=u*u*a[1]+2*u*f*my+f*f*b[1];
    x.fillStyle='#ffd54f';x.shadowColor='#ffd54f';x.shadowBlur=6;x.beginPath();x.arc(qx,qy,2.3,0,7);x.fill();}}x.shadowBlur=0;}
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
</script></body></html>"""
out = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_combined_grid.html", "w", encoding="utf-8").write(out)
print("cells", len(cells), "routes", len(routes), "od", len(lines), "->", round(len(out)/1024), "KB")
