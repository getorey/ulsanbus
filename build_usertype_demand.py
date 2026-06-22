"""이용자유형별 정류장 수요 통합 — 전체/일반/청소년/어린이/경로/장애/국가유공 필터
입력: uploads card_records_20260407*.csv (01 + _etc), 좌표원, grid100_population.csv
출력: ulsan_usertype_demand.html
"""
import csv, re, glob, math, json, os
from collections import defaultdict
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
bs={}
for r in csv.DictReader(open("ulsan_busstops_20260407.csv",encoding="utf-8-sig")): bs[r["sttn_id"]]=r["sttn_nm"]
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
# 유형 인덱스
TYPES=["01","02","03","04","05","06"]
TIDX={t:i for i,t in enumerate(TYPES)}
COLS=["rte_id","users_type_cd","ride_dt","ride_sttn_id","goff_dt","goff_sttn_id","utztn_nope","utztn_dstnc","brdg_hr","trnf_cnt"]
# 01 본파일 + _etc 모두 읽기
files=[]
for pat in ["card_records_20260407.csv","card_records_20260407-*.csv","card_records_20260407_etc.csv"]:
    files+=glob.glob("/sessions/jolly-gifted-albattani/mnt/uploads/"+pat)
files=sorted(set(files))
# 01 중복 방지: 01 파일은 하나만(가장 큰 것), _etc는 02~06만
board=defaultdict(lambda:[0]*6)  # sid -> 6유형 승차
seen01=False
typ_tot=[0]*6
for f in files:
    is_etc = f.endswith("_etc.csv")
    for x in csv.reader(open(f,encoding="utf-8-sig")):
        if len(x)<10 or x[1]=="users_type_cd": continue
        ut=x[1]
        if ut not in TIDX: continue
        if ut=="01":
            if is_etc: continue
        else:
            if not is_etc: continue   # 02~06 은 _etc 에서만
        n=int(x[6] or 1); board[x[3]][TIDX[ut]]+=n; typ_tot[TIDX[ut]]+=n
# 01 중복: 두 01 파일이 동일하므로 한 번만 — 위 로직은 두 01파일 모두 더함 → 중복!
# 01 파일이 여러 개면 첫 번째만 쓰도록 재집계
board=defaultdict(lambda:[0]*6); typ_tot=[0]*6
f01=[f for f in files if not f.endswith("_etc.csv")]
use01=sorted(f01,key=lambda f:os.path.getsize(f),reverse=True)[:1]
fetc=[f for f in files if f.endswith("_etc.csv")]
for f in use01+fetc:
    is_etc=f.endswith("_etc.csv")
    for x in csv.reader(open(f,encoding="utf-8-sig")):
        if len(x)<10 or x[1]=="users_type_cd": continue
        ut=x[1]
        if ut not in TIDX: continue
        if (ut=="01")==is_etc: continue   # 01은 비_etc, 그외는 _etc
        n=int(x[6] or 1); board[x[3]][TIDX[ut]]+=n; typ_tot[TIDX[ut]]+=n
print("유형 총승차:",dict(zip(TYPES,typ_tot)))
# 정류장 좌표+이름
stops=[]
for sid,arr in board.items():
    if sum(arr)<=0: continue
    c=resolve(sid)
    if not c: continue
    stops.append([round(c[0],5),round(c[1],5),(bs.get(sid) or "").strip()]+arr)
cells=[]
for r in csv.DictReader(open("grid100_population.csv",encoding="utf-8-sig")):
    cells.append([round(float(r["lon"]),5),round(float(r["lat"]),5),int(r["pop"])])
data={"stops":stops,"cells":cells,"typeTot":typ_tot}
print("정류장",len(stops),"/ 격자",len(cells))
json.dump(data,open("usertype_data_20260407.json","w"),separators=(",",":"),ensure_ascii=False)

HTML=r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 이용자유형별 정류장 수요</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#070b16;color:#eaf0ff;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}#c{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.panel{position:absolute;z-index:10;background:#0d1530e0;backdrop-filter:blur(7px);border:1px solid #ffffff22;border-radius:13px;padding:12px 15px}
#title{left:16px;top:16px;max-width:380px}#title h1{margin:0 0 5px;font-size:15px}#title p{margin:3px 0;font-size:11.5px;color:#bcd0f5;line-height:1.5}
#tabs{left:16px;top:120px;display:flex;flex-wrap:wrap;gap:6px;max-width:330px}
#tabs button{background:#1a2647;color:#cfe0ff;border:1px solid #ffffff2a;border-radius:9px;padding:7px 11px;font-size:12.5px;cursor:pointer}
#tabs button.on{background:#3a6bd5;color:#fff;border-color:#5a8bff}
#tabs button .n{opacity:.65;font-size:10.5px;margin-left:3px}
#list{right:16px;top:16px;font-size:12px;max-height:92vh;overflow:auto;min-width:230px}
#list h3{margin:0 0 6px;font-size:13px}#list table{border-collapse:collapse;width:100%}
#list td{padding:3px 7px;border-bottom:1px solid #ffffff12}#list td:last-child{text-align:right;color:#ffd54f;font-weight:600}
#list tr.hd td{color:#9fb2dd;font-weight:600}#list tr:hover td{background:#23305aa0}
#leg{left:16px;bottom:16px;font-size:11.5px;line-height:1.7}#leg .g{display:inline-block;width:130px;height:11px;border-radius:3px;vertical-align:-1px;background:linear-gradient(90deg,#3a4a78,#ffd54f,#ff8c1e,#e8503a)}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:10.5px;margin-top:6px}#themeBtn{position:absolute;z-index:30;top:34px;left:50%;transform:translateX(-50%);background:#0d1530cc;color:#eaf0ff;border:1px solid #ffffff33;border-radius:9px;padding:6px 12px;font-size:12.5px;cursor:pointer}body.light{background:#eef1f7}body.light .panel{background:#ffffffe0;border-color:#0000001f;color:#1b2640;box-shadow:0 2px 10px #00000014}body.light .panel *{color:#1b2640 !important}body.light #themeBtn{background:#ffffffe0;color:#1b2640;border-color:#0000002a}body.light #tabs button,body.light #utf button,body.light #bar button,body.light #list td,body.light select{background:#e9edf6}body.light #tabs button.on{background:#3a6bd5 !important}body.light #tabs button.on *{color:#fff !important}body.light #utf button.on{background:#2aa17a !important}body.light #utf button.on *{color:#fff !important}body.light #tabs button.on,body.light #utf button.on{color:#fff !important}.popgrad{display:inline-block;width:90px;height:9px;border-radius:3px;vertical-align:-1px;margin:0 5px;background:linear-gradient(90deg,#14283c,#3a96a0,#ebcd6e)}body.light .popgrad{background:linear-gradient(90deg,#dfeed8,#78b46e,#1c683a)}</style>
</head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>이용자유형별 정류장 수요</h1>
<p>원 크기·색 = 그 정류장 승차 인원(선택 유형) · 배경 = 인구밀도 · 2026-04-07</p><span class="tag">실데이터</span> <a href="ulsan_용어설명.html" target="_blank" style="display:inline-block;margin-top:6px;margin-left:6px;font-size:11px;color:#7fb4ff">ℹ 용어 설명</a></div>
<div class="panel" id="tabs"></div>
<div class="panel" id="list"></div>
<div class="panel" id="leg"><b>정류장 승차 인원</b><br><span style="opacity:.6">적음</span> <span class="g"></span> <span>많음</span></div></div>
<script>
const D=__DATA__,S=D.stops,CELLS=D.cells;
const NAMES=['일반','어린이','청소년','경로','장애','국가유공'];
const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
let mnLon=1e9,mxLon=-1e9,mnLat=1e9,mxLat=-1e9;
for(const cl of CELLS){mnLon=Math.min(mnLon,cl[0]);mxLon=Math.max(mxLon,cl[0]);mnLat=Math.min(mnLat,cl[1]);mxLat=Math.max(mxLat,cl[1]);}
const pad=54,latC=(mnLat+mxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(mxLon-mnLon)*kx,dH=(mxLat-mnLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
let Z=1,TX=0,TY=0;addEventListener('wheel',e=>{if(e.target.closest&&e.target.closest('.panel'))return;e.preventDefault();const cx=e.clientX,cy=e.clientY,f=e.deltaY<0?1.15:1/1.15,Zn=Math.min(25,Math.max(1,Z*f));TX=cx-(cx-TX)/Z*Zn;TY=cy-(cy-TY)/Z*Zn;Z=Zn;},{passive:false});let _dg=null;addEventListener('mousedown',e=>{if(e.target.closest&&e.target.closest('.panel'))return;_dg=[e.clientX,e.clientY,TX,TY];});addEventListener('mousemove',e=>{if(_dg){TX=_dg[2]+(e.clientX-_dg[0]);TY=_dg[3]+(e.clientY-_dg[1]);}});addEventListener('mouseup',()=>_dg=null);addEventListener('dblclick',e=>{if(e.target.closest&&e.target.closest('.panel'))return;Z=1;TX=0;TY=0;});
const PX=lon=>(ox+(lon-mnLon)*kx*sc)*Z+TX, PY=lat=>(H-(oy+(lat-mnLat)*sc))*Z+TY;
const pmax=(()=>{const v=CELLS.map(c=>c[2]).sort((a,b)=>a-b);return v[Math.floor(v.length*.99)];})();
function PG(t,a){t=Math.min(1,Math.max(0,t));var A=[150,200,150],B=[46,150,70],C=[8,72,34],r,g,b;if(t<.55){var f=t/.55;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{var f=(t-.55)/.45;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}return 'rgba('+(r|0)+','+(g|0)+','+(b|0)+','+(a==null?1:a)+')';}
function pcol(v){let t=Math.min(1,Math.log(1+v)/Math.log(1+pmax));if(document.body.classList.contains('light'))return PG(t);return `rgb(${14+22*t|0},${28+55*t|0},${52+30*t|0})`;}
function scol(t){t=Math.min(1,t);const A=[58,74,120],B=[255,213,79],C=[232,80,58];let r,g,b;
 if(t<.5){const f=t/.5;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{const f=(t-.5)/.5;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}
 return `rgb(${r|0},${g|0},${b|0})`;}
// 유형: -1=전체, 0~5=각 유형. 정류장 값: val(s)
let mode=-1;
function val(s){if(mode<0){let t=0;for(let i=0;i<6;i++)t+=s[3+i];return t;}return s[3+mode];}
// 탭
(()=>{let h=`<button data-m="-1" class="on">전체<span class="n">${D.typeTot.reduce((a,b)=>a+b,0).toLocaleString()}</span></button>`;
 NAMES.forEach((nm,i)=>h+=`<button data-m="${i}">${nm}<span class="n">${D.typeTot[i].toLocaleString()}</span></button>`);
 const el=document.getElementById('tabs');el.innerHTML=h;
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>{mode=+b.dataset.m;el.querySelectorAll('button').forEach(z=>z.classList.toggle('on',z===b));buildList();});})();
let hi=-1;
function buildList(){const arr=S.map((s,i)=>[i,val(s)]).filter(z=>z[1]>0).sort((a,b)=>b[1]-a[1]).slice(0,15);
 let h=`<h3>${mode<0?'전체':NAMES[mode]} 승차 상위 정류장</h3><table><tr class="hd"><td>정류장</td><td>승차</td></tr>`;
 arr.forEach(z=>{const s=S[z[0]];h+=`<tr data-i="${z[0]}"><td>${s[2]||'-'}</td><td>${z[1].toLocaleString()}</td></tr>`;});
 h+='</table>';const el=document.getElementById('list');el.innerHTML=h;
 el.querySelectorAll('tr[data-i]').forEach(tr=>tr.onmouseenter=()=>hi=+tr.dataset.i);el.onmouseleave=()=>hi=-1;}
buildList();
function frame(){fit();x.fillStyle=(document.body.classList.contains('light')?'#e9edf4':'#070b16');x.fillRect(0,0,W,H);
 const px=Math.max(2,(100/111000*sc)*1.5*Z);
 for(const cl of CELLS){x.fillStyle=pcol(cl[2]);x.fillRect(PX(cl[0])-px/2,PY(cl[1])-px/2,px,px);}
 let mx=1;for(const s of S){const v=val(s);if(v>mx)mx=v;}
 for(const s of S){const v=val(s);if(v<=0)continue;const r=2+Math.sqrt(v)*(mode<0?0.9:1.6);
  x.fillStyle=scol(v/mx);x.globalAlpha=.88;x.beginPath();x.arc(PX(s[0]),PY(s[1]),r,0,7);x.fill();}
 x.globalAlpha=1;
 if(hi>=0&&S[hi]){const s=S[hi],X=PX(s[0]),Y=PY(s[1]),v=val(s),r=2+Math.sqrt(v)*(mode<0?0.9:1.6);
  x.strokeStyle='#fff';x.lineWidth=2;x.beginPath();x.arc(X,Y,r+4,0,7);x.stroke();
  x.fillStyle='#fff';x.font='bold 13px sans-serif';x.fillText((s[2]||'')+' '+v.toLocaleString()+'명',X+10,Y-8);}
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
;(function(){var b=document.createElement('button');b.id='themeBtn';b.textContent='☀ 라이트';(document.getElementById('wrap')||document.body).appendChild(b);b.onclick=function(){document.body.classList.toggle('light');b.textContent=document.body.classList.contains('light')?'🌙 다크':'☀ 라이트';};})();;(function(){var t=document.getElementById('title');if(!t)return;var d=document.createElement('div');d.style.cssText='margin-top:7px;font-size:11px;opacity:.85';d.innerHTML='배경=인구밀도 낮음<span class="popgrad"></span>높음';t.appendChild(d);})();</script></body></html>"""
open("ulsan_usertype_demand.html","w",encoding="utf-8").write(HTML.replace("__DATA__",json.dumps(data,separators=(",",":"),ensure_ascii=False)))
print("HTML MB:",round(os.path.getsize('ulsan_usertype_demand.html')/1e6,2))
