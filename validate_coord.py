"""좌표계 변환 파이프라인 검증 — 울산 샘플 좌표."""
import sys
sys.path.insert(0, "/sessions/jolly-gifted-albattani/mnt/Ulsan Bus")
from coord_pipeline import (
    to_utmk, to_wgs84, grid_cell_id, cell_polygon_wgs84,
    assign_points_to_grid, aggregate_by_cell, grid_cell,
)

# 울산 주요 지점 (WGS84 위경도, 대략값)
points = [
    {"name": "울산광역시청",   "lon": 129.3114, "lat": 35.5384, "count": 120},
    {"name": "태화강역",       "lon": 129.3315, "lat": 35.5546, "count": 300},
    {"name": "삼산동(남구)",   "lon": 129.3380, "lat": 35.5400, "count": 250},
    {"name": "울산대학교",     "lon": 129.2580, "lat": 35.5430, "count": 80},
    {"name": "현대중공업(동구)","lon": 129.4280, "lat": 35.5170, "count": 60},
]

print("=" * 78)
print("1) 왕복 변환 정확도 (WGS84 -> UTM-K -> WGS84)")
print("=" * 78)
max_err_m = 0.0
for p in points:
    x, y = to_utmk(p["lon"], p["lat"])
    lon2, lat2 = to_wgs84(x, y)
    # 위경도 오차를 대략 미터로 환산 (위도 1도≈111,000m, 경도 1도≈111,000*cos(lat))
    import math
    err_lat = abs(lat2 - p["lat"]) * 111_000
    err_lon = abs(lon2 - p["lon"]) * 111_000 * math.cos(math.radians(p["lat"]))
    err = math.hypot(err_lat, err_lon)
    max_err_m = max(max_err_m, err)
    print(f"  {p['name']:14s} WGS84({p['lon']:.4f},{p['lat']:.4f}) "
          f"-> UTM-K({x:,.1f},{y:,.1f}) 왕복오차 {err*100:.4f} cm")
print(f"\n  최대 왕복 오차: {max_err_m*1000:.4f} mm  -> {'PASS (<1cm)' if max_err_m < 0.01 else 'CHECK'}")

print()
print("=" * 78)
print("2) 격자 셀 매칭 (100m 격자)")
print("=" * 78)
assigned = assign_points_to_grid(points, size=100)
for r in assigned:
    print(f"  {r['name']:14s} UTM-K({r['utmk_x']:,.1f},{r['utmk_y']:,.1f}) -> cell {r['cell_id']}")

print()
print("=" * 78)
print("3) 격자 셀 폴리곤(WGS84) — 시청 예시 (deck.gl 렌더용)")
print("=" * 78)
x0, y0 = to_utmk(points[0]["lon"], points[0]["lat"])
cx, cy = grid_cell(x0, y0, 100)
poly = cell_polygon_wgs84(cx, cy, 100)
for i, (lon, lat) in enumerate(poly):
    print(f"  corner{i}: ({lon:.6f}, {lat:.6f})")
# 셀 한 변의 실제 길이 확인 (렌더 좌표가 ~100m 사각형인지)
import math
d_lat = (poly[3][1]-poly[0][1]) * 111_000
d_lon = (poly[1][0]-poly[0][0]) * 111_000 * math.cos(math.radians(points[0]["lat"]))
print(f"  셀 변 길이 ~= 가로 {d_lon:.1f} m / 세로 {d_lat:.1f} m (목표 100m)")

print()
print("=" * 78)
print("4) 셀별 집계 (히트맵/차감용)")
print("=" * 78)
agg = aggregate_by_cell(assigned, value_key="count", size=100)
for cid, v in agg.items():
    print(f"  {cid}: value={v['value']} (폴리곤 꼭짓점 {len(v['polygon_wgs84'])}개)")

print()
print("=" * 78)
print("5) 1km 격자 비교")
print("=" * 78)
for r in assign_points_to_grid(points, size=1000):
    print(f"  {r['name']:14s} -> cell {r['cell_id']}")
