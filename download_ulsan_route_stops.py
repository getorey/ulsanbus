"""
울산 전 노선 '경유정류장(순번)' 전체 일괄 수집 → ulsan_route_stops_<date>.csv
- 핵심: getBusRoutespecificStopInformation 은 rte_id 없이 'opr_ymd+ctpv_cd+sgg_cd' 만으로
  해당 시군구의 '모든 노선' 경유정류장을 한꺼번에 돌려준다.
  → 울산 = 시군구 5개 × 페이지네이션 = 약 24회 호출이면 전체(약 21,653행) 수집 완료.
  (노선별로 4,600회 부를 필요 없음)

검증(2026-06-15): 필수 opr_ymd, ctpv_cd, sgg_cd / numOfRows 최대 1000
응답 필드: rte_id, rte_no, rte_nm, sttn_seq, sttn_id, sttn_nm, ctpv_nm, sgg_nm, emd_nm, trfc_mns_se_cd

실행(맥 터미널):
  cd ~/Documents/Claude/Projects/"Ulsan Bus"
  python3 download_ulsan_route_stops.py <서비스키> --date 20260407
산출: ulsan_route_stops_<date>.csv
  → 특정 노선 루트는 'rte_id 로 필터 후 sttn_seq 오름차순 정렬'하면 됨.
"""
from __future__ import annotations
import sys, csv, json, time, argparse, urllib.request, urllib.parse

CTPV = "31"
SGGS = {"31110": "중구", "31140": "남구", "31170": "동구", "31200": "북구", "31710": "울주군"}
RSS = "https://apis.data.go.kr/1613000/BusRoutespecificStopInformation/getBusRoutespecificStopInformation"
FIELDS = ["rte_id", "rte_no", "rte_nm", "sttn_seq", "sttn_id", "sttn_nm",
          "ctpv_nm", "sgg_nm", "emd_nm", "trfc_mns_se_cd"]


# 이 서비스는 '1분 내 5회 초과 시 임시 차단' → 호출 간 최소 간격을 둬서 분당 5회 이하 유지
MIN_INTERVAL = 13.0   # 초 (≈4.6회/분, 안전)
_last_call = [0.0]

def get(url, retries=5):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last = None
    for attempt in range(retries):
        # 속도 제한 준수: 직전 호출과 최소 간격 유지
        wait = MIN_INTERVAL - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        except Exception as e:           # 502(임시차단)/타임아웃 → 더 길게 쉬고 재시도
            last = e
            back = 20 * (attempt + 1)
            print(f"    (재시도 {attempt+1}/{retries}: {type(e).__name__} → {back}초 대기)")
            time.sleep(back)
    raise last


def items_total(d):
    b = d.get("Response", {}).get("body", {})
    it = (b.get("items") or {}).get("item")
    if it is None:
        it = []
    elif isinstance(it, dict):
        it = [it]
    return it, int(b.get("totalCount", 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    out_csv = f"ulsan_route_stops_{a.date}.csv"

    rows_all = []
    for sgg, nm in SGGS.items():
        page = 1
        while True:
            p = {"serviceKey": a.key, "pageNo": page, "numOfRows": 1000, "dataType": "JSON",
                 "opr_ymd": a.date, "ctpv_cd": CTPV, "sgg_cd": sgg}
            d = get(RSS + "?" + urllib.parse.urlencode(p))
            if "Error" in d:
                print(f"  [{nm}] API Error: {d['Error']}"); break
            it, tot = items_total(d)
            rows_all.extend(it)
            print(f"  [{nm}] page {page}: +{len(it)} (구 합계 {tot}, 전체 누적 {len(rows_all)})")
            if page * 1000 >= tot or not it:
                break
            page += 1
            time.sleep(0.1)

    # 정렬: 노선ID → 순번
    rows_all.sort(key=lambda r: (str(r.get("rte_id", "")), int(r.get("sttn_seq", 0) or 0)))
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(FIELDS)
        for r in rows_all:
            w.writerow([r.get(k, "") for k in FIELDS])
    routes = len({r.get("rte_id") for r in rows_all})
    print(f"\n완료: {len(rows_all)}행 / 노선 {routes}개 -> {out_csv}")


if __name__ == "__main__":
    main()
