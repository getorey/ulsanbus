# 좌표계 변환 파이프라인 (To-Do 0-1) — 구현·검증 결과

> 작성일: 2026-06-15
> 관련: `울산_버스데이터_시각화_공간단위설계.md`

## 파일

| 파일 | 내용 |
|---|---|
| `coord_pipeline.py` | 변환·격자 매칭 모듈 (재사용 함수) |
| `validate_coord.py` | 울산 좌표 검증 스크립트 |
| `sample_grid_population.geojson` | 파이프라인 산출물 예시 (deck.gl 입력 포맷) |

## 기능

- `to_utmk(lon, lat)` / `to_wgs84(x, y)` — WGS84(EPSG:4326) ↔ UTM-K(EPSG:5179) 변환 (pyproj)
- `grid_cell_id(x, y, size)` — UTM-K 좌표 → 격자 셀 ID (`floor` 연산, point-in-grid)
- `cell_polygon_wgs84(...)` — 격자 셀 → WGS84 폴리곤 (웹 렌더용 역변환)
- `assign_points_to_grid(...)` / `aggregate_by_cell(...)` — 점 귀속 + 셀별 집계(히트맵·차감용)

## 검증 결과 (울산 5개 지점, 100m 격자)

- **왕복 변환 오차: 0.0000 mm** (WGS84→UTM-K→WGS84) → PASS
- UTM-K 좌표 범위 정상 (울산 X≈1,16~1,17M / Y≈1,72~1,73M, 한국 동부권에 부합)
- 격자 셀 매칭 정상 (예: 울산시청 → `100_1164200_1728400`)
- 셀 폴리곤 변 길이 ≈ 가로 99.6m / 세로 100.0m (목표 100m, 위도 보정에 따른 미세 차)
- 셀별 집계·GeoJSON export 정상 (5개 feature)
- 100m / 1km 격자 모두 동작 확인

## 실행

```bash
pip install pyproj --break-system-packages
python3 validate_coord.py
```

## 비고

- 대량 좌표는 SGIS `transcoord` API 대신 **로컬 pyproj**로 처리(트래픽 절감). SGIS API는 정확도 검증용으로만 대조.
- 셀 변 가로 길이가 100m에서 약간 벗어나는 것은 정상 — UTM-K 격자를 위경도로 역변환하면 경도 방향이 위도에 따라 미세하게 달라짐. 분석은 UTM-K 평면에서 수행하므로 정확도 영향 없음.
- 다음 단계: 실제 BIS 정류장 좌표 수집(To-Do 1) → 본 파이프라인에 투입.
