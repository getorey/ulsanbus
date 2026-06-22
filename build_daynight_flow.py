"""울산 버스 주야 흐름 시각화 (설계서 반영)
- 시간 구동 테마: 밤=짙은 남색+불빛, 낮=흰 바탕+검정 명암, 여명/낙조 1시간 페이드
- 승객 마크 = 색 사각형, 면적 = 정류장 승차 인원(√로 한 변)
- 자동/낮 고정/밤 고정 + 이용자유형 필터 + 휠 확대
입력: card_trips_20260407.json (build_time_anim 산출 재사용)
출력: ulsan_daynight_flow.html
"""
import json, os
d = json.load(open("card_trips_20260407.json"))
try:
    d["cong"] = json.load(open("route_congestion_20260407.json"))
except FileNotFoundError:
    d["cong"] = {}
try:
    d["abol"] = json.load(open("abolished_routes.json"))
except FileNotFoundError:
    d["abol"] = []

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 버스 주야 흐름 (2026-04-07)</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;color:#eaf0ff;overflow:hidden;background:#0a1430}
#wrap{position:relative;width:100vw;height:100vh}#c{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.panel{position:absolute;z-index:10;background:#0d1530cc;backdrop-filter:blur(7px);border:1px solid #ffffff22;border-radius:13px;padding:11px 14px;transition:background .4s,color .4s}
#title{left:16px;top:16px;max-width:360px}#title h1{margin:0 0 5px;font-size:15px}#title p{margin:2px 0;font-size:11.5px;opacity:.85;line-height:1.5}
#clock{right:16px;top:16px;text-align:center;min-width:150px}
#clock .t{font-size:32px;font-weight:700;font-variant-numeric:tabular-nums}#clock .ph{font-size:12px;margin-top:2px}#clock .ride{font-size:11.5px;margin-top:5px;opacity:.9}
#modes{right:16px;top:128px;display:flex;gap:5px}#modes button,#utf button{background:#1b2748;color:#cfe0ff;border:1px solid #ffffff2a;border-radius:8px;padding:5px 10px;font-size:12px;cursor:pointer}
#modes button.on{background:#3a6bd5;color:#fff;border-color:#5a8bff}
#rsel{right:16px;top:176px;font-size:11px}#rsel select{margin-top:4px;background:#1b2748;color:#fff;border:1px solid #ffffff33;border-radius:8px;padding:5px 8px;font-size:13px;max-width:200px}
body.day #rsel select{background:#e9edf6;color:#1b2640}
#rinfo{right:16px;top:232px;bottom:250px;width:300px;overflow-y:auto;display:none;font-size:12px}
#rinfo h2{margin:0 0 4px;font-size:15px}#rinfo .sub{font-size:11px;opacity:.8;margin-bottom:8px}
#rinfo .kv{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
#rinfo .kv div{background:#ffffff14;border-radius:7px;padding:5px 8px;font-size:11px;min-width:64px}
#rinfo .kv b{display:block;font-size:14px}
#rinfo .sec{font-size:11px;opacity:.8;margin:8px 0 4px}
#rinfo .hb{display:flex;align-items:flex-end;gap:1px;height:46px}
#rinfo .hb i{flex:1;background:#3a6bd5;border-radius:1px 1px 0 0;min-height:1px}
#rinfo .hb i.pk{background:#ffd54f}
#rinfo .hbx{display:flex;justify-content:space-between;font-size:9px;opacity:.55;margin-top:2px}
#rinfo table{width:100%;border-collapse:collapse}#rinfo td{padding:2px 5px;border-bottom:1px solid #ffffff12;font-size:11px}#rinfo td:last-child{text-align:right;color:#ffd54f;font-weight:600;white-space:nowrap}
#rinfo td .bar{display:inline-block;height:7px;background:#3a6bd5;border-radius:2px;margin-right:5px;vertical-align:1px}
body.day #rinfo .kv div{background:#0000000d}body.day #rinfo td:last-child{color:#c07a00}body.day #rinfo .hb i.pk{background:#d59b00}body.day #rinfo td .bar{background:#3a6bd5}
#utf{left:16px;top:120px;display:flex;flex-wrap:wrap;gap:5px;max-width:330px}#utf button.on{background:#2aa17a;color:#fff;border-color:#46d5a5}#utf button .n{opacity:.6;font-size:10px;margin-left:3px}
#leg{left:16px;bottom:128px;font-size:11.5px;max-width:300px;line-height:1.7}
#leg .sq{display:inline-block;background:#ffd54f;vertical-align:-1px;margin:0 2px}
#tip{position:absolute;z-index:20;pointer-events:none;display:none;background:#0b1226f0;border:1px solid #ffffff44;border-radius:9px;padding:7px 10px;font-size:12px;line-height:1.5;white-space:nowrap}#tip b{font-size:14px;color:#ffd54f}
#bar{left:16px;right:16px;bottom:16px;padding:10px 14px}#bar .row{display:flex;align-items:center;gap:12px}
#scrub{display:block;width:100%;margin:9px 0 0;accent-color:#ffd54f}
button{cursor:pointer}#bar .row button{background:#22305a;color:#eaf0ff;border:1px solid #ffffff33;border-radius:8px;padding:6px 12px;font-size:13px}
#hist{width:100%;height:32px;margin-top:8px;display:block}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:10.5px;margin-top:6px}
/* 낮 고정/낮 시간대일 때 패널 밝게 */
body.day .panel{background:#ffffffdb;color:#1b2640;border-color:#0000001f}body.day .panel *{color:#1b2640}
body.day #modes button,body.day #utf button,body.day #bar .row button{background:#e9edf6;color:#1b2640}
body.day #modes button.on{background:#3a6bd5;color:#fff}body.day #utf button.on{background:#2aa17a;color:#fff}
</style></head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 버스 주야 흐름</h1>
<p>밤=남색·불빛 / 낮=흰 바탕·검정 명암 / 여명·낙조 1시간 전환 · 사각형 면적=정류장 승차 인원 · 색=노선</p>
<span class="tag">실데이터 2026-04-07</span> <a href="ulsan_용어설명.html" target="_blank" style="display:inline-block;margin-top:6px;font-size:11px;color:#7fb4ff">ℹ 용어 설명</a></div>
<div class="panel" id="clock"><div class="t" id="ct">--:--</div><div class="ph" id="cp"></div><div class="ride" id="cr"></div></div>
<div class="panel" id="modes"></div>
<div class="panel" id="rsel"></div>
<div class="panel" id="rinfo"></div>
<div class="panel" id="utf"></div>
<div class="panel" id="leg"></div>
<div id="tip"></div>
<div class="panel" id="bar"><div class="row"><button id="play">⏸ 일시정지</button><button id="spd">속도 1×</button>
 <span style="flex:1"></span><span style="font-size:11px;opacity:.7">Space=재생/정지 · ◀▶=속도</span></div>
 <input type="range" id="scrub" min="0" max="1440" value="300"><canvas id="hist"></canvas></div>
</div>
<script>
const D=__DATA__;const T=D.trips,N=T.length;
const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
const LON=v=>129+v/1e4,LAT=v=>35+v/1e4,KX0=Math.cos(35.55*Math.PI/180);
// 노선 폴리라인 + 누적거리
const R2=[],CUM=[];
for(const poly of D.routes){const pts=poly.map(p=>[LON(p[0]),LAT(p[1])]);const cum=[0];
 for(let i=1;i<pts.length;i++){const dx=(pts[i][0]-pts[i-1][0])*KX0,dy=pts[i][1]-pts[i-1][1];cum.push(cum[i-1]+Math.hypot(dx,dy));}R2.push(pts);CUM.push(cum);}
function posOn(ri,si,ei,f){const p=R2[ri],cum=CUM[ri];if(!p||!p.length)return null;
 if(si>=p.length)si=p.length-1;if(ei>=p.length)ei=p.length-1;if(si===ei)return p[si];
 const tD=cum[si]+(cum[ei]-cum[si])*f,lo=Math.min(si,ei),hi=Math.max(si,ei);let k=lo;
 while(k<hi&&cum[k+1]<tD)k++;if(k>=p.length-1)return p[p.length-1];
 const seg=cum[k+1]-cum[k]||1e-9,g=(tD-cum[k])/seg;return [p[k][0]+(p[k+1][0]-p[k][0])*g,p[k][1]+(p[k+1][1]-p[k][1])*g];}
// 경계
let mnx=1e9,mxx=-1e9,mny=1e9,mxy=-1e9;
for(const cl of D.cells){mnx=Math.min(mnx,cl[0]);mxx=Math.max(mxx,cl[0]);mny=Math.min(mny,cl[1]);mxy=Math.max(mxy,cl[1]);}
const B={mnLon:LON(mnx),mxLon:LON(mxx),mnLat:LAT(mny),mxLat:LAT(mxy)};
const pad=46,latC=(B.mnLat+B.mxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(B.mxLon-B.mnLon)*kx,dH=(B.mxLat-B.mnLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
let Z=1,TX=0,TY=0;
addEventListener('wheel',e=>{if(e.target.closest&&e.target.closest('.panel'))return;e.preventDefault();const cx=e.clientX,cy=e.clientY,f=e.deltaY<0?1.15:1/1.15,Zn=Math.min(25,Math.max(1,Z*f));TX=cx-(cx-TX)/Z*Zn;TY=cy-(cy-TY)/Z*Zn;Z=Zn;},{passive:false});
let _dg=null;addEventListener('mousedown',e=>{if(e.target.closest&&e.target.closest('.panel'))return;_dg=[e.clientX,e.clientY,TX,TY];});
addEventListener('mousemove',e=>{if(_dg){TX=_dg[2]+(e.clientX-_dg[0]);TY=_dg[3]+(e.clientY-_dg[1]);}});
addEventListener('mouseup',()=>_dg=null);addEventListener('dblclick',e=>{if(e.target.closest&&e.target.closest('.panel'))return;Z=1;TX=0;TY=0;});
const PX=lon=>(ox+(lon-B.mnLon)*kx*sc)*Z+TX, PY=lat=>(H-(oy+(lat-B.mnLat)*sc))*Z+TY;
// ---------- 시간/주야 ----------
const SUNR=110,SUNS=895,TW=30;  // 일출110(05:50) 일몰895(18:55), 전환 ±30분
function smooth(a){a=Math.min(1,Math.max(0,a));return a*a*(3-2*a);}
function daylight(m){m=((m%1440)+1440)%1440;
 if(m<SUNR-TW)return 0; if(m<SUNR+TW)return smooth((m-(SUNR-TW))/(2*TW));
 if(m<SUNS-TW)return 1; if(m<SUNS+TW)return 1-smooth((m-(SUNS-TW))/(2*TW)); return 0;}
let forceMode=-1; // -1 자동, 1 낮, 0 밤
function dNow(m){return forceMode<0?daylight(m):forceMode;}
const lerp=(a,b,f)=>a+(b-a)*f, mix=(A,Bc,f)=>[lerp(A[0],Bc[0],f),lerp(A[1],Bc[1],f),lerp(A[2],Bc[2],f)];
const NIGHT_BG=[10,20,48], DAY_BG=[244,246,250];
// 인구 밀도 t
function dens(v){return Math.min(1,Math.log(1+Math.max(0,v))/Math.log(1+D.maxv));}
// 밤 셀: 남색(저) → 불빛 미색(고) / 낮 셀: 옅은회(저) → 먹색(고)
const N_LO=[14,26,58],N_MID=[90,111,176],N_HI=[255,243,208];
const D_LO=[228,232,240],D_MID=[138,147,166],D_HI=[26,32,48];
function ramp(LO,MID,HI,t){return t<.5?mix(LO,MID,t/.5):mix(MID,HI,(t-.5)/.5);}
function cellCol(v,d){const t=dens(v);const nc=ramp(N_LO,N_MID,N_HI,t),dc=ramp(D_LO,D_MID,D_HI,t);
 const c2=mix(nc,dc,d);return `rgb(${c2[0]|0},${c2[1]|0},${c2[2]|0})`;}
// 하늘 틴트(여명/낙조 전환대): 종모양 가중
function skyTint(m){m=((m%1440)+1440)%1440;
 function bell(center){const x=Math.abs(m-center);return x>TW?0:1-x/TW;}
 const dawn=bell(SUNR),dusk=bell(SUNS);
 if(forceMode>=0) return null;
 if(dawn>0.02)return ['rgba(58,90,160,'+(0.28*dawn).toFixed(3)+')'];
 if(dusk>0.02)return ['rgba(232,133,58,'+(0.32*dusk).toFixed(3)+')'];
 return null;}
function phaseName(m){const d=daylight(m);if(forceMode===1)return'☀ 낮(고정)';if(forceMode===0)return'🌑 밤(고정)';
 m=((m%1440)+1440)%1440;if(m<SUNR-TW||m>=SUNS+TW)return'🌑 밤';if(m<SUNR+TW)return'🌅 여명';if(m>SUNS-TW)return'🌇 낙조';return'☀ 낮';}
function routeCol(idx,d){const hue=(idx*137.508)%360;const L=22+18*(1-d); // 낮엔 약간 진하게
 return `hsl(${hue.toFixed(0)},85%,${(50- (1-d)*0)|0}%)`;}
// 사각형 한 변: 면적=인원 → side=k*sqrt
function sqSide(cnt){return Math.min(22,2+Math.sqrt(cnt)*1.7);}
// ---------- 이용자유형 필터 ----------
const UNAMES=['일반','어린이','청소년','경로','장애','국가유공'];
let utf=-1;const pass=tr=>utf<0||tr[7]===utf;
const utTot=[0,0,0,0,0,0];for(const t of T)utTot[t[7]]+=t[6];
(()=>{let h=`<button data-u="-1" class="on">전체</button>`;UNAMES.forEach((nm,i)=>{if(utTot[i]>0)h+=`<button data-u="${i}">${nm}<span class="n">${utTot[i].toLocaleString()}</span></button>`;});
 const el=document.getElementById('utf');el.innerHTML=h;el.querySelectorAll('button').forEach(b=>b.onclick=()=>{utf=+b.dataset.u;el.querySelectorAll('button').forEach(z=>z.classList.toggle('on',z===b));recomputeBins();});})();
// 모드 버튼(자동/낮/밤)
(()=>{const el=document.getElementById('modes');el.innerHTML=`<button data-f="-1" class="on">자동</button><button data-f="1">낮</button><button data-f="0">밤</button>`;
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>{forceMode=+b.dataset.f;el.querySelectorAll('button').forEach(z=>z.classList.toggle('on',z===b));});})();
// 노선 선택 → 경로선·정류장 표시 (드롭다운 + 하단 칩 바)
const RNAMES=D.routeNames||[], RI=D.routeInfo||[], RC=D.cong||{}, RIDS=D.routeRids||[], RSIDS=D.routeSids||[], ABOL=D.abol||[];
function congOf(i){const rid=RIDS[i];return rid?RC[rid]:null;}
let selRoute=-1;
const sortedRoutes=D.routeNos.map((no,i)=>[no,i]).filter(([no,i])=>R2[i]&&R2[i].length>=2)
  .sort((a,b)=>String(a[0]).localeCompare(String(b[0]),'ko',{numeric:true}));
function renderInfo(i){const el=document.getElementById('rinfo');
 if(i<0||!RI[i]){el.style.display='none';return;}
 const r=RI[i],no=D.routeNos[i]||'',nms=RNAMES[i]||[];const mx=Math.max(1,...r.hb);
 const cg=congOf(i);
 let am=5,pm=12;for(let hh=5;hh<=11;hh++)if(r.hb[hh]>r.hb[am])am=hh;for(let hh=12;hh<=22;hh++)if(r.hb[hh]>r.hb[pm])pm=hh;
 let first=-1,last=-1;r.hb.forEach((v,hh)=>{if(v>0){if(first<0)first=hh;last=hh;}});
 const segs=(r.sg||[]).map((v,k)=>[v,k]).sort((a,b)=>b[0]-a[0]).slice(0,3).filter(s=>s[0]>0);
 const hws=cg?cg.hwy.filter(v=>v>0):[];const avgHw=hws.length?Math.round(hws.reduce((a,b)=>a+b,0)/hws.length):0;
 let h=`<h2>${no}번</h2><div class="sub">${r.a} → ${r.b}</div>`;
 h+=`<div class="kv"><div>일 이용<b>${r.tot.toLocaleString()}</b>명</div><div>정류장<b>${r.ns}</b>개</div>`
   +`<div>총연장<b>${r.len}</b>km</div><div>회전<b>${r.cyc}</b>분*</div><div>첨두비<b>${r.pk}</b>×</div>`
   +(first>=0?`<div>운행<b>${first}~${last}</b>시</div>`:'')
   +(cg?`<div>평균배차<b>${avgHw}</b>분</div><div>최대재차<b>${cg.peakLoad}</b>명</div>`:'')+`</div>`;
 h+=`<div class="sec">시간대별 승차 · 오전첨두 ${am}시 / 오후첨두 ${pm}시</div><div class="hb">`;
 r.hb.forEach((v,hh)=>h+=`<i class="${hh===am||hh===pm?'pk':''}" style="height:${Math.round(v/mx*46)}px" title="${hh}시 ${v}명"></i>`);
 h+='</div><div class="hbx"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>';
 const tmax=Math.max(1,...r.tops.map(t=>t[1]));
 h+='<div class="sec">승차 많은 정류장</div><table>';
 r.tops.forEach(t=>h+=`<tr><td><span class="bar" style="width:${Math.round(t[1]/tmax*64)}px"></span>${t[0]||'-'}</td><td>${t[1].toLocaleString()}</td></tr>`);
 h+='</table>';
 // 혼잡도 API 연동(배차간격·차내 재차인원)
 if(cg){
  const hwmax=Math.max(1,...cg.hwy.filter(v=>v>0)), ldmax=Math.max(1,...cg.load);
  h+=`<div class="sec">시간대별 배차간격(분) · 적을수록 자주옴</div><div class="hb">`;
  cg.hwy.forEach((v,hh)=>{const ht=v>0?Math.round((1-Math.min(1,v/Math.max(20,hwmax)))*40)+6:0;
   h+=`<i style="height:${ht}px;background:${v>0?'#5ad6a0':'transparent'}" title="${hh}시 배차 ${v||'-'}분"></i>`;});
  h+='</div><div class="hbx"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>';
  h+=`<div class="sec">시간대별 차내 재차인원(평균)</div><div class="hb">`;
  cg.load.forEach((v,hh)=>h+=`<i style="height:${Math.round(v/ldmax*46)}px;background:#ff8c5a" title="${hh}시 ${v}명"></i>`);
  h+='</div><div class="hbx"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>';
  // 혼잡 정류장 Top(차내 재차 최대) — byStop을 노선 정류장명에 매핑
  const sidArr=RSIDS[i]||[];const cs=[];
  for(let k=0;k<sidArr.length;k++){const v=cg.byStop[sidArr[k]];if(v)cs.push([nms[k]||'',v]);}
  cs.sort((a,b)=>b[1]-a[1]);
  if(cs.length){h+='<div class="sec">혼잡 정류장 (최대 차내 재차)</div><table>';
   cs.slice(0,5).forEach(t=>h+=`<tr><td>${t[0]||'-'}</td><td>${t[1]}명</td></tr>`);h+='</table>';}
 } else if(segs.length){h+='<div class="sec">혼잡 구간 (재차 추정)</div><table>';
  segs.forEach(([v,k])=>h+=`<tr><td>${(nms[k]||'')} → ${(nms[k+1]||'')}</td><td>${v.toLocaleString()}</td></tr>`);h+='</table>';}
 h+='<div class="sub" style="margin-top:8px">배차·재차인원=국토부 혼잡도 실측 / 회전시간=추정</div>';
 el.innerHTML=h;el.style.display='block';}
function setRoute(i){selRoute=i;
 const rs=document.getElementById('rs');if(rs)rs.value=i;
 renderInfo(i);}
(()=>{let h='<div style="opacity:.8">노선 선택(경로·정류장 표시)</div><select id="rs"><option value="-1">— 선택 안 함 —</option>';
 sortedRoutes.forEach(([no,i])=>h+=`<option value="${i}">${no}</option>`);h+='</select>';
 // 폐지 노선(과거) 별도 선택창
 h+='<div style="margin-top:9px;opacity:.8">폐지 노선(과거)</div><select id="as"><option value="-1">— 선택 안 함 —</option>';
 ABOL.forEach((r,k)=>h+=`<option value="${k}">${r.no}번 (폐지)</option>`);h+='</select><div id="ameta" style="font-size:11px;opacity:.85;margin-top:5px;line-height:1.5"></div>';
 document.getElementById('rsel').innerHTML=h;
 document.getElementById('rs').onchange=e=>setRoute(+e.target.value);
 document.getElementById('as').onchange=e=>{selAbol=+e.target.value;const m=document.getElementById('ameta');
  if(selAbol<0){m.innerHTML='';return;}const r=ABOL[selAbol];
  m.innerHTML=`<b style="color:#ff7ad9">${r.no}번 (폐지)</b><br>${r.a} ↔ ${r.b}<br>첫·막차 ${r.car} · 배차 ${r.hw}<br>${r.op}`;};})();
let selAbol=-1;
// 범례
(()=>{let h='<b>사각형 면적 = 정류장 승차 인원</b><br>';
 [1,5,20,50].forEach(v=>{const s=Math.round(sqSide(v));h+=`<span style="display:inline-block;width:46px;text-align:center"><span class="sq" style="width:${s}px;height:${s}px"></span><br><span style="font-size:10px">${v}명</span></span>`;});
 h+='<br>색 = 노선별 · 배경 = 인구밀도(밤 불빛/낮 먹)';document.getElementById('leg').innerHTML=h;})();
// 히스토그램
const hc=document.getElementById('hist'),hx=hc.getContext('2d');
let bins=new Array(96).fill(0),hmax=1;
function recomputeBins(){bins=new Array(96).fill(0);for(const t of T){if(!pass(t))continue;bins[Math.min(95,Math.floor(((t[0]%1440)+1440)%1440/15))]+=t[6];}hmax=Math.max(1,...bins);}
recomputeBins();
function drawHist(now,d){const w=hc.clientWidth,h=hc.clientHeight;hc.width=w*dpr;hc.height=h*dpr;hx.setTransform(dpr,0,0,dpr,0,0);hx.clearRect(0,0,w,h);
 const bw=w/96,base=d>.5?'#9aa6c0':'#3a4a78',on=d>.5?'#d59b00':'#ffd54f';
 for(let i=0;i<96;i++){const bh=bins[i]/hmax*(h-3);hx.fillStyle=Math.floor(now/15)===i?on:base;hx.fillRect(i*bw,h-bh,bw-0.6,bh);}}
// ---------- 컨트롤 ----------
let now=300,playing=true,speed=1,ptr=0,active=[];
const scrub=document.getElementById('scrub'),ctEl=document.getElementById('ct'),cpEl=document.getElementById('cp'),crEl=document.getElementById('cr'),tip=document.getElementById('tip');
function hhmm(m){let mm=Math.floor(((m%1440)+1440)%1440);let h=Math.floor((mm+240)/60)%24,mi=(mm+240)%60;return String(h).padStart(2,'0')+':'+String(mi).padStart(2,'0');}
function reseek(t){active=[];ptr=0;while(ptr<N&&T[ptr][0]<=t){if(T[ptr][1]>t)active.push(T[ptr]);ptr++;}now=t;}
const playBtn=document.getElementById('play'),spdBtn=document.getElementById('spd');
function setPlay(p){playing=p;playBtn.textContent=playing?'⏸ 일시정지':'▶ 재생';}
function setSpeed(s){speed=s;spdBtn.textContent='속도 '+speed+'×';}
playBtn.onclick=()=>setPlay(!playing);spdBtn.onclick=()=>setSpeed(speed>=8?1:speed*2);
scrub.addEventListener('input',e=>{setPlay(false);reseek(+e.target.value);});
addEventListener('keydown',e=>{if(e.code==='Space'){e.preventDefault();setPlay(!playing);}else if(e.code==='ArrowRight')setSpeed(speed>=8?8:speed*2);else if(e.code==='ArrowLeft')setSpeed(speed<=1?1:speed/2);});
let mx2=-1,my2=-1,mcx=0,mcy=0,crect=c.getBoundingClientRect();
addEventListener('resize',()=>crect=c.getBoundingClientRect());
addEventListener('mousemove',e=>{crect=c.getBoundingClientRect();mx2=e.clientX-crect.left;my2=e.clientY-crect.top;mcx=e.clientX;mcy=e.clientY;});
addEventListener('mouseout',()=>{mx2=my2=-1;});
reseek(300);
let last=performance.now();
function frame(t){const dt=(t-last)/1000;last=t;fit();
 const d=dNow(now);
 document.body.classList.toggle('day',d>0.55);
 if(playing){now+=dt*speed*6;if(now>=1440){reseek(0);}else{while(ptr<N&&T[ptr][0]<=now){if(T[ptr][1]>now)active.push(T[ptr]);ptr++;}}scrub.value=Math.floor(now);}
 // 배경
 const bg=mix(NIGHT_BG,DAY_BG,d);x.fillStyle=`rgb(${bg[0]|0},${bg[1]|0},${bg[2]|0})`;x.fillRect(0,0,W,H);
 // 인구 격자
 const cpx=Math.max(2,(100/111000*sc)*1.5*Z);
 for(const cl of D.cells){x.fillStyle=cellCol(cl[2],d);x.fillRect(PX(LON(cl[0]))-cpx/2,PY(LAT(cl[1]))-cpx/2,cpx,cpx);}
 // 하늘 틴트(여명·낙조)
 const st=skyTint(now);if(st){x.fillStyle=st[0];x.fillRect(0,0,W,H);}
 // 종료 통행 제거
 for(let i=active.length-1;i>=0;i--){if(active[i][1]<=now){active[i]=active[active.length-1];active.pop();}}
 // 승객 사각형
 let people=0;const hov=!playing&&mx2>=0;let hbest=1e9,htr=null;
 const night=d<0.5;
 for(const tr of active){if(!pass(tr))continue;people+=tr[6];
  const f=(now-tr[0])/(tr[1]-tr[0]);const pos=posOn(tr[2],tr[3],tr[4],f<0?0:f>1?1:f);if(!pos)continue;
  const s=sqSide(tr[5]),X=PX(pos[0]),Y=PY(pos[1]);
  x.fillStyle=`hsl(${(tr[2]*137.508)%360|0},85%,${night?58:46}%)`;
  if(night){x.shadowColor=x.fillStyle;x.shadowBlur=Math.min(8,s);}
  x.fillRect(X-s/2,Y-s/2,s,s);x.shadowBlur=0;
  if(!night){x.strokeStyle='rgba(20,28,48,.55)';x.lineWidth=0.6;x.strokeRect(X-s/2,Y-s/2,s,s);}
  if(hov){const dd=(X-mx2)*(X-mx2)+(Y-my2)*(Y-my2),lim=Math.max(8,s);if(dd<hbest&&dd<lim*lim){hbest=dd;htr=tr;}}}
 // 선택 노선 경로선 + 정류장 (+ 정류장 호버)
 let stopHit=null;
 if(selRoute>=0&&R2[selRoute]&&R2[selRoute].length>=2){const p=R2[selRoute],nms=RNAMES[selRoute]||[],day=d>0.55;
  // 구간 색·굵기 = 차내 재차인원(혼잡도 실측 우선, 없으면 카드 추정)
  const cg=RC[RIDS[selRoute]],sids=RSIDS[selRoute]||[];let segL=[];
  if(cg){for(let k=0;k<p.length-1;k++)segL.push(Math.max(cg.byStop[sids[k]]||0,cg.byStop[sids[k+1]]||0));}
  else{segL=((RI[selRoute]&&RI[selRoute].sg)||[]).slice();}
  let smx=1;for(const v of segL)if(v>smx)smx=v;
  for(let k=0;k<p.length-1;k++){const tcg=segL.length?Math.min(1,(segL[k]||0)/smx):0;
   x.strokeStyle=`rgb(${60+195*tcg|0},${120-50*tcg|0},${210-190*tcg|0})`;x.lineWidth=2.4+3.4*tcg;
   x.beginPath();x.moveTo(PX(p[k][0]),PY(p[k][1]));x.lineTo(PX(p[k+1][0]),PY(p[k+1][1]));x.stroke();}
  let hb=64;
  for(let i=0;i<p.length;i++){const X=PX(p[i][0]),Y=PY(p[i][1]);
   x.fillStyle=day?'#0a2a80':'#eaf6ff';x.strokeStyle=day?'#ffffff':'#0a1430';x.lineWidth=0.8;
   x.beginPath();x.arc(X,Y,2.8,0,7);x.fill();x.stroke();
   if(mx2>=0){const dd=(X-mx2)*(X-mx2)+(Y-my2)*(Y-my2);if(dd<hb){hb=dd;stopHit={nm:nms[i]||'정류장',seq:i+1,tot:p.length,X:X,Y:Y};}}}
  const a=p[0],b=p[p.length-1];x.fillStyle='#ff5a5a';for(const q of [a,b]){x.beginPath();x.arc(PX(q[0]),PY(q[1]),5,0,7);x.fill();}
  if(stopHit){x.strokeStyle='#ffd54f';x.lineWidth=2;x.beginPath();x.arc(stopHit.X,stopHit.Y,6,0,7);x.stroke();}}
 // 폐지 노선(점선 마젠타) — 선택 시 별도 표시
 if(selAbol>=0&&ABOL[selAbol]&&ABOL[selAbol].pts.length>=2){const p=ABOL[selAbol].pts;
  x.save();x.setLineDash([7,5]);x.strokeStyle='#ff5ad0';x.lineWidth=3;if(d<0.5){x.shadowColor='#ff5ad0';x.shadowBlur=6;}
  x.beginPath();p.forEach((q,i)=>{const X=PX(q[0]),Y=PY(q[1]);i?x.lineTo(X,Y):x.moveTo(X,Y);});x.stroke();x.restore();
  x.fillStyle='#ffb0e8';for(const q of p){x.beginPath();x.arc(PX(q[0]),PY(q[1]),2.6,0,7);x.fill();}
  const aa=p[0],bb=p[p.length-1];x.fillStyle='#fff';x.strokeStyle='#ff5ad0';x.lineWidth=2;
  for(const q of [aa,bb]){x.beginPath();x.arc(PX(q[0]),PY(q[1]),5,0,7);x.fill();x.stroke();}}
 // 툴팁: 정류장(우선) > 승객
 if(stopHit){tip.innerHTML='<b>'+stopHit.nm+'</b><br>'+(D.routeNos[selRoute]||'')+'번 · '+stopHit.seq+'/'+stopHit.tot+'번째 정류장';
  tip.style.display='block';tip.style.left=(mcx>W-190?mcx-180:mcx+14)+'px';tip.style.top=(mcy+14)+'px';}
 else if(htr){const ri=htr[2];tip.innerHTML='<b>'+(D.routeNos[ri]||'노선')+'번</b><br>정류장 승차 '+htr[5].toLocaleString()+'명<span style="opacity:.7">(±4분)</span>';
  tip.style.display='block';tip.style.left=(mcx>W-170?mcx-160:mcx+14)+'px';tip.style.top=(mcy+14)+'px';}else tip.style.display='none';
 // HUD
 ctEl.textContent=hhmm(now);cpEl.textContent=phaseName(now);crEl.textContent='운행 중 '+people.toLocaleString()+'명';
 drawHist(((now%1440)+1440)%1440,d);
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
</script></body></html>"""
open("ulsan_daynight_flow.html","w",encoding="utf-8").write(HTML.replace("__DATA__", json.dumps(d, separators=(",",":"))))
print("ulsan_daynight_flow.html", round(os.path.getsize("ulsan_daynight_flow.html")/1e6,2),"MB")
