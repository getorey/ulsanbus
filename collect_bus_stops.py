"""
울산 BIS 정류장 좌표 수집 (To-Do 1)
- 엔드포인트: http://openapi.its.ulsan.kr/UlsanAPI/BusStopInfo.xo
- 응답: XML  tableInfo > list > row[]  (정류장ID/명/경도/위도 등)
- 좌표 변환·격자 매칭(coord_pipeline) 후 CSV/GeoJSON 저장

사용:
    python3 collect_bus_stops.py YOUR_SERVICE_KEY

참고: openapi.its.ulsan.kr 는 발급 IP/키 기준으로 접근을 제한할 수 있어
      등록된 환경(로컬 PC 등)에서 실행해야 한다. (resultCode 20 = SERVICE ACCESS DENIED)
"""
from __future__ import annotations
import sys, json, csv
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, ".")
from coord_pipeline import to_utmk, grid_cell_id, cell_polygon_wgs84, grid_cell

BASE = "http://openapi.its.ulsan.kr/UlsanAPI/BusStopInfo.xo"

# 정류장 응답 필드 후보 (BIS 스펙: 정류장ID/정류장명/경도/위도/노선유형/비고)
LON_KEYS = ["gpslong", "longitude", "lon", "posX", "gpsX", "경도", "wgs84Lon"]
LAT_KEYS = ["gpslati", "latitude", "lat", "posY", "gpsY", "위도", "wgs84Lat"]
ID_KEYS  = ["busStopId", "stopid", "stationId", "nodeId", "정류장ID", "BUSSTOP_ID"]
NAME_KEYS= ["busStopName", "stopName", "stationNm", "정류장명", "BUSSTOP_NM"]


def fetch(service_key: str, rows: int = 10000) -> bytes:
    url = f"{BASE}?serviceKey={service_key}&numOfRows={rows}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/xml"})
    return urllib.request.urlopen(req, timeout=30).read()


def parse_rows(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    # 오류 응답 체크
    err = root.find(".//resultMsg")
    if err is not None:
        code = root.findtext(".//resultCode")
        raise RuntimeError(f"API error: {err.text} (resultCode={code})")
    rows = []
    for row in root.iter("row"):
        rows.append({child.tag: (child.text or "").strip() for child in row})
    return rows


def pick(d: dict, keys: list[str]):
    for k in keys:
        if k in d and d[k] not in ("", None):
            return d[k]
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    key = sys.argv[1]
    print("Fetching bus stops ...")
    raw = fetch(key)
    rows = parse_rows(raw)
    print(f"  rows: {len(rows)}")
    if rows:
        print(f"  fields: {list(rows[0].keys())}")

    out = []
    skipped = 0
    for r in rows:
        lon, lat = pick(r, LON_KEYS), pick(r, LAT_KEYS)
        if not lon or not lat:
            skipped += 1; continue
        lon, lat = float(lon), float(lat)
        x, y = to_utmk(lon, lat)
        out.append({
            "stop_id": pick(r, ID_KEYS),
            "stop_name": pick(r, NAME_KEYS),
            "lon": lon, "lat": lat,
            "utmk_x": round(x, 2), "utmk_y": round(y, 2),
            "cell_100": grid_cell_id(x, y, 100),
            "cell_1000": grid_cell_id(x, y, 1000),
            **r,  # 원본 필드 보존
        })
    print(f"  geocoded: {len(out)} (skipped {skipped} without coords)")

    # CSV
    if out:
        keys = list(out[0].keys())
        with open("bus_stops_with_grid.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
        # GeoJSON (정류장 포인트)
        feats = [{"type": "Feature",
                  "properties": {"stop_id": r["stop_id"], "stop_name": r["stop_name"], "cell_100": r["cell_100"]},
                  "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]}} for r in out]
        json.dump({"type": "FeatureCollection", "features": feats},
                  open("bus_stops.geojson", "w", encoding="utf-8"), ensure_ascii=False)
        print("  wrote bus_stops_with_grid.csv, bus_stops.geojson")


if __name__ == "__main__":
    main()
