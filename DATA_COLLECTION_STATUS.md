# 데이터 수집 현황

> 업데이트: 2026-06-15

## 요약

| 소스 | 상태 | 비고 |
|---|---|---|
| 국토부 교통카드 합성데이터(울산) | ✅ **작동 검증 완료** | resultCode 200, OD 데이터 정상 수집 |
| 정류소 위치 정보 CSV(다운로드) | ✅ **가공 완료** | 3,960개 정류소 좌표·격자화 |
| 울산 BIS 정류장정보 API | ⛔ **접근 거부** | resultCode 20 (크로스워크용으로 여전히 필요할 수 있음) |

> ⚠️ **핵심 이슈 — 정류장 ID 체계 불일치**: 교통카드 OD의 정류장ID는 **7자리(예: 3101480)**, 다운로드 CSV의 `서비스아이디`는 **5자리(예: 40117)**. 둘 사이 직접 매칭 **0건**, 산술 변환도 불가. → OD를 지도에 올리려면 **크로스워크(7자리 표준ID ↔ 좌표)**가 필요. 상세 §3 참조.

---

## 1. 국토부 교통카드 합성데이터 — ✅ 작동

- 엔드포인트: `https://apis.data.go.kr/1613000/RegionalTransportationCardUsageSyntheticData/getUlsanTransportationCardUsageSyntheticData`
- **필수 파라미터**: serviceKey, pageNo, numOfRows, dataType, opr_ymd, **rte_id, users_type_cd, ride_ctpv_cd**
  - 누락 시 `code 52 MISSING_REQUIRED_PARAMETER`
  - `ride_ctpv_cd=31` (울산)
- 응답: `Response.body.items.item[]`, `Response.body.totalCount`
- 검증 호출: rte_id=31001122, opr_ymd=20260101, users_type_cd=01 → **54건 정상 반환**

### 산출 파일
- `collect_card_data.py` — 노선·이용자유형 순회 수집 (로컬 실행용; 샌드박스는 apis.data.go.kr 프록시 차단)
- `sample_card_od.json` — 라이브 검증 샘플(54건 중 15건)
- `process_od.py` — OD 정류장쌍 집계 + 시간대 분포 + (좌표 확보 시) `od_lines.geojson`
- `od_edges.csv` — 샘플 OD 집계 결과

### 검증 실행 결과(샘플 15건)
- 17시 승차 피크 확인, 상위 OD쌍 집계 정상
- 좌표(BIS) 확보 시 `od_lines.geojson`(deck.gl Arc/Path) 자동 생성

### 수집 설계 메모
- `rte_id` 필수 → **노선 목록 선확보 후 노선별 순회** 필요(노선목록은 BIS 노선정보 또는 카드데이터의 rte_id 집합)
- 일일 트래픽 1000회 → 날짜×노선×이용자유형 조합 수 관리, 페이지네이션(totalCount) 처리

---

## 1-2. 정류소 위치 정보 CSV — ✅ 가공 완료

- 원본: `울산광역시_버스 정류소 위치 정보_20260522.CSV` (EUC-KR, 3,972행)
- 컬럼: 정류장명, 위도, 경도, 관리부서, **서비스아이디(5자리)**, 권역
- 가공: 유효 3,960개 → 좌표 정리 + UTM-K 변환 + 격자(100m/1km) 매칭

### 산출 파일
- `stops_master.csv` — 정류소 마스터(좌표·UTM-K·격자·권역)
- `stops.geojson` — 정류소 포인트 (3,960개)
- `stops_density_grid100.geojson` — 100m 격자 정류소 밀도 (2,711셀) → 배경 레이어 시연용
- `stop_coords.csv` — `stop_id,lon,lat` (process_od 입력용)

권역 분포: 울주군 1,611 / 남구 684 / 북구 532 / 중구 440 / 동구 337 / (양산·경주·부산 일부)

---

## 3. ⚠️ 정류장 ID 크로스워크 (미해결 — 다음 관문)

- **문제**: 카드 OD `ride_sttn_id/goff_sttn_id`(7자리, 3101480) ↔ 위치 CSV `서비스아이디`(5자리, 40117). 교집합 0건.
- **영향**: 현재 `process_od.py` + `stop_coords.csv` 로 OD 라인 생성 시 **0 lines**(매칭 실패). 즉 OD를 지도에 직접 못 올림.
- **원인**: 카드데이터는 국토부 **표준 정류장ID(7자리)**, 위치 CSV는 울산 **BIS 서비스아이디(5자리)** — 별개 체계.

### 검증 결과 (2026-06-15, 다운로드 파일 2종 대조)
- 전국 정류장 파일 `모바일단축번호` ∩ 울산 위치파일 `서비스아이디` = **3,913건 일치** → 두 파일은 **동일 ID 체계**(모바일/서비스 ID).
- 카드 OD 정류장ID(7자리) ∩ 전국 `모바일단축번호` = **0건**
- 카드 OD 정류장ID(7자리) ∩ 울산 `서비스아이디` = **0건**
- 카드 OD 정류장ID(7자리, 5자리부 변환 포함) ∩ 전국 `정류장번호`(USB…) = **0건**

> **결론**: 카드 데이터는 **BIS 내부 정류장ID** 체계, 다운로드 파일 2종은 **모바일/서비스 ID** 체계 — 서로 다름. **다운로드 파일만으로는 카드 OD를 좌표에 연결 불가.**

### 유일한 해결 경로 — BIS API (활성화 대기)
- **BIS `버스정류장정보 조회`(#2)** 는 스펙상 **정류장ID + 경도 + 위도를 직접 제공**. 이 정류장ID가 카드의 7자리와 일치 → **BIS만 열리면 파일 없이 즉시 해결**.
- 만약 BIS 응답에 좌표가 비더라도: BIS `정류장ID ↔ 모바일번호`(또는 정류장명) → `ulsan_stop_coords_master.csv`(모바일ID/이름+좌표) 조인으로 **폴백 크로스워크** 가능.
- 즉 단일 의존성 = **BIS API 활성화** (현재 resultCode 20, 같은 키로 카드 API는 정상 → BIS 엔드포인트 바인딩 지연으로 판단).

### 준비된 자산
- `ulsan_stop_coords_master.csv` — 울산 3,960개 정류소(node_id, **mobile_id**, 이름, 좌표, 격자). BIS 크로스워크/배경/폴백용.
- `process_od.py` — `stop_coords.csv`(stop_id=7자리, lon, lat)만 들어오면 `od_lines.geojson` 즉시 생성.
- `collect_bus_stops.py` — BIS 활성화 시 정류장ID+좌표 수집 → 위 입력 생성.

---

## 2. 울산 BIS 정류장정보 API — ⛔ 접근 거부

- 엔드포인트: `http://openapi.its.ulsan.kr/UlsanAPI/BusStopInfo.xo` (XML, `tableInfo>list>row[]`)
- 호출 결과: `SERVICE ACCESS DENIED ERROR (resultCode 20)`
- 추정 원인: 키 활성화 지연(승인 당일) / ITS 포털 전용 키 필요 / 신청 IP 제한
- 산출: `collect_bus_stops.py` (활성화 후 로컬 실행 준비 완료)
- 상세: `README_bus_stops_collect.md`

### 빠른 점검
```
http://openapi.its.ulsan.kr/UlsanAPI/BusStopInfo.xo?serviceKey=<키>&numOfRows=3
```
`<row>`가 나오면 활성화 완료 → `python3 collect_bus_stops.py <키>` 실행.

---

## 다음 단계

1. BIS 정류장 좌표 확보(키 활성화 대기/확인) → `stop_coords.csv`(stop_id,lon,lat) 구성
2. 교통카드 OD 수집(`collect_card_data.py`)으로 다일자·다노선 확대
3. `process_od.py` 재실행 → `od_lines.geojson` 생성 → deck.gl 시각화 연결
