"""통합 시각화: SGIS 인구밀도 배경 + BIS 실노선 + 카드 OD 흐름
입력: sgis_emd_raw.txt(인구밀도), routes_all_encoded.txt(노선 polyline), od_top_20260407.geojson(OD)
출력: ulsan_combined.html
"""
import json, re
from pyproj import Transformer
T = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

# 1) 인구밀도 읍면동 폴리곤
polys = []
for line in open("sgis_emd_raw.txt", encoding="utf-8"):
    line = line.rstrip("\n")
    if not line:
        continue
    nm, pop, dens, cx, cy, ring = line.split("|")
    pts = []
    for pair in ring.split(";"):
        x, y = pair.split()
        lon, lat = T.transform(float(x), float(y))
        pts.append([round(lon, 5), round(lat, 5)])
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    polys.append({"n": nm.replace("울산광역시 ", ""), "d": float(dens) if dens else 0,
                  "p": int(pop) if pop else 0, "c": pts})

# 2) 노선 polyline 디코드 + 다운샘플
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
raw = open("routes_all_encoded.txt", encoding="utf-8").read().strip()
for blk in re.split(r"~(?=\d+\|)", raw):
    if "|" not in blk:
        continue
    no, enc = blk.split("|", 1)
    pts = decode(enc)  # (lon,lat)
    pts = [p for p in pts if 35.0 < p[1] < 36.0 and 128.5 < p[0] < 129.9]
    if len(pts) >= 2:
        routes.append([p for p in pts])

# 3) OD 흐름
od = json.load(open("od_top_20260407.geojson", encoding="utf-8"))["features"]
lines = [{"o": f["geometry"]["coordinates"][0], "d": f["geometry"]["coordinates"][1],
          "t": f["properties"]["trips"]} for f in od]

maxd = max(p["d"] for p in polys)
allc = [c for pg in polys for c in pg["c"]]
B = {"minLon": min(c[0] for c in allc), "maxLon": max(c[0] for c in allc),
     "minLat": min(c[1] for c in allc), "maxLat": max(c[1] for c in allc)}
data = {"polys": polys, "routes": routes, "od": lines, "maxd": maxd, "bounds": B}

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 인구밀도 + 버스 이동 흐름 (통합)</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#0a0f1f;color:#e8eefc;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}canvas{position:absolute;inset:0;width:100%;height:100%}
.panel{position:absolute;background:#0f1830d0;backdrop-filter:blur(6px);border:1px solid #ffffff22;border-radius:12px;padding:12px 14px;font-size:13px}
#title{left:16px;top:16px;max-width:340px}#title h1{margin:0 0 6px;font-size:16px}#title p{margin:3px 0;font-size:12px;color:#bcd0f5;line-height:1.5}
#ctrl{right:16px;top:16px;font-size:13px;line-height:1.9}#ctrl label{display:block;cursor:pointer}
#ctrl input{vertical-align:-1px;margin-right:6px}
#leg{left:16px;bottom:16px}#leg i{display:inline-block;width:16px;height:10px;margin-right:6px;vertical-align:1px}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:11px;margin-top:6px}</style>
</head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 인구밀도 + 버스 이동 흐름</h1>
<p>배경: SGIS 읍면동 인구밀도(실데이터) · 선: BIS 실노선 · 흐름: 카드 OD(2026-04-07)</p>
<span class="tag">전부 실데이터</span></div>
<div class="panel" id="ctrl">
<label><input type="checkbox" id="t_pop" checked> 인구밀도 배경</label>
<label><input type="checkbox" id="t_rte"> 버스 노선 (515)</label>
<label><input type="checkbox" id="t_od" checked> 카드 OD 흐름</label>
</div>
<div class="panel" id="leg"></div></div>
<script>
const D=__DATA__;const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
const B=D.bounds,pad=44,latC=(B.minLat+B.maxLat)/2,kx=Math.cos(latC*Math.PI/180);
function P(lon,lat){const dW=(B.maxLon-B.minLon)*kx,dH=(B.maxLat-B.minLat);const sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);
 const ox=(W-dW*sc)/2,oy=(H-dH*sc)/2;return[ox+(lon-B.minLon)*kx*sc,H-(oy+(lat-B.minLat)*sc)];}
function col(d){const t=Math.sqrt(d/D.maxd);return `rgb(${20+235*t|0},${40+80*t|0},${90-30*t|0})`;}
const S={pop:1,rte:0,od:1};
for(const k of ['pop','rte','od']){document.getElementById('t_'+k).onchange=e=>{S[k]=e.target.checked?1:0;};}
(()=>{let h='<b>인구밀도(명/㎢)</b><br>';[0,2000,6000,12000,20000,28000].forEach(v=>h+=`<div><i style="background:${col(v)}"></i>${v.toLocaleString()}</div>`);
 h+='<div style="margin-top:5px"><i style="background:#3a86ff"></i>버스 노선</div><div><i style="background:#ffd54f"></i>OD 이동</div>';document.getElementById('leg').innerHTML=h;})();
let t0=performance.now();
function frame(now){const tt=((now-t0)/2600)%1;
 x.fillStyle='#0a0f1f';x.fillRect(0,0,W,H);
 if(S.pop)for(const pg of D.polys){x.beginPath();pg.c.forEach((p,i)=>{const q=P(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});x.closePath();x.fillStyle=col(pg.d);x.fill();x.strokeStyle='#0a0f1f';x.lineWidth=0.6;x.stroke();}
 else {x.strokeStyle='#1a2540';for(const pg of D.polys){x.beginPath();pg.c.forEach((p,i)=>{const q=P(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});x.closePath();x.lineWidth=0.6;x.stroke();}}
 if(S.rte){x.strokeStyle='rgba(58,134,255,0.5)';x.lineWidth=0.8;for(const r of D.routes){x.beginPath();r.forEach((p,i)=>{const q=P(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});x.stroke();}}
 if(S.od){for(const l of D.od){const a=P(l.o[0],l.o[1]),b=P(l.d[0],l.d[1]);const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*0.18;
   x.strokeStyle='rgba(255,213,79,0.25)';x.lineWidth=Math.min(5,1+l.t/40);x.beginPath();x.moveTo(a[0],a[1]);x.quadraticCurveTo(mx,my,b[0],b[1]);x.stroke();
   const k=Math.max(1,Math.round(l.t/40));
   for(let j=0;j<k;j++){const f=(tt+j/k)%1,u=1-f;const px=u*u*a[0]+2*u*f*mx+f*f*b[0],py=u*u*a[1]+2*u*f*my+f*f*b[1];
    x.fillStyle='#ffd54f';x.shadowColor='#ffd54f';x.shadowBlur=6;x.beginPath();x.arc(px,py,2.4,0,7);x.fill();}}
  x.shadowBlur=0;}
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
</script></body></html>"""
out = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_combined.html", "w", encoding="utf-8").write(out)
print("polys", len(polys), "routes", len(routes), "od", len(lines), "->", round(len(out)/1024), "KB")
