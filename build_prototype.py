"""
배경 시각화 프로토타입 생성기
- 입력: ulsan_stop_coords_master.csv (실 정류소 좌표)
- 출력: ulsan_bus_prototype.html (단일 파일, 오프라인 동작)
기능: 정류소 밀도 배경 + 정류소 점 + 하루 시간축 재생 + 주야(일출/일몰) 연출 + 데모 이동흐름
"""
import csv, json, math, random

random.seed(42)
STOPS = []
with open("ulsan_stop_coords_master.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        try:
            lon, lat = float(r["lon"]), float(r["lat"])
        except:
            continue
        # 울산 본토 대략 범위로 한정(외곽 양산/경주/부산 일부 제외해 화면 집중)
        if 35.40 <= lat <= 35.70 and 129.05 <= lon <= 129.48:
            STOPS.append([round(lon, 6), round(lat, 6)])

# 500m 격자 밀도(정류소 수) 집계
def cellkey(lon, lat, size_m=500):
    # 대략 m 환산(위도보정)
    x = lon * 88800  # 경도 1도 ≈ 88.8km (위도35.5)
    y = lat * 111000
    return (int(x // size_m), int(y // size_m))

from collections import Counter
dens = Counter(cellkey(lon, lat) for lon, lat in STOPS)
maxd = max(dens.values())

# 데모 이동흐름: 출퇴근 피크형 시간분포로 출발시각 생성
def sample_depart_min():
    # 두 피크(08:00, 18:00) 혼합 + 베이스
    r = random.random()
    if r < 0.35:
        m = int(random.gauss(8 * 60, 50))
    elif r < 0.70:
        m = int(random.gauss(18 * 60, 55))
    else:
        m = int(random.uniform(6 * 60, 23 * 60))
    return max(300, min(1439, m))

ROUTE_COLORS = ["#ff5252", "#ffb300", "#42a5f5", "#66bb6a", "#ab47bc", "#26c6da", "#ec407a", "#8d6e63"]
TRIPS = []
for _ in range(450):
    o = random.choice(STOPS); d = random.choice(STOPS)
    if o == d:
        continue
    dep = sample_depart_min()
    dur = random.randint(6, 40)  # 분
    TRIPS.append({
        "o": o, "d": d, "dep": dep, "dur": dur,
        "c": random.randrange(len(ROUTE_COLORS)),
    })

# 시간대별 데모 수요 히스토그램(출발 기준)
hist = [0] * 24
for t in TRIPS:
    hist[t["dep"] // 60] += 1

data = {
    "stops": STOPS,
    "density": [[k[0], k[1], v] for k, v in dens.items()],
    "maxd": maxd,
    "cellsize": 500,
    "trips": TRIPS,
    "colors": ROUTE_COLORS,
    "hist": hist,
    "bounds": {
        "minLon": min(s[0] for s in STOPS), "maxLon": max(s[0] for s in STOPS),
        "minLat": min(s[1] for s in STOPS), "maxLat": max(s[1] for s in STOPS),
    },
}

HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>울산 버스 인구이동 시각화 — 프로토타입</title>
<style>
  :root{ --panel:#0f1830cc; --txt:#e8eefc; --accent:#42a5f5; }
  *{box-sizing:border-box} html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#0a0f1f;color:var(--txt)}
  #wrap{position:relative;width:100vw;height:100vh;overflow:hidden}
  canvas{position:absolute;inset:0;width:100%;height:100%}
  .panel{position:absolute;background:var(--panel);backdrop-filter:blur(6px);border:1px solid #ffffff22;border-radius:12px;padding:12px 14px;font-size:13px}
  #ctrl{left:16px;bottom:16px;right:16px;display:flex;align-items:center;gap:14px}
  #ctrl button{background:var(--accent);border:0;color:#04122b;font-weight:700;border-radius:8px;padding:8px 14px;cursor:pointer;font-size:14px}
  #ctrl input[type=range]{flex:1;accent-color:var(--accent)}
  #clock{font-size:22px;font-weight:800;min-width:118px;letter-spacing:1px}
  #sun{font-size:20px}
  #title{left:16px;top:16px;max-width:330px}
  #title h1{margin:0 0 6px;font-size:16px}
  #title p{margin:4px 0;font-size:12px;color:#bcd0f5;line-height:1.5}
  #legend{right:16px;top:16px;font-size:12px;line-height:1.7}
  .sw{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:-1px}
  #hist{position:absolute;right:16px;bottom:84px;width:280px;height:90px}
  .tag{display:inline-block;background:#ffffff1a;border-radius:6px;padding:2px 7px;font-size:11px;margin-top:6px}
  .speed{display:flex;gap:4px}.speed button{padding:5px 9px;font-size:12px;background:#ffffff22;color:var(--txt)}
  .speed button.on{background:var(--accent);color:#04122b}
</style></head>
<body><div id="wrap">
  <canvas id="map"></canvas>
  <div class="panel" id="title">
    <h1>울산 버스 인구이동 — 프로토타입</h1>
    <p>배경: 정류소 밀도(실데이터 3,960개) · 점: 정류소 · 흐름: 하루 시간축 이동(데모)</p>
    <p>주야 배경은 일출·일몰 시각에 따라 변합니다.</p>
    <span class="tag">실데이터: 정류소/밀도</span> <span class="tag">데모: 이동선(BIS 연결 전)</span>
  </div>
  <div class="panel" id="legend">
    <div><b>밀도(정류소)</b></div>
    <div><span class="sw" style="background:#13294b"></span>낮음</div>
    <div><span class="sw" style="background:#2e6fb0"></span>중간</div>
    <div><span class="sw" style="background:#7fd4ff"></span>높음</div>
    <div style="margin-top:6px"><b>노선(데모)</b> 색상 구분</div>
  </div>
  <canvas id="hist" class="panel" style="padding:8px"></canvas>
  <div class="panel" id="ctrl">
    <span id="sun">☀️</span>
    <span id="clock">06:00</span>
    <button id="play">▶ 재생</button>
    <input id="time" type="range" min="0" max="1439" value="360">
    <div class="speed">
      <button data-s="60">1m/s</button>
      <button data-s="600" class="on">10m/s</button>
      <button data-s="1800">30m/s</button>
    </div>
  </div>
</div>
<script>
const DATA = __DATA__;
const SUNRISE = 5.5*60, SUNSET = 19.5*60;   // 울산 여름 기준(분). 계절별 조정 가능
const map = document.getElementById('map'), ctx = map.getContext('2d');
const histC = document.getElementById('hist'), hx = histC.getContext('2d');
let W,H, dpr=window.devicePixelRatio||1;
function resize(){ W=map.clientWidth; H=map.clientHeight; for(const c of [map]){c.width=W*dpr;c.height=H*dpr;} ctx.setTransform(dpr,0,0,dpr,0,0);
  histC.width=histC.clientWidth*dpr; histC.height=histC.clientHeight*dpr; hx.setTransform(dpr,0,0,dpr,0,0); }
window.addEventListener('resize',resize); resize();

const B=DATA.bounds, pad=40;
const latC=(B.minLat+B.maxLat)/2, kx=Math.cos(latC*Math.PI/180);
function proj(lon,lat){
  const nx=(lon-B.minLon)/(B.maxLon-B.minLon);
  const ny=(lat-B.minLat)/(B.maxLat-B.minLat);
  // 종횡비 보정
  const availW=W-pad*2, availH=H-pad*2;
  const dataW=(B.maxLon-B.minLon)*kx, dataH=(B.maxLat-B.minLat);
  const scale=Math.min(availW/dataW, availH/dataH);
  const ox=(W-dataW*scale)/2, oy=(H-dataH*scale)/2;
  return [ox+(lon-B.minLon)*kx*scale, H-(oy+(lat-B.minLat)*scale)];
}

// 주야 배경색 보간
function lerp(a,b,t){return a+(b-a)*t}
function skyColor(min){
  // 밤(어두움) <-> 낮(밝음)
  const night=[8,14,32], dawn=[40,46,86], day=[26,52,92], dusk=[60,34,60];
  let c;
  if(min<SUNRISE-60) c=night;
  else if(min<SUNRISE+30){ const t=(min-(SUNRISE-60))/90; c=mix(night,dawn,t);}
  else if(min<SUNRISE+120){ const t=(min-(SUNRISE+30))/90; c=mix(dawn,day,t);}
  else if(min<SUNSET-60) c=day;
  else if(min<SUNSET){ const t=(min-(SUNSET-60))/60; c=mix(day,dusk,t);}
  else if(min<SUNSET+60){ const t=(min-SUNSET)/60; c=mix(dusk,night,t);}
  else c=night;
  return c;
}
function mix(a,b,t){return [lerp(a[0],b[0],t),lerp(a[1],b[1],t),lerp(a[2],b[2],t)]}
function isNight(min){return min<SUNRISE||min>SUNSET}

let curMin=360, playing=false, speed=600, last=0;
const timeEl=document.getElementById('time'), clockEl=document.getElementById('clock'), sunEl=document.getElementById('sun');

function draw(){
  const sky=skyColor(curMin);
  // 배경 그라데이션
  const g=ctx.createLinearGradient(0,0,0,H);
  g.addColorStop(0,`rgb(${sky[0]*0.7|0},${sky[1]*0.7|0},${sky[2]|0})`);
  g.addColorStop(1,`rgb(${sky[0]|0},${sky[1]|0},${sky[2]*0.8|0})`);
  ctx.fillStyle=g; ctx.fillRect(0,0,W,H);

  // 밀도 격자(정류소 밀도) — 셀 중심 좌표 복원
  const night=isNight(curMin);
  for(const [cx,cy,v] of DATA.density){
    const lon=(cx*DATA.cellsize+DATA.cellsize/2)/88800;
    const lat=(cy*DATA.cellsize+DATA.cellsize/2)/111000;
    const p=proj(lon,lat);
    const t=v/DATA.maxd;
    const a=0.12+0.6*t;
    ctx.fillStyle=`rgba(${60+160*t|0},${150+90*t|0},255,${a})`;
    const s=Math.max(6, (W/ (B.maxLon-B.minLon)/88800*DATA.cellsize));
    ctx.fillRect(p[0]-s/2,p[1]-s/2,s,s);
  }

  // 정류소 점
  ctx.fillStyle=night?'rgba(180,210,255,0.45)':'rgba(255,255,255,0.5)';
  for(const [lon,lat] of DATA.stops){ const p=proj(lon,lat); ctx.fillRect(p[0],p[1],1.4,1.4); }

  // 이동 흐름(데모): 출발~도착 사이 보간, 야간 glow
  for(const t of DATA.trips){
    const start=t.dep, end=t.dep+t.dur;
    if(curMin<start||curMin>end) continue;
    const f=(curMin-start)/(end-start);
    const a=proj(t.o[0],t.o[1]), b=proj(t.d[0],t.d[1]);
    const x=lerp(a[0],b[0],f), y=lerp(a[1],b[1],f);
    const col=DATA.colors[t.c];
    if(night){ ctx.shadowColor=col; ctx.shadowBlur=8; } else ctx.shadowBlur=0;
    ctx.fillStyle=col;
    ctx.beginPath(); ctx.arc(x,y,3.2,0,7); ctx.fill();
  }
  ctx.shadowBlur=0;

  // 시계/해달
  const hh=String(curMin/60|0).padStart(2,'0'), mm=String(curMin%60|0).padStart(2,'0');
  clockEl.textContent=`${hh}:${mm}`;
  sunEl.textContent=isNight(curMin)?'🌙':'☀️';
  drawHist();
}

function drawHist(){
  const w=histC.clientWidth, h=histC.clientHeight; hx.clearRect(0,0,w,h);
  const max=Math.max(...DATA.hist), bw=w/24;
  hx.fillStyle='#bcd0f5'; hx.font='10px sans-serif'; hx.fillText('시간대별 이동(데모)',6,12);
  for(let i=0;i<24;i++){
    const bh=(DATA.hist[i]/max)*(h-28);
    hx.fillStyle = (i===(curMin/60|0))?'#ffd54f':'#42a5f5aa';
    hx.fillRect(i*bw+2, h-8-bh, bw-3, bh);
  }
  hx.fillStyle='#8aa'; hx.fillText('0',2,h-1); hx.fillText('12',w/2-4,h-1); hx.fillText('23',w-14,h-1);
}

timeEl.addEventListener('input',e=>{curMin=+e.target.value; draw();});
document.getElementById('play').addEventListener('click',e=>{playing=!playing; e.target.textContent=playing?'⏸ 정지':'▶ 재생'; if(playing){last=performance.now(); requestAnimationFrame(loop);}});
document.querySelectorAll('.speed button').forEach(b=>b.addEventListener('click',()=>{
  speed=+b.dataset.s; document.querySelectorAll('.speed button').forEach(x=>x.classList.remove('on')); b.classList.add('on');
}));
function loop(now){
  if(!playing) return;
  const dt=(now-last)/1000; last=now;
  curMin+=dt*speed/60;            // speed = 분/초
  if(curMin>=1440) curMin=0;
  timeEl.value=curMin|0; draw();
  requestAnimationFrame(loop);
}
draw();
</script></body></html>"""

out = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_bus_prototype.html", "w", encoding="utf-8").write(out)
print("stops in view:", len(STOPS), "| density cells:", len(dens), "| trips:", len(TRIPS))
print("wrote ulsan_bus_prototype.html", round(len(out)/1024), "KB")
