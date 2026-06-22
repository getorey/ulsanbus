"""동구 집중 지도: 동구 정류장 승차 + 동구→도심(삼산·성남) 흐름 강조 + 진단 패널
출력: ulsan_donggu.html
"""
import csv, glob, os, json, re, statistics as st
from collections import defaultdict
UP = "/sessions/jolly-gifted-albattani/mnt/uploads/"
# 좌표 해석기
def norm(s): s=(s or "").split("(")[0]; return re.sub(r"[ .()\-·,]","",s)
def norm_core(s):
    s=norm(s)
    for suf in ("정류소","정류장","건너편","건너","방면","앞","후문","정문","입구"):
        if s.endswith(suf) and len(s)>len(suf)+1: s=s[:-len(suf)]
    return s
xw={}
for r in csv.DictReader(open("stop_crosswalk.csv",encoding="utf-8-sig")):
    try: xw[r["sttn_id"].strip()]=(float(r["lon"]),float(r["lat"]))
    except: pass
bs={}; sgg={}; emd={}
for r in csv.DictReader(open("ulsan_busstops_20260407.csv",encoding="utf-8-sig")):
    bs[r["sttn_id"]]=r["sttn_nm"]; sgg[r["sttn_id"]]=r["sgg_cd"]; emd[r["sttn_id"]]=r.get("emd_nm") or ""
n2c={}; c2c={}
def add(nm,c):
    k=norm(nm); kc=norm_core(nm)
    if k and k not in n2c: n2c[k]=c
    if kc and kc not in c2c: c2c[kc]=c
for r in csv.DictReader(open("ulsan_stop_coords_master.csv",encoding="utf-8-sig")):
    try: add(r["stop_name"],(float(r["lon"]),float(r["lat"])))
    except: pass
for r in csv.DictReader(open("stop_crosswalk.csv",encoding="utf-8-sig")):
    try: add(r["sttn_nm"],(float(r["lon"]),float(r["lat"])))
    except: pass
for r in csv.DictReader(open("nat_stops_raw.csv",encoding="cp949")):
    if "울산" in (r["도시명"] or ""):
        try: add(r["정류장명"],(float(r["경도"]),float(r["위도"])))
        except: pass
def resolve(sid):
    if sid in xw: return xw[sid]
    nm=bs.get(sid)
    if not nm: return None
    if norm(nm) in n2c: return n2c[norm(nm)]
    if norm_core(nm) in c2c: return c2c[norm_core(nm)]
    return None
DONG="31170"
def is_core(sid): e=emd.get(sid,""); return ("삼산" in e) or ("성남" in e)
COLS=["rte_id","users_type_cd","ride_dt","ride_sttn_id","goff_dt","goff_sttn_id","utztn_nope","utztn_dstnc","brdg_hr","trnf_cnt"]
f01=sorted([f for f in glob.glob(UP+"card_records_20260407*.csv") if not f.endswith("_etc.csv")],key=os.path.getsize,reverse=True)[:1]
fetc=[f for f in glob.glob(UP+"card_records_20260407*.csv") if f.endswith("_etc.csv")]
board=defaultdict(int)      # 동구 정류장 승차
od=defaultdict(int)         # (b,g) 동구발 통행
d_n=0; d_br=[]; dest=defaultdict(int); core_n=0; core_br=[]; alln=0; allbr=[]
for f in f01+fetc:
    et=f.endswith("_etc.csv")
    for x in csv.reader(open(f,encoding="utf-8-sig")):
        if len(x)<10 or x[1]=="users_type_cd": continue
        if (x[1]=="01")==et: continue
        n=int(x[6] or 1);
        try: br=int(x[8] or 0)
        except: br=0
        alln+=n; allbr.append(br)
        b=x[3]; g=x[5]
        if sgg.get(b)==DONG:
            board[b]+=n; d_n+=n; d_br.append(br)
            if g and b!=g: od[(b,g)]+=n
            if is_core(g): core_n+=n; core_br.append(br); dest["core"]+=n
            elif sgg.get(b)==DONG and sgg.get(g)==DONG: dest["dong"]+=n
            else: dest["etc"]+=n
# 동구 정류장
stops=[]
for sid,bd in board.items():
    c=resolve(sid)
    if not c: continue
    stops.append([round(c[0],5),round(c[1],5),bd,(bs.get(sid) or "").strip()])
# OD 상위(동구발) 좌표
odl=[]
for (b,g),t in sorted(od.items(),key=lambda x:-x[1])[:400]:
    cb,cg=resolve(b),resolve(g)
    if not cb or not cg: continue
    odl.append([round(cb[0],5),round(cb[1],5),round(cg[0],5),round(cg[1],5),t,1 if is_core(g) else 0])
    if len(odl)>=180: break
cells=[]
for r in csv.DictReader(open("grid100_population.csv",encoding="utf-8-sig")):
    cells.append([round(float(r["lon"]),5),round(float(r["lat"]),5),int(r["pop"])])
tot=sum(dest.values()) or 1
stats={"dn":d_n,"share":round(d_n/alln*100,1),
       "inner":round(dest['dong']/tot*100),"core":round(dest['core']/tot*100),
       "avgCore":round((st.mean(core_br)/60) if core_br else 0,1),"avgAll":round(st.mean(allbr)/60,1)}
data={"stops":stops,"od":odl,"cells":cells,"stats":stats}
print("동구 정류장",len(stops),"/ OD선",len(odl),"/", stats)

HTML=r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 동구 집중 — 버스 이용·이동</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#070b16;color:#eaf0ff;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}#c{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.panel{position:absolute;z-index:10;background:#0d1530dd;backdrop-filter:blur(7px);border:1px solid #ffffff22;border-radius:13px;padding:12px 15px}
#title{left:16px;top:16px;max-width:360px}#title h1{margin:0 0 5px;font-size:15px}#title p{margin:3px 0;font-size:11.5px;color:#bcd0f5;line-height:1.5}
#stat{right:16px;top:16px;min-width:210px;font-size:12px}#stat h3{margin:0 0 6px;font-size:13px}
#stat .kv{display:flex;flex-wrap:wrap;gap:6px}#stat .kv div{background:#ffffff14;border-radius:7px;padding:6px 9px;min-width:92px}#stat .kv b{display:block;font-size:15px;color:#ffd54f}
#stat .note{font-size:11px;opacity:.75;margin-top:8px}
#leg{left:16px;bottom:16px;font-size:11.5px;line-height:1.8}#leg i{display:inline-block;width:14px;height:9px;margin-right:6px;border-radius:2px;vertical-align:1px}
#tip{position:absolute;z-index:20;pointer-events:none;display:none;background:#0b1226f0;border:1px solid #ffffff44;border-radius:9px;padding:6px 10px;font-size:12px}#tip b{color:#ffd54f}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:10.5px;margin-top:6px}
#themeBtn{position:absolute;z-index:30;top:14px;left:50%;transform:translateX(-50%);background:#0d1530cc;color:#eaf0ff;border:1px solid #ffffff33;border-radius:9px;padding:6px 12px;font-size:12.5px;cursor:pointer}
body.light{background:#eef1f7}body.light .panel{background:#ffffffe0;color:#1b2640;border-color:#0000001f}body.light .panel *{color:#1b2640 !important}body.light #themeBtn{background:#ffffffe0;color:#1b2640}body.light #stat .kv div{background:#0000000d}
</style></head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 동구 집중 — 버스 이용·이동</h1>
<p>주황 원=동구 정류장 승차 · <b style="color:#ff5a5a">빨강 선</b>=동구→시내(삼산·성남) · 회색 선=그 외 동구발 이동 · 배경=인구밀도</p>
<span class="tag">실데이터 2026-04-07</span> <a href="ulsan_용어설명.html" target="_blank" style="font-size:11px;color:#7fb4ff;margin-left:6px">ℹ 용어 설명</a></div>
<div class="panel" id="stat"></div>
<div class="panel" id="leg"><b>범례</b><br><i style="background:#ffb02e"></i>동구 정류장 승차(원 크기)<br><i style="background:#ff5a5a"></i>동구→시내(삼산·성남) 이동<br><i style="background:#5a6b8a"></i>그 외 동구발 이동</div>
<div id="tip"></div></div>
<script>
const D=__DATA__,S=D.stops,OD=D.od,CELLS=D.cells,ST=D.stats;
const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
// 경계: 동구 정류장 + OD 목적지(시내 포함)
let mnLon=1e9,mxLon=-1e9,mnLat=1e9,mxLat=-1e9;
function ext(lo,la){mnLon=Math.min(mnLon,lo);mxLon=Math.max(mxLon,lo);mnLat=Math.min(mnLat,la);mxLat=Math.max(mxLat,la);}
for(const s of S)ext(s[0],s[1]);for(const l of OD){ext(l[0],l[1]);ext(l[2],l[3]);}
const pad=70,latC=(mnLat+mxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(mxLon-mnLon)*kx,dH=(mxLat-mnLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
let Z=1,TX=0,TY=0;
addEventListener('wheel',e=>{if(e.target.closest&&e.target.closest('.panel'))return;e.preventDefault();const cx=e.clientX,cy=e.clientY,f=e.deltaY<0?1.15:1/1.15,Zn=Math.min(25,Math.max(1,Z*f));TX=cx-(cx-TX)/Z*Zn;TY=cy-(cy-TY)/Z*Zn;Z=Zn;},{passive:false});
let _dg=null;addEventListener('mousedown',e=>{if(e.target.closest&&e.target.closest('.panel'))return;_dg=[e.clientX,e.clientY,TX,TY];});
addEventListener('mousemove',e=>{if(_dg){TX=_dg[2]+(e.clientX-_dg[0]);TY=_dg[3]+(e.clientY-_dg[1]);}crect=c.getBoundingClientRect();mx2=e.clientX-crect.left;my2=e.clientY-crect.top;mcx=e.clientX;mcy=e.clientY;});
addEventListener('mouseup',()=>_dg=null);addEventListener('dblclick',e=>{if(e.target.closest&&e.target.closest('.panel'))return;Z=1;TX=0;TY=0;});
addEventListener('mouseout',()=>{mx2=my2=-1;});
const PX=lon=>(ox+(lon-mnLon)*kx*sc)*Z+TX, PY=lat=>(H-(oy+(lat-mnLat)*sc))*Z+TY;
let mx2=-1,my2=-1,mcx=0,mcy=0,crect=c.getBoundingClientRect();
const pmax=(()=>{const v=CELLS.map(c=>c[2]).sort((a,b)=>a-b);return v[Math.floor(v.length*.99)];})();
function pcol(v){const day=document.body.classList.contains('light');let t=Math.min(1,Math.log(1+v)/Math.log(1+pmax));
 if(day){const a=[233,237,243],b=[150,200,150],cc=[8,72,34];const f=t,A=t<.55?a:b,Bc=t<.55?b:cc,ff=t<.55?t/.55:(t-.55)/.45;return `rgb(${A[0]+(Bc[0]-A[0])*ff|0},${A[1]+(Bc[1]-A[1])*ff|0},${A[2]+(Bc[2]-A[2])*ff|0})`;}
 return `rgb(${16+30*t|0},${30+70*t|0},${58+34*t|0})`;}
const tip=document.getElementById('tip');
const odmx=Math.max(1,...OD.map(l=>l[4]));
const smx=Math.max(1,...S.map(s=>s[2]));
(()=>{const e=document.getElementById('stat');
 e.innerHTML=`<h3>동구 진단 (2026-04-07)</h3><div class="kv">`
 +`<div>동구 승차<b>${ST.dn.toLocaleString()}명</b></div><div>도시 점유<b>${ST.share}%</b></div>`
 +`<div>동구 내부행<b>${ST.inner}%</b></div><div>시내 직접행<b>${ST.core}%</b></div>`
 +`<div>동구→시내 소요<b>${ST.avgCore}분</b></div><div>전체 평균<b>${ST.avgAll}분</b></div></div>`
 +`<div class="note">동구 통행 대부분이 동구 내부이고 시내(삼산·성남) 직접 통행은 ${ST.core}%로 적으며, 시내까지 소요는 전체 평균의 약 ${(ST.avgCore/ST.avgAll).toFixed(1)}배입니다.</div>`;})();
function frame(){fit();x.fillStyle=document.body.classList.contains('light')?'#e9edf4':'#070b16';x.fillRect(0,0,W,H);
 const px=Math.max(2,(100/111000*sc)*1.5*Z);
 for(const cl of CELLS){x.fillStyle=pcol(cl[2]);x.globalAlpha=.5;x.fillRect(PX(cl[0])-px/2,PY(cl[1])-px/2,px,px);}x.globalAlpha=1;
 // OD: 비도심(회색) 먼저, 도심(빨강) 위에
 for(const l of OD)if(!l[5]){const a=[PX(l[0]),PY(l[1])],b=[PX(l[2]),PY(l[3])],t=l[4]/odmx;
  const mxp=(a[0]+b[0])/2,myp=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*.16;
  x.strokeStyle=`rgba(120,140,170,${0.12+0.3*t})`;x.lineWidth=0.5+t*3;x.beginPath();x.moveTo(a[0],a[1]);x.quadraticCurveTo(mxp,myp,b[0],b[1]);x.stroke();}
 for(const l of OD)if(l[5]){const a=[PX(l[0]),PY(l[1])],b=[PX(l[2]),PY(l[3])],t=l[4]/odmx;
  const mxp=(a[0]+b[0])/2,myp=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*.16;
  x.strokeStyle=`rgba(255,70,70,${0.4+0.5*t})`;x.lineWidth=1+t*6;x.beginPath();x.moveTo(a[0],a[1]);x.quadraticCurveTo(mxp,myp,b[0],b[1]);x.stroke();}
 // 동구 정류장
 let hit=null,hb=80;
 for(const s of S){const r=2+Math.sqrt(s[2])*1.1,X=PX(s[0]),Y=PY(s[1]);
  x.fillStyle='rgba(255,176,46,.9)';x.beginPath();x.arc(X,Y,r,0,7);x.fill();
  if(mx2>=0){const dd=(X-mx2)**2+(Y-my2)**2;if(dd<hb&&dd<(r+5)**2){hb=dd;hit={s,X,Y};}}}
 if(hit){x.strokeStyle='#fff';x.lineWidth=2;x.beginPath();x.arc(hit.X,hit.Y,2+Math.sqrt(hit.s[2])*1.1+4,0,7);x.stroke();
  tip.innerHTML='<b>'+(hit.s[3]||'정류장')+'</b><br>승차 '+hit.s[2].toLocaleString()+'명';tip.style.display='block';
  tip.style.left=(mcx>W-160?mcx-150:mcx+14)+'px';tip.style.top=(mcy+14)+'px';}else tip.style.display='none';
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
(function(){var b=document.createElement('button');b.id='themeBtn';b.textContent='☀ 라이트';document.getElementById('wrap').appendChild(b);
 b.onclick=function(){document.body.classList.toggle('light');b.textContent=document.body.classList.contains('light')?'🌙 다크':'☀ 라이트';};})();
</script></body></html>"""
open("ulsan_donggu.html","w",encoding="utf-8").write(HTML.replace("__DATA__",json.dumps(data,separators=(",",":"),ensure_ascii=False)))
print("ulsan_donggu.html", round(os.path.getsize("ulsan_donggu.html")/1e6,2),"MB")
