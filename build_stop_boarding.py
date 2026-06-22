"""노선 선택 → 그 노선에서 탑승이 많은 정류장 표시(크기·색) + 순위 목록
출력: ulsan_stop_boarding.html
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
def despike(items):
    """갔다가 되돌아오는 비정상 우회 정류장(좌표 오매칭) 제거. items=[lon,lat,...]"""
    out=[list(p) for p in items]; changed=True
    while changed and len(out)>=3:
        changed=False
        for i in range(1,len(out)-1):
            a,c,b=out[i-1],out[i],out[i+1]
            dac=km(a,c); dcb=km(c,b); dab=km(a,b)
            if dac>2.0 and dcb>2.0 and (dac+dcb)>dab*2.5+0.5:
                del out[i]; changed=True; break
    return out
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
# 노선·정류장별 승차
COLS=["rte_id","users_type_cd","ride_dt","ride_sttn_id","goff_dt","goff_sttn_id","utztn_nope","utztn_dstnc","brdg_hr","trnf_cnt"]
_all=glob.glob("/sessions/jolly-gifted-albattani/mnt/uploads/card_records_20260407*.csv")
_f01=sorted([f for f in _all if not f.endswith("_etc.csv")],key=lambda f:os.path.getsize(f),reverse=True)[:1]
_fetc=[f for f in _all if f.endswith("_etc.csv")]
board=defaultdict(int); tot=defaultdict(int)
for _f in _f01+_fetc:
    _isetc=_f.endswith("_etc.csv")
    for x in csv.reader(open(_f,encoding="utf-8-sig")):
        if len(x)<10 or x[1]=="users_type_cd": continue
        if (x[1]=="01")==_isetc: continue
        r=dict(zip(COLS,x)); n=int(r["utztn_nope"] or 1)
        board[(r["rte_id"],r["ride_sttn_id"])]+=n; tot[r["rte_id"]]+=n
# 노선 구성(일승차 300+), 정류장 순서대로 좌표·승차·이름
routes=[]
for rid in sorted(tot,key=tot.get,reverse=True):
    if tot[rid]<300: continue
    stops=[]; prev=None
    for s,sid in sorted(seq.get(rid,[])):
        cs=cands(sid)
        if not cs: continue
        c=min(cs,key=lambda x:km(x,prev)) if prev else cs[0]
        if prev and km(c,prev)>5.0: continue
        nm=(bs.get(sid) or "").strip()
        stops.append([round(c[0],5),round(c[1],5),board.get((rid,sid),0),nm]); prev=c
    stops=despike(stops)
    if len(stops)>=2:
        routes.append({"no":rid2no.get(rid,rid),"tot":tot[rid],"stops":stops})
cells=[]
for r in csv.DictReader(open("grid100_population.csv",encoding="utf-8-sig")):
    cells.append([round(float(r["lon"]),5),round(float(r["lat"]),5),int(r["pop"])])
data={"routes":routes,"cells":cells}
print("노선",len(routes),"/ 격자",len(cells))

HTML=r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>노선별 탑승 많은 정류장</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#070b16;color:#eaf0ff;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}#c{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.panel{position:absolute;z-index:10;background:#0d1530e0;backdrop-filter:blur(7px);border:1px solid #ffffff22;border-radius:13px;padding:12px 15px}
#title{left:16px;top:16px;max-width:380px}#title h1{margin:0 0 6px;font-size:15px}#title p{margin:3px 0;font-size:11.5px;color:#bcd0f5;line-height:1.5}
#title select{margin-top:7px;background:#1a2647;color:#fff;border:1px solid #ffffff33;border-radius:8px;padding:6px 10px;font-size:14px;width:100%}
#list{right:16px;top:16px;font-size:12px;max-height:90vh;overflow:auto;min-width:200px}
#list h3{margin:0 0 6px;font-size:13px}#list table{border-collapse:collapse;width:100%}
#list td{padding:3px 7px;border-bottom:1px solid #ffffff12}#list td:last-child{text-align:right;color:#ffd54f;font-weight:600}
#list tr.hd td{color:#9fb2dd;font-weight:600}
#leg{left:16px;bottom:16px;font-size:11.5px;line-height:1.7}#leg .g{display:inline-block;width:130px;height:11px;border-radius:3px;vertical-align:-1px;background:linear-gradient(90deg,#3a4a78,#ffd54f,#ff8c1e,#e8503a)}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:10.5px;margin-top:6px}#themeBtn{position:absolute;z-index:30;top:34px;left:50%;transform:translateX(-50%);background:#0d1530cc;color:#eaf0ff;border:1px solid #ffffff33;border-radius:9px;padding:6px 12px;font-size:12.5px;cursor:pointer}body.light{background:#eef1f7}body.light .panel{background:#ffffffe0;border-color:#0000001f;color:#1b2640;box-shadow:0 2px 10px #00000014}body.light .panel *{color:#1b2640 !important}body.light #themeBtn{background:#ffffffe0;color:#1b2640;border-color:#0000002a}body.light #tabs button,body.light #utf button,body.light #bar button,body.light #list td,body.light select{background:#e9edf6}body.light #tabs button.on{background:#3a6bd5 !important}body.light #tabs button.on *{color:#fff !important}body.light #utf button.on{background:#2aa17a !important}body.light #utf button.on *{color:#fff !important}body.light #tabs button.on,body.light #utf button.on{color:#fff !important}.popgrad{display:inline-block;width:90px;height:9px;border-radius:3px;vertical-align:-1px;margin:0 5px;background:linear-gradient(90deg,#14283c,#3a96a0,#ebcd6e)}body.light .popgrad{background:linear-gradient(90deg,#dfeed8,#78b46e,#1c683a)}</style>
</head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>노선별 탑승 많은 정류장</h1>
<p>원 크기·색 = 그 정류장 승차 인원 · 선 = 노선 경로 · 2026-04-07</p>
<select id="sel"></select><span class="tag" style="display:block">실데이터</span> <a href="ulsan_용어설명.html" target="_blank" style="display:inline-block;margin-top:6px;margin-left:6px;font-size:11px;color:#7fb4ff">ℹ 용어 설명</a></div>
<div class="panel" id="list"></div>
<div class="panel" id="leg"><b>정류장 승차 인원</b><br><span style="opacity:.6">적음</span> <span class="g"></span> <span>많음</span></div></div>
<script>
const D=__DATA__,RTS=D.routes,CELLS=D.cells;
const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
const kx=Math.cos(35.55*Math.PI/180),pad=70;
// 전체 격자 경계(인구배경 항상 동일 영역)
let gmnLon=1e9,gmxLon=-1e9,gmnLat=1e9,gmxLat=-1e9;
for(const cl of CELLS){gmnLon=Math.min(gmnLon,cl[0]);gmxLon=Math.max(gmxLon,cl[0]);gmnLat=Math.min(gmnLat,cl[1]);gmxLat=Math.max(gmxLat,cl[1]);}
let B={mnLon:gmnLon,mxLon:gmxLon,mnLat:gmnLat,mxLat:gmxLat},sc,ox,oy;
function fit(){const dW=(B.mxLon-B.mnLon)*kx,dH=(B.mxLat-B.mnLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
let Z=1,TX=0,TY=0;addEventListener('wheel',e=>{if(e.target.closest&&e.target.closest('.panel'))return;e.preventDefault();const cx=e.clientX,cy=e.clientY,f=e.deltaY<0?1.15:1/1.15,Zn=Math.min(25,Math.max(1,Z*f));TX=cx-(cx-TX)/Z*Zn;TY=cy-(cy-TY)/Z*Zn;Z=Zn;},{passive:false});let _dg=null;addEventListener('mousedown',e=>{if(e.target.closest&&e.target.closest('.panel'))return;_dg=[e.clientX,e.clientY,TX,TY];});addEventListener('mousemove',e=>{if(_dg){TX=_dg[2]+(e.clientX-_dg[0]);TY=_dg[3]+(e.clientY-_dg[1]);}});addEventListener('mouseup',()=>_dg=null);addEventListener('dblclick',e=>{if(e.target.closest&&e.target.closest('.panel'))return;Z=1;TX=0;TY=0;});const PX=lon=>(ox+(lon-B.mnLon)*kx*sc)*Z+TX, PY=lat=>(H-(oy+(lat-B.mnLat)*sc))*Z+TY;
const pmax=(()=>{const v=CELLS.map(c=>c[2]).sort((a,b)=>a-b);return v[Math.floor(v.length*.99)];})();
function PG(t,a){t=Math.min(1,Math.max(0,t));var A=[150,200,150],B=[46,150,70],C=[8,72,34],r,g,b;if(t<.55){var f=t/.55;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{var f=(t-.55)/.45;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}return 'rgba('+(r|0)+','+(g|0)+','+(b|0)+','+(a==null?1:a)+')';}
function pcol(v){let t=Math.min(1,Math.log(1+v)/Math.log(1+pmax));if(document.body.classList.contains('light'))return PG(t);return `rgb(${14+22*t|0},${28+55*t|0},${52+30*t|0})`;}
function scol(t){t=Math.min(1,t);const A=[58,74,120],B=[255,213,79],C=[232,80,58];let r,g,b;
 if(t<.5){const f=t/.5;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{const f=(t-.5)/.5;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}
 return `rgb(${r|0},${g|0},${b|0})`;}
let cur=0;
const sel=document.getElementById('sel');
sel.innerHTML=RTS.map((r,i)=>`<option value="${i}">${r.no} — 일승차 ${r.tot.toLocaleString()}명</option>`).join('');
sel.onchange=()=>{cur=+sel.value;setBounds();buildList();};
function setBounds(){const st=RTS[cur].stops;let a=1e9,b=-1e9,cc=1e9,d=-1e9;
 for(const s of st){a=Math.min(a,s[0]);b=Math.max(b,s[0]);cc=Math.min(cc,s[1]);d=Math.max(d,s[1]);}
 const mx=(b-a)*0.12+0.002,my=(d-cc)*0.12+0.002;B={mnLon:a-mx,mxLon:b+mx,mnLat:cc-my,mxLat:d+my};}
function buildList(){const st=RTS[cur].stops.slice().map((s,i)=>s).sort((p,q)=>q[2]-p[2]).slice(0,12);
 let h=`<h3>${RTS[cur].no} 승차 상위 정류장</h3><table><tr class="hd"><td>정류장</td><td>승차</td></tr>`;
 st.forEach(s=>h+=`<tr><td>${s[3]||'-'}</td><td>${s[2].toLocaleString()}</td></tr>`);
 h+='</table>';document.getElementById('list').innerHTML=h;}
setBounds();buildList();
function frame(){fit();x.fillStyle=(document.body.classList.contains('light')?'#e9edf4':'#070b16');x.fillRect(0,0,W,H);
 const px=Math.max(2,(100/111000*sc)*1.5*Z);
 for(const cl of CELLS){x.fillStyle=pcol(cl[2]);x.fillRect(PX(cl[0])-px/2,PY(cl[1])-px/2,px,px);}
 const st=RTS[cur].stops;let mx=1;for(const s of st)mx=Math.max(mx,s[2]);
 // 경로선
 x.strokeStyle='rgba(120,160,235,.55)';x.lineWidth=2;x.beginPath();
 st.forEach((s,j)=>{const X=PX(s[0]),Y=PY(s[1]);j?x.lineTo(X,Y):x.moveTo(X,Y);});x.stroke();
 // 정류장 원(승차 인원)
 for(const s of st){const t=s[2]/mx,r=2+Math.sqrt(s[2])*1.1;
  x.fillStyle=scol(t);x.globalAlpha=s[2]?0.9:0.5;x.beginPath();x.arc(PX(s[0]),PY(s[1]),s[2]?r:2,0,7);x.fill();}
 x.globalAlpha=1;
 // 상위 3개 이름 라벨
 const top=st.map((s,i)=>s).sort((a,b)=>b[2]-a[2]).slice(0,3);
 x.fillStyle='#fff';x.font='bold 12px sans-serif';
 for(const s of top){if(!s[2])continue;x.fillText(s[3]||'',PX(s[0])+8,PY(s[1])-6);}
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
;(function(){var b=document.createElement('button');b.id='themeBtn';b.textContent='☀ 라이트';(document.getElementById('wrap')||document.body).appendChild(b);b.onclick=function(){document.body.classList.toggle('light');b.textContent=document.body.classList.contains('light')?'🌙 다크':'☀ 라이트';};})();;(function(){var t=document.getElementById('title');if(!t)return;var d=document.createElement('div');d.style.cssText='margin-top:7px;font-size:11px;opacity:.85';d.innerHTML='배경=인구밀도 낮음<span class="popgrad"></span>높음';t.appendChild(d);})();</script></body></html>"""
open("ulsan_stop_boarding.html","w",encoding="utf-8").write(HTML.replace("__DATA__",json.dumps(data,separators=(",",":"),ensure_ascii=False))
)
print("HTML MB:",round(os.path.getsize('ulsan_stop_boarding.html')/1e6,2))
