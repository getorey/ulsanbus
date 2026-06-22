"""이용량(구간 재차인원)을 단색 진하기로 표현 + 인구밀도 배경 + 우측 노선목록(호버 시 경로 강조)
입력: improve_data_20260407.json(segs,cells), 정류장 좌표원, ulsan_route_stops, card_records
출력: ulsan_top_routes.html
"""
import csv, re, glob, math, json, os
from collections import defaultdict
# ---- 좌표 해석기(candidates+nearest) ----
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
n2l=defaultdict(list); c2l=defaultdict(list)
def add(nm,c): n2l[norm(nm)].append(c); c2l[norm_core(nm)].append(c)
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
def cands(sid):
    if sid in xw: return [xw[sid]]
    nm=bs.get(sid)
    if not nm: return []
    if norm(nm) in n2l: return n2l[norm(nm)]
    if norm_core(nm) in c2l: return c2l[norm_core(nm)]
    return []
seq=defaultdict(list); rid2no={}
for r in csv.DictReader(open("ulsan_route_stops_20260407.csv",encoding="utf-8-sig")):
    seq[r["rte_id"]].append((int(r["sttn_seq"]),r["sttn_id"])); rid2no[r["rte_id"]]=r.get("rte_no") or r["rte_id"]
def despike(pts):
    """갔다가 되돌아오는 비정상 우회점(좌표 오매칭) 제거"""
    out=[list(p) for p in pts]
    changed=True
    while changed and len(out)>=3:
        changed=False
        for i in range(1,len(out)-1):
            a,c,b=out[i-1],out[i],out[i+1]
            dac=km(a,c); dcb=km(c,b); dab=km(a,b)
            if dac>2.0 and dcb>2.0 and (dac+dcb)>dab*2.5+0.5:
                del out[i]; changed=True; break
    return out
def poly(rid):
    raw=[]; prev=None
    for s,sid in sorted(seq.get(rid,[])):
        cs=cands(sid)
        if not cs: continue
        c=min(cs,key=lambda x:km(x,prev)) if prev else cs[0]
        if prev and km(c,prev)>5.0: continue
        raw.append((c[0],c[1])); prev=c
    return [[round(p[0],5),round(p[1],5)] for p in despike(raw)]
# ---- 노선별 총승차 + 시간대(첨두비) ----
COLS=["rte_id","users_type_cd","ride_dt","ride_sttn_id","goff_dt","goff_sttn_id","utztn_nope","utztn_dstnc","brdg_hr","trnf_cnt"]
_all=glob.glob("/sessions/jolly-gifted-albattani/mnt/uploads/card_records_20260407*.csv")
_f01=sorted([f for f in _all if not f.endswith("_etc.csv")],key=lambda f:os.path.getsize(f),reverse=True)[:1]
_fetc=[f for f in _all if f.endswith("_etc.csv")]
tot=defaultdict(int); rhour=defaultdict(lambda:[0]*24)
for _f in _f01+_fetc:
    _isetc=_f.endswith("_etc.csv")
    for x in csv.reader(open(_f,encoding="utf-8-sig")):
        if len(x)<10 or x[1]=="users_type_cd": continue
        if (x[1]=="01")==_isetc: continue
        r=dict(zip(COLS,x)); n=int(r["utztn_nope"] or 1); tot[r["rte_id"]]+=n
        if len(r["ride_dt"])>=10: rhour[r["rte_id"]][int(r["ride_dt"][8:10])%24]+=n
def peak(rid):
    hh=rhour[rid]; t=sum(hh)
    if not t: return 0
    pk=max(sum(hh[i:i+3]) for i in range(22)); base=t/24*3
    return round(pk/base,1) if base else 0
TOPN=25
top=sorted(tot,key=tot.get,reverse=True)[:TOPN]
routes=[{"no":rid2no.get(rid,rid),"tot":tot[rid],"peak":peak(rid),"pts":poly(rid)} for rid in top]
routes=[r for r in routes if len(r["pts"])>=2]
# ---- 배경/구간 ----
d=json.load(open("improve_data_20260407.json"))
segs=d["segs"]; cells=[[c[0],c[1],c[2]] for c in d["cells"]]
data={"segs":segs,"cells":cells,"routes":routes}
print("노선목록",len(routes),"/ 구간",len(segs),"/ 격자",len(cells))

HTML=r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 버스 이용량 + 노선목록</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#070b16;color:#eaf0ff;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}#c{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.panel{position:absolute;z-index:10;background:#0d1530dd;backdrop-filter:blur(7px);border:1px solid #ffffff22;border-radius:13px;padding:12px 15px}
#title{left:16px;top:16px;max-width:380px}#title h1{margin:0 0 5px;font-size:15px}#title p{margin:3px 0;font-size:11.5px;color:#bcd0f5;line-height:1.5}
#leg{left:16px;bottom:16px;font-size:11.5px;line-height:1.7}
#leg .g{display:inline-block;width:150px;height:11px;border-radius:3px;vertical-align:-1px;
 background:linear-gradient(90deg,#ffee64,#ff8c1e,#d62819,#780c0c)}
#list{right:16px;top:16px;font-size:12px;max-height:90vh;overflow:auto;min-width:160px}
#list h3{margin:0 0 6px;font-size:13px}#list table{border-collapse:collapse;width:100%}
#list td{padding:3px 7px;border-bottom:1px solid #ffffff12;cursor:pointer}
#list tr.hd td{cursor:default;color:#9fb2dd;font-weight:600}
#list td:first-child{font-weight:600}#list td:nth-child(2),#list td:nth-child(3){text-align:right;color:#cfe0ff}
#list tr.on td{background:#3a6bd5;color:#fff}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:10.5px;margin-top:6px}#themeBtn{position:absolute;z-index:30;top:34px;left:50%;transform:translateX(-50%);background:#0d1530cc;color:#eaf0ff;border:1px solid #ffffff33;border-radius:9px;padding:6px 12px;font-size:12.5px;cursor:pointer}body.light{background:#eef1f7}body.light .panel{background:#ffffffe0;border-color:#0000001f;color:#1b2640;box-shadow:0 2px 10px #00000014}body.light .panel *{color:#1b2640 !important}body.light #themeBtn{background:#ffffffe0;color:#1b2640;border-color:#0000002a}body.light #tabs button,body.light #utf button,body.light #bar button,body.light #list td,body.light select{background:#e9edf6}body.light #tabs button.on{background:#3a6bd5 !important}body.light #tabs button.on *{color:#fff !important}body.light #utf button.on{background:#2aa17a !important}body.light #utf button.on *{color:#fff !important}body.light #tabs button.on,body.light #utf button.on{color:#fff !important}.popgrad{display:inline-block;width:90px;height:9px;border-radius:3px;vertical-align:-1px;margin:0 5px;background:linear-gradient(90deg,#14283c,#3a96a0,#ebcd6e)}body.light .popgrad{background:linear-gradient(90deg,#dfeed8,#78b46e,#1c683a)}</style>
</head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>버스 이용량(구간 재차인원) + 노선목록</h1>
<p>색 진하기·굵기=구간 동시 탑승 인원 · 배경=인구밀도 · <b>우측 노선에 마우스 올리면 경로 강조</b></p>
<span class="tag">실데이터 · 2026-04-07</span> <a href="ulsan_용어설명.html" target="_blank" style="display:inline-block;margin-top:6px;margin-left:6px;font-size:11px;color:#7fb4ff">ℹ 용어 설명</a></div>
<div class="panel" id="leg"><b>구간 이용량</b><br><span style="opacity:.6">적음</span> <span class="g"></span> <span>많음</span><br>
<span style="opacity:.55">노랑(적음)→주황→붉음→검붉음(많음) · 배경=인구밀도(청록)</span></div>
<div class="panel" id="list"></div></div>
<script>
const D=__DATA__,SEG=D.segs,CELLS=D.cells,RTS=D.routes;
const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
let mnLon=1e9,mxLon=-1e9,mnLat=1e9,mxLat=-1e9;
for(const cl of CELLS){mnLon=Math.min(mnLon,cl[0]);mxLon=Math.max(mxLon,cl[0]);mnLat=Math.min(mnLat,cl[1]);mxLat=Math.max(mxLat,cl[1]);}
const pad=54,latC=(mnLat+mxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(mxLon-mnLon)*kx,dH=(mxLat-mnLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
let Z=1,TX=0,TY=0;addEventListener('wheel',e=>{if(e.target.closest&&e.target.closest('.panel'))return;e.preventDefault();const cx=e.clientX,cy=e.clientY,f=e.deltaY<0?1.15:1/1.15,Zn=Math.min(25,Math.max(1,Z*f));TX=cx-(cx-TX)/Z*Zn;TY=cy-(cy-TY)/Z*Zn;Z=Zn;},{passive:false});let _dg=null;addEventListener('mousedown',e=>{if(e.target.closest&&e.target.closest('.panel'))return;_dg=[e.clientX,e.clientY,TX,TY];});addEventListener('mousemove',e=>{if(_dg){TX=_dg[2]+(e.clientX-_dg[0]);TY=_dg[3]+(e.clientY-_dg[1]);}});addEventListener('mouseup',()=>_dg=null);addEventListener('dblclick',e=>{if(e.target.closest&&e.target.closest('.panel'))return;Z=1;TX=0;TY=0;});const PX=lon=>(ox+(lon-mnLon)*kx*sc)*Z+TX, PY=lat=>(H-(oy+(lat-mnLat)*sc))*Z+TY;
const pmax=(()=>{const v=CELLS.map(c=>c[2]).sort((a,b)=>a-b);return v[Math.floor(v.length*.99)];})();
function PG(t,a){t=Math.min(1,Math.max(0,t));var A=[150,200,150],B=[46,150,70],C=[8,72,34],r,g,b;if(t<.55){var f=t/.55;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{var f=(t-.55)/.45;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}return 'rgba('+(r|0)+','+(g|0)+','+(b|0)+','+(a==null?1:a)+')';}
function pcol(v){let t=Math.min(1,Math.log(1+v)/Math.log(1+pmax));if(document.body.classList.contains('light'))return PG(t);return `rgb(${16+34*t|0},${34+80*t|0},${66+34*t|0})`;}
const lmax=(()=>{const v=SEG.map(s=>s[4]).sort((a,b)=>a-b);return v[Math.floor(v.length*.97)]||1;})();
const RAMP=[[0,[255,238,100]],[0.35,[255,140,30]],[0.7,[214,40,25]],[1,[120,12,12]]];
function rcol(t){t=Math.min(1,Math.max(0,t));for(let i=1;i<RAMP.length;i++){if(t<=RAMP[i][0]){
 const a=RAMP[i-1],b=RAMP[i],f=(t-a[0])/(b[0]-a[0]);
 return [a[1][0]+(b[1][0]-a[1][0])*f|0,a[1][1]+(b[1][1]-a[1][1])*f|0,a[1][2]+(b[1][2]-a[1][2])*f|0];}}return [120,12,12];}
SEG.sort((a,b)=>a[4]-b[4]);
let hover=-1;
// 노선 목록
(()=>{let h='<h3>일승차 상위 노선</h3><table><tr class="hd"><td>노선</td><td>일승차</td><td>첨두</td></tr>';
 RTS.forEach((r,i)=>h+=`<tr data-i="${i}"><td>${r.no}</td><td>${r.tot.toLocaleString()}</td><td>${r.peak.toFixed(1)}×</td></tr>`);
 h+='</table>';const el=document.getElementById('list');el.innerHTML=h;
 el.querySelectorAll('tr[data-i]').forEach(tr=>{
  tr.onmouseenter=()=>{hover=+tr.dataset.i;el.querySelectorAll('tr[data-i]').forEach(z=>z.classList.toggle('on',z===tr));};
 });
 el.onmouseleave=()=>{hover=-1;el.querySelectorAll('tr[data-i]').forEach(z=>z.classList.remove('on'));};})();
function frame(){fit();x.fillStyle=(document.body.classList.contains('light')?'#e9edf4':'#070b16');x.fillRect(0,0,W,H);
 const px=Math.max(2,(100/111000*sc)*1.5*Z);
 for(const cl of CELLS){x.fillStyle=pcol(cl[2]);x.fillRect(PX(cl[0])-px/2,PY(cl[1])-px/2,px,px);}
 x.lineCap='round';
 for(const s of SEG){const t=Math.min(1,s[4]/lmax),col=rcol(t);
  x.strokeStyle=`rgba(${col[0]},${col[1]},${col[2]},${(0.7+0.3*t).toFixed(3)})`;
  x.lineWidth=0.4+Math.sqrt(s[4])*0.16;
  x.beginPath();x.moveTo(PX(s[0]),PY(s[1]));x.lineTo(PX(s[2]),PY(s[3]));x.stroke();}
 // 호버 노선 경로 강조
 if(hover>=0&&RTS[hover]){const r=RTS[hover];
  x.strokeStyle='rgba(255,255,255,.95)';x.lineWidth=4.5;x.shadowColor='#5aacff';x.shadowBlur=10;
  x.beginPath();r.pts.forEach((p,j)=>{const X=PX(p[0]),Y=PY(p[1]);j?x.lineTo(X,Y):x.moveTo(X,Y);});x.stroke();
  x.shadowBlur=0;x.strokeStyle='#2e7bff';x.lineWidth=2;x.stroke();
  // 기·종점 표시
  const a=r.pts[0],b=r.pts[r.pts.length-1];x.fillStyle='#fff';
  for(const p of [a,b]){x.beginPath();x.arc(PX(p[0]),PY(p[1]),4,0,7);x.fill();}}
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
;(function(){var b=document.createElement('button');b.id='themeBtn';b.textContent='☀ 라이트';(document.getElementById('wrap')||document.body).appendChild(b);b.onclick=function(){document.body.classList.toggle('light');b.textContent=document.body.classList.contains('light')?'🌙 다크':'☀ 라이트';};})();;(function(){var t=document.getElementById('title');if(!t)return;var d=document.createElement('div');d.style.cssText='margin-top:7px;font-size:11px;opacity:.85';d.innerHTML='배경=인구밀도 낮음<span class="popgrad"></span>높음';t.appendChild(d);})();</script></body></html>"""
open("ulsan_top_routes.html","w",encoding="utf-8").write(HTML.replace("__DATA__",json.dumps(data,separators=(",",":"))))
print("HTML MB:",round(os.path.getsize('ulsan_top_routes.html')/1e6,2))
