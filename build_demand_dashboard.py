"""울산 버스 수요 분석 대시보드 (4뷰): 정류장 수요 히트맵 / 인구대비 수요 / OD 욕망선 / 순유입·유출
입력: uploads card_records_20260407*.csv (전체, 헤더없음), 정류장 좌표원들, grid100_population.csv
출력: demand_data_20260407.json, ulsan_demand_dashboard.html
"""
import csv, json, re, glob, math, os
from collections import defaultdict

# ---------- 좌표 해석기 (build_time_anim 과 동일 로직) ----------
def norm(s):
    s = (s or "").split("(")[0]
    return re.sub(r"[ .()\-·,]", "", s)
def norm_core(s):
    s = norm(s)
    for suf in ("정류소","정류장","건너편","건너","방면","앞","후문","정문","입구"):
        if s.endswith(suf) and len(s) > len(suf)+1: s = s[:-len(suf)]
    return s
xw = {}
for r in csv.DictReader(open("stop_crosswalk.csv", encoding="utf-8-sig")):
    try: xw[r["sttn_id"].strip()] = (float(r["lon"]), float(r["lat"]))
    except: pass
bs = {}
for r in csv.DictReader(open("ulsan_busstops_20260407.csv", encoding="utf-8-sig")):
    bs[r["sttn_id"]] = r["sttn_nm"]
name2c = {}; core2c = {}
def add(nm,c):
    k=norm(nm);
    if k and k not in name2c: name2c[k]=c
    kc=norm_core(nm)
    if kc and kc not in core2c: core2c[kc]=c
for r in csv.DictReader(open("ulsan_stop_coords_master.csv", encoding="utf-8-sig")):
    try: add(r["stop_name"], (float(r["lon"]), float(r["lat"])))
    except: pass
for r in csv.DictReader(open("stop_crosswalk.csv", encoding="utf-8-sig")):
    try: add(r["sttn_nm"], (float(r["lon"]), float(r["lat"])))
    except: pass
for r in csv.DictReader(open("nat_stops_raw.csv", encoding="cp949")):
    if "울산" in (r["도시명"] or ""):
        try: add(r["정류장명"], (float(r["경도"]), float(r["위도"])))
        except: pass
_cache = {}
def resolve(sid):
    if sid in _cache: return _cache[sid]
    c = None
    if sid in xw: c = xw[sid]
    else:
        nm = bs.get(sid)
        if nm:
            if norm(nm) in name2c: c = name2c[norm(nm)]
            else:
                cc = norm_core(nm)
                if cc in core2c: c = core2c[cc]
                elif len(cc) >= 4:
                    for k,v in core2c.items():
                        if len(k)>=4 and (cc in k or k in cc) and abs(len(cc)-len(k))<=1: c=v; break
    _cache[sid] = c; return c
def nm_of(sid): return bs.get(sid, "")

# ---------- 집계 ----------
COLS = ["rte_id","users_type_cd","ride_dt","ride_sttn_id","goff_dt","goff_sttn_id","utztn_nope","utztn_dstnc","brdg_hr","trnf_cnt"]
TYPES = ["01","02","03","04","05","06"]; TIDX = {t:i for i,t in enumerate(TYPES)}
_all = glob.glob("/sessions/jolly-gifted-albattani/mnt/uploads/card_records_20260407*.csv")
_f01 = sorted([f for f in _all if not f.endswith("_etc.csv")], key=lambda f: os.path.getsize(f), reverse=True)[:1]
_fetc = [f for f in _all if f.endswith("_etc.csv")]
rows = []
for _f in _f01 + _fetc:
    _isetc = _f.endswith("_etc.csv")
    for r in csv.reader(open(_f, encoding="utf-8-sig")):
        if len(r) < 10 or r[1] == "users_type_cd": continue
        if (r[1] == "01") == _isetc: continue
        rows.append(dict(zip(COLS, r)))
print("병합 행:", len(rows))

# 정류장 -> 6유형 × 24시간 승차/하차
board = defaultdict(lambda: [[0]*24 for _ in range(6)])
alight = defaultdict(lambda: [[0]*24 for _ in range(6)])
od = defaultdict(lambda: [0]*6)        # (board,alight) -> 유형별 통행
for r in rows:
    ti = TIDX.get(r["users_type_cd"])
    if ti is None: continue
    n = int(r["utztn_nope"] or 1)
    rd, gd = r["ride_dt"], r["goff_dt"]
    bsid, gsid = r["ride_sttn_id"], r["goff_sttn_id"]
    if len(rd) >= 10: board[bsid][ti][int(rd[8:10]) % 24] += n
    if gsid and len(gd) >= 10: alight[gsid][ti][int(gd[8:10]) % 24] += n
    if gsid and bsid != gsid: od[(bsid, gsid)][ti] += n

# 정류장 좌표 + (6×24 승차, 6×24 하차)
stops = []
allids = set(board) | set(alight)
for sid in allids:
    c = resolve(sid)
    if not c: continue
    stops.append([round(c[0],5), round(c[1],5),
                  board.get(sid, [[0]*24]*6), alight.get(sid, [[0]*24]*6)])

# OD 상위(전체 통행 기준 정렬) → 욕망선 (유형별 통행수 포함)
od_lines = []
for (o,d), t6 in sorted(od.items(), key=lambda x:-sum(x[1])):
    co, cd = resolve(o), resolve(d)
    if not co or not cd: continue
    od_lines.append([round(co[0],5),round(co[1],5),round(cd[0],5),round(cd[1],5)] + t6)
    if len(od_lines) >= 250: break

# 인구 격자
cells = []
for r in csv.DictReader(open("grid100_population.csv", encoding="utf-8-sig")):
    cells.append([round(float(r["lon"]),5), round(float(r["lat"]),5), int(r["pop"])])

tb = sum(sum(sum(h) for h in s[2]) for s in stops)
typ_tot = [sum(sum(s[2][i]) for s in stops) for i in range(6)]
print(f"정류장 {len(stops)} / 승차합 {tb} / 유형별 {typ_tot} / OD선 {len(od_lines)} / 격자 {len(cells)}")
data = {"stops": stops, "od": od_lines, "cells": cells, "typeTot": typ_tot}
json.dump(data, open("demand_data_20260407.json","w"), separators=(",",":"))
print("JSON MB:", round(os.path.getsize("demand_data_20260407.json")/1e6,2))

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 버스 수요 분석 대시보드 (2026-04-07)</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#070b16;color:#eaf0ff;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}#c{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.panel{position:absolute;z-index:10;background:#0d1530d8;backdrop-filter:blur(7px);border:1px solid #ffffff22;border-radius:13px;padding:12px 15px}
#title{left:16px;top:16px;max-width:380px}#title h1{margin:0 0 5px;font-size:15px}#title p{margin:3px 0;font-size:11.5px;color:#bcd0f5;line-height:1.5}
#tabs{right:16px;top:16px;display:flex;flex-direction:column;gap:6px}
#tabs button{background:#1a2647;color:#cfe0ff;border:1px solid #ffffff2a;border-radius:9px;padding:8px 13px;font-size:13px;cursor:pointer;text-align:left}
#tabs button.on{background:#3a6bd5;color:#fff;border-color:#5a8bff}
#utf{left:16px;top:118px;display:flex;flex-wrap:wrap;gap:5px;max-width:340px}
#utf button{background:#1a2647;color:#cfe0ff;border:1px solid #ffffff2a;border-radius:8px;padding:5px 9px;font-size:12px;cursor:pointer}
#utf button.on{background:#2aa17a;color:#fff;border-color:#46d5a5}
#utf button .n{opacity:.6;font-size:10px;margin-left:3px}
#leg{left:16px;bottom:90px;font-size:11.5px;max-width:300px;line-height:1.7}
#leg i{display:inline-block;width:14px;height:10px;margin-right:6px;border-radius:2px;vertical-align:1px}
#bar{left:16px;right:16px;bottom:16px;padding:10px 16px;display:flex;align-items:center;gap:14px}
#hour{flex:1;accent-color:#ffd54f}#hl{min-width:96px;font-variant-numeric:tabular-nums;font-size:14px;font-weight:600}
#bar button{background:#22305a;color:#eaf0ff;border:1px solid #ffffff33;border-radius:8px;padding:6px 12px;font-size:13px;cursor:pointer}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:10.5px;margin-top:6px}
#themeBtn{position:absolute;z-index:30;top:34px;left:50%;transform:translateX(-50%);background:#0d1530cc;color:#eaf0ff;border:1px solid #ffffff33;border-radius:9px;padding:6px 12px;font-size:12.5px;cursor:pointer}body.light{background:#eef1f7}body.light .panel{background:#ffffffe0;border-color:#0000001f;color:#1b2640;box-shadow:0 2px 10px #00000014}body.light .panel *{color:#1b2640 !important}body.light #themeBtn{background:#ffffffe0;color:#1b2640;border-color:#0000002a}body.light #tabs button,body.light #utf button,body.light #bar button,body.light #list td,body.light select{background:#e9edf6}body.light #tabs button.on{background:#3a6bd5 !important}body.light #tabs button.on *{color:#fff !important}body.light #utf button.on{background:#2aa17a !important}body.light #utf button.on *{color:#fff !important}body.light #tabs button.on,body.light #utf button.on{color:#fff !important}.popgrad{display:inline-block;width:90px;height:9px;border-radius:3px;vertical-align:-1px;margin:0 5px;background:linear-gradient(90deg,#14283c,#3a96a0,#ebcd6e)}body.light .popgrad{background:linear-gradient(90deg,#dfeed8,#78b46e,#1c683a)}</style></head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1 id="ht">정류장 수요 히트맵</h1><p id="hp"></p>
<p>2026-04-07(화) · 교통카드 합성데이터(1차) · 승차 100% 신뢰</p><span class="tag">실데이터</span> <a href="ulsan_용어설명.html" target="_blank" style="display:inline-block;margin-top:6px;margin-left:6px;font-size:11px;color:#7fb4ff">ℹ 용어 설명</a></div>
<div class="panel" id="tabs">
 <button data-m="heat" class="on">🔥 정류장 수요 히트맵</button>
 <button data-m="pop">👥 인구 대비 수요</button>
 <button data-m="od">↔ OD 욕망선</button>
 <button data-m="net">⇅ 출퇴근 순유입·유출</button></div>
<div class="panel" id="utf"></div>
<div class="panel" id="leg"></div>
<div class="panel" id="bar"><button id="play">▶ 시간재생</button>
 <input type="range" id="hour" min="0" max="24" value="24"><span id="hl">전체</span></div>
</div>
<script>
const D=__DATA__,S=D.stops,OD=D.od,CELLS=D.cells;
const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
// 경계(정류장+격자)
let mnLon=1e9,mxLon=-1e9,mnLat=1e9,mxLat=-1e9;
for(const s of S){mnLon=Math.min(mnLon,s[0]);mxLon=Math.max(mxLon,s[0]);mnLat=Math.min(mnLat,s[1]);mxLat=Math.max(mxLat,s[1]);}
const pad=54,latC=(mnLat+mxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(mxLon-mnLon)*kx,dH=(mxLat-mnLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
let Z=1,TX=0,TY=0;addEventListener('wheel',e=>{if(e.target.closest&&e.target.closest('.panel'))return;e.preventDefault();const cx=e.clientX,cy=e.clientY,f=e.deltaY<0?1.15:1/1.15,Zn=Math.min(25,Math.max(1,Z*f));TX=cx-(cx-TX)/Z*Zn;TY=cy-(cy-TY)/Z*Zn;Z=Zn;},{passive:false});let _dg=null;addEventListener('mousedown',e=>{if(e.target.closest&&e.target.closest('.panel'))return;_dg=[e.clientX,e.clientY,TX,TY];});addEventListener('mousemove',e=>{if(_dg){TX=_dg[2]+(e.clientX-_dg[0]);TY=_dg[3]+(e.clientY-_dg[1]);}});addEventListener('mouseup',()=>_dg=null);addEventListener('dblclick',e=>{if(e.target.closest&&e.target.closest('.panel'))return;Z=1;TX=0;TY=0;});const PX=lon=>(ox+(lon-mnLon)*kx*sc)*Z+TX, PY=lat=>(H-(oy+(lat-mnLat)*sc))*Z+TY;
// 격자 인구 색(로그)
const pmax=(()=>{const v=CELLS.map(c=>c[2]).sort((a,b)=>a-b);return v[Math.floor(v.length*0.99)];})();
function PG(t,a){t=Math.min(1,Math.max(0,t));var A=[150,200,150],B=[46,150,70],C=[8,72,34],r,g,b;if(t<.55){var f=t/.55;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{var f=(t-.55)/.45;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}return 'rgba('+(r|0)+','+(g|0)+','+(b|0)+','+(a==null?1:a)+')';}
function pcol(v,a){let t=Math.min(1,Math.log(1+v)/Math.log(1+pmax));if(document.body.classList.contains('light'))return PG(t,a);const A=[18,34,60],B=[60,140,150],C=[235,205,120];let r,g,b;
 if(t<.6){const f=t/.6;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{const f=(t-.6)/.4;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}
 return `rgba(${r|0},${g|0},${b|0},${a==null?1:a})`;}
function heatCol(t){t=Math.min(1,t);const A=[40,40,90],B=[240,200,70],C=[235,60,40];let r,g,b;
 if(t<.5){const f=t/.5;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{const f=(t-.5)/.5;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}
 return `rgb(${r|0},${g|0},${b|0})`;}
// 이용자유형 필터(-1=전체, 0~5)  s[2]=6×24 승차, s[3]=6×24 하차
const UNAMES=['일반','어린이','청소년','경로','장애','국가유공'];
let utf=-1;
function sumTypeHour(mat,h){ // mat=6×24
 let t=0; for(let i=0;i<6;i++){ if(utf>=0&&i!==utf)continue;
  if(h>=24){const a=mat[i];for(let j=0;j<24;j++)t+=a[j];} else t+=mat[i][h]; } return t;}
function bval(s,h){return sumTypeHour(s[2],h);}
function aval(s,h){return sumTypeHour(s[3],h);}
let mode='heat',hour=24,playing=false;
const tt={heat:['정류장 수요 히트맵','정류장별 승차량(원 크기·색). 시간 슬라이더로 시간대별 수요 이동을 확인.'],
 pop:['인구 대비 버스 수요','배경=인구밀도(100m), 원=정류장 승차량. 인구는 많은데 수요가 적은/많은 지역 비교.'],
 od:['OD 욕망선(이동 흐름)','승차→하차 지역간 주요 흐름(상위 250). 굵을수록 통행 많음. 유효 이동만(승≠하).'],
 net:['출퇴근 순유입·유출','정류장별 (승차−하차). 빨강=순승차(유출지), 파랑=순하차(유입지). 시간대별로 통근 구조가 뒤집힘.']};
// 컨트롤
document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{mode=b.dataset.m;
 document.querySelectorAll('#tabs button').forEach(z=>z.classList.toggle('on',z===b));
 document.getElementById('bar').style.display=(mode==='od'||mode==='pop')?'none':'flex';
 document.getElementById('ht').textContent=tt[mode][0];document.getElementById('hp').textContent=tt[mode][1];buildLeg();});
const hourEl=document.getElementById('hour'),hlEl=document.getElementById('hl');
function setHour(h){hour=h;hlEl.textContent=h>=24?'전체':String(h).padStart(2,'0')+':00';hourEl.value=h;}
hourEl.oninput=e=>{playing=false;setHour(+e.target.value);};
document.getElementById('play').onclick=e=>{playing=!playing;e.target.textContent=playing?'⏸ 정지':'▶ 시간재생';if(hour>=24)setHour(5);};
function buildLeg(){let h='';
 if(mode==='heat')h='<b>승차 인원</b><br><i style="background:'+heatCol(.1)+'"></i>적음 &nbsp;<i style="background:'+heatCol(.5)+'"></i>중간 &nbsp;<i style="background:'+heatCol(1)+'"></i>많음<br>원 크기도 승차량에 비례';
 else if(mode==='pop')h='<b>배경=인구밀도 · 원=승차량</b><br><i style="background:'+pcol(pmax*.6)+'"></i>인구 밀집 &nbsp;<i style="background:#ffd54f"></i>버스 승차';
 else if(mode==='od')h='<b>이동 흐름(욕망선)</b><br>굵을수록 통행 많음<br><span style="opacity:.8">승차→하차, 상위 250쌍</span>';
 else h='<b>순유입·유출(승차−하차)</b><br><i style="background:rgb(235,70,55)"></i>순승차=유출지(아침 주거지)<br><i style="background:rgb(70,150,255)"></i>순하차=유입지(아침 도심)';
 document.getElementById('leg').innerHTML=h;}
// 이용자유형 필터 버튼
(()=>{let h=`<button data-u="-1" class="on">전체</button>`;
 UNAMES.forEach((nm,i)=>{if((D.typeTot[i]||0)>0)h+=`<button data-u="${i}">${nm}<span class="n">${D.typeTot[i].toLocaleString()}</span></button>`;});
 const el=document.getElementById('utf');el.innerHTML=h;
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>{utf=+b.dataset.u;el.querySelectorAll('button').forEach(z=>z.classList.toggle('on',z===b));});})();
document.getElementById('hp').textContent=tt.heat[1];buildLeg();
let last=performance.now();
function frame(t){const dt=t-last;last=t;fit();
 // 시간 자동재생(약 0.65초/시간)
 if(playing){acc+=dt;if(acc>650){acc=0;setHour(hour>=23?5:(hour<5?5:hour+1));}}
 x.fillStyle=(document.body.classList.contains('light')?'#e9edf4':'#070b16');x.fillRect(0,0,W,H);
 if(mode==='pop'){const px=Math.max(2,(100/111000*sc)*1.5*Z);for(const cl of CELLS){x.fillStyle=pcol(cl[2]);x.fillRect(PX(cl[0])-px/2,PY(cl[1])-px/2,px,px);}}
 else if(mode!=='od'){for(const cl of CELLS){x.fillStyle=pcol(cl[2],0.16);const px=Math.max(2,(100/111000*sc)*1.5*Z);x.fillRect(PX(cl[0])-px/2,PY(cl[1])-px/2,px,px);}}
 if(mode==='heat'||mode==='pop'){
  let mx=1;for(const s of S)mx=Math.max(mx,bval(s,hour));
  for(const s of S){const v=bval(s,hour);if(v<=0)continue;const t2=v/mx;
   const r=Math.min(16,1+Math.sqrt(v)*(mode==='pop'?0.7:1.2));
   x.fillStyle=mode==='pop'?`rgba(255,213,79,${0.25+0.6*Math.sqrt(t2)})`:heatCol(Math.sqrt(t2));
   x.beginPath();x.arc(PX(s[0]),PY(s[1]),r,0,7);x.fill();}}
 else if(mode==='net'){
  let mx=1;for(const s of S)mx=Math.max(mx,Math.abs(bval(s,hour)-aval(s,hour)));
  for(const s of S){const net=bval(s,hour)-aval(s,hour);if(!net)continue;const t2=Math.min(1,Math.abs(net)/mx);
   const r=Math.min(15,1+Math.sqrt(Math.abs(net))*1.3);
   x.fillStyle=net>0?`rgba(235,70,55,${0.3+0.6*t2})`:`rgba(70,150,255,${0.3+0.6*t2})`;
   x.beginPath();x.arc(PX(s[0]),PY(s[1]),r,0,7);x.fill();}}
 else if(mode==='od'){
  const odv=l=>{let t=0;for(let i=0;i<6;i++){if(utf>=0&&i!==utf)continue;t+=l[4+i];}return t;};
  let mx=1;for(const l of OD)mx=Math.max(mx,odv(l));
  for(const l of OD){const v=odv(l);if(v<=0)continue;const a=[PX(l[0]),PY(l[1])],b=[PX(l[2]),PY(l[3])];
   const t2=v/mx,w=Math.min(6,0.4+t2*8);
   const midx=(a[0]+b[0])/2,midy=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*0.16;
   x.strokeStyle=`rgba(${120+135*t2|0},${180-60*t2|0},${255-120*t2|0},${0.25+0.5*t2})`;x.lineWidth=w;
   x.beginPath();x.moveTo(a[0],a[1]);x.quadraticCurveTo(midx,midy,b[0],b[1]);x.stroke();}
  x.fillStyle='#ffffffcc';for(const l of OD){if(odv(l)<=0)continue;x.beginPath();x.arc(PX(l[0]),PY(l[1]),1.3,0,7);x.fill();}}
 requestAnimationFrame(frame);}
let acc=0;requestAnimationFrame(frame);
;(function(){var b=document.createElement('button');b.id='themeBtn';b.textContent='☀ 라이트';(document.getElementById('wrap')||document.body).appendChild(b);b.onclick=function(){document.body.classList.toggle('light');b.textContent=document.body.classList.contains('light')?'🌙 다크':'☀ 라이트';};})();;(function(){var t=document.getElementById('title');if(!t)return;var d=document.createElement('div');d.style.cssText='margin-top:7px;font-size:11px;opacity:.85';d.innerHTML='배경=인구밀도 낮음<span class="popgrad"></span>높음';t.appendChild(d);})();</script></body></html>"""
out = HTML.replace("__DATA__", json.dumps(data, separators=(",",":")))
open("ulsan_demand_dashboard.html","w",encoding="utf-8").write(out)
print("HTML MB:", round(len(out)/1e6,2))
