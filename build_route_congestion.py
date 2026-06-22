"""congestion_20260407.csv → 노선별 혼잡도/배차 요약 JSON
- cgst = 운행 1회차 차내 재차인원, 같은 (노선·정류장·시간대) 다중행 = 그 시간대 운행 편수
출력: route_congestion_20260407.json  { rid: {byStop:{sid:max재차}, runs[24], hwy[24], load[24], peakLoad, peakHour} }
"""
import csv, json, os
from collections import defaultdict

F = "congestion_20260407.csv"
rows = list(csv.DictReader(open(F, encoding="utf-8-sig")))
# (rid) -> tzon(hour) -> list of cgst ; (rid)->tzon->set of sttn_seq ; (rid)->sid->max
byhour = defaultdict(lambda: defaultdict(list))      # rid -> h -> [cgst...]
seqset = defaultdict(lambda: defaultdict(set))       # rid -> h -> {sttn_seq}
bystop = defaultdict(lambda: defaultdict(int))       # rid -> sid -> max cgst
for r in rows:
    rid = r["rte_id"];
    try: h = int(r["tzon"]) % 24; cg = int(r["cgst"] or 0)
    except: continue
    byhour[rid][h].append(cg)
    seqset[rid][h].add(r["sttn_seq"])
    sid = r["sttn_id"]
    if cg > bystop[rid][sid]: bystop[rid][sid] = cg

out = {}
for rid in byhour:
    runs = [0]*24; load = [0]*24; hwy = [0]*24
    for h in range(24):
        cs = byhour[rid].get(h, [])
        if not cs: continue
        nseq = max(1, len(seqset[rid][h]))
        rn = max(1, round(len(cs)/nseq))          # 그 시간대 운행 편수 추정
        runs[h] = rn
        load[h] = round(sum(cs)/len(cs), 1)       # 평균 차내 재차인원
        hwy[h] = round(60/rn)                      # 배차간격(분)
    bs = bystop[rid]
    peakLoad = max(bs.values()) if bs else 0
    # 시간대별 최대 평균재차 → peakHour
    peakHour = max(range(24), key=lambda h: load[h]) if any(load) else 0
    out[rid] = {"byStop": bs, "runs": runs, "hwy": hwy, "load": load,
                "peakLoad": peakLoad, "peakHour": peakHour}
json.dump(out, open("route_congestion_20260407.json", "w"), separators=(",", ":"), ensure_ascii=False)
print("노선", len(out), "/ JSON MB", round(os.path.getsize("route_congestion_20260407.json")/1e6, 2))
# 샘플
import statistics
rid = next(iter(out)); s = out[rid]
print("예 rid", rid, "| 배차(분) 08시", s["hwy"][8], "17시", s["hwy"][17], "| 평균재차 08시", s["load"][8], "| 최대재차", s["peakLoad"])
