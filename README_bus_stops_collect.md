# BIS 정류장 좌표 수집 (To-Do 1) — 진행 상황

> 작성일: 2026-06-15

## 확인된 사항 (완료)

- **엔드포인트**: `http://openapi.its.ulsan.kr/UlsanAPI/BusStopInfo.xo`
- **파라미터**: `serviceKey`, `numOfRows` (예: 10000)
- **응답 구조(XML)**: `tableInfo > list > row[]` — 각 row가 정류장 1건
- **수집 스크립트**: `collect_bus_stops.py` 작성 완료
  - XML 파싱 → 좌표(경도·위도) 추출 → `coord_pipeline`로 UTM-K 변환·격자(100m/1km) 매칭
  - 산출: `bus_stops_with_grid.csv`, `bus_stops.geojson`
- 엔드포인트/오퍼레이션 명은 공개 예제 코드(GitHub hatoba29/ulsanbus)에서 교차 확인

## 막힌 부분 (사용자 조치 필요)

제공된 인증키로 실제 호출 시 다음 응답이 반환됨:

```xml
<Response><error>
  <resultMsg>SERVICE ACCESS DENIED ERROR.</resultMsg>
  <resultCode>20</resultCode>
</error></Response>
```

`resultCode 20 = 서비스 접근 거부`. 추정 원인과 조치:

1. **키 활성화 지연** — 활용신청 승인일이 오늘(2026-06-15). data.go.kr/ITS 키는 승인 후 수십 분~수 시간(때로는 익일) 뒤 활성화됨. → 잠시 후 재시도.
2. **키 종류 불일치** — `openapi.its.ulsan.kr`(울산 ITS 직접 포털)는 data.go.kr 일반 인증키와 별개의 키를 요구할 수 있음. 현재 키는 국토부 data.go.kr 건과 동일값이라, ITS 포털 발급 키인지 확인 필요. → 울산 BIS가 data.go.kr 경유라면 `apis.data.go.kr` 계열 엔드포인트와 data.go.kr 키 조합도 점검.
3. **IP 제한** — 일부 기관 API는 신청 시 등록한 IP에서만 호출 허용. → 등록 IP(로컬 PC)에서 실행.
4. **인코딩 키** — Encoding/Decoding 키 중 구동되는 값 사용(현재 키는 특수문자 없는 hex라 인코딩 영향은 적음).

> 참고: 본 작업 샌드박스는 해당 API가 IP 차단(403)되어 직접 수집 불가. **등록 IP 환경(로컬)에서 아래 명령으로 실행**하면 됩니다.

## 실행 방법 (키 활성화 후, 로컬)

```bash
pip install pyproj
python3 collect_bus_stops.py <서비스키>
# -> bus_stops_with_grid.csv, bus_stops.geojson 생성
```

## 빠른 점검 (브라우저)

아래 URL을 브라우저에 붙여 응답이 `SERVICE ACCESS DENIED`가 아니라 `<row>...`로 나오면 키 활성화 완료:

```
http://openapi.its.ulsan.kr/UlsanAPI/BusStopInfo.xo?serviceKey=<서비스키>&numOfRows=3
```

## 다음 단계

- 키 활성화 확인 → `collect_bus_stops.py` 실행 → 정류장 마스터 확보
- 이후: 노선정보(`RouteInfo.xo`)·노선별 정류장(`AllRouteDetailInfo.xo`) 수집 → 노선 형상 구성
