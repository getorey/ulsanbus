"""울산 버스 주야 흐름 시각화 (설계서 반영)
- 시간 구동 테마: 밤=짙은 남색+불빛, 낮=흰 바탕+검정 명암, 여명/낙조 1시간 페이드
- 승객 마크 = 색 사각형, 면적 = 정류장 승차 인원(√로 한 변)
- 자동/낮 고정/밤 고정 + 이용자유형 필터 + 휠 확대
입력: card_trips_20260407.json (build_time_anim 산출 재사용)
출력: ulsan_daynight_flow.html
"""
import json, os, csv, re
from collections import defaultdict
d = json.load(open("card_trips_20260407.json"))
try:
    d["cong"] = json.load(open("route_congestion_20260407.json"))
except FileNotFoundError:
    d["cong"] = {}
try:
    d["abol"] = json.load(open("abolished_routes.json"))
except FileNotFoundError:
    d["abol"] = []

# ---------- 만차(혼잡) 데이터: 노선별 차내 재차 ÷ 정원(유형별) ----------
def _norm(s): s=(s or "").split("(")[0]; return re.sub(r"[ .()\-·,]","",s)
def _ncore(s):
    s=_norm(s)
    for suf in ("정류소","정류장","건너편","건너","방면","앞","후문","정문","입구"):
        if s.endswith(suf) and len(s)>len(suf)+1: s=s[:-len(suf)]
    return s
_xw={}
for r in csv.DictReader(open("stop_crosswalk.csv",encoding="utf-8-sig")):
    try: _xw[r["sttn_id"].strip()]=(float(r["lon"]),float(r["lat"]))
    except: pass
_bs={}
for r in csv.DictReader(open("ulsan_busstops_20260407.csv",encoding="utf-8-sig")): _bs[r["sttn_id"]]=r["sttn_nm"]
_n2c={}; _c2c={}
def _add(nm,c):
    k=_norm(nm); kc=_ncore(nm)
    if k and k not in _n2c: _n2c[k]=c
    if kc and kc not in _c2c: _c2c[kc]=c
for r in csv.DictReader(open("ulsan_stop_coords_master.csv",encoding="utf-8-sig")):
    try: _add(r["stop_name"],(float(r["lon"]),float(r["lat"])))
    except: pass
for r in csv.DictReader(open("stop_crosswalk.csv",encoding="utf-8-sig")):
    try: _add(r["sttn_nm"],(float(r["lon"]),float(r["lat"])))
    except: pass
for r in csv.DictReader(open("nat_stops_raw.csv",encoding="cp949")):
    if "울산" in (r["도시명"] or ""):
        try: _add(r["정류장명"],(float(r["경도"]),float(r["위도"])))
        except: pass
def _resolve(sid):
    if sid in _xw: return _xw[sid]
    nm=_bs.get(sid)
    if not nm: return None
    if _norm(nm) in _n2c: return _n2c[_norm(nm)]
    if _ncore(nm) in _c2c: return _c2c[_ncore(nm)]
    return None
_rid2no={}
for r in csv.DictReader(open("ulsan_route_stops_20260407.csv",encoding="utf-8-sig")):
    _rid2no[r["rte_id"]]=r.get("rte_no") or r["rte_id"]
# 울산 노선번호 → 버스 유형 + 정원 (JS busType()와 동일 규칙)
_PREF=("울주","중구","남구","동구","북구")
def _btype(no):
    base=(no or "").split("(")[0].strip()
    pref=next((p for p in _PREF if base.startswith(p)),None)
    if pref:
        m=re.findall(r"\d+",base[len(pref):]); n=int(m[0]) if m else 0
        if 51<=n<=79: return ("마을",20)
        if 80<=n<=99: return ("순환",20)
        return ("지선",50)            # 01~49
    if base.isdigit():
        if len(base)==4 and base[0]=="1": return ("좌석",40)
        if len(base)==4 and base[0]=="5": return ("리무진",40)
        return ("일반",50)            # 3자리 시내
    return ("일반",50)
def _cap(no): return _btype(no)[1]
try:
    shr=defaultdict(lambda:[0]*24); shn=defaultdict(lambda:[""]*24)
    hv=defaultdict(lambda:[None]*24)   # sid → 시간별 [[no,ratio,cg,C],...] (ratio>=50)
    hrRuns=[0]*24; buses=[]
    for r in csv.DictReader(open("congestion_20260407.csv",encoding="utf-8-sig")):
        try: h=int(r["tzon"])%24; cg=int(r["cgst"] or 0)
        except: continue
        no=_rid2no.get(r["rte_id"],r["rte_id"]); C=_cap(no); ratio=cg/C*100
        sid=r["sttn_id"]
        if ratio>=100:
            hrRuns[h]+=1
            buses.append([h,no,(_bs.get(sid) or "").strip(),cg,C,round(ratio)])
        if ratio>=50:
            l=hv[sid][h]
            if l is None: l=hv[sid][h]=[]
            l.append([no,round(ratio),cg,C])
        if ratio>shr[sid][h]: shr[sid][h]=round(ratio); shn[sid][h]=no
    mstops=[]
    for sid in shr:
        c=_resolve(sid)
        if not c: continue
        rr=shr[sid]
        if max(rr)<=0: continue
        hvs=[]
        for h in range(24):
            l=hv[sid][h] or []
            l.sort(key=lambda z:-z[1])
            hvs.append(l)
        mstops.append([round(c[0],5),round(c[1],5),(_bs.get(sid) or "").strip(),rr,shn[sid],hvs])
    hrStops=[sum(1 for s in mstops if s[3][h]>=100) for h in range(24)]
    buses.sort(key=lambda b:-b[5])
    d["mancha"]={"stops":mstops,"hrStops":hrStops,"hrRuns":hrRuns,"buses":buses}
    print("만차: 정류장", len(mstops), "/ 만차버스행", len(buses))
except FileNotFoundError:
    d["mancha"]={"stops":[],"hrStops":[0]*24,"hrRuns":[0]*24,"buses":[]}

# ---------- 카드로 실제 버스 운행 복원 (편도 보정 + 배차창 W분) ----------
import statistics as _st, math as _math
W=8*60  # 같은 노선 출발시각이 이 창 안이면 같은 버스로 간주(초)
# 노선별 정류장 시퀀스(왕복 한 줄) → 회차점 찾아 '편도 위치(p)'로 변환
_ordered=defaultdict(list)  # rid -> [(seq,sttn_id)]
for r in csv.DictReader(open("ulsan_route_stops_20260407.csv",encoding="utf-8-sig")):
    _ordered[r["rte_id"]].append((int(r["sttn_seq"]),r["sttn_id"]))
def _km(a,b): return _math.hypot((a[0]-b[0])*88.9,(a[1]-b[1])*111.0)
_opos={}; _rpos={}  # rid -> {sttn_id: 상행위치}, {sttn_id: 하행위치}
_pfrac={}           # rid -> 회차점 비율(폴리라인 상행/하행 경계)
for rid,lst in _ordered.items():
    lst.sort()
    sids=[s for _,s in lst]; N=len(sids)
    c0=_resolve(sids[0])
    turn=N-1
    if c0:
        best=-1
        for i,sid in enumerate(sids):
            c=_resolve(sid)
            if c:
                dd=_km(c0,c)
                if dd>best: best=dd; turn=i
    op={}; rp={}
    for i in range(0,turn+1):                 # 상행: 시작 → 회차점
        if sids[i] not in op: op[sids[i]]=i+1
    for j,i in enumerate(range(turn,N)):       # 하행: 회차점 → 종점(시작)
        if sids[i] not in rp: rp[sids[i]]=j+1
    _opos[rid]=op; _rpos[rid]=rp; _pfrac[rid]=(turn+1)/float(max(N,2))
def _sec(s):
    s=s.strip(); return int(s[8:10])*3600+int(s[10:12])*60+int(s[12:14]) if len(s)>=14 else None
# ===== 재도입 노선(123·126·307) =====
import random as _rnd
_rnd.seed(7)
NR=json.load(open("abolished_routes.json"))      # [{no,pts,names,...}] (편도 정류장열)
NR_HW={"123":20,"126":35,"307":15}               # 고시 배차(분)
NRpts=[r["pts"] for r in NR]                      # 각 [[lon,lat],...]
TAUN=90                                           # 신규 노선 정류장당 초(가정)
def _nearidx(c,pts,rmax=0.3):
    bi=-1; bd=rmax
    for i,p in enumerate(pts):
        dd=_km(c,(p[0],p[1]))
        if dd<bd: bd=dd; bi=i
    return bi
_cand=defaultdict(list)  # 신규노선 k -> [(rs,gs,n,ut,ai,bi,tdir,rnd)]  (전환 후보)
_rec=defaultdict(list)   # rid -> (rs,pos,gs,n,ut,dir,tgt,rnd)
for path,hdr in [("card_records_20260407.csv",False),("card_records_20260407_etc.csv",True)]:
    try: rd=csv.reader(open(path,encoding="utf-8-sig"))
    except FileNotFoundError: continue
    if hdr: next(rd)
    for x in rd:
        if len(x)<7: continue
        rid=x[0]; op=_opos.get(rid); rp=_rpos.get(rid)
        if op is None: continue
        rs=_sec(x[2])
        if rs is None: continue
        ride=x[3]; goff=x[5]
        ro=op.get(ride); go=op.get(goff); rr=rp.get(ride); gr=rp.get(goff)
        outv = ro is not None and go is not None and go>ro
        retv = rr is not None and gr is not None and gr>rr
        if outv and (not retv or (go-ro)<=(gr-rr)): dirn=0; pos=ro
        elif retv: dirn=1; pos=rr
        elif ro is not None: dirn=0; pos=ro
        elif rr is not None: dirn=1; pos=rr
        else: continue
        gs=_sec(x[4])
        try: br=int(x[8] or 0)
        except: br=0
        if gs is None: gs=rs+(br if br>0 else 600)
        try: n=int(x[6] or 1)
        except: n=1
        try: ut=int(x[1]); ut=ut-1 if 1<=ut<=6 else 0
        except: ut=0
        # --- 재도입 노선 흡수 판정: 양 끝이 노선상(±300m) & 시간단축 시만 ---
        tgt=-1; rndv=_rnd.randint(0,255); cur=gs-rs
        if cur>0:
            rc=_resolve(ride); gc=_resolve(goff)
            if rc and gc:
                best=cur; bk=-1; bai=0; bbi=0; bdir=0
                for k,pts in enumerate(NRpts):
                    ai=_nearidx(rc,pts); bi=_nearidx(gc,pts)
                    if ai<0 or bi<0 or ai==bi: continue
                    newt=abs(bi-ai)*TAUN + NR_HW[NR[k]["no"]]*30  # 차내 + 평균대기(배차/2)
                    if newt<best:
                        best=newt; bk=k; bai=ai; bbi=bi; bdir=0 if bi>ai else 1
                if bk>=0:
                    tgt=bk; _cand[bk].append((rs,gs,n,ut,bai,bbi,bdir,rndv))
        _rec[rid].append((rs,pos,gs,n,ut,dirn,tgt,rndv))
_rid2ri={}
for i,rr in enumerate(d.get("routeRids",[])):
    if rr and rr not in _rid2ri: _rid2ri[rr]=i
busT=[]
for rid,rsl in _rec.items():
    ri=_rid2ri.get(rid)
    if ri is None: continue
    durs=sorted(gs-r for r,pos,gs,n,ut,dn,tg,rv in rsl if gs>r)
    travel=durs[int(len(durs)*0.8)] if durs else 1800
    travel=int(min(max(travel,1200),4500))
    npts=len(d["routes"][ri]) if ri<len(d["routes"]) else 2
    ei=max(1,min(npts-1,round(_pfrac.get(rid,0.5)*(npts-1))))
    for dn in (0,1):
        sub=[t for t in rsl if t[5]==dn]
        if not sub: continue
        taus=[(gs-r)/pos for r,pos,gs,n,ut,_,_,_ in sub if pos>0 and gs>r]
        tau=min(max(_st.median(taus) if taus else 90,30),180)
        grp=defaultdict(list)
        for r,pos,gs,n,ut,_,tg,rv in sub:
            grp[round((r-pos*tau)/W)].append((r,gs,n,ut,tg,rv))
        for b,riders in grp.items():
            dep=b*W; end=dep+travel
            rr2=[(r,min(gs,end),n,ut,tg,rv) for r,gs,n,ut,tg,rv in riders if dep-120<=r<=end+120]
            if not rr2: continue
            t0=round(dep/60-240,2); t1=round(end/60-240,2)
            if t1<=t0: t1=t0+1
            busT.append([t0,t1,ri,dep,travel,ei,dn,[[r,gs,n,ut,tg,rv] for r,gs,n,ut,tg,rv in rr2]])
busT.sort(key=lambda z:z[0])
d["trips"]=busT
# ===== 가상 신규노선 버스 생성(전환 후보 → 신규노선에 태움) =====
def _enc(pts): return [[round((p[0]-129)*1e4),round((p[1]-35)*1e4)] for p in pts]
d["newroutes"]=[{"no":NR[k]["no"],"pts":_enc(NRpts[k]),"hw":NR_HW[NR[k]["no"]]} for k in range(len(NR))]
newbuses=[]
for k,cand in _cand.items():
    pts=NRpts[k]; L=len(pts); Wn=NR_HW[NR[k]["no"]]*60
    durs=sorted(gs-rs for rs,gs,n,ut,ai,bi,td,rv in cand if gs>rs)
    travel=int(min(max(durs[int(len(durs)*0.8)] if durs else 1800,900),4500))
    for dn in (0,1):
        sub=[c for c in cand if c[6]==dn]
        if not sub: continue
        grp=defaultdict(list)
        for rs,gs,n,ut,ai,bi,td,rv in sub:
            rpos=(ai+1) if dn==0 else (L-ai)
            grp[round((rs-rpos*TAUN)/Wn)].append((rs,gs,n,ut,rv))
        for b,riders in grp.items():
            dep=b*Wn; end=dep+travel
            rr2=[(rs,min(gs,end),n,ut,rv) for rs,gs,n,ut,rv in riders if dep-120<=rs<=end+120]
            if not rr2: continue
            t0=round(dep/60-240,2); t1=round(end/60-240,2)
            if t1<=t0: t1=t0+1
            newbuses.append([t0,t1,k,dn,[[rs,gs,n,ut,rv] for rs,gs,n,ut,rv in rr2]])
newbuses.sort(key=lambda z:z[0])
d["newbuses"]=newbuses
# 시간대별 전환 후보 인원 + 인가대수(투입 효율용)
NR_AUTH={"123":8,"126":8,"307":12}
newhr=[[0]*24 for _ in NR]
for k,cand in _cand.items():
    for rs,gs,n,ut,ai,bi,td,rv in cand:
        newhr[k][(rs//3600)%24]+=n
for k in range(len(NR)): d["newroutes"][k]["auth"]=NR_AUTH.get(NR[k]["no"],8)
d["newhr"]=newhr
print("재도입 후보 통행:",{NR[k]["no"]:len(v) for k,v in _cand.items()},"| 가상버스:",len(newbuses))
print("복원 버스(통행 엔티티):",len(busT),"상행",sum(1 for b in busT if b[6]==0),"하행",sum(1 for b in busT if b[6]==1))

HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>울산 폐지노선 재도입 시뮬레이션 (2026-04-07)</title>
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
#rinfo{right:16px;top:232px;bottom:262px;width:300px;overflow-y:auto;display:none;font-size:12px}
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
#leg{display:none}
/* 만차 현황 (좌측) */
#mstat{left:16px;top:188px;width:248px;bottom:262px;overflow-y:auto;font-size:12px}
#mstat h2{margin:0 0 6px;font-size:14px}
#mstat .big{display:flex;gap:8px;margin-bottom:8px}
#mstat .big div{flex:1;background:#ffffff14;border-radius:8px;padding:7px 8px;text-align:center}
#mstat .big b{display:block;font-size:22px;font-variant-numeric:tabular-nums}
#mstat .big.red div:first-child b{color:#ff6b6b}
#mstat .sec{font-size:11px;opacity:.8;margin:9px 0 4px}
#mstat .hb{display:flex;align-items:flex-end;gap:1px;height:42px}
#mstat .hb i{flex:1;background:#5a6b9a;border-radius:1px 1px 0 0;min-height:1px;cursor:pointer}
#mstat .hb i.now{background:#ff5a5a}
#mstat .hbx{display:flex;justify-content:space-between;font-size:9px;opacity:.55;margin-top:2px}
#mstat .lgd{font-size:11px;line-height:1.8;margin-top:6px}
#mstat .lgd .d{display:inline-block;width:10px;height:10px;border-radius:2px;vertical-align:-1px;margin-right:4px}
body.day #mstat .big div{background:#0000000d}body.day #mstat .hb i{background:#9aa6c0}body.day #mstat .hb i.now{background:#e23b3b}
/* 만차 버스 목록 (하단) */
#mlist{left:16px;right:16px;bottom:118px;height:148px;display:flex;flex-direction:column;padding:9px 12px}
#mlist h2{margin:0 0 5px;font-size:13px;flex:0 0 auto}#mlist h2 .c{opacity:.7;font-weight:400;font-size:11px;margin-left:6px}
#mlist .scroll{flex:1;overflow-y:auto}
#mlist table{width:100%;border-collapse:collapse}
#mlist th{position:sticky;top:0;background:#0d1530;text-align:left;font-size:10px;opacity:.7;padding:3px 8px;font-weight:600}
#mlist td{padding:3px 8px;border-bottom:1px solid #ffffff12;font-size:11.5px;white-space:nowrap}
#mlist td.no{font-weight:700;font-variant-numeric:tabular-nums}
#mlist td.r{text-align:right;font-variant-numeric:tabular-nums}
#mlist .pill{display:inline-block;min-width:46px;text-align:center;border-radius:6px;padding:1px 6px;font-weight:700;color:#10131c}
body.day #mlist th{background:#ffffff}
#sim{left:50%;transform:translateX(-50%);top:14px;max-width:62vw;font-size:12px;text-align:center}
#sim .ttl{font-weight:700;margin-right:8px}
#sim label{margin:0 5px;cursor:pointer}
#sim input[type=range]{vertical-align:middle;accent-color:#ffd54f}
#sim #ba{background:#3a6bd5;color:#fff;border:1px solid #5a8bff;border-radius:8px;padding:4px 10px;font-size:12px;margin-left:8px;cursor:pointer}
#sim #ba.off{background:#2a3658;color:#cfe0ff}
#sim .nrc{display:inline-block;width:10px;height:10px;border-radius:2px;vertical-align:-1px;margin-right:3px}
#simstat{margin-top:6px;font-size:12px;line-height:1.5}
#simstat b{color:#ffd54f}
body.day #simstat b{color:#c07a00}
</style></head><body><div id="wrap"><canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 폐지노선 재도입 시뮬레이션</h1>
<p><b>박스 1개 = 카드로 복원한 버스 1대</b>(같은 노선·방향·8분 배차창으로 묶음) · <b>상행=■ 사각형 / 하행=▲ 삼각형</b>(정류장=● 원과 구분, 도로 양쪽 차선 분리) · 박스 크기·혼잡률 = 그 순간 차내 재차 ÷ 정원 · 색=버스 유형 · <b>만차는 붉은 테두리</b> · 정류장 색=국토부 혼잡도(참고) · 박스에 마우스를 올리면 노선·재차/정원 · 왼쪽 사용자유형=해당 유형만 집계 · <span style="opacity:.8">카드는 표본이라 절대 재차는 낮을 수 있음(상대 혼잡 비교용)</span></p>
<span class="tag">실데이터 2026-04-07</span> <a href="ulsan_용어설명.html" target="_blank" style="display:inline-block;margin-top:6px;font-size:11px;color:#7fb4ff">ℹ 용어 설명</a></div>
<div class="panel" id="clock"><div class="t" id="ct">--:--</div><div class="ph" id="cp"></div><div class="ride" id="cr"></div></div>
<div class="panel" id="modes"></div>
<div class="panel" id="rsel"></div>
<div class="panel" id="rinfo"></div>
<div class="panel" id="utf"></div>
<div class="panel" id="mstat"></div>
<div class="panel" id="leg"></div>
<div class="panel" id="mlist"></div>
<div class="panel" id="sim"></div>
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
// 재도입 신규 노선 폴리라인
const R2N=[],CUMN=[];
for(const nr of (D.newroutes||[])){const pts=nr.pts.map(p=>[LON(p[0]),LAT(p[1])]);const cum=[0];
 for(let i=1;i<pts.length;i++){const dx=(pts[i][0]-pts[i-1][0])*KX0,dy=pts[i][1]-pts[i-1][1];cum.push(cum[i-1]+Math.hypot(dx,dy));}R2N.push(pts);CUMN.push(cum);}
function posN(k,si,ei,f){const p=R2N[k],cum=CUMN[k];if(!p||!p.length)return null;
 if(si>=p.length)si=p.length-1;if(ei>=p.length)ei=p.length-1;if(si===ei)return p[si];
 const tD=cum[si]+(cum[ei]-cum[si])*f,lo=Math.min(si,ei),hi=Math.max(si,ei);let k2=lo;
 while(k2<hi&&cum[k2+1]<tD)k2++;if(k2>=p.length-1)return p[p.length-1];
 const seg=cum[k2+1]-cum[k2]||1e-9,g=(tD-cum[k2])/seg;return [p[k2][0]+(p[k2+1][0]-p[k2][0])*g,p[k2][1]+(p[k2+1][1]-p[k2][1])*g];}
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
// 혼잡률(%) 기반 박스 크기: 만차(100%) 기준 뚜렷, 면적∝혼잡률
function sqSideC(p){return Math.max(2.5,Math.min(26,3+Math.sqrt(Math.max(0,p))*1.7));}
// 군집 박스 크기: 묶인 승객 수 기준 (많을수록 큰 '버스')
function sqSideN(n){return Math.max(5,Math.min(32,4+Math.sqrt(n)*3));}
// ---------- 이용자유형 필터 ----------
const UNAMES=['일반','어린이','청소년','경로','장애','국가유공'];
let utf=-1;
function onb(b,ts){let v=0;const rs=b[7];for(let i=0;i<rs.length;i++){const r=rs[i];if(r[0]<=ts&&ts<r[1]&&(utf<0||r[3]===utf))v+=r[2];}return v;}
// ===== 재도입 시뮬레이션 상태 =====
const NEWB=D.newbuses||[], NROUTES=D.newroutes||[], NRCOL=['#ff4fd8','#36e0ff','#ffe14a','#7CFC00'];
let SIMON=new Set(), ALPHA=0.5, MODE=1;  // SIMON=활성 재도입노선, MODE 1=도입후 0=도입전
for(let k=0;k<NROUTES.length;k++)SIMON.add(k);
function shifted(r){return r[4]>=0&&SIMON.has(r[4])&&r[5]<ALPHA*255;} // 기존 버스 승객이 전환되는가
function onbA(b,ts){let v=0;const rs=b[7];for(let i=0;i<rs.length;i++){const r=rs[i];if(r[0]<=ts&&ts<r[1]&&(utf<0||r[3]===utf)){if(MODE&&shifted(r))continue;v+=r[2];}}return v;}
function onbN(b,ts){let v=0;const rs=b[4];for(let i=0;i<rs.length;i++){const r=rs[i];if(r[0]<=ts&&ts<r[1]&&(utf<0||r[3]===utf)&&r[4]<ALPHA*255)v+=r[2];}return v;}
const NEWHR=D.newhr||[];let effx=null,effv=null;
function drawEff(){if(!effx)return;const w=300,hh=46;effx.clearRect(0,0,w,hh);
 const vals=[];let mx=1;for(let h=0;h<24;h++){let v=0;for(let k=0;k<NEWHR.length;k++)if(SIMON.has(k))v+=(NEWHR[k][h]||0)*ALPHA;vals.push(v);if(v>mx)mx=v;}
 const bw=w/24,day=document.body.classList.contains('day');
 for(let h=0;h<24;h++){const bh=vals[h]/mx*(hh-4);effx.fillStyle=(h===curHour)?'#ffd54f':(day?'#3a6bd5':'#5a8bff');effx.fillRect(h*bw+1,hh-bh,bw-1.5,bh);}
 let s='';for(let k=0;k<NROUTES.length;k++){if(!SIMON.has(k))continue;let tot=0;for(let h=0;h<24;h++)tot+=(NEWHR[k][h]||0)*ALPHA;const a=NROUTES[k].auth||8;
  s+=`<span style="color:${NRCOL[k%NRCOL.length]};font-weight:700">${NROUTES[k].no}</span> ${Math.round(tot).toLocaleString()}명÷${a}대=<b>${Math.round(tot/a).toLocaleString()}</b> `;}
 if(effv)effv.innerHTML='시간대별 전환(막대,0~23시) · 투입효율(명/대): '+(s||'노선 선택');}
const utTot=[0,0,0,0,0,0];for(const b of T)for(const r of b[7])utTot[r[3]]+=r[2];
(()=>{let h=`<button data-u="-1" class="on">전체</button>`;UNAMES.forEach((nm,i)=>{if(utTot[i]>0)h+=`<button data-u="${i}">${nm}<span class="n">${utTot[i].toLocaleString()}</span></button>`;});
 const el=document.getElementById('utf');el.innerHTML=h;el.querySelectorAll('button').forEach(b=>b.onclick=()=>{utf=+b.dataset.u;el.querySelectorAll('button').forEach(z=>z.classList.toggle('on',z===b));recomputeBins();});})();
// 모드 버튼(자동/낮/밤)
(()=>{const el=document.getElementById('modes');el.innerHTML=`<button data-f="-1" class="on">자동</button><button data-f="1">낮</button><button data-f="0">밤</button>`;
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>{forceMode=+b.dataset.f;el.querySelectorAll('button').forEach(z=>z.classList.toggle('on',z===b));});})();
// 재도입 시뮬레이션 컨트롤
let simstatEl=null;
(()=>{const el=document.getElementById('sim');if(!NROUTES.length){el.style.display='none';return;}
 let h='<span class="ttl">폐지노선 재도입 효과</span>';
 NROUTES.forEach((r,k)=>h+=`<label><input type="checkbox" data-k="${k}" checked><span class="nrc" style="background:${NRCOL[k%NRCOL.length]}"></span>${r.no}번(배차${r.hw}분)</label>`);
 h+=' 전환율 <input type="range" id="alp" min="0" max="100" value="50" style="width:90px"> <span id="alpv">50%</span>';
 h+='<button id="ba">도입 후</button>';
 // 하루 흡수 가능 규모(노선별 전환 후보 인원, 전환100% 기준)
 const dayTot={};for(const b of NEWB){const k=b[2];for(const r of b[4])dayTot[k]=(dayTot[k]||0)+r[2];}
 h+='<div style="width:100%;margin-top:4px;font-size:11px;opacity:.85">하루 흡수 가능 통행: '+NROUTES.map((r,k)=>r.no+'번 '+(dayTot[k]||0).toLocaleString()+'명').join(' · ')+'</div>';
 h+='<div id="simstat"></div>';
 h+='<div style="width:100%;margin-top:5px"><canvas id="effc" style="width:300px;height:46px;display:block;margin:0 auto"></canvas><div id="effv" style="font-size:10.5px;opacity:.85;margin-top:2px"></div></div>';
 el.innerHTML=h;
 const _ec=document.getElementById('effc');_ec.width=300*dpr;_ec.height=46*dpr;effx=_ec.getContext('2d');effx.setTransform(dpr,0,0,dpr,0,0);effv=document.getElementById('effv');
 el.querySelectorAll('input[type=checkbox]').forEach(c=>c.onclick=()=>{const k=+c.dataset.k;if(c.checked)SIMON.add(k);else SIMON.delete(k);});
 const al=document.getElementById('alp');al.oninput=()=>{ALPHA=+al.value/100;document.getElementById('alpv').textContent=al.value+'%';};
 const ba=document.getElementById('ba');ba.onclick=()=>{MODE=MODE?0:1;ba.textContent=MODE?'도입 후':'도입 전';ba.classList.toggle('off',!MODE);};
 simstatEl=document.getElementById('simstat');})();
// 노선 선택 → 경로선·정류장 표시 (드롭다운 + 하단 칩 바)
const RNAMES=D.routeNames||[], RI=D.routeInfo||[], RC=D.cong||{}, RIDS=D.routeRids||[], RSIDS=D.routeSids||[], ABOL=D.abol||[];
function congOf(i){const rid=RIDS[i];return rid?RC[rid]:null;}
// ---------- 만차(혼잡) 레이어 ----------
const MAN=D.mancha||{stops:[],hrStops:[],hrRuns:[],buses:[]};
// 시간대별 만차 노선번호 집합 (버스 상자 만차 테두리용)
const MANSET=Array.from({length:24},()=>new Set());
for(const b of MAN.buses)MANSET[b[0]].add(b[1]);
function rcol(p){return p>=100?'#ff3a3a':p>=80?'#ff8c1e':p>=50?'#ffd54f':'#3a9b7a';}
// 버스 유형별 상징색 (사용자 지정)
const BTYPE={'일반':'#ffd23f','좌석':'#b9a0f0','리무진':'#ff4d4d','지선':'#4d9bff','마을':'#7ed957','순환':'#ff8fc8'};
const BPREF=['울주','중구','남구','동구','북구'];
function busType(no){const base=String(no||'').split('(')[0].trim();
 const pf=BPREF.find(p=>base.startsWith(p));
 if(pf){const m=base.slice(pf.length).match(/\d+/);const n=m?+m[0]:0;
  if(n>=51&&n<=79)return'마을';if(n>=80&&n<=99)return'순환';return'지선';}
 if(/^\d+$/.test(base)){if(base.length===4&&base[0]==='1')return'좌석';if(base.length===4&&base[0]==='5')return'리무진';return'일반';}
 return'일반';}
function typeCol(no){return BTYPE[busType(no)]||'#ffd23f';}
const BCAP={'일반':50,'좌석':40,'리무진':40,'지선':50,'마을':20,'순환':20};
function busCap(no){return BCAP[busType(no)]||50;}
// 정류장 혼잡도 → 색 (초록·노랑·주황·빨강)
function congCol(p){return p>=100?'#ff3a3a':p>=80?'#ff8c1e':p>=50?'#f4d03f':'#2ecc71';}
function congAlpha(p){return p>=100?1:p>=80?0.9:p>=50?0.78:p>=30?0.6:0.45;}
function hexA(hex,a){const n=parseInt(hex.slice(1),16);return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`;}
let curHour=-1;
function curHourOf(){return Math.floor(((((now%1440)+1440)%1440)+240)/60)%24;}
function renderMancha(h){
 const ms=document.getElementById('mstat');
 const nStop=MAN.hrStops[h]||0,nRun=MAN.hrRuns[h]||0,smx=Math.max(1,...MAN.hrStops);
 let hb='';for(let i=0;i<24;i++)hb+=`<i class="${i===h?'now':''}" data-h="${i}" style="height:${Math.round((MAN.hrStops[i]||0)/smx*42)}px" title="${i}시 ${MAN.hrStops[i]||0}곳"></i>`;
 ms.innerHTML=`<h2>🚍 만차 현황 · ${String(h).padStart(2,'0')}시</h2>`
  +`<div class="big red"><div><b>${nStop}</b>만차 정류장</div><div><b>${nRun}</b>만차 운행편</div></div>`
  +`<div class="sec">시간대별 만차 정류장 수 (막대=이동)</div><div class="hb">${hb}</div>`
  +`<div class="hbx"><span>0</span><span>6</span><span>12</span><span>18</span><span>23</span></div>`
  +`<div class="sec">정류장 색 = 혼잡도 (정원 대비)</div><div class="lgd">`
  +`<span class="d" style="background:#ff3a3a"></span>만차 ≥100%<br>`
  +`<span class="d" style="background:#ff8c1e"></span>혼잡 80~99%<br>`
  +`<span class="d" style="background:#f4d03f"></span>보통 50~79%<br>`
  +`<span class="d" style="background:#2ecc71"></span>여유 &lt;50%</div>`
  +`<div class="sec">버스·목록 색 = 유형 (만차 버스=<span style="color:#ff5a5a">붉은 테두리</span>)</div><div class="lgd">`
  +Object.entries(BTYPE).map(([k,v])=>`<span class="d" style="background:${v}"></span>${k}`).join('  ')+`</div>`
  +`<div class="sec" style="margin-top:8px">정원: 좌석/리무진 40 · 일반/지선 50 · 마을/순환 20</div>`;
 ms.querySelectorAll('.hb i').forEach(b=>b.onclick=()=>{setPlay(false);reseek((((+b.dataset.h)*60-240)%1440+1440)%1440);});
 const ml=document.getElementById('mlist');
 const list=MAN.buses.filter(b=>b[0]===h).sort((a,b)=>b[5]-a[5]);
 let rows='';for(const b of list){const p=b[5];
  rows+=`<tr><td class="no" style="color:${typeCol(b[1])}">${b[1]} <span style="opacity:.55;font-weight:400;font-size:10px">${busType(b[1])}</span></td><td>${b[2]||'-'}</td><td class="r">${b[3]} / ${b[4]}</td>`
   +`<td class="r"><span class="pill" style="background:${rcol(p)}">${p}%</span></td></tr>`;}
 if(!rows)rows='<tr><td colspan="4" style="opacity:.6;padding:10px">이 시각 만차 운행 없음</td></tr>';
 ml.innerHTML=`<h2>만차로 보이는 버스 — 만차 정류장 통과<span class="c">${String(h).padStart(2,'0')}시 · ${list.length}편 · 혼잡률순</span></h2>`
  +`<div class="scroll"><table><thead><tr><th>노선</th><th>통과 만차 정류장</th><th style="text-align:right">재차/정원</th><th style="text-align:right">혼잡률</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
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
function recomputeBins(){bins=new Array(96).fill(0);for(const b of T)for(const r of b[7]){if(utf>=0&&r[3]!==utf)continue;let m=r[0]/60-240;m=((m%1440)+1440)%1440;bins[Math.min(95,Math.floor(m/15))]+=r[2];}hmax=Math.max(1,...bins);}
recomputeBins();
function drawHist(now,d){const w=hc.clientWidth,h=hc.clientHeight;hc.width=w*dpr;hc.height=h*dpr;hx.setTransform(dpr,0,0,dpr,0,0);hx.clearRect(0,0,w,h);
 const bw=w/96,base=d>.5?'#9aa6c0':'#3a4a78',on=d>.5?'#d59b00':'#ffd54f';
 for(let i=0;i<96;i++){const bh=bins[i]/hmax*(h-3);hx.fillStyle=Math.floor(now/15)===i?on:base;hx.fillRect(i*bw,h-bh,bw-0.6,bh);}}
// ---------- 컨트롤 ----------
let now=300,playing=true,speed=1,ptr=0,active=[];
const scrub=document.getElementById('scrub'),ctEl=document.getElementById('ct'),cpEl=document.getElementById('cp'),crEl=document.getElementById('cr'),tip=document.getElementById('tip');
function hhmm(m){let mm=Math.floor(((m%1440)+1440)%1440);let h=Math.floor((mm+240)/60)%24,mi=(mm+240)%60;return String(h).padStart(2,'0')+':'+String(mi).padStart(2,'0');}
let activeN=[];
function reseek(t){active=[];ptr=0;while(ptr<N&&T[ptr][0]<=t){if(T[ptr][1]>t)active.push(T[ptr]);ptr++;}
 activeN=[];for(let i=0;i<NEWB.length;i++){const b=NEWB[i];if(b[0]<=t&&b[1]>t)activeN.push(b);} now=t;}
const playBtn=document.getElementById('play'),spdBtn=document.getElementById('spd');
function setPlay(p){playing=p;playBtn.textContent=playing?'⏸ 일시정지':'▶ 재생';}
const SPDS=[-2,-1,-0.5,-0.25,0.25,0.5,1,2,4,8];let sidx=6;  // 느린 0.25×/0.5× + 역재생 포함
function setSpeed(i){sidx=Math.max(0,Math.min(SPDS.length-1,i));speed=SPDS[sidx];spdBtn.textContent='속도 '+(speed>0?'+':'')+speed+'×';}
playBtn.onclick=()=>setPlay(!playing);spdBtn.onclick=()=>setSpeed(sidx>=SPDS.length-1?6:sidx+1);
setSpeed(6);
scrub.addEventListener('input',e=>{setPlay(false);reseek(+e.target.value);});
addEventListener('keydown',e=>{if(e.code==='Space'){e.preventDefault();setPlay(!playing);}else if(e.code==='ArrowRight')setSpeed(sidx+1);else if(e.code==='ArrowLeft')setSpeed(sidx-1);});
let mx2=-1,my2=-1,mcx=0,mcy=0,crect=c.getBoundingClientRect();
addEventListener('resize',()=>crect=c.getBoundingClientRect());
addEventListener('mousemove',e=>{crect=c.getBoundingClientRect();mx2=e.clientX-crect.left;my2=e.clientY-crect.top;mcx=e.clientX;mcy=e.clientY;});
addEventListener('mouseout',()=>{mx2=my2=-1;});
reseek(300);
let last=performance.now();
function frame(t){const dt=(t-last)/1000;last=t;fit();
 const d=dNow(now);
 document.body.classList.toggle('day',d>0.55);
 {const h=curHourOf();if(h!==curHour){curHour=h;renderMancha(h);}}
 if(playing){now+=dt*speed*6;if(now>=1440)now-=1440;else if(now<0)now+=1440;scrub.value=Math.floor(now);}
 reseek(now); // 매 프레임 활성 버스 재계산(정·역방향·스크럽 모두 대응)
 // 배경
 const bg=mix(NIGHT_BG,DAY_BG,d);x.fillStyle=`rgb(${bg[0]|0},${bg[1]|0},${bg[2]|0})`;x.fillRect(0,0,W,H);
 // 인구 격자
 const cpx=Math.max(2,(100/111000*sc)*1.5*Z);
 for(const cl of D.cells){x.fillStyle=cellCol(cl[2],d);x.fillRect(PX(LON(cl[0]))-cpx/2,PY(LAT(cl[1]))-cpx/2,cpx,cpx);}
 // 하늘 틴트(여명·낙조)
 const st=skyTint(now);if(st){x.fillStyle=st[0];x.fillRect(0,0,W,H);}
 // 종료 통행 제거
 for(let i=active.length-1;i>=0;i--){if(active[i][1]<=now){active[i]=active[active.length-1];active.pop();}}
 // 승객 사각형(버스)은 맨 앞 레이어로 — 선언만 먼저, 그리기는 정류장·노선 뒤에
 let people=0;const hov=!playing&&mx2>=0;let hbest=1e9,htr=null;
 const night=d<0.5;
 // 만차/혼잡 정류장 — 시간 보간으로 부드럽게 흐름 · 색=버스유형, 투명도=혼잡도
 const _mm=((now%1440)+1440)%1440,_hf=(_mm+240)/60;const h0=Math.floor(_hf)%24,frac=_hf-Math.floor(_hf),h1=(h0+1)%24;
 let manHit=null,mhb=200;const pulse=0.5+0.5*Math.sin(t/350);
 for(const s of MAN.stops){const rt=s[3];if(!rt)continue;
  const r=rt[h0]*(1-frac)+rt[h1]*frac;if(r<15)continue;
  const X=PX(s[0]),Y=PY(s[1]);if(X<-20||X>W+20||Y<-20||Y>H+20)continue;
  const col=congCol(r),a=congAlpha(r),sz=r>=100?6.5:r>=80?5:r>=50?4:3;
  if(r>=100){x.beginPath();x.arc(X,Y,sz+3+pulse*5,0,7);x.fillStyle='rgba(255,58,58,'+(0.20*(1-pulse*0.4)).toFixed(3)+')';x.fill();}
  x.beginPath();x.arc(X,Y,sz,0,7);x.fillStyle=hexA(col,a);x.fill();
  if(r>=100){x.lineWidth=1.3;x.strokeStyle='#ff3a3a';x.stroke();}
  else{x.lineWidth=0.7;x.strokeStyle=night?'rgba(255,255,255,'+(a*0.6).toFixed(2)+')':'rgba(16,19,28,'+(a*0.5).toFixed(2)+')';x.stroke();}
  if(mx2>=0){const dd=(X-mx2)*(X-mx2)+(Y-my2)*(Y-my2);if(dd<mhb){mhb=dd;manHit={s:s,r:Math.round(r),h:h0,X:X,Y:Y};}}}
 if(manHit&&manHit.r>=80){x.beginPath();x.arc(manHit.X,manHit.Y,11,0,7);x.lineWidth=2;x.strokeStyle='#ff3a3a';x.stroke();}
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
 // 재도입 신규 노선 경로(점선) — 도입후 모드
 const tsec=((((now%1440)+1440)%1440)+240)*60;
 if(MODE){x.save();x.setLineDash([8,6]);x.lineWidth=2.6;
  for(let k=0;k<R2N.length;k++){if(!SIMON.has(k))continue;const P=R2N[k];if(!P||P.length<2)continue;
   x.strokeStyle=NRCOL[k%NRCOL.length];x.beginPath();
   P.forEach((q,i)=>{const X=PX(q[0]),Y=PY(q[1]);i?x.lineTo(X,Y):x.moveTo(X,Y);});x.stroke();}
  x.restore();}
 // 복원된 실제 버스 — 카드로 묶은 운행 단위 (맨 앞 레이어)
 let bHit=null,bhb=1e9;
 for(const b of active){const f=(now-b[0])/(b[1]-b[0]);if(f<0||f>1)continue;
  const on=(MODE?onbA(b,tsec):onb(b,tsec));if(on<=0)continue;people+=on;
  const ri=b[2],R=R2[ri];if(!R||R.length<2)continue;
  const last=R.length-1,ei=Math.max(1,Math.min(b[5]||last,last)),dir=b[6];
  const sA=dir?ei:0, eA=dir?last:ei;            // 상행 0→회차 / 하행 회차→종점
  const pos=posOn(ri,sA,eA,f);if(!pos)continue;
  const p2=posOn(ri,sA,eA,Math.min(1,f+0.02))||pos;
  const no=D.routeNos[ri];let X=PX(pos[0]),Y=PY(pos[1]);
  // 진행방향 오른쪽으로 차선 분리(상·하행이 도로 양쪽으로 나뉘어 보이게)
  {const X2=PX(p2[0]),Y2=PY(p2[1]);let dx=X2-X,dy=Y2-Y,Ln=Math.hypot(dx,dy)||1;const off=5;X+=dy/Ln*off;Y+=-dx/Ln*off;}
  if(X<-30||X>W+30||Y<-30||Y>H+30)continue;
  const cap=busCap(no),s=sqSideN(on),full=on>=cap;
  x.fillStyle=typeCol(no);
  if(night){x.shadowColor=x.fillStyle;x.shadowBlur=Math.min(9,s);}
  if(dir===0){ // 상행 = 사각형
   x.fillRect(X-s/2,Y-s/2,s,s);x.shadowBlur=0;
   if(full){x.strokeStyle='#ff2020';x.lineWidth=2;x.strokeRect(X-s/2-1,Y-s/2-1,s+2,s+2);}
   else if(!night){x.strokeStyle='rgba(20,28,48,.5)';x.lineWidth=0.6;x.strokeRect(X-s/2,Y-s/2,s,s);}
  } else { // 하행 = 삼각형 (정류장 원과 구분)
   x.beginPath();x.moveTo(X,Y-s*0.62);x.lineTo(X+s*0.58,Y+s*0.46);x.lineTo(X-s*0.58,Y+s*0.46);x.closePath();x.fill();x.shadowBlur=0;
   if(full){x.strokeStyle='#ff2020';x.lineWidth=2;x.stroke();}
   else if(!night){x.strokeStyle='rgba(20,28,48,.5)';x.lineWidth=0.6;x.stroke();}
  }
  if(hov){const dd=(X-mx2)*(X-mx2)+(Y-my2)*(Y-my2),lim=Math.max(9,s);if(dd<bhb&&dd<lim*lim){bhb=dd;bHit={no:no,on:on,cap:cap,dir:dir};}}}
 // 가상 신규노선 버스 (도입후 모드 · 전환 승객을 태움)
 if(MODE){for(const b of activeN){const k=b[2];if(!SIMON.has(k))continue;
   const f=(now-b[0])/(b[1]-b[0]);if(f<0||f>1)continue;
   const on=onbN(b,tsec);if(on<=0)continue;people+=on;
   const P=R2N[k];if(!P||P.length<2)continue;const last=P.length-1,dir=b[3];
   const pos=dir?posN(k,last,0,f):posN(k,0,last,f);if(!pos)continue;
   const p2=(dir?posN(k,last,0,Math.min(1,f+0.02)):posN(k,0,last,Math.min(1,f+0.02)))||pos;
   let X=PX(pos[0]),Y=PY(pos[1]);
   {const X2=PX(p2[0]),Y2=PY(p2[1]);let dx=X2-X,dy=Y2-Y,Ln=Math.hypot(dx,dy)||1;const off=5;X+=dy/Ln*off;Y+=-dx/Ln*off;}
   if(X<-30||X>W+30||Y<-30||Y>H+30)continue;
   const s=Math.max(6,sqSideN(on)),col=NRCOL[k%NRCOL.length];
   x.fillStyle=col;x.shadowColor=col;x.shadowBlur=9;
   if(dir===0){x.fillRect(X-s/2,Y-s/2,s,s);x.shadowBlur=0;x.strokeStyle='#fff';x.lineWidth=1.4;x.strokeRect(X-s/2,Y-s/2,s,s);}
   else{x.beginPath();x.moveTo(X,Y-s*0.62);x.lineTo(X+s*0.58,Y+s*0.46);x.lineTo(X-s*0.58,Y+s*0.46);x.closePath();x.fill();x.shadowBlur=0;x.strokeStyle='#fff';x.lineWidth=1.4;x.stroke();}
   if(hov){const dd=(X-mx2)*(X-mx2)+(Y-my2)*(Y-my2),lim=Math.max(9,s);if(dd<bhb&&dd<lim*lim){bhb=dd;bHit={no:NROUTES[k].no+'(재도입)',on:on,cap:45,dir:dir};}}
  }}
 // 툴팁: 정류장(우선) > 승객
 if(stopHit){tip.innerHTML='<b>'+stopHit.nm+'</b><br>'+(D.routeNos[selRoute]||'')+'번 · '+stopHit.seq+'/'+stopHit.tot+'번째 정류장';
  tip.style.display='block';tip.style.left=(mcx>W-190?mcx-180:mcx+14)+'px';tip.style.top=(mcy+14)+'px';}
 else if(manHit){const s=manHit.s,hv=(s[5]&&s[5][manHit.h])||[];
  let inner='<b>'+s[2]+'</b> <span style="opacity:.6">'+String(manHit.h).padStart(2,'0')+'시</span>';
  const full=hv.filter(z=>z[1]>=100),other=hv.filter(z=>z[1]<100);
  if(full.length){inner+='<br><span style="color:#ff6b6b;font-weight:700">● 현재 만차 버스</span>';
   full.forEach(z=>inner+='<br><b style="color:'+typeCol(z[0])+'">'+z[0]+'</b> <span style="opacity:.6">'+busType(z[0])+'</span> · 재차 '+z[2]+'/'+z[3]+' · <b style="color:#ff6b6b">'+z[1]+'%</b>');}
  if(other.length){inner+='<br><span style="opacity:.65">혼잡(50%+)</span>';
   other.slice(0,5).forEach(z=>inner+='<br><span style="color:'+typeCol(z[0])+'">'+z[0]+'</span> · '+z[2]+'/'+z[3]+' · '+z[1]+'%');}
  if(!hv.length)inner+='<br><span style="opacity:.6">현재 혼잡 50% 미만</span>';
  tip.innerHTML=inner;tip.style.display='block';tip.style.left=(mcx>W-250?mcx-240:mcx+14)+'px';tip.style.top=(mcy+14)+'px';}
 else if(bHit){const no=bHit.no,pr=Math.round(bHit.on/bHit.cap*100);
  let inner='<b style="color:'+typeCol(no)+'">'+no+'</b> <span style="opacity:.6">'+busType(no)+' · '+(bHit.dir?'하행':'상행')+'</span>';
  inner+='<br>현재 차내 재차 <b>'+bHit.on+'</b>명 / 정원 '+bHit.cap+' · 혼잡률 <b style="color:'+congCol(pr)+'">'+pr+'%</b>'+(bHit.on>=bHit.cap?' · <b style="color:#ff5a5a">만차</b>':'');
  inner+='<br><span style="opacity:.55">카드 표본으로 복원한 운행</span>';
  tip.innerHTML=inner;tip.style.display='block';tip.style.left=(mcx>W-230?mcx-220:mcx+14)+'px';tip.style.top=(mcy+14)+'px';}else tip.style.display='none';
 // HUD
 ctEl.textContent=hhmm(now);cpEl.textContent=phaseName(now);crEl.textContent='운행 중 '+people.toLocaleString()+'명';
 // 재도입 효과 요약(현재 시각)
 if(simstatEl){let mb=0,ma=0,shift=0;
  for(const b of active){const cap=busCap(D.routeNos[b[2]]);if(onb(b,tsec)>=cap)mb++;if(onbA(b,tsec)>=cap)ma++;}
  for(const b of activeN){if(SIMON.has(b[2]))shift+=onbN(b,tsec);}
  const cut=mb?Math.round((mb-ma)/mb*100):0;
  simstatEl.innerHTML=`만차 편수 <b>${mb}</b> → <b>${ma}</b>편 (${cut>=0?'−':'+'}${Math.abs(cut)}%) · 재도입 노선 탑승 <b>${shift}</b>명 · <span style="opacity:.7">${MODE?'도입 후':'도입 전'} · 카드표본</span>`;
  drawEff();}
 drawHist(((now%1440)+1440)%1440,d);
 requestAnimationFrame(frame);}
requestAnimationFrame(frame);
</script></body></html>"""
open("ulsan_route_sim2.html","w",encoding="utf-8").write(HTML.replace("__DATA__", json.dumps(d, separators=(",",":"))))
print("ulsan_route_sim2.html", round(os.path.getsize("ulsan_route_sim2.html")/1e6,2),"MB")
