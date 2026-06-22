"""
좌표계 변환 + 격자 셀 매칭 파이프라인
- WGS84(EPSG:4326, 위경도) <-> UTM-K(EPSG:5179, GRS80, 미터)
- 점 -> 격자 셀 매칭(point-in-grid, floor 연산)
- 격자 셀 경계 폴리곤(WGS84) 생성 -> deck.gl/GeoJSON 렌더용

울산 버스 인구이동 시각화 프로젝트 (2026-06)
의존성: pyproj, (선택) pandas
"""
from __future__ import annotations

from pyproj import Transformer

# WGS84(위경도) <-> UTM-K. always_xy=True 이면 (경도, 위도) 순서.
_TO_UTMK = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
_TO_WGS84 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)


def to_utmk(lon: float, lat: float) -> tuple[float, float]:
    """WGS84 경도/위도 -> UTM-K (X, Y) 미터."""
    x, y = _TO_UTMK.transform(lon, lat)
    return x, y


def to_wgs84(x: float, y: float) -> tuple[float, float]:
    """UTM-K (X, Y) 미터 -> WGS84 (경도, 위도)."""
    lon, lat = _TO_WGS84.transform(x, y)
    return lon, lat


def grid_cell(x: float, y: float, size: int = 100) -> tuple[int, int]:
    """UTM-K 좌표가 속한 격자 셀의 좌측하단(원점) 좌표. size=셀크기(m)."""
    cell_x = int(x // size) * size
    cell_y = int(y // size) * size
    return cell_x, cell_y


def grid_cell_id(x: float, y: float, size: int = 100) -> str:
    """격자 셀 고유 ID. 예: '100_990300_1817500'."""
    cx, cy = grid_cell(x, y, size)
    return f"{size}_{cx}_{cy}"


def cell_polygon_wgs84(cell_x: int, cell_y: int, size: int = 100) -> list[tuple[float, float]]:
    """격자 셀(UTM-K 원점)을 WGS84 폴리곤 [(lon,lat)...] 으로 변환. 렌더용."""
    corners_utmk = [
        (cell_x, cell_y),
        (cell_x + size, cell_y),
        (cell_x + size, cell_y + size),
        (cell_x, cell_y + size),
        (cell_x, cell_y),  # 닫기
    ]
    return [to_wgs84(px, py) for px, py in corners_utmk]


def assign_points_to_grid(points: list[dict], size: int = 100) -> list[dict]:
    """
    점 리스트를 격자에 귀속. 각 점 dict는 'lon','lat' 키 필요.
    반환: 입력 dict에 utmk_x, utmk_y, cell_id 추가.
    """
    out = []
    for p in points:
        x, y = to_utmk(p["lon"], p["lat"])
        rec = dict(p)
        rec["utmk_x"], rec["utmk_y"] = round(x, 2), round(y, 2)
        rec["cell_id"] = grid_cell_id(x, y, size)
        out.append(rec)
    return out


def aggregate_by_cell(assigned: list[dict], value_key: str = "count", size: int = 100) -> dict:
    """셀별 값 집계 + 셀 폴리곤(WGS84) 반환. 히트맵/차감 계산용."""
    agg: dict[str, dict] = {}
    for r in assigned:
        cid = r["cell_id"]
        if cid not in agg:
            _, cx, cy = cid.split("_")
            cx, cy = int(cx), int(cy)
            agg[cid] = {
                "cell_id": cid,
                "cell_x": cx,
                "cell_y": cy,
                "value": 0,
                "polygon_wgs84": cell_polygon_wgs84(cx, cy, size),
            }
        agg[cid]["value"] += r.get(value_key, 1)
    return agg
