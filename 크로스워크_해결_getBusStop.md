# 정류장ID 크로스워크 해결 — 국토교통부 BusStop API

> 작성일: 2026-06-15 · 상태: **해결(검증 완료)**

## 결론
카드 OD의 정류장ID(`ride_sttn_id`/`goff_sttn_id`)는 **국토교통부_버스정류장(BusStop) API의 `sttn_id`와 동일**하다.
BusStop이 `sttn_id ↔ 정류장명(sttn_nm) ↔ 행정동(emd)`을 제공하므로, 정류장명으로 좌표(위치 파일/BIS)에 연결하면 카드 OD를 지도에 올릴 수 있다.

검증: 카드 표본 정류장ID 10개 → BusStop sttn_id **10/10 일치**.
- 3101480 = 현대중공업미포문(서부동), 3100144 = 현대중공업울산대학병원(서부동), 3101442 = 동부경찰서(전하동) … (카드 노선 31001122 = 동구 노선과 정확히 부합)

## BusStop API 사양 (검증됨)
- End Point: `https://apis.data.go.kr/1613000/BusStop`
- 오퍼레이션: `/getBusStop`
- data.go.kr: 국토교통부_버스정류장 (15142032)
- **필수 파라미터**: `serviceKey`, `pageNo`, `numOfRows`, `dataType`, **`opr_ymd`(운행일자)**, **`ctpv_cd`(시도코드)**, **`sgg_cd`(시군구코드)**
  - `emd_cd`(읍면동)는 선택. 잘못된 값 입력 시 code 51(INVALID_PARAMETER)
  - 누락 시 code 52(MISSING_REQUIRED_PARAMETER)
- 검증 호출 예: `opr_ymd=20260101&ctpv_cd=31&sgg_cd=31110` → 중구 339개 정상 반환
- **응답 필드**: `opr_ymd, sttn_id, sttn_nm, sttn_ars_no, ctpv_cd, sgg_cd, emd_cd, ctpv_nm, sgg_nm, emd_nm`
  - ⚠️ 좌표(위경도) 없음. `sttn_ars_no`는 대부분 빈값('~'). → 좌표는 정류장명 매칭으로 확보.

## 울산 시군구 코드 (sgg_cd)
| 코드 | 지역 | 정류장 수 |
|---|---|---|
| 31110 | 중구 | 339 |
| 31140 | 남구 | 564 |
| 31170 | 동구 | 281 |
| 31200 | 북구 | 397 |
| 31710 | 울주군 | 890 |
| (합계) | 울산 | 2,471 |

## 좌표 연결(크로스워크 체인)
```
카드 OD: ride_sttn_id (예 3101480)
   = BusStop sttn_id  →  sttn_nm "현대중공업미포문" + emd_nm "서부동"
   →  정류장명 매칭  →  위치 파일/BIS 의 (정류장명 → 위경도)
   →  좌표 확보 →  OD 이동선(deck.gl) 렌더
```

## 시도코드(ctpv_cd) — 울산 = 31
`11`서울 `26`부산 `27`대구 `28`인천 `29`광주 `30`대전 **`31`울산** `36`세종 `41`경기 `43`충북 `44`충남 `45`전북 `46`전남 `47`경북 `48`경남 `50`제주
(주의: 예시 문서의 `ctpv_cd=11`은 서울. 울산은 31.)

## BusRoute API (노선 목록) — 검증됨
- End Point: `https://apis.data.go.kr/1613000/BusRoute/getBusRoute`
- **필수 파라미터**: `serviceKey, pageNo, numOfRows, dataType, opr_ymd, ctpv_cd`  (sgg_cd 넣으면 51 오류)
- 검증: `opr_ymd=20260101&ctpv_cd=31` → **울산 919개 노선**, 카드 rte_id(31001122) 포함 확인
- 응답 필드: `opr_ymd, ctpv_cd, sgg_cd, rte_id, rte_no, rte_nm, dptre_sttn_id, dptre_sttn_nm, arvl_sttn_id, arvl_sttn_nm`
- → 카드 OD를 **전 노선으로 확장**할 때 이 rte_id 목록을 사용. (`build_crosswalk_and_od.py --routes ALL`)

## 함께 제공되는 동일 계열 기준데이터 (1613000)
- `/BusStop/getBusStop` — 정류장(본 문서)
- `/BusRoute/...` — 노선 기준정보
- `/PublicTransportationUserType/...` — 이용자유형 코드
- `/PublicTransportationMode/...` — 교통수단 코드
- (참고) `/BusRoutespecificStopInformation/getBusRoutespecificStopInformation` — 노선별 경유정류장(현재 키 미신청 시 Forbidden)

## 비고
- apis.data.go.kr 는 본 작업 샌드박스에서 차단 → 실제 수집은 사용자 환경(브라우저/로컬)에서 실행.
- 전체 자동화는 `build_crosswalk_and_od.py` 참조.
