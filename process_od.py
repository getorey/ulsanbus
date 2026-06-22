"""
교통카드 OD 레코드 -> 정류장쌍 흐름 집계 + 시간대 분포 + (좌표 있으면) 격자/라인 GeoJSON
입력: collect_card_data.py 의 CSV 또는 sample_card_od.json
정류장 좌표(stop_coords.csv: stop_id,lon,lat)가 있으면 지도용 산출물까지 생성.
"""
from __future__ import annotations
import sys, json, csv, os
from collections import Counter, defaultdict

sys.path.insert(0, ".")
try:
    from coord_pipeline import to_utmk, grid_cell_id
    HAS_COORD = True
except Exception:
    HAS_COORD = False


def load_records(path):
    if path.endswith(".json"):
        return json.load(open(path, encoding="utf-8"))["items"]
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def hour_of(dt):  # 'YYYYMMDDHHMMSS' -> HH
    return int(dt[8:10]) if len(dt) >= 10 else None


def main(path, coords_path=None):
    recs = load_records(path)
    print(f"records: {len(recs)}")

    # 1) 정류장쌍 OD 흐름
    od = Counter()
    hourly = Counter()
    for r in recs:
        o, d = r["ride_sttn_id"], r["goff_sttn_id"]
        n = int(r.get("utztn_nope", 1) or 1)
        od[(o, d)] += n
        h = hour_of(r["ride_dt"])
        if h is not None:
            hourly[h] += n

    print("\n[상위 OD 정류장쌍]")
    for (o, d), c in od.most_common(8):
        tag = "  (동일정류장)" if o == d else ""
        print(f"  {o} -> {d}: {c}{tag}")

    print("\n[시간대별 승차 인원]")
    for h in sorted(hourly):
        bar = "#" * hourly[h]
        print(f"  {h:02d}시: {hourly[h]:2d} {bar}")

    # 2) OD CSV 저장
    with open("od_edges.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["origin","dest","trips"])
        for (o, d), c in od.most_common():
            w.writerow([o, d, c])
    print("\nwrote od_edges.csv")

    # 3) 좌표 있으면 지도 산출물
    if coords_path and os.path.exists(coords_path) and HAS_COORD:
        coords = {}
        with open(coords_path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                coords[r["stop_id"]] = (float(r["lon"]), float(r["lat"]))
        # OD 라인 GeoJSON (deck.gl ArcLayer/PathLayer)
        feats = []
        for (o, d), c in od.items():
            if o in coords and d in coords and o != d:
                feats.append({"type":"Feature","properties":{"trips":c},
                    "geometry":{"type":"LineString","coordinates":[list(coords[o]),list(coords[d])]}})
        json.dump({"type":"FeatureCollection","features":feats},
                  open("od_lines.geojson","w",encoding="utf-8"), ensure_ascii=False)
        print(f"wrote od_lines.geojson ({len(feats)} lines)")
    else:
        print("\n(정류장 좌표 stop_coords.csv 확보 후 재실행하면 od_lines.geojson 생성)")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_card_od.json"
    coords = sys.argv[2] if len(sys.argv) > 2 else "stop_coords.csv"
    main(path, coords)
