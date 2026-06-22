"""통합 v4: 100m 격자 인구 배경 + 국토부 노선도 + 카드 OD
입력: grid100/ul100.shp (울산 100m, val=인구), routes_gukto.json, od_top_20260407.geojson
출력: ulsan_combined_v4.html, grid100_population.csv
"""
import csv, json
import shapefile
from pyproj import Transformer
T = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

# 100m 격자: 인구>0 셀만, 중심좌표 + 인구
r = shapefile.Reader("grid100/ul100", encoding="cp949")
fld = [f[0] for f in r.fields[1:]]
vi = fld.index("VAL")
cells = []
for sr in r.iterShapeRecords():
    try:
        v = float(sr.record[vi])
    except Exception:
        continue
    if not v or v <= 0:
        continue
    bb = sr.shape.bbox
    cx, cy = (bb[0]+bb[2])/2, (bb[1]+bb[3])/2
    lon, lat = T.transform(cx, cy)
    cells.append([round(lon, 5), round(lat, 5), int(v)])

with open("grid100_population.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["lon", "lat", "pop"])
    for c in cells: w.writerow(c)

vals = sorted(c[2] for c in cells); maxv = vals[int(len(vals)*0.99)]
print("100m 인구셀", len(cells), "| 합계", sum(vals), "| 최대", vals[-1], "| 98%상한", maxv)

routes = json.load(open("routes_gukto.json"))
od = json.load(open("od_top_20260407.geojson", encoding="utf-8"))["features"]
lines = [{"o": f["geometry"]["coordinates"][0], "d": f["geometry"]["coordinates"][1], "t": f["properties"]["trips"]} for f in od]

B = {"minLon": min(c[0] for c in cells), "maxLon": max(c[0] for c in cells),
     "minLat": min(c[1] for c in cells), "maxLat": max(c[1] for c in cells)}
data = {"cells": cells, "routes": routes, "od": lines, "maxv": maxv, "bounds": B, "cellM": 100}

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 인구밀도(100m 격자) + 버스 노선도 + OD</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#070b16;color:#e8eefc;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}canvas{position:absolute;inset:0;width:100%;height:100%}
.panel{position:absolute;background:#0f1830d0;backdrop-filter:blur(6px);border:1px solid #ffffff22;border-radius:12px;padding:12px 14px;font-size:13px}
#title{left:16px;top:16px;max-width:360px}#title h1{margin:0 0 6px;font-size:16px}#title p{margin:3px 0;font-size:12px;color:#bcd0f5;line-height:1.5}
#ctrl{right:16px;top:16px;line-height:1.9}#ctrl label{display:block;cursor:pointer}#ctrl input{margin-right:6px;vertical-align:-1px}
#leg{left:16px;bottom:16px}#leg i{display:inline-block;width:16px;height:10px;margin-right:6px;vertical-align:1px}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:11px;margin-top:6px}</style>
</head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 인구밀도(100m) + 버스 노선도 + OD</h1>
<p>배경: NGII 100m 격자 인구(2024.10, 8,029셀) · 선: 국토부 경유정류장 노선도 · 흐름: 카드 OD(2026-04-07)</p>
<span class="tag">전부 실데이터</span></div>
<div class="panel" id="ctrl">
<label><input type="checkbox" id="t_pop" checked> 인구 격자(100m)</label>
<label><input type="checkbox" id="t_rte" checked> 버스 노선도</label>
<label><input type="checkbox" id="t_od" checked> 카드 OD 흐름</label></div>
<div class="panel" id="leg"></div></div>
<script>
const D=__DATA__;const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
const B=D.bounds,pad=44,latC=(B.minLat+B.maxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(B.maxLon-B.minLon)*kx,dH=(B.maxLat-B.minLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
function P(lon,lat){return[ox+(lon-B.minLon)*kx*sc,H-(oy+(lat-B.minLat)*sc)];}
// 로그 스케일(인구 분포가 한쪽으로 치우쳐 있어) + 가시 바닥색(저인구도 보이게)
const STOPS=[[0,[35,70,110]],[0.3,[40,150,165]],[0.55,[120,205,120]],[0.78,[245,205,75]],[1,[240,75,50]]];
function col(v){let t=Math.log(1+Math.max(0,v))/Math.log(1+D.maxv);t=Math.min(1,t);
 for(let i=1;i<STOPS.length;i++){if(t<=STOPS[i][0]){const a=STOPS[i-1],b=STOPS[i],f=(t-a[0])/(b[0]-a[0]);
  return `rgb(${a[1][0]+(b[1][0]-a[1][0])*f|0},${a[1][1]+(b[1][1]-a[1][1])*f|0},${a[1][2]+(b[1][2]-a[1][2])*f|0})`;}}
 return 'rgb(240,75,50)';}
const S={pop:1,rte:1,od:1};for(const k of ['pop','rte','od'])document.getElementById('t_'+k).onchange=e=>S[k]=e.target.checked?1:0;
(()=>{let h='<b>100m 격자 인구(명, 로그)</b><br>';[5,20,50,150,400,900].forEach(v=>h+=`<div><i style="background:${col(v)}"></i>${v.toLocaleString()}</div>`);
 h+='<div style="margin-top:5px"><i style="background:#3a86ff"></i>버스 노선(국토부)</div><div><i style="background:#ffd54f"></i>OD 이동</div>';document.getElementById('leg').innerHTML=h;})();
let t0=performance.now();
function frame(now){fit();const tt=((now-t0)/2600)%1;
 x.fillStyle='#070b16';x.fillRect(0,0,W,H);
 if(S.pop){const px=Math.max(2.4,(D.cellM/111000*sc)*1.5);for(const[lon,lat,v] of D.cells){const p=P(lon,lat);x.fillStyle=col(v);x.fillRect(p[0]-px/2,p[1]-px/2,px,px);}}
 if(S.rte){x.strokeStyle='rgba(58,134,255,0.55)';x.lineWidth=0.8;for(const r of D.routes){x.beginPath();r.forEach((p,i)=>{const q=P(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});x.stroke();}}
 if(S.od){for(const l of D.od){const a=P(l.o[0],l.o[1]),b=P(l.d[0],l.d[1]);const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*0.18;
   x.strokeStyle='rgba(255,213,79,0.22)';x.lineWidth=Math.min(5,1+l.t/40);x.beginPath();x.moveTo(a[0],a[1]);x.quadraticCurveTo(mx,my,b[0],b[1]);x.stroke();
   const k=Math.max(1,Math.round(l.t/40));for(let j=0;j<k;j++){const f=(tt+j/k)%1,u=1-f;const qx=u*u*a[0]+2*u*f*mx+f*f*b[0],qy=u*u*a[1]+2*u*f*my+f*f*b[1];
    x.fillStyle='#ffd54f';x.shadowColor='#ffd54f';x.shadowBlur=6;x.beginPath();x.arc(qx,qy,2.3,0,7);x.fill();}}x.shadowBlur=0;}
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
</script></body></html>"""
out = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_combined_v4.html", "w", encoding="utf-8").write(out)
print("cells", len(cells), "routes", len(routes), "od", len(lines), "->", round(len(out)/1024), "KB")
