"""폐지 버스 노선(123·126·307)을 정류장명→좌표로 복원 → abolished_routes.json
정류장명은 나무위키 노선도 기반. 좌표 매칭은 기존 정류장 좌표 사전(이름) 사용 + 최근접/스파이크 정리.
"""
import csv, re, math, json
from collections import defaultdict
def norm(s): s=(s or "").split("(")[0]; return re.sub(r"[ .()\-·,]","",s)
def norm_core(s):
    s=norm(s)
    for suf in ("정류소","정류장","건너편","건너","방면","앞","후문","정문","입구"):
        if s.endswith(suf) and len(s)>len(suf)+1: s=s[:-len(suf)]
    return s
n2l=defaultdict(list); c2l=defaultdict(list)
def add(nm,c):
    k=norm(nm); kc=norm_core(nm)
    if k: n2l[k].append(c)
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
def cand(name):
    k=norm(name)
    if k in n2l: return n2l[k]
    cs=[]
    for part in re.split(r"[.·\s/]", name):
        kp=norm(part)
        if kp and kp in n2l: cs+=n2l[kp]
    if cs: return cs
    kc=norm_core(name)
    if kc in c2l: return c2l[kc]
    for kk,v in c2l.items():
        if len(kc)>=3 and (kc in kk or kk in kc) and abs(len(kc)-len(kk))<=2: cs+=v
    return cs
def despike(pts):
    out=[list(p) for p in pts]; ch=True
    while ch and len(out)>=3:
        ch=False
        for i in range(1,len(out)-1):
            a,c,b=out[i-1],out[i],out[i+1]
            if km(a,c)>2 and km(c,b)>2 and (km(a,c)+km(c,b))>km(a,b)*2.5+0.5: del out[i];ch=True;break
    return out
def build(stops):
    pts=[]; nms=[]; prev=None; miss=[]
    for nm in stops:
        cs=cand(nm)
        if not cs: miss.append(nm); continue
        c=min(cs,key=lambda x:km(x,prev)) if prev else cs[0]
        if prev and km(c,prev)>6.0: miss.append(nm+"(점프)"); continue
        pts.append([c[0],c[1]]); nms.append(nm); prev=c
    # despike (좌표만), 이름 동기화는 근사
    ds=despike(pts)
    return [[round(p[0],5),round(p[1],5)] for p in ds], nms, miss

R123=["꽃바위","비치타운","방어동행정복지센터","대왕암공원입구","동부경찰서","현대중공업.울산대학병원","현대청운고","남목고등학교","성내","현대자동차정문","현대출고사무소","울산종합운동장","학성공원","옥성초등학교","학성배수장","성남동","태화루","학성여중","삼호교","삼호지하차도","구영교","대리","울주경찰서.범서중학교","현대3차아파트","현대2차아파트","구영리입구","천상1교사거리","범서초등학교","천상중학교"]
R126=["꽃바위","비치타운","방어진초등학교","화진맨션","문재사거리","송정타워","울산과학대학교","동구청","한마음회관.울산대학병원","녹수초등학교","현대청운고","남목고등학교","성내","현대출고사무소","효문사거리","태화강역","시외고속버스터미널","공업탑","수암시장","야음장생포동행정복지센터","변전소","선암동","상개동","덕하삼거리","덕하시장","덕하공영차고지"]
R307=["천상중학교","범서초등학교","천상1교사거리","구영리입구","현대2차아파트","현대3차아파트","울주경찰서.범서중학교","구영교","삼호지하차도","신복로터리","울산대학교","옥현주공3단지","옥현주공2단지","성광여고","법원","옥동초등학교","공업탑","롯데마트","강남초등학교","목화예식장","시외고속버스터미널","농수산물도매시장","이마트","태화강역"]
defs=[
 ("123",R123,"동구 방어동(방어진공영차고지)","울주 범서읍 천상리(천상중학교)","05:30/22:30","평일 15~45분","남성여객 · 8대"),
 ("126",R126,"동구 방어동(방어진공영차고지)","울주 청량읍 상남리(덕하공영차고지)","05:20/22:30","평일 30~40분(1일32회)","학성버스 · 8대"),
 ("307",R307,"울주 범서읍 천상리(천상중학교)","남구 삼산동(태화강역)","05:10/23:15","평일 10~25분","한성교통 · 12대"),
]
out=[]
for no,stops,a,b,car,hw,op in defs:
    pts,nms,miss=build(stops)
    out.append({"no":no,"a":a,"b":b,"car":car,"hw":hw,"op":op,"pts":pts,"names":nms})
    print(f"{no}번: 정류장 {len(stops)} → 점 {len(pts)} / 미매칭 {len(miss)} {miss}")
json.dump(out, open("abolished_routes.json","w"), separators=(",",":"), ensure_ascii=False)
print("저장 abolished_routes.json")
