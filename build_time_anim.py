"""4월 7일 교통카드(승하차+시각) → 시간축 이동 애니메이션 HTML
입력: uploads card_records_20260407*.csv (헤더없음, 위치읽기),
      ulsan_busstops_20260407.csv, ulsan_stop_coords_master.csv, stop_crosswalk.csv,
      nat_stops_raw.csv(cp949), grid100_population.csv(배경)
출력: card_trips_20260407.json(중간), ulsan_time_anim.html
"""
import csv, json, re, glob, math
from collections import defaultdict

# ---------- 좌표 해석기 ----------
def norm(s):
    s = (s or "").split("(")[0]
    return re.sub(r"[ .()\-·,]", "", s)

def norm_core(s):
    """접미사(앞/건너/방면/정류소 등) 제거한 핵심명"""
    s = norm(s)
    for suf in ("정류소", "정류장", "건너편", "건너", "방면", "앞", "후문", "정문", "입구"):
        if s.endswith(suf) and len(s) > len(suf) + 1:
            s = s[: -len(suf)]
    return s

xw = {}                      # sttn_id -> coord (직접)
for r in csv.DictReader(open("stop_crosswalk.csv", encoding="utf-8-sig")):
    try: xw[r["sttn_id"].strip()] = (float(r["lon"]), float(r["lat"]))
    except: pass

bs = {}                      # sttn_id -> name
for r in csv.DictReader(open("ulsan_busstops_20260407.csv", encoding="utf-8-sig")):
    bs[r["sttn_id"]] = r["sttn_nm"]

name2c = {}                  # 정규화명 -> coord (대표 1개)
core2c = {}                  # 핵심명 -> coord
name2list = defaultdict(list)  # 정규화명 -> [동명 좌표들]  (오매칭 방지: 가장 가까운 후보 선택용)
core2list = defaultdict(list)
def add(nm, c):
    k = norm(nm)
    if k and k not in name2c: name2c[k] = c
    if k: name2list[k].append(c)
    kc = norm_core(nm)
    if kc and kc not in core2c: core2c[kc] = c
    if kc: core2list[kc].append(c)
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

def resolve(sid):
    if sid in xw: return xw[sid]
    nm = bs.get(sid)
    if not nm: return None
    if norm(nm) in name2c: return name2c[norm(nm)]
    c = norm_core(nm)
    if c in core2c: return core2c[c]
    # 접두 퍼지: 핵심명이 충분히 길고(≥4) 한쪽이 다른쪽을 완전포함 + 길이차≤1 일 때만
    if len(c) >= 4:
        for k, v in core2c.items():
            if len(k) >= 4 and (c in k or k in c) and abs(len(c) - len(k)) <= 1:
                return v
    return None

def candidates(sid):
    """동명 정류장 좌표 후보 리스트(오매칭 방지용). 크로스워크 직접매칭이면 그것만 신뢰."""
    if sid in xw: return [xw[sid]]
    nm = bs.get(sid)
    if not nm: return []
    k = norm(nm)
    if k in name2list: return name2list[k]
    kc = norm_core(nm)
    if kc in core2list: return core2list[kc]
    r = resolve(sid)
    return [r] if r else []

# ---------- 카드 레코드 ----------
COLS = ["rte_id", "users_type_cd", "ride_dt", "ride_sttn_id", "goff_dt",
        "goff_sttn_id", "utztn_nope", "utztn_dstnc", "brdg_hr", "trnf_cnt"]
TYPES = ["01", "02", "03", "04", "05", "06"]; TIDX = {t: i for i, t in enumerate(TYPES)}
import os as _os
_all = glob.glob("/sessions/jolly-gifted-albattani/mnt/uploads/card_records_20260407*.csv")
_f01 = sorted([f for f in _all if not f.endswith("_etc.csv")], key=lambda f: _os.path.getsize(f), reverse=True)[:1]
_fetc = [f for f in _all if f.endswith("_etc.csv")]
rows = []
for _f in _f01 + _fetc:
    _isetc = _f.endswith("_etc.csv")
    for r in csv.reader(open(_f, encoding="utf-8-sig")):
        if len(r) < 10 or r[1] == "users_type_cd": continue
        if (r[1] == "01") == _isetc: continue   # 01은 본파일에서만, 02~06은 _etc에서만
        rows.append(dict(zip(COLS, r)))
print("카드 병합:", len(rows), "행 / 파일", [_os.path.basename(f) for f in _f01+_fetc])

def mins(dt):
    """YYYYMMDDHHMMSS -> 04:00 기준 분(다음날은 +1440). 04:00 이전은 +1440 처리(심야)."""
    if len(dt) < 12: return None
    day = int(dt[6:8]); h = int(dt[8:10]); m = int(dt[10:12])
    base = (day - 7) * 1440 + h * 60 + m - 240   # 04:00 = 0
    if base < 0: base += 1440
    return base

import math
def km(o, d):
    return math.hypot((d[0]-o[0])*88.9, (d[1]-o[1])*111.0)

trips = []
res_cache = {}
def R(sid):
    if sid not in res_cache: res_cache[sid] = resolve(sid)
    return res_cache[sid]

route_idx = {}                       # rte_id -> 정수 인덱스(색상/크기용)
def RID(rid):
    if rid not in route_idx: route_idx[rid] = len(route_idx)
    return route_idx[rid]

# ---- 노선별 경유정류장 순서 → 폴리라인(정류장 좌표열) + 정류장ID→인덱스 ----
from collections import defaultdict
seq_raw = defaultdict(list); rid2no = {}
for r in csv.DictReader(open("ulsan_route_stops_20260407.csv", encoding="utf-8-sig")):
    seq_raw[r["rte_id"]].append((int(r["sttn_seq"]), r["sttn_id"]))
    rid2no[r["rte_id"]] = r.get("rte_no") or r.get("rte_nm") or r["rte_id"]

route_poly = {}     # rte_idx -> [(lon,lat), ...] (좌표 매칭된 정류장만, 순서 유지)
route_sidx = {}     # rte_idx -> {sttn_id: 폴리라인 내 인덱스}
route_nm = {}       # rte_idx -> [정류장명, ...] (폴리라인 점과 정렬)
route_sid = {}      # rte_idx -> [sttn_id, ...] (폴리라인 점과 정렬, 혼잡도 조인용)
JUMP_KM = 5.0   # 직전 정류장과 5km 넘게 떨어진 매칭은 오매칭으로 보고 제외(경로 왜곡 방지)
def build_route(rid):
    if rid in route_idx:
        return route_idx[rid]
    ri = len(route_idx); route_idx[rid] = ri
    pts = []; sidx = {}; prev = None; nms = []; sids = []
    for s, sid in sorted(seq_raw.get(rid, [])):
        cands = candidates(sid)
        if not cands: continue
        # 직전 정류장과 가장 가까운 동명 후보 선택(엉뚱한 먼 정류장 매칭 방지)
        c = min(cands, key=lambda x: km(x, prev)) if prev else cands[0]
        if prev and km(c, prev) > JUMP_KM:   # 그래도 너무 멀면 오매칭 → 건너뜀
            continue
        if sid not in sidx:
            sidx[sid] = len(pts); pts.append((round((c[0]-129)*1e4), round((c[1]-35)*1e4)))
            nms.append((bs.get(sid) or "").strip()); sids.append(sid); prev = c
    route_poly[ri] = pts; route_sidx[ri] = sidx; route_nm[ri] = nms; route_sid[ri] = sids
    return ri

def pathlen_km(ri, a, b):
    p = route_poly[ri]; lo, hi = (a, b) if a < b else (b, a)
    s = 0.0
    for i in range(lo, hi):
        x0, y0 = p[i]; x1, y1 = p[i+1]
        s += km((129+x0/1e4, 35+y0/1e4), (129+x1/1e4, 35+y1/1e4))
    return s

import bisect
tot = len(rows); ok = 0; drop_spd = 0; drop_route = 0
tmp = []                                  # (t0,t1,ri,si,ei,n, ride_sttn_id)
stop_ev = defaultdict(list)               # 정류장 -> [(승차시각, 인원)]  (정류장 승차 인원 계산용)
for r in rows:
    rid = r["rte_id"]
    if rid not in seq_raw: drop_route += 1; continue
    ri = build_route(rid)
    si = route_sidx[ri].get(r["ride_sttn_id"]); ei = route_sidx[ri].get(r["goff_sttn_id"])
    if si is None or ei is None: drop_route += 1; continue
    t0 = mins(r["ride_dt"]); t1 = mins(r["goff_dt"])
    if t0 is None: continue
    if t1 is None or t1 < t0: t1 = t0 + max(1, int(r["brdg_hr"] or 60) // 60)
    if t1 == t0: t1 = t0 + 1
    ok += 1
    dur_h = (t1 - t0) / 60.0
    if si != ei and pathlen_km(ri, si, ei) / dur_h > 80:   # 비정상 속도 제외
        drop_spd += 1; continue
    n = int(r["utztn_nope"] or 1)
    ut = TIDX.get(r["users_type_cd"], 0)
    tmp.append([t0, t1, ri, si, ei, n, r["ride_sttn_id"], ut])
    stop_ev[r["ride_sttn_id"]].append((t0, n))

# 정류장별 승차시각 정렬 + 누적합 → ±W분 승차 인원 빠르게
W = 4
for sid in stop_ev:
    stop_ev[sid].sort()
stop_ts = {sid: [t for t, _ in ev] for sid, ev in stop_ev.items()}
stop_cum = {}
for sid, ev in stop_ev.items():
    c = [0]
    for _, nn in ev: c.append(c[-1] + nn)
    stop_cum[sid] = c
def board_count(sid, t):
    ts = stop_ts[sid]; cum = stop_cum[sid]
    lo = bisect.bisect_left(ts, t - W); hi = bisect.bisect_right(ts, t + W)
    return cum[hi] - cum[lo]

# 통행 = [t0,t1, route_idx, si, ei, bcount(정류장 ±4분 승차인원), n, ut(이용자유형 0~5)]
for t0, t1, ri, si, ei, n, sid, ut in tmp:
    trips.append([t0, t1, ri, si, ei, board_count(sid, t0), n, ut])

print(f"카드 {tot} / 사용 {len(trips)} / 노선미스 {drop_route} / 과속 {drop_spd} / 노선 {len(route_idx)}")

# 표본추출(파일/성능): 최대 12만 통행. 시간분포 보존 위해 균등 추출
CAP = 120000
if len(trips) > CAP:
    import random; random.seed(7)
    trips = random.sample(trips, CAP)
    print(f"표본 {CAP}건으로 축소")
trips.sort(key=lambda t: t[0])   # 시작시각 정렬 → 런타임 포인터 활성화

# 사용된 노선만 폴리라인 배열로(인덱스 순서 유지)
routes = [route_poly[i] for i in range(len(route_idx))]
route_names = [route_nm.get(i, []) for i in range(len(route_idx))]
idx2rid = {ri: rid for rid, ri in route_idx.items()}
route_nos = [rid2no.get(idx2rid[i], "") for i in range(len(route_idx))]
route_rids = [idx2rid[i] for i in range(len(route_idx))]
route_sids = [route_sid.get(i, []) for i in range(len(route_idx))]

# 배경 격자(100m) — 컴팩트화
cells = []
for r in csv.DictReader(open("grid100_population.csv", encoding="utf-8-sig")):
    cells.append([round((float(r["lon"])-129)*1e4), round((float(r["lat"])-35)*1e4), int(r["pop"])])
vals = sorted(c[2] for c in cells); maxv = vals[int(len(vals)*0.99)]

# ---- 노선별 정보 집계(패널용): 시간별승차·정류장Top·구간재차·총연장·회전시간 ----
ri_hb = defaultdict(lambda: [0]*24)
ri_stop = defaultdict(lambda: defaultdict(int))
ri_seg = defaultdict(lambda: defaultdict(int))
for r in rows:
    rid = r["rte_id"]
    if rid not in route_idx: continue
    ri = route_idx[rid]; n = int(r["utztn_nope"] or 1); rd = r["ride_dt"]
    if len(rd) >= 10: ri_hb[ri][int(rd[8:10]) % 24] += n
    si = route_sidx[ri].get(r["ride_sttn_id"]); ei = route_sidx[ri].get(r["goff_sttn_id"])
    if si is not None: ri_stop[ri][si] += n
    if si is not None and ei is not None and si != ei:
        lo, hi = (si, ei) if si < ei else (ei, si)
        for k in range(lo, hi): ri_seg[ri][k] += n
route_info = []
for i in range(len(route_idx)):
    pts = route_poly[i]; nms = route_nm[i]
    lk = 0.0
    for j in range(len(pts)-1):
        a = (129+pts[j][0]/1e4, 35+pts[j][1]/1e4); b = (129+pts[j+1][0]/1e4, 35+pts[j+1][1]/1e4)
        lk += km(a, b)
    hb = ri_hb.get(i, [0]*24); tot = sum(hb)
    pk = round(max(sum(hb[h:h+3]) for h in range(22))/(tot/24*3), 2) if tot else 0
    sb = ri_stop.get(i, {})
    tops = sorted(((nms[k] if k < len(nms) else "", v) for k, v in sb.items()), key=lambda x: -x[1])[:8]
    sg = [ri_seg.get(i, {}).get(k, 0) for k in range(max(0, len(pts)-1))]
    route_info.append({"hb": hb, "tot": tot, "pk": pk, "tops": [[t[0], t[1]] for t in tops],
                       "sg": sg, "len": round(lk, 1), "cyc": round(lk/22*60*2),
                       "a": nms[0] if nms else "", "b": nms[-1] if nms else "", "ns": len(pts)})

data = {"trips": trips, "routes": routes, "routeNos": route_nos, "routeNames": route_names,
        "routeRids": route_rids, "routeSids": route_sids,
        "routeInfo": route_info, "cells": cells, "maxv": maxv, "nroutes": len(route_idx)}
json.dump(data, open("card_trips_20260407.json", "w"), separators=(",", ":"))
import os
print("JSON 크기 MB:", round(os.path.getsize("card_trips_20260407.json")/1e6, 2))

# ---------- HTML ----------
HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>울산 버스 승객 이동 — 시간축 (2026-04-07)</title>
<style>*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:'Apple SD Gothic Neo',system-ui,sans-serif;background:#05070f;color:#eaf0ff;overflow:hidden}
#wrap{position:relative;width:100vw;height:100vh}#c{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.panel{position:absolute;z-index:10;background:#0d1530cc;backdrop-filter:blur(7px);border:1px solid #ffffff22;border-radius:13px;padding:12px 15px}
#title{left:16px;top:40px;max-width:340px}#title h1{margin:0 0 5px;font-size:15px}#title p{margin:2px 0;font-size:11.5px;color:#b8caf0;line-height:1.5}
#clock{right:16px;top:40px;text-align:center;min-width:150px}
#clock .t{font-size:34px;font-weight:700;letter-spacing:1px;font-variant-numeric:tabular-nums}
#clock .ph{font-size:12px;margin-top:2px;color:#cfe0ff}
#clock .ride{font-size:11.5px;margin-top:6px;color:#ffd54f}
#utf{left:16px;top:172px;display:flex;flex-wrap:wrap;gap:5px;max-width:330px}
#utf button{padding:5px 9px;font-size:12px;background:#1a2647;border:1px solid #ffffff2a;border-radius:8px}
#utf button.on{background:#3a6bd5;color:#fff;border-color:#5a8bff}
#utf button .n{opacity:.6;font-size:10px;margin-left:3px}
#leg{left:16px;bottom:150px;font-size:11.5px;max-width:280px}#leg i{display:inline-block;width:14px;height:9px;margin-right:6px;border-radius:2px;vertical-align:1px}
#tip{position:absolute;z-index:20;pointer-events:none;display:none;background:#0b1226f0;border:1px solid #ffffff44;border-radius:9px;padding:7px 10px;font-size:12px;line-height:1.5;white-space:nowrap;box-shadow:0 4px 14px #000a}
#tip b{font-size:14px;color:#ffd54f}
#bar{left:16px;right:16px;bottom:16px;padding:10px 14px}
#bar .row{display:flex;align-items:center;gap:12px}
#scrub{display:block;width:100%;margin:9px 0 0;accent-color:#ffd54f}
button{background:#22305a;color:#eaf0ff;border:1px solid #ffffff33;border-radius:8px;padding:6px 12px;font-size:13px;cursor:pointer}
button:hover{background:#2c3e72}
#hist{width:100%;height:34px;margin-top:8px;display:block}
.tag{display:inline-block;background:#3a7bd522;border:1px solid #42a5f5;border-radius:6px;padding:2px 7px;font-size:10.5px;margin-top:6px}
#themeBtn{position:absolute;z-index:30;top:34px;left:50%;transform:translateX(-50%);background:#0d1530cc;color:#eaf0ff;border:1px solid #ffffff33;border-radius:9px;padding:6px 12px;font-size:12.5px;cursor:pointer}body.light{background:#eef1f7}body.light .panel{background:#ffffffe0;border-color:#0000001f;color:#1b2640;box-shadow:0 2px 10px #00000014}body.light .panel *{color:#1b2640 !important}body.light #themeBtn{background:#ffffffe0;color:#1b2640;border-color:#0000002a}body.light #tabs button,body.light #utf button,body.light #bar button,body.light #list td,body.light select{background:#e9edf6}body.light #tabs button.on{background:#3a6bd5 !important}body.light #tabs button.on *{color:#fff !important}body.light #utf button.on{background:#2aa17a !important}body.light #utf button.on *{color:#fff !important}body.light #tabs button.on,body.light #utf button.on{color:#fff !important}.popgrad{display:inline-block;width:90px;height:9px;border-radius:3px;vertical-align:-1px;margin:0 5px;background:linear-gradient(90deg,#14283c,#3a96a0,#ebcd6e)}body.light .popgrad{background:linear-gradient(90deg,#dfeed8,#78b46e,#1c683a)}</style></head><body><div id="wrap">
<canvas id="c"></canvas>
<div class="panel" id="title"><h1>울산 버스 승객 이동 · 시간축</h1>
<p>2026-04-07(화) · 교통카드 합성데이터(전 이용자유형) 표본 <b id="nT"></b>통행 · 좌측 유형 버튼으로 필터</p>
<p>점 = 운행 중 승객(승차→하차 이동) · 색 = 노선별 · 크기 = 정류장 승차 인원 · 배경 = 인구밀도 · 상단 띠 = 시간(해·달)</p>
<p style="opacity:.85">⏯ Space=재생/정지 · ◀▶=속도</p>
<span class="tag">실데이터(1차 수집분)</span> <a href="ulsan_용어설명.html" target="_blank" style="display:inline-block;margin-top:6px;margin-left:6px;font-size:11px;color:#7fb4ff">ℹ 용어 설명</a></div>
<div class="panel" id="clock"><div class="t" id="ct">--:--</div><div class="ph" id="cp"></div><div class="ride" id="cr"></div></div>
<div class="panel" id="utf"></div>
<div class="panel" id="leg"></div>
<div id="tip"></div>
<div class="panel" id="bar">
 <div class="row"><button id="play">⏸ 일시정지</button><button id="spd">속도 1×</button>
  <span style="flex:1"></span><span style="font-size:11px;opacity:.7">Space 재생/정지 · ◀▶ 속도</span></div>
 <input type="range" id="scrub" min="0" max="1440" value="0">
 <canvas id="hist"></canvas></div>
</div>
<script>
const D=__DATA__;
const c=document.getElementById('c'),x=c.getContext('2d');let W,H,dpr=devicePixelRatio||1;
function rs(){W=c.clientWidth;H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;x.setTransform(dpr,0,0,dpr,0,0);}addEventListener('resize',rs);rs();
const T=D.trips, N=T.length; document.getElementById('nT').textContent=N.toLocaleString();
const LON=v=>129+v/1e4, LAT=v=>35+v/1e4;
// 노선 폴리라인 복원: R2[ri]=[[lon,lat],...], CUM[ri]=누적거리(평면근사)
const latC0=35.55, KX0=Math.cos(latC0*Math.PI/180);
const R2=[], CUM=[];
for(const poly of D.routes){
 const pts=poly.map(p=>[LON(p[0]),LAT(p[1])]);
 const cum=[0];for(let i=1;i<pts.length;i++){const dx=(pts[i][0]-pts[i-1][0])*KX0,dy=(pts[i][1]-pts[i-1][1]);cum.push(cum[i-1]+Math.hypot(dx,dy));}
 R2.push(pts);CUM.push(cum);}
// 경로 위 위치: ri 노선의 si→ei 정류장 구간을 거리비율 f로 보간
function posOn(ri,si,ei,f){const p=R2[ri],cum=CUM[ri];
 if(!p||!p.length)return null;
 if(si>=p.length)si=p.length-1; if(ei>=p.length)ei=p.length-1;
 if(si===ei)return p[si];
 const tD=cum[si]+(cum[ei]-cum[si])*f, lo=Math.min(si,ei),hi=Math.max(si,ei);
 let k=lo;while(k<hi-0&&cum[k+1]<tD)k++;
 if(k>=p.length-1)return p[p.length-1];
 const seg=cum[k+1]-cum[k]||1e-9,g=(tD-cum[k])/seg;
 return [p[k][0]+(p[k+1][0]-p[k][0])*g, p[k][1]+(p[k+1][1]-p[k][1])*g];}
// 경계: 노선 + 격자 전체
let mnx=1e9,mxx=-1e9,mny=1e9,mxy=-1e9;
for(const poly of D.routes)for(const p of poly){mnx=Math.min(mnx,p[0]);mxx=Math.max(mxx,p[0]);mny=Math.min(mny,p[1]);mxy=Math.max(mxy,p[1]);}
for(const cl of D.cells){mnx=Math.min(mnx,cl[0]);mxx=Math.max(mxx,cl[0]);mny=Math.min(mny,cl[1]);mxy=Math.max(mxy,cl[1]);}
const B={mnLon:LON(mnx),mxLon:LON(mxx),mnLat:LAT(mny),mxLat:LAT(mxy)};
const pad=46,latC=(B.mnLat+B.mxLat)/2,kx=Math.cos(latC*Math.PI/180);
let sc,ox,oy;function fit(){const dW=(B.mxLon-B.mnLon)*kx,dH=(B.mxLat-B.mnLat);sc=Math.min((W-pad*2)/dW,(H-pad*2)/dH);ox=(W-dW*sc)/2;oy=(H-dH*sc)/2;}
let Z=1,TX=0,TY=0;addEventListener('wheel',e=>{if(e.target.closest&&e.target.closest('.panel'))return;e.preventDefault();const cx=e.clientX,cy=e.clientY,f=e.deltaY<0?1.15:1/1.15,Zn=Math.min(25,Math.max(1,Z*f));TX=cx-(cx-TX)/Z*Zn;TY=cy-(cy-TY)/Z*Zn;Z=Zn;},{passive:false});let _dg=null;addEventListener('mousedown',e=>{if(e.target.closest&&e.target.closest('.panel'))return;_dg=[e.clientX,e.clientY,TX,TY];});addEventListener('mousemove',e=>{if(_dg){TX=_dg[2]+(e.clientX-_dg[0]);TY=_dg[3]+(e.clientY-_dg[1]);}});addEventListener('mouseup',()=>_dg=null);addEventListener('dblclick',e=>{if(e.target.closest&&e.target.closest('.panel'))return;Z=1;TX=0;TY=0;});function PX(lon,lat){return (ox+(lon-B.mnLon)*kx*sc)*Z+TX;}
function PY(lon,lat){return (H-(oy+(lat-B.mnLat)*sc))*Z+TY;}
// 시간: 0=04:00 … 1439=다음날 03:59
function hhmm(m){let mm=Math.floor(((m%1440)+1440)%1440);let h=Math.floor((mm+240)/60)%24;let mi=(mm+240)%60;return String(h).padStart(2,'0')+':'+String(mi).padStart(2,'0');}
const lerp=(a,b,f)=>a+(b-a)*f, mix3=(a,b,f)=>[lerp(a[0],b[0],f),lerp(a[1],b[1],f),lerp(a[2],b[2],f)];
// 하늘(배경) 시간색 키프레임  [분(04:00기준),[R,G,B]]  밤=검정 → 일출=푸름 → 낮=흰색 → 일몰=노을 → 밤
const SKY=[[0,[6,9,20]],[60,[14,30,72]],[110,[60,120,225]],[175,[175,205,242]],
 [240,[250,251,255]],[810,[250,251,255]],[855,[255,168,98]],[895,[245,92,38]],
 [955,[70,28,42]],[1030,[6,9,20]],[1440,[6,9,20]]];
function keyf(m){m=((m%1440)+1440)%1440;let a=SKY[0],b=SKY[SKY.length-1];
 for(let i=1;i<SKY.length;i++){if(m<=SKY[i][0]){a=SKY[i-1];b=SKY[i];break;}}
 return mix3(a[1],b[1],(m-a[0])/((b[0]-a[0])||1));}
// 낮 정도 0(밤)~1(낮): 인구 레이어 색 대비 결정에 사용
function daylight(m){m=((m%1440)+1440)%1440;
 if(m<=60||m>=1030)return 0; if(m<175)return (m-60)/115; if(m<855)return 1; if(m<955)return (955-m)/100; return 0;}
// 인구 격자 색(고정 팔레트, 다크 배경용): 저밀도 남색 → 청록 → 노랑
function PG(t,a){t=Math.min(1,Math.max(0,t));var A=[150,200,150],B=[46,150,70],C=[8,72,34],r,g,b;if(t<.55){var f=t/.55;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}else{var f=(t-.55)/.45;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}return 'rgba('+(r|0)+','+(g|0)+','+(b|0)+','+(a==null?1:a)+')';}
function pcol(v){let t=Math.log(1+Math.max(0,v))/Math.log(1+D.maxv);t=Math.min(1,t);if(document.body.classList.contains('light'))return PG(t);
 const a=[20,40,75],b=[55,150,160],c2=[235,205,110];let r,g,bl;
 if(t<.6){const f=t/.6;r=a[0]+(b[0]-a[0])*f;g=a[1]+(b[1]-a[1])*f;bl=a[2]+(b[2]-a[2])*f;}
 else{const f=(t-.6)/.4;r=b[0]+(c2[0]-b[0])*f;g=b[1]+(c2[1]-b[1])*f;bl=b[2]+(c2[2]-b[2])*f;}
 return `rgb(${r|0},${g|0},${bl|0})`;}
// 상단 하늘 띠 + 해/달
const SH=26;
function drawStrip(now){
 const g=x.createLinearGradient(0,0,W,0);
 for(const k of SKY){const r=k[1];g.addColorStop(Math.max(0,Math.min(1,k[0]/1440)),`rgb(${r[0]},${r[1]},${r[2]})`);}
 x.fillStyle=g;x.fillRect(0,0,W,SH);
 // 시각 눈금
 x.fillStyle='rgba(255,255,255,.55)';x.font='9px sans-serif';x.textAlign='center';
 for(const[lb,mm] of [['06',120],['12',480],['18',840],['00',1200]]){const px=mm/1440*W;x.fillRect(px,SH-4,1,4);x.fillText(lb,px,SH-6);}
 x.textAlign='start';
 // 해/달 마커
 const sx=((now%1440)+1440)%1440/1440*W, sy=SH/2, day=daylight(now)>0.4;
 x.save();
 if(day){x.fillStyle='#ffe27a';x.strokeStyle='#ffe27a';x.lineWidth=1.4;
  for(let i=0;i<8;i++){const an=i/8*6.283;x.beginPath();x.moveTo(sx+Math.cos(an)*8,sy+Math.sin(an)*8);x.lineTo(sx+Math.cos(an)*11,sy+Math.sin(an)*11);x.stroke();}
  x.beginPath();x.arc(sx,sy,6,0,7);x.fill();}
 else{x.fillStyle='#eef2ff';x.beginPath();x.arc(sx,sy,6,0,7);x.fill();
  x.fillStyle=SKY[0][1]?`rgb(${keyf(now)[0]|0},${keyf(now)[1]|0},${keyf(now)[2]|0})`:'#06101e';x.beginPath();x.arc(sx+2.6,sy-1.6,5.2,0,7);x.fill();}
 x.restore();
 // 띠 아래 경계선
 x.fillStyle='rgba(255,255,255,.18)';x.fillRect(0,SH,W,1);}
function phaseName(m){m=((m%1440)+1440)%1440;
 if(m<60||m>=1030)return'🌑 밤'; if(m<175)return'🌅 일출'; if(m<810)return'☀ 낮'; if(m<955)return'🌇 일몰'; return'🌑 밤';}
// 노선별 고유색(황금각 분산 → 인접 노선도 구분)
const NR=D.nroutes||320;
function routeCol(idx){const hue=(idx*137.508)%360;return `hsl(${hue.toFixed(0)},88%,50%)`;}
// 점 반지름(px): 그 노선 탑승 인원 기준. 기본(1명) 작게.
function dotR(load){return Math.min(7,0.6+Math.sqrt(load)*0.62);}
// 이용자유형 필터
const UNAMES=['일반','어린이','청소년','경로','장애','국가유공'];
let utf=-1; const pass=tr=>utf<0||tr[7]===utf;
const utTot=[0,0,0,0,0,0]; for(const t of T)utTot[t[7]]+=t[6];
(()=>{let h=`<button data-u="-1" class="on">전체</button>`;
 UNAMES.forEach((nm,i)=>{if(utTot[i]>0)h+=`<button data-u="${i}">${nm}<span class="n">${utTot[i].toLocaleString()}</span></button>`;});
 const el=document.getElementById('utf');el.innerHTML=h;
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>{utf=+b.dataset.u;el.querySelectorAll('button').forEach(z=>z.classList.toggle('on',z===b));recomputeBins();});})();
// 히스토그램(분포, 필터 반영)
const hc=document.getElementById('hist'),hx=hc.getContext('2d');
let bins=new Array(96).fill(0), hmax=1;
function recomputeBins(){bins=new Array(96).fill(0);for(const t of T){if(!pass(t))continue;bins[Math.min(95,Math.floor(((t[0]%1440)+1440)%1440/15))]+=t[6];}hmax=Math.max(1,...bins);}
recomputeBins();
function drawHist(now){const w=hc.clientWidth,h=hc.clientHeight;hc.width=w*dpr;hc.height=h*dpr;hx.setTransform(dpr,0,0,dpr,0,0);
 hx.clearRect(0,0,w,h);const bw=w/96;
 for(let i=0;i<96;i++){const bh=bins[i]/hmax*(h-4);const on=Math.floor(now/15)===i;
  hx.fillStyle=on?'#ffd54f':'#3a4a78';hx.fillRect(i*bw,h-bh,bw-0.6,bh);}
 hx.fillStyle='#9fb2dd';hx.font='9px sans-serif';
 [['06',8],['09',20],['12',32],['15',44],['18',56],['21',68],['00',80]].forEach(([lb,i])=>hx.fillText(lb,i*bw,h-1));}
// 런타임
let now=300, playing=true, speed=1; // 시작 05:00 부근
let ptr=0; // 다음 활성화할 trip 인덱스(t0 정렬)
let active=[];
const scrub=document.getElementById('scrub'),ctEl=document.getElementById('ct'),cpEl=document.getElementById('cp'),crEl=document.getElementById('cr');
function reseek(t){active=[];ptr=0;while(ptr<N&&T[ptr][0]<=t){if(T[ptr][1]>t)active.push(T[ptr]);ptr++;}now=t;}
const playBtn=document.getElementById('play'),spdBtn=document.getElementById('spd');
function setPlay(p){playing=p;playBtn.textContent=playing?'⏸ 일시정지':'▶ 재생';}
function setSpeed(s){speed=s;spdBtn.textContent='속도 '+speed+'×';}
playBtn.addEventListener('click',()=>setPlay(!playing));
spdBtn.addEventListener('click',()=>setSpeed(speed>=8?1:speed*2));
scrub.addEventListener('input',e=>{setPlay(false);reseek(+e.target.value);});
addEventListener('keydown',e=>{
 if(e.code==='Space'){e.preventDefault();setPlay(!playing);}
 else if(e.code==='ArrowRight')setSpeed(speed>=8?8:speed*2);
 else if(e.code==='ArrowLeft')setSpeed(speed<=1?1:speed/2);});
// 마우스(일시정지 시 점 호버 → 노선번호·인원)
const tip=document.getElementById('tip');let mx=-1,my=-1,mcx=0,mcy=0,crect=c.getBoundingClientRect();
addEventListener('resize',()=>crect=c.getBoundingClientRect());
addEventListener('mousemove',e=>{crect=c.getBoundingClientRect();mx=e.clientX-crect.left;my=e.clientY-crect.top;mcx=e.clientX;mcy=e.clientY;});
addEventListener('mouseout',()=>{mx=my=-1;});
(()=>{let h='<b>점 = 운행 중 승객</b><br>색 = 노선별 · 크기 = 정류장 승차 인원(±4분)<br><div style="margin:7px 0 3px">';
 [1,5,15,30,60].forEach(v=>{const d=Math.round(dotR(v)*2);h+=`<span style="display:inline-flex;flex-direction:column;align-items:center;width:42px;vertical-align:bottom"><span style="display:inline-block;width:${d}px;height:${d}px;border-radius:50%;background:#ffd54f;margin-bottom:3px"></span><span style="font-size:10px">${v}명</span></span>`;});
 h+='</div><i style="background:'+pcol(D.maxv*0.7)+'"></i>배경: 인구 밀집';document.getElementById('leg').innerHTML=h;})();
let last=performance.now();
function frame(t){const dt=(t-last)/1000;last=t;fit();
 if(playing){now+=dt*speed*6; // 1초≈6분(기본): 하루 한바퀴 약 4분
  if(now>=1440){reseek(0);} else {
   while(ptr<N&&T[ptr][0]<=now){if(T[ptr][1]>now)active.push(T[ptr]);ptr++;}
  }
  scrub.value=Math.floor(now);}
 // 배경: 항상 다크 + 인구격자(고정 팔레트로 선명하게)
 x.fillStyle=(document.body.classList.contains('light')?'#e9edf4':'#070b16');x.fillRect(0,0,W,H);
 const cpx=Math.max(2.4,(100/111000*sc)*1.5*Z);
 for(const cl of D.cells){x.fillStyle=pcol(cl[2]);
  x.fillRect(PX(LON(cl[0]))-cpx/2,PY(0,LAT(cl[1]))-cpx/2,cpx,cpx);}
 // 종료 통행 제거
 for(let i=active.length-1;i>=0;i--){if(active[i][1]<=now){active[i]=active[active.length-1];active.pop();}}
 // 점: 색=노선, 크기=승차 정류장의 그 시각(±4분) 승차 인원, 위치=경유정류장 경로 따라 이동
 // trip=[t0,t1,ri,si,ei,bcount,n]
 let people=0; const hov=!playing&&mx>=0; let hbest=1e9,htr=null;
 for(const tr of active){
  if(!pass(tr))continue;                  // 이용자유형 필터
  people+=tr[6];
  const f=(now-tr[0])/(tr[1]-tr[0]);
  const pos=posOn(tr[2],tr[3],tr[4],f<0?0:f>1?1:f); if(!pos)continue;
  const r=dotR(tr[5]),sx=PX(pos[0]),sy=PY(0,pos[1]);
  x.fillStyle=routeCol(tr[2]);x.beginPath();x.arc(sx,sy,r,0,7);x.fill();
  if(hov){const dd=(sx-mx)*(sx-mx)+(sy-my)*(sy-my),lim=Math.max(8,r+5);if(dd<hbest&&dd<lim*lim){hbest=dd;htr=tr;}}}
 // 호버 툴팁(일시정지 시)
 if(htr){const ri=htr[2];
  tip.innerHTML='<b>'+(D.routeNos[ri]||'노선')+'번</b><br>승차 정류장 승차 '+htr[5].toLocaleString()+'명<span style="opacity:.7">(±4분)</span><br><span style="opacity:.75">이 승객 '+htr[6]+'명</span>';
  tip.style.display='block';tip.style.left=(mcx>W-180?mcx-168:mcx+14)+'px';tip.style.top=(mcy+14)+'px';}
 else tip.style.display='none';
 // 상단 하늘 띠 + 해/달 (지도 위에)
 drawStrip(now);
 // HUD
 ctEl.textContent=hhmm(now);cpEl.textContent=phaseName(now);crEl.textContent='운행 중 '+people.toLocaleString()+'명';
 drawHist(((now%1440)+1440)%1440);
 requestAnimationFrame(frame);}
reseek(300);scrub.value=300;requestAnimationFrame(frame);
;(function(){var b=document.createElement('button');b.id='themeBtn';b.textContent='☀ 라이트';(document.getElementById('wrap')||document.body).appendChild(b);b.onclick=function(){document.body.classList.toggle('light');b.textContent=document.body.classList.contains('light')?'🌙 다크':'☀ 라이트';};})();;(function(){var t=document.getElementById('title');if(!t)return;var d=document.createElement('div');d.style.cssText='margin-top:7px;font-size:11px;opacity:.85';d.innerHTML='배경=인구밀도 낮음<span class="popgrad"></span>높음';t.appendChild(d);})();</script></body></html>"""
out = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_time_anim.html", "w", encoding="utf-8").write(out)
print("HTML 크기 MB:", round(len(out)/1e6, 2), "| 통행", len(trips), "| 격자", len(cells))

