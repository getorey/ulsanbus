"""
실노선 시각화 프로토타입 v2
- 배경: 정류소 밀도(ulsan_stop_coords_master.csv, 실데이터)
- 노선: BIS 실제 노선 경로 10개(routes_bis.txt, 실데이터) — 노선별 색상 폴리라인
- 버스: 노선 위를 시간축에 따라 왕복 이동(주야 연출)
출력: ulsan_bus_prototype_v2.html (단일 파일, 오프라인)
"""
import csv, json

# 노선 파싱
routes = []
for blk in open("routes_bis.txt", encoding="utf-8").read().strip().split("~"):
    no, pts = blk.split("|")
    coords = [[float(x) for x in p.split(",")] for p in pts.split(";")]
    routes.append({"no": no, "coords": coords})

# 배경 정류소(본토 범위)
stops = []
with open("ulsan_stop_coords_master.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        try:
            lon, lat = float(r["lon"]), float(r["lat"])
        except:
            continue
        if 35.40 <= lat <= 35.73 and 129.05 <= lon <= 129.48:
            stops.append([round(lon, 5), round(lat, 5)])

# 500m 밀도
from collections import Counter
def ck(lon, lat, s=500): return (int(lon*88800//s), int(lat*111000//s))
dens = Counter(ck(*s) for s in stops); maxd = max(dens.values())
density = [[k[0], k[1], v] for k, v in dens.items()]

allc = [c for r in routes for c in r["coords"]] + stops
bounds = {"minLon": min(c[0] for c in allc), "maxLon": max(c[0] for c in allc),
          "minLat": min(c[1] for c in allc), "maxLat": max(c[1] for c in allc)}

data = {"routes": routes, "stops": stops, "density": density, "maxd": maxd,
        "cellsize": 500, "bounds": bounds,
        "colors": ["#ff5252","#ffb300","#42a5f5","#66bb6a","#ab47bc","#26c6da","#ec407a","#8d6e63","#ffee58","#5c6bc0"]}

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>울산 버스 실노선 시각화 — 프로토타입 v2</title>
<style>
 *{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#0a0f1f;color:#e8eefc;overflow:hidden}
 #wrap{position:relative;width:100vw;height:100vh}canvas#map{position:absolute;inset:0;width:100%;height:100%}
 .panel{position:absolute;background:#0f1830cc;backdrop-filter:blur(6px);border:1px solid #ffffff22;border-radius:12px;padding:12px 14px;font-size:13px}
 #ctrl{left:16px;bottom:16px;right:16px;display:flex;align-items:center;gap:14px}
 #ctrl button{background:#42a5f5;border:0;color:#04122b;font-weight:700;border-radius:8px;padding:8px 14px;cursor:pointer}
 #ctrl input[type=range]{flex:1;accent-color:#42a5f5}#clock{font-size:22px;font-weight:800;min-width:118px}
 #title{left:16px;top:16px;max-width:330px}#title h1{margin:0 0 6px;font-size:16px}#title p{margin:3px 0;font-size:12px;color:#bcd0f5;line-height:1.5}
 #legend{right:16px;top:16px;max-height:60vh;overflow:auto;font-size:12px;line-height:1.6}
 .sw{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}
 .speed{display:flex;gap:4px}.speed button{padding:5px 9px;font-size:12px;background:#ffffff22;color:#e8eefc}.speed button.on{background:#42a5f5;color:#04122b}
 .tag{display:inline-block;background:#ffffff1a;border-radius:6px;padding:2px 7px;font-size:11px;margin-top:6px}
</style></head><body><div id="wrap">
 <canvas id="map"></canvas>
 <div class="panel" id="title"><h1>울산 버스 실노선 시각화 v2</h1>
   <p>배경: 정류소 밀도(실데이터) · 선: BIS 실제 노선 10개 · 점: 버스(시간축 이동)</p>
   <p>주야 배경은 일출·일몰에 따라 변합니다.</p>
   <span class="tag">실데이터: 정류소·노선경로(BIS)</span></div>
 <div class="panel" id="legend"><b>노선(BIS)</b><div id="rlist"></div></div>
 <div class="panel" id="ctrl"><span id="sun">☀️</span><span id="clock">06:00</span>
   <button id="play">▶ 재생</button>
   <input id="time" type="range" min="0" max="1439" value="360">
   <div class="speed"><button data-s="60">1m/s</button><button data-s="600" class="on">10m/s</button><button data-s="1800">30m/s</button></div>
 </div></div>
<script>
const DATA=__DATA__;
const SUNRISE=5.5*60,SUNSET=19.5*60;
const map=document.getElementById('map'),ctx=map.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function resize(){W=map.clientWidth;H=map.clientHeight;map.width=W*dpr;map.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);}
addEventListener('resize',resize);resize();
const B=DATA.bounds,pad=46,latC=(B.minLat+B.maxLat)/2,kx=Math.cos(latC*Math.PI/180);
function proj(lon,lat){const dW=(B.maxLon-B.minLon)*kx,dH=(B.maxLat-B.minLat);
 const sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);const ox=(W-dW*sc)/2,oy=(H-dH*sc)/2;
 return [ox+(lon-B.minLon)*kx*sc, H-(oy+(lat-B.minLat)*sc)];}
const lerp=(a,b,t)=>a+(b-a)*t,mix=(a,b,t)=>[lerp(a[0],b[0],t),lerp(a[1],b[1],t),lerp(a[2],b[2],t)];
function sky(m){const N=[8,14,32],D1=[40,46,86],D=[26,52,92],K=[60,34,60];
 if(m<SUNRISE-60)return N;if(m<SUNRISE+30)return mix(N,D1,(m-(SUNRISE-60))/90);
 if(m<SUNRISE+120)return mix(D1,D,(m-(SUNRISE+30))/90);if(m<SUNSET-60)return D;
 if(m<SUNSET)return mix(D,K,(m-(SUNSET-60))/60);if(m<SUNSET+60)return mix(K,N,(m-SUNSET)/60);return N;}
const night=m=>m<SUNRISE||m>SUNSET;
// 노선별 누적길이(버스 위치 보간용)
DATA.routes.forEach((r,i)=>{r.col=DATA.colors[i%DATA.colors.length];r.seg=[];let L=0;
 for(let k=0;k<r.coords.length-1;k++){const a=r.coords[k],b=r.coords[k+1];
  const d=Math.hypot((b[0]-a[0])*kx,b[1]-a[1]);r.seg.push(L);L+=d;}r.len=L;});
// 범례
document.getElementById('rlist').innerHTML=DATA.routes.map(r=>`<div><span class="sw" style="background:${r.col}"></span>${r.no}번</div>`).join('');
function posOnRoute(r,f){const target=f*r.len;let k=0;while(k<r.seg.length-1&&r.seg[k+1]<target)k++;
 const segLen=(k+1<r.seg.length?r.seg[k+1]:r.len)-r.seg[k];const t=segLen?(target-r.seg[k])/segLen:0;
 const a=r.coords[k],b=r.coords[k+1]||a;return [lerp(a[0],b[0],t),lerp(a[1],b[1],t)];}
let cur=360,playing=false,speed=600,last=0;
const timeEl=document.getElementById('time'),clockEl=document.getElementById('clock'),sunEl=document.getElementById('sun');
function draw(){
 const s=sky(cur);const g=ctx.createLinearGradient(0,0,0,H);
 g.addColorStop(0,`rgb(${s[0]*0.7|0},${s[1]*0.7|0},${s[2]|0})`);g.addColorStop(1,`rgb(${s[0]|0},${s[1]|0},${s[2]*0.8|0})`);
 ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
 // 밀도
 const cs=(W/((B.maxLon-B.minLon)*88800)*DATA.cellsize);
 for(const [cx,cy,v] of DATA.density){const lon=(cx*DATA.cellsize+250)/88800,lat=(cy*DATA.cellsize+250)/111000;
  const p=proj(lon,lat),t=v/DATA.maxd;ctx.fillStyle=`rgba(${60+150*t|0},${150+90*t|0},255,${0.10+0.5*t})`;
  ctx.fillRect(p[0]-cs/2,p[1]-cs/2,Math.max(5,cs),Math.max(5,cs));}
 // 정류소
 ctx.fillStyle=night(cur)?'rgba(180,210,255,0.35)':'rgba(255,255,255,0.4)';
 for(const [lon,lat] of DATA.stops){const p=proj(lon,lat);ctx.fillRect(p[0],p[1],1.2,1.2);}
 // 노선 폴리라인 + 버스
 const nt=night(cur);
 for(const r of DATA.routes){
  ctx.strokeStyle=r.col;ctx.globalAlpha=nt?0.85:0.7;ctx.lineWidth=2;ctx.beginPath();
  r.coords.forEach((c,i)=>{const p=proj(c[0],c[1]);i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]);});
  ctx.stroke();ctx.globalAlpha=1;
  // 운행시간(05~24시) 동안 왕복하는 버스 2대
  if(cur>=300&&cur<=1439){
   for(let b=0;b<2;b++){
    const period=90;const phase=((cur-300)/period + b*0.5)%1;const f=phase<0.5?phase*2:(1-phase)*2;
    const pos=posOnRoute(r,f);const p=proj(pos[0],pos[1]);
    if(nt){ctx.shadowColor=r.col;ctx.shadowBlur=9;}else ctx.shadowBlur=0;
    ctx.fillStyle=r.col;ctx.beginPath();ctx.arc(p[0],p[1],3.6,0,7);ctx.fill();
   }
  }
 }
 ctx.shadowBlur=0;
 clockEl.textContent=String(cur/60|0).padStart(2,'0')+':'+String(cur%60|0).padStart(2,'0');
 sunEl.textContent=nt?'🌙':'☀️';
}
timeEl.oninput=e=>{cur=+e.target.value;draw();};
document.getElementById('play').onclick=e=>{playing=!playing;e.target.textContent=playing?'⏸ 정지':'▶ 재생';if(playing){last=performance.now();requestAnimationFrame(loop);}};
document.querySelectorAll('.speed button').forEach(b=>b.onclick=()=>{speed=+b.dataset.s;document.querySelectorAll('.speed button').forEach(x=>x.classList.remove('on'));b.classList.add('on');});
function loop(now){if(!playing)return;cur+=(now-last)/1000*speed/60;last=now;if(cur>=1440)cur=300;timeEl.value=cur|0;draw();requestAnimationFrame(loop);}
draw();
</script></body></html>"""
out = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_bus_prototype_v2.html", "w", encoding="utf-8").write(out)
print("routes:", len(routes), "stops:", len(stops), "density cells:", len(density))
print("wrote ulsan_bus_prototype_v2.html", round(len(out)/1024), "KB")
