"""울산 버스 노선 개선 분석 — 데이터 집계
4뷰: ① 직통 신설 후보(욕망선+환승) ② 구간 재차인원(혼잡·공차) ③ 인구 대비 공급공백 ④ 시간대 수요→배차
출력: improve_data_20260407.json  (HTML은 다음 단계)
"""
import csv, re, glob, math, json, os
from collections import defaultdict

# ---------- 좌표 해석기 (candidates + nearest 로 노선 경로 깔끔하게) ----------
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
n2c={}; c2c={}; n2l=defaultdict(list); c2l=defaultdict(list)
def add(nm,c):
    k=norm(nm); kc=norm_core(nm)
    if k and k not in n2c: n2c[k]=c
    if k: n2l[k].append(c)
    if kc and kc not in c2c: c2c[kc]=c
    if kc: c2l[kc].append(c)
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
def km(a,b): return math.hypot((a[0]-b[0])*88.9,(a[1]-b[1])*111.0)
def resolve(sid):
    if sid in xw: return xw[sid]
    nm=bs.get(sid)
    if not nm: return None
    if norm(nm) in n2c: return n2c[norm(nm)]
    if norm_core(nm) in c2c: return c2c[norm_core(nm)]
    return None
def candidates(sid):
    if sid in xw: return [xw[sid]]
    nm=bs.get(sid)
    if not nm: return []
    if norm(nm) in n2l: return n2l[norm(nm)]
    if norm_core(nm) in c2l: return c2l[norm_core(nm)]
    return []

# ---------- 노선 경유열 → 폴리라인 + sttn_id→index ----------
seq_raw=defaultdict(list); rid2no={}
for r in csv.DictReader(open("ulsan_route_stops_20260407.csv",encoding="utf-8-sig")):
    seq_raw[r["rte_id"]].append((int(r["sttn_seq"]),r["sttn_id"]))
    rid2no[r["rte_id"]]=r.get("rte_no") or r["rte_id"]
route_pts={}; route_sidx={}
JUMP=5.0
for rid,lst in seq_raw.items():
    pts=[]; sidx={}; prev=None
    for s,sid in sorted(lst):
        cs=candidates(sid)
        if not cs: continue
        c=min(cs,key=lambda x:km(x,prev)) if prev else cs[0]
        if prev and km(c,prev)>JUMP: continue
        if sid not in sidx:
            sidx[sid]=len(pts); pts.append(c); prev=c
    route_pts[rid]=pts; route_sidx[rid]=sidx

# ---------- 카드 레코드 (01 + _etc 병합, 유형별) ----------
COLS=["rte_id","users_type_cd","ride_dt","ride_sttn_id","goff_dt","goff_sttn_id","utztn_nope","utztn_dstnc","brdg_hr","trnf_cnt"]
TYPES=["01","02","03","04","05","06"]; TIDX={t:i for i,t in enumerate(TYPES)}
_all=glob.glob("/sessions/jolly-gifted-albattani/mnt/uploads/card_records_20260407*.csv")
_f01=sorted([f for f in _all if not f.endswith("_etc.csv")],key=lambda f:os.path.getsize(f),reverse=True)[:1]
_fetc=[f for f in _all if f.endswith("_etc.csv")]
rows=[]
for _f in _f01+_fetc:
    _isetc=_f.endswith("_etc.csv")
    for r in csv.reader(open(_f,encoding="utf-8-sig")):
        if len(r)<10 or r[1]=="users_type_cd": continue
        if (r[1]=="01")==_isetc: continue
        rows.append(dict(zip(COLS,r)))
def hr(dt): return int(dt[8:10])%24 if len(dt)>=10 else 0

od=defaultdict(lambda:[0]*6); od_tr=defaultdict(int)        # OD 유형별 통행 + 환승합
seg_load=defaultdict(lambda:defaultdict(lambda:[0]*6))      # route -> seg -> 6유형
hour_t=[[0]*24 for _ in range(6)]; route_hour=defaultdict(lambda:[0]*24)  # 시간대 유형별 + 노선(전체)
stop_board=defaultdict(lambda:[0]*6)                         # 정류장 유형별 승차
for r in rows:
    ti=TIDX.get(r["users_type_cd"]);
    if ti is None: continue
    n=int(r["utztn_nope"] or 1); b=r["ride_sttn_id"]; g=r["goff_sttn_id"]; rid=r["rte_id"]
    tr=int(r["trnf_cnt"] or 0)
    h=hr(r["ride_dt"]); hour_t[ti][h]+=n; route_hour[rid][h]+=n
    stop_board[b][ti]+=n
    if g and b!=g:
        od[(b,g)][ti]+=n;
        if tr>0: od_tr[(b,g)]+=n
        si=route_sidx.get(rid,{}).get(b); ei=route_sidx.get(rid,{}).get(g)
        if si is not None and ei is not None and si!=ei:
            lo,hi=(si,ei) if si<ei else (ei,si)
            for k in range(lo,hi): seg_load[rid][k][ti]+=n
print(f"병합 행 {len(rows)}")

# ① 욕망선 상위 250(전체 통행 기준): [..coords.., t0..t5, trf]
od_lines=[]
for (b,g),t6 in sorted(od.items(),key=lambda x:-sum(x[1])):
    cb,cg=resolve(b),resolve(g)
    if not cb or not cg: continue
    od_lines.append([round(cb[0],5),round(cb[1],5),round(cg[0],5),round(cg[1],5)]+t6+[od_tr[(b,g)]])
    if len(od_lines)>=250: break

# ② 구간 라인: [..coords.., total, l0..l5]  (top_routes 호환 위해 total 먼저)
segs=[]
for rid,segd in seg_load.items():
    pts=route_pts.get(rid,[])
    for k,l6 in segd.items():
        if k+1<len(pts):
            a=pts[k]; b=pts[k+1]
            segs.append([round(a[0],5),round(a[1],5),round(b[0],5),round(b[1],5),sum(l6)]+l6)
segs.sort(key=lambda s:s[4])

# ③ 인구 격자 + 인접 정류장 승차(유형별): [lon,lat,pop, total, nb0..nb5]
cells=[]
for r in csv.DictReader(open("grid100_population.csv",encoding="utf-8-sig")):
    cells.append([round(float(r["lon"]),5),round(float(r["lat"]),5),int(r["pop"])])
GS=0.004
hashb=defaultdict(lambda:[0]*6)
for sid,b6 in stop_board.items():
    c=resolve(sid)
    if not c: continue
    hb=hashb[(round(c[0]/GS),round(c[1]/GS))]
    for i in range(6): hb[i]+=b6[i]
def near_board(lon,lat):
    gx,gy=round(lon/GS),round(lat/GS); s=[0]*6
    for dx in(-1,0,1):
        for dy in(-1,0,1):
            hb=hashb.get((gx+dx,gy+dy))
            if hb:
                for i in range(6): s[i]+=hb[i]
    return s
cell_out=[]
for lon,lat,pop in cells:
    nb=near_board(lon,lat); cell_out.append([lon,lat,pop,sum(nb)]+nb)

# ④ 노선별 첨두비(전체 기준)
route_peak=[]
for rid,hh in route_hour.items():
    tot=sum(hh)
    if tot<200: continue
    peak=max(sum(hh[i:i+3]) for i in range(22)); base=tot/24*3
    route_peak.append([rid2no.get(rid,rid),tot,round(peak/base,2) if base else 0])
route_peak.sort(key=lambda r:-r[1])
typ_tot=[sum(hour_t[i]) for i in range(6)]

data={"od":od_lines,"segs":segs[-1500:],"cells":cell_out,"hourT":hour_t,
      "routePeak":route_peak[:40],"typeTot":typ_tot}
json.dump(data,open("improve_data_20260407.json","w"),separators=(",",":"))
print(f"OD {len(od_lines)} / 구간 {len(segs)}(상위1500) / 격자 {len(cell_out)} / 유형별 {typ_tot}")
print("JSON MB:",round(os.path.getsize('improve_data_20260407.json')/1e6,2))

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 버스 노선 개선 분석 (2026-04-07)</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#070b16;color:#eaf0ff;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}#c{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.panel{position:absolute;z-index:10;background:#0d1530dd;backdrop-filter:blur(7px);border:1px solid #ffffff22;border-radius:13px;padding:12px 15px}
#title{left:16px;top:16px;max-width:400px}#title h1{margin:0 0 5px;font-size:15px}#title p{margin:3px 0;font-size:11.5px;color:#bcd0f5;line-height:1.5}
#tabs{right:16px;top:16px;display:flex;flex-direction:column;gap:6px}
#tabs button{background:#1a2647;color:#cfe0ff;border:1px solid #ffffff2a;border-radius:9px;padding:8px 13px;font-size:13px;cursor:pointer;text-align:left}
#tabs button.on{background:#3a6bd5;color:#fff;border-color:#5a8bff}
#utf{left:16px;top:110px;display:flex;flex-wrap:wrap;gap:5px;max-width:340px}
#utf button{background:#1a2647;color:#cfe0ff;border:1px solid #ffffff2a;border-radius:8px;padding:5px 9px;font-size:12px;cursor:pointer}
#utf button.on{background:#2aa17a;color:#fff;border-color:#46d5a5}
#utf button .n{opacity:.6;font-size:10px;margin-left:3px}
#leg{left:16px;bottom:16px;font-size:11.5px;max-width:330px;line-height:1.7}#leg i{display:inline-block;width:15px;height:9px;margin-right:6px;border-radius:2px;vertical-align:1px}
#p4{left:50%;top:52%;transform:translate(-50%,-50%);width:min(760px,92vw);max-height:80vh;overflow:auto;display:none}
#p4 h2{margin:2px 0 10px;font-size:15px}.barrow{display:flex;align-items:center;gap:8px;margin:2px 0;font-size:11px}
.bar{height:13px;background:#3a6bd5;border-radius:3px}table{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}
td,th{padding:3px 6px;border-bottom:1px solid #ffffff14;text-align:right}th{color:#9fb2dd}td:first-child,th:first-child{text-align:left}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:10.5px;margin-top:6px}
#themeBtn{position:absolute;z-index:30;top:34px;left:50%;transform:translateX(-50%);background:#0d1530cc;color:#eaf0ff;border:1px solid #ffffff33;border-radius:9px;padding:6px 12px;font-size:12.5px;cursor:pointer}body.light{background:#eef1f7}body.light .panel{background:#ffffffe0;border-color:#0000001f;color:#1b2640;box-shadow:0 2px 10px #00000014}body.light .panel *{color:#1b2640 !important}body.light #themeBtn{background:#ffffffe0;color:#1b2640;border-color:#0000002a}body.light #tabs button,body.light #utf button,body.light #bar button,body.light #list td,body.light select{background:#e9edf6}body.light #tabs button.on{background:#3a6bd5 !important}body.light #tabs button.on *{color:#fff !important}body.light #utf button.on{background:#2aa17a !important}body.light #utf button.on *{color:#fff !important}body.light #tabs button.on,body.light #utf button.on{color:#fff !important}.popgrad{display:inline-block;width:90px;height:9px;border-radius:3px;vertical-align:-1px;margin:0 5px;background:linear-gradient(90deg,#14283c,#3a96a0,#ebcd6e)}body.light .popgrad{background:linear-gradient(90deg,#dfeed8,#78b46e,#1c683a)}</style></head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1 id="ht">직통 신설 후보 (욕망선)</h1><p id="hp"></p>
<p>2026-04-07(화) · 교통카드 합성데이터(1차) · 개선분석은 참고용</p><span class="tag">실데이터 기반</span> <a href="ulsan_용어설명.html" target="_blank" style="display:inline-block;margin-top:6px;margin-left:6px;font-size:11px;color:#7fb4ff">ℹ 용어 설명</a></div>
<div class="panel" id="tabs">
 <button data-m="od" class="on">↔ 직통 신설 후보(욕망선)</button>
 <button data-m="seg">🚍 구간 혼잡(재차인원)</button>
 <button data-m="gap">⚠ 인구 대비 공급공백</button>
 <button data-m="peak">⏱ 시간대 수요·첨두</button></div>
<div class="panel" id="utf"></div>
<div class="panel" id="leg"></div>
<div class="panel" id="p4"></div></div>
<script>
const D=__DATA__,OD=D.od,SEG=D.segs,CELLS=D.cells;
const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
let mnLon=1e9,mxLon=-1e9,mnLat=1e9,mxLat=-1e9;
for(const cl of CELLS){mnLon=Math.min(mnLon,cl[0]);mxLon=Math.max(mxLon,cl[0]);mnLat=Math.min(mnLat,cl[1]);mxLat=Math.max(mxLat,cl[1]);}
const pad=54,latC=(mnLat+mxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(mxLon-mnLon)*kx,dH=(mxLat-mnLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
let Z=1,TX=0,TY=0;addEventListener('wheel',e=>{if(e.target.closest&&e.target.closest('.panel'))return;e.preventDefault();const cx=e.clientX,cy=e.clientY,f=e.deltaY<0?1.15:1/1.15,Zn=Math.min(25,Math.max(1,Z*f));TX=cx-(cx-TX)/Z*Zn;TY=cy-(cy-TY)/Z*Zn;Z=Zn;},{passive:false});let _dg=null;addEventListener('mousedown',e=>{if(e.target.closest&&e.target.closest('.panel'))return;_dg=[e.clientX,e.clientY,TX,TY];});addEventListener('mousemove',e=>{if(_dg){TX=_dg[2]+(e.clientX-_dg[0]);TY=_dg[3]+(e.clientY-_dg[1]);}});addEventListener('mouseup',()=>_dg=null);addEventListener('dblclick',e=>{if(e.target.closest&&e.target.closest('.panel'))return;Z=1;TX=0;TY=0;});const PX=lon=>(ox+(lon-mnLon)*kx*sc)*Z+TX, PY=lat=>(H-(oy+(lat-mnLat)*sc))*Z+TY;
const pmax=(()=>{const v=CELLS.map(c=>c[2]).sort((a,b)=>a-b);return v[Math.floor(v.length*.99)];})();
function PG(t,a){t=Math.min(1,Math.max(0,t));var A=[150,200,150],B=[46,150,70],C=[8,72,34],r,g,b;if(t<.55){var f=t/.55;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{var f=(t-.55)/.45;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}return 'rgba('+(r|0)+','+(g|0)+','+(b|0)+','+(a==null?1:a)+')';}
function pcol(v,a){let t=Math.min(1,Math.log(1+v)/Math.log(1+pmax));if(document.body.classList.contains('light'))return PG(t,a);return `rgba(${30+40*t|0},${50+90*t|0},${90+30*t|0},${a==null?1:a})`;}
// 이용자유형 필터  segs:[..4..,total,l0..l5] / od:[..4..,t0..t5,trf] / cells:[lon,lat,pop,total,nb0..nb5]
const UNAMES=['일반','어린이','청소년','경로','장애','국가유공'];
let utf=-1;
const segv=s=>{if(utf<0)return s[4];return s[5+utf];};
const odv=l=>{if(utf<0)return l[4]+l[5]+l[6]+l[7]+l[8]+l[9];return l[4+utf];};
const cnb=cl=>{if(utf<0)return cl[3];return cl[4+utf];};
function bmaxF(){let v=CELLS.map(cnb).sort((a,b)=>a-b);return v[Math.floor(v.length*.99)]||1;}
function heat(t){t=Math.min(1,t);const A=[40,60,120],B=[245,205,70],C=[235,55,40];let r,g,b;
 if(t<.5){const f=t/.5;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{const f=(t-.5)/.5;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}
 return `rgb(${r|0},${g|0},${b|0})`;}
let mode='od';
const tt={od:['직통 신설 후보 (욕망선)','실제 OD 흐름(상위 250). 굵을수록 통행 많음, 붉을수록 환승 비율↑ → 직통 신설/연장 후보. (환승기록 5%로 보조지표)'],
 seg:['구간 혼잡 (재차인원)','노선 구간별 동시 탑승 인원. 붉고 굵을수록 혼잡 → 증차 후보, 가늘면 공차 → 단축 검토.'],
 gap:['인구 대비 공급공백','배경=인구밀도. 빨강=인구는 많은데 인근 정류장 승차가 적은 과소공급 지역(노선·정류장 보강 후보).'],
 peak:['시간대 수요·첨두','시간대별 총 승차와 노선별 첨두비(첨두3시간/평균). 첨두비 높은 노선=증감차/급행 후보.']};
document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{mode=b.dataset.m;
 document.querySelectorAll('#tabs button').forEach(z=>z.classList.toggle('on',z===b));
 document.getElementById('ht').textContent=tt[mode][0];document.getElementById('hp').textContent=tt[mode][1];
 document.getElementById('p4').style.display=mode==='peak'?'block':'none';
 document.getElementById('leg').style.display=mode==='peak'?'none':'block';buildLeg();if(mode==='peak')buildP4();});
function buildLeg(){let h='';
 if(mode==='od')h='<b>욕망선(통행 흐름)</b><br>굵기=통행량 · 색=환승비율<br><i style="background:#5a8bff"></i>환승 적음 &nbsp;<i style="background:#e8503a"></i>환승 많음(직통 부재)';
 else if(mode==='seg')h='<b>구간 재차인원</b><br><i style="background:'+heat(.15)+'"></i>한산 &nbsp;<i style="background:'+heat(.6)+'"></i>보통 &nbsp;<i style="background:'+heat(1)+'"></i>혼잡';
 else if(mode==='gap')h='<b>공급공백 점수</b><br><i style="background:rgb(235,60,45)"></i>과소공급(인구↑·승차↓)<br><i style="background:rgb(60,150,90)"></i>충분 &nbsp;<i style="background:'+pcol(pmax*.6)+'"></i>인구';
 document.getElementById('leg').innerHTML=h;}
function hourArr(){const a=new Array(24).fill(0);for(let i=0;i<6;i++){if(utf>=0&&i!==utf)continue;for(let h=0;h<24;h++)a[h]+=D.hourT[i][h];}return a;}
function buildP4(){const el=document.getElementById('p4');const HA=hourArr();const mx=Math.max(1,...HA);
 let h=`<h2>시간대별 총 승차 ${utf<0?'(전체)':'('+UNAMES[utf]+')'}</h2>`;
 HA.forEach((v,i)=>{h+=`<div class="barrow"><span style="width:30px">${String(i).padStart(2,'0')}시</span><div class="bar" style="width:${Math.round(v/mx*440)}px;background:${i>=7&&i<=9||i>=16&&i<=18?'#ffd54f':'#3a6bd5'}"></div><span>${v.toLocaleString()}</span></div>`;});
 h+='<h2 style="margin-top:14px">노선별 첨두비 상위(첨두3시간 ÷ 평균)</h2><table><tr><th>노선</th><th>일승차</th><th>첨두비</th></tr>';
 D.routePeak.slice().sort((a,b)=>b[2]-a[2]).slice(0,15).forEach(r=>{h+=`<tr><td>${r[0]}</td><td>${r[1].toLocaleString()}</td><td>${r[2].toFixed(2)}×</td></tr>`;});
 h+='</table><p style="font-size:11px;opacity:.7;margin-top:8px">첨두비 높을수록 출퇴근 집중 → 첨두 증차/급행, 비첨두 감차 후보</p>';el.innerHTML=h;}
// 이용자유형 필터 버튼
(()=>{let h=`<button data-u="-1" class="on">전체</button>`;
 UNAMES.forEach((nm,i)=>{if((D.typeTot[i]||0)>0)h+=`<button data-u="${i}">${nm}<span class="n">${D.typeTot[i].toLocaleString()}</span></button>`;});
 const el=document.getElementById('utf');el.innerHTML=h;
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>{utf=+b.dataset.u;el.querySelectorAll('button').forEach(z=>z.classList.toggle('on',z===b));if(mode==='peak')buildP4();});})();
document.getElementById('hp').textContent=tt.od[1];buildLeg();
function frame(){fit();x.fillStyle=(document.body.classList.contains('light')?'#e9edf4':'#070b16');x.fillRect(0,0,W,H);
 if(mode==='gap'){const px=Math.max(2,(100/111000*sc)*1.5*Z);
  for(const cl of CELLS){x.fillStyle=pcol(cl[2],0.5);x.fillRect(PX(cl[0])-px/2,PY(cl[1])-px/2,px,px);}
  // 공백 점수 = 인구순위 - 승차순위 (양수=과소공급)
  const bmax=bmaxF();
  for(const cl of CELLS){const pn=Math.min(1,Math.log(1+cl[2])/Math.log(1+pmax)),bn=Math.min(1,Math.log(1+cnb(cl))/Math.log(1+bmax));
   const gap=pn-bn;if(cl[2]<30)continue;const r=Math.max(1.6,px*0.7);
   if(gap>0.15)x.fillStyle=`rgba(235,60,45,${0.25+0.6*Math.min(1,gap)})`;
   else if(gap<-0.15)x.fillStyle=`rgba(60,150,90,${0.18+0.4*Math.min(1,-gap)})`;else continue;
   x.beginPath();x.arc(PX(cl[0]),PY(cl[1]),r,0,7);x.fill();}}
 else {const px=Math.max(2,(100/111000*sc)*1.5*Z);for(const cl of CELLS){x.fillStyle=pcol(cl[2],0.13);x.fillRect(PX(cl[0])-px/2,PY(cl[1])-px/2,px,px);}}
 if(mode==='seg'){let mx=1;for(const s of SEG)mx=Math.max(mx,segv(s));
  for(const s of SEG){const v=segv(s);if(v<=0)continue;const t=v/mx;x.strokeStyle=heat(Math.sqrt(t));x.lineWidth=Math.min(7,0.6+Math.sqrt(v)*0.5);
   x.beginPath();x.moveTo(PX(s[0]),PY(s[1]));x.lineTo(PX(s[2]),PY(s[3]));x.stroke();}}
 else if(mode==='od'){let mx=1;for(const l of OD)mx=Math.max(mx,odv(l));
  for(const l of OD){const v=odv(l);if(v<=0)continue;const a=[PX(l[0]),PY(l[1])],b=[PX(l[2]),PY(l[3])],t=v/mx,trf=Math.min(1,l[10]/v);
   const midx=(a[0]+b[0])/2,midy=(a[1]+b[1])/2-Math.hypot(b[0]-a[0],b[1]-a[1])*0.16;
   const col=`rgba(${90+165*trf|0},${139-90*trf|0},${255-200*trf|0},${0.22+0.5*t})`;
   x.strokeStyle=col;x.lineWidth=Math.min(7,0.5+t*8);x.beginPath();x.moveTo(a[0],a[1]);x.quadraticCurveTo(midx,midy,b[0],b[1]);x.stroke();}
  x.fillStyle='#ffffffcc';for(const l of OD){if(odv(l)<=0)continue;x.beginPath();x.arc(PX(l[0]),PY(l[1]),1.2,0,7);x.fill();}}
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
;(function(){var b=document.createElement('button');b.id='themeBtn';b.textContent='☀ 라이트';(document.getElementById('wrap')||document.body).appendChild(b);b.onclick=function(){document.body.classList.toggle('light');b.textContent=document.body.classList.contains('light')?'🌙 다크':'☀ 라이트';};})();;(function(){var t=document.getElementById('title');if(!t)return;var d=document.createElement('div');d.style.cssText='margin-top:7px;font-size:11px;opacity:.85';d.innerHTML='배경=인구밀도 낮음<span class="popgrad"></span>높음';t.appendChild(d);})();</script></body></html>"""
out=HTML.replace("__DATA__",json.dumps(data,separators=(",",":")))
open("ulsan_route_improvement.html","w",encoding="utf-8").write(out)
print("HTML MB:",round(len(out)/1e6,2))
