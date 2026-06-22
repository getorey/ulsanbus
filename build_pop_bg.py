"""SGIS 울산 읍면동 인구밀도 → WGS84 변환 → 인구밀도 배경(choropleth) 프로토타입
입력: sgis_emd_raw.txt (name|pop|density|cx|cy|ring(UTM-K))
출력: emd_population.geojson, ulsan_population_bg.html
"""
import csv, json
from pyproj import Transformer
T = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

feats = []
for line in open("sgis_emd_raw.txt", encoding="utf-8"):
    line = line.rstrip("\n")
    if not line:
        continue
    nm, pop, dens, cx, cy, ring = line.split("|")
    pts = []
    for pair in ring.split(";"):
        x, y = pair.split()
        lon, lat = T.transform(float(x), float(y))
        pts.append([round(lon, 6), round(lat, 6)])
    if pts and pts[0] != pts[-1]:
        pts.append(pts[0])
    feats.append({
        "type": "Feature",
        "properties": {"name": nm.replace("울산광역시 ", ""),
                       "pop": int(pop) if pop else None,
                       "density": float(dens) if dens else None},
        "geometry": {"type": "Polygon", "coordinates": [pts]},
    })

fc = {"type": "FeatureCollection", "features": feats}
json.dump(fc, open("emd_population.geojson", "w", encoding="utf-8"), ensure_ascii=False)

dens_vals = [f["properties"]["density"] for f in feats if f["properties"]["density"]]
print("읍면동:", len(feats), "| 밀도 범위:", round(min(dens_vals)), "~", round(max(dens_vals)),
      "| 최고밀도:", max(feats, key=lambda f: f["properties"]["density"] or 0)["properties"]["name"])

# 배경용 데이터(폴리곤+밀도) — 프로토타입에 임베드
polys = [{"n": f["properties"]["name"], "d": f["properties"]["density"] or 0,
          "p": f["properties"]["pop"] or 0, "c": f["geometry"]["coordinates"][0]} for f in feats]
allc = [c for pj in polys for c in pj["c"]]
B = {"minLon": min(c[0] for c in allc), "maxLon": max(c[0] for c in allc),
     "minLat": min(c[1] for c in allc), "maxLat": max(c[1] for c in allc)}
data = {"polys": polys, "bounds": B, "maxd": max(dens_vals)}

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 인구밀도 (읍면동) — SGIS 실데이터</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#0a0f1f;color:#e8eefc;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}canvas{position:absolute;inset:0;width:100%;height:100%}
.panel{position:absolute;background:#0f1830cc;backdrop-filter:blur(6px);border:1px solid #ffffff22;border-radius:12px;padding:12px 14px;font-size:13px}
#title{left:16px;top:16px;max-width:330px}#title h1{margin:0 0 6px;font-size:16px}#title p{margin:3px 0;font-size:12px;color:#bcd0f5;line-height:1.5}
#legend{right:16px;top:16px;font-size:12px}#legend i{display:inline-block;width:16px;height:10px;margin-right:6px;vertical-align:1px}
#tip{position:absolute;pointer-events:none;background:#000a;border:1px solid #fff3;border-radius:6px;padding:4px 8px;font-size:12px;display:none}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:11px;margin-top:6px}</style>
</head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 인구밀도 (읍면동)</h1>
<p>SGIS 통계청 실데이터 · 2023년 총조사 · 읍면동 56개</p>
<p>색이 진할수록 인구밀도(명/㎢) 높음</p><span class="tag">실데이터: SGIS 인구밀도</span></div>
<div class="panel" id="legend"></div><div id="tip"></div></div>
<script>
const D=__DATA__;const c=document.getElementById('c'),x=c.getContext('2d'),tip=document.getElementById('tip');
let W,H,dpr=devicePixelRatio||1;function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);draw();}addEventListener('resize',rs);
const B=D.bounds,pad=40,latC=(B.minLat+B.maxLat)/2,kx=Math.cos(latC*Math.PI/180);
function P(lon,lat){const dW=(B.maxLon-B.minLon)*kx,dH=(B.maxLat-B.minLat);const sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);
 const ox=(W-dW*sc)/2,oy=(H-dH*sc)/2;return[ox+(lon-B.minLon)*kx*sc,H-(oy+(lat-B.minLat)*sc)];}
// 색: 밀도 0..max → 연파랑→진빨강 (sqrt 스케일)
function col(d){const t=Math.sqrt(d/D.maxd);const r=[20,40,90],g=[40,90,160],b=[255,120,60];
 const R=r[0]+(b[0]-r[0])*t,G=g[0]+(b[1]-g[0])*t,Bl=90+(b[2]-90)*t;return `rgb(${R|0},${G|0},${Bl|0})`;}
function draw(){x.clearRect(0,0,W,H);x.fillStyle='#0a0f1f';x.fillRect(0,0,W,H);
 for(const pg of D.polys){x.beginPath();pg.c.forEach((p,i)=>{const q=P(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});x.closePath();
  x.fillStyle=col(pg.d);x.fill();x.strokeStyle='#0a0f1f';x.lineWidth=0.8;x.stroke();}}
// 범례
(()=>{let h='<b>인구밀도(명/㎢)</b><br>';const steps=[0,2000,6000,12000,20000,28000];
 steps.forEach(v=>{h+=`<div><i style="background:${col(v)}"></i>${v.toLocaleString()}</div>`;});document.getElementById('legend').innerHTML=h;})();
// hover
c.addEventListener('mousemove',e=>{const mx=e.offsetX,my=e.offsetY;let hit=null;
 for(const pg of D.polys){x.beginPath();pg.c.forEach((p,i)=>{const q=P(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});x.closePath();
  if(x.isPointInPath(mx*dpr,my*dpr)){hit=pg;break;}}
 if(hit){tip.style.display='block';tip.style.left=(mx+12)+'px';tip.style.top=(my+12)+'px';
  tip.innerHTML=`<b>${hit.n}</b><br>인구 ${hit.p.toLocaleString()}명<br>밀도 ${hit.d.toLocaleString()}/㎢`;}else tip.style.display='none';});
rs();
</script></body></html>"""
out = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_population_bg.html", "w", encoding="utf-8").write(out)
print("wrote emd_population.geojson, ulsan_population_bg.html", round(len(out)/1024), "KB")
