"""
전체 노선 시각화 프로토타입 v3 — BIS 516개 노선 전부
입력: routes_all_encoded.txt (polyline 인코딩), ulsan_stop_coords_master.csv
출력: ulsan_bus_prototype_full.html
"""
import csv, json, re

def decode_polyline(s):
    """Google polyline decode -> [(lat,lon),...] (1e5)."""
    coords, i, lat, lon = [], 0, 0, 0
    while i < len(s):
        for is_lon in (0, 1):
            shift, result = 0, 0
            while True:
                b = ord(s[i]) - 63; i += 1
                result |= (b & 0x1f) << shift; shift += 5
                if b < 0x20: break
            d = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lon: lon += d
            else: lat += d
        coords.append((lat / 1e5, lon / 1e5))
    return coords

routes = []
raw = open("routes_all_encoded.txt", encoding="utf-8").read().strip()
# polyline 인코딩은 ASCII 63~126만 사용(숫자 48~57 없음) → '~' 뒤에 숫자가 오는 경우만 진짜 구분자
for blk in re.split(r"~(?=\d+\|)", raw):
    if "|" not in blk: continue
    no, enc = blk.split("|", 1)
    pts = decode_polyline(enc)            # (lat,lon)
    coords = [[round(lon, 5), round(lat, 5)] for lat, lon in pts]  # -> [lon,lat]
    coords = [c for c in coords if 35.0 < c[1] < 36.0 and 128.5 < c[0] < 129.9]
    if len(coords) >= 2:
        routes.append({"no": no, "coords": coords})

# 배경 정류소 밀도
stops = []
with open("ulsan_stop_coords_master.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        try: lon, lat = float(r["lon"]), float(r["lat"])
        except: continue
        if 35.40 <= lat <= 35.73 and 129.05 <= lon <= 129.48:
            stops.append([round(lon, 5), round(lat, 5)])
from collections import Counter
def ck(lon, lat, s=500): return (int(lon*88800//s), int(lat*111000//s))
dens = Counter(ck(*s) for s in stops); maxd = max(dens.values())
density = [[k[0], k[1], v] for k, v in dens.items()]

allc = [c for r in routes for c in r["coords"]]
bounds = {"minLon": min(c[0] for c in allc), "maxLon": max(c[0] for c in allc),
          "minLat": min(c[1] for c in allc), "maxLat": max(c[1] for c in allc)}

data = {"routes": routes, "density": density, "maxd": maxd, "cellsize": 500,
        "stops": stops, "bounds": bounds}

# verify route 111
r111 = next((r for r in routes if r["no"] == "111"), None)
print("routes decoded:", len(routes), "| total points:", sum(len(r["coords"]) for r in routes))
print("route 111 first pt:", r111["coords"][0] if r111 else "NONE", "(expect ~129.4098,35.4781)")
print("bounds:", bounds)

TPL = open("proto_template.html", encoding="utf-8").read()
out = TPL.replace("__DATA__", json.dumps(data, separators=(",", ":")))
open("ulsan_bus_prototype_full.html", "w", encoding="utf-8").write(out)
print("wrote ulsan_bus_prototype_full.html", round(len(out)/1024), "KB")
