"""실제 카드 OD 이동선 시연 프로토타입 (노선 31001122)
입력: od_lines.geojson (실 OD, 좌표매칭), ulsan_stop_coords_master.csv (배경)
출력: ulsan_od_demo.html
"""
import csv, json

od = json.load(open("od_lines.geojson", encoding="utf-8"))["features"]
lines = [{"o": f["geometry"]["coordinates"][0], "d": f["geometry"]["coordinates"][1],
          "t": f["properties"]["trips"], "on": f["properties"]["o"], "dn": f["properties"]["d"]} for f in od]

stops = []
with open("ulsan_stop_coords_master.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        try: lon, lat = float(r["lon"]), float(r["lat"])
        except: continue
        if 35.40 <= lat <= 35.73 and 129.05 <= lon <= 129.48:
            stops.append([round(lon, 5), round(lat, 5)])
from collections import Counter
def ck(lon, lat, s=500): return (int(lon*88800//s), int(lat*111000//s))
dens = Counter(ck(*s) for s in stops); maxd = max(dens.values())
density = [[k[0], k[1], v] for k, v in dens.items()]

pts = [c for l in lines for c in (l["o"], l["d"])]
b = {"minLon": min(p[0] for p in pts)-.01, "maxLon": max(p[0] for p in pts)+.01,
     "minLat": min(p[1] for p in pts)-.01, "maxLat": max(p[1] for p in pts)+.01}
data = {"lines": lines, "density": density, "maxd": maxd, "cellsize": 500, "bounds": b}

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 카드 OD 이동흐름 — 실데이터</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#0a0f1f;color:#e8eefc;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}canvas{position:absolute;inset:0;width:100%;height:100%}
.panel{position:absolute;background:#0f1830cc;backdrop-filter:blur(6px);border:1px solid #ffffff22;border-radius:12px;padding:12px 14px;font-size:13px}
#title{left:16px;top:16px;max-width:340px}#title h1{margin:0 0 6px;font-size:16px}#title p{margin:3px 0;font-size:12px;color:#bcd0f5;line-height:1.5}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:11px;margin-top:6px}
#leg{right:16px;top:16px;font-size:12px;line-height:1.7}.sw{display:inline-block;width:14px;height:3px;margin-right:6px;vertical-align:3px;background:#42a5f5}</style>
</head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 카드 OD 이동 흐름 (실데이터)</h1>
<p>국토부 교통카드 합성데이터 → 정류장ID 크로스워크(BusStop) → 좌표 매칭</p>
<p>노선 31001122 · 2026-01-01 · 승객 이동 OD <b id="n"></b>건</p>
<span class="tag">실데이터: OD 이동선 + 정류소 밀도 배경</span></div>
<div class="panel" id="leg"><div><span class="sw"></span>이동선(굵을수록 통행량↑)</div><div style="margin-top:5px">점: 출발→도착 이동</div></div>
</div><script>
const D=__DATA__;const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
document.getElementById('n').textContent=D.lines.length;
const B=D.bounds,pad=60,latC=(B.minLat+B.maxLat)/2,kx=Math.cos(latC*Math.PI/180);
function P(lon,lat){const dW=(B.maxLon-B.minLon)*kx,dH=(B.maxLat-B.minLat);const sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);
 const ox=(W-dW*sc)/2,oy=(H-dH*sc)/2;return[ox+(lon-B.minLon)*kx*sc,H-(oy+(lat-B.minLat)*sc)];}
let t0=performance.now();
function frame(now){const tt=((now-t0)/2600)%1;
 const g=x.createLinearGradient(0,0,0,H);g.addColorStop(0,'#0b1430');g.addColorStop(1,'#0a1020');x.fillStyle=g;x.fillRect(0,0,W,H);
 // density
 const cs=Math.max(5,(W/((B.maxLon-B.minLon)*88800)*D.cellsize));
 for(const[cx,cy,v]of D.density){const lon=(cx*D.cellsize+250)/88800,lat=(cy*D.cellsize+250)/111000;const p=P(lon,lat);const r=v/D.maxd;
  x.fillStyle=`rgba(${50+150*r|0},${130+90*r|0},255,${0.06+0.4*r})`;x.fillRect(p[0]-cs/2,p[1]-cs/2,cs,cs);}
 // OD arcs
 for(const l of D.lines){const a=P(l.o[0],l.o[1]),b=P(l.d[0],l.d[1]);
  const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*0.18;
  x.strokeStyle='rgba(66,165,245,0.35)';x.lineWidth=Math.min(6,1+l.t);x.beginPath();x.moveTo(a[0],a[1]);x.quadraticCurveTo(mx,my,b[0],b[1]);x.stroke();}
 // moving dots
 for(const l of D.lines){const a=P(l.o[0],l.o[1]),b=P(l.d[0],l.d[1]);
  const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*0.18;
  for(let k=0;k<l.t;k++){const f=(tt+k/l.t)%1;const u=1-f;
   const px=u*u*a[0]+2*u*f*mx+f*f*b[0],py=u*u*a[1]+2*u*f*my+f*f*b[1];
   x.fillStyle='#ffd54f';x.shadowColor='#ffd54f';x.shadowBlur=8;x.beginPath();x.arc(px,py,2.6,0,7);x.fill();}}
 x.shadowBlur=0;
 // endpoints
 for(const l of D.lines){const a=P(l.o[0],l.o[1]),b=P(l.d[0],l.d[1]);
  x.fillStyle='rgba(255,255,255,.55)';x.beginPath();x.arc(a[0],a[1],2,0,7);x.fill();x.beginPath();x.arc(b[0],b[1],2,0,7);x.fill();}
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
</script></body></html>"""
out = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_od_demo.html", "w", encoding="utf-8").write(out)
print("OD lines:", len(lines), "| wrote ulsan_od_demo.html", round(len(out)/1024), "KB")
