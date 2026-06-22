"""
국토부 교통카드 합성데이터(울산) 수집 — 검증 완료(2026-06-15, resultCode 200)
엔드포인트: https://apis.data.go.kr/1613000/RegionalTransportationCardUsageSyntheticData
오퍼레이션: /getUlsanTransportationCardUsageSyntheticData

필수 파라미터: serviceKey, pageNo, numOfRows, dataType, opr_ymd, rte_id, users_type_cd, ride_ctpv_cd
  -> rte_id 필수이므로 노선목록을 순회. users_type_cd 도 코드별 순회.

사용:
    python3 collect_card_data.py <서비스키> --date 20260101 --routes 31001122,31001123 --users 01,02
산출: card_od_<date>.csv  (노선·이용자유형별 합산)

참고: apis.data.go.kr 는 본 작업 샌드박스에서 프록시 차단(403). 로컬/등록 환경에서 실행.
"""
from __future__ import annotations
import sys, csv, json, time, argparse
import urllib.request, urllib.parse

BASE = ("https://apis.data.go.kr/1613000/RegionalTransportationCardUsageSyntheticData"
        "/getUlsanTransportationCardUsageSyntheticData")
RIDE_CTPV_ULSAN = "31"

FIELDS = ["opr_ymd","ride_ctpv_cd","goff_ctpv_cd","clcln_bzmn_id","vr_card_no","card_se_cd",
          "clcln_bzmn_trfc_mns_cd","rte_id","ride_dt","ride_sttn_id","goff_dt","goff_sttn_id",
          "trnf_cnt","users_type_cd","utztn_nope","utztn_dstnc","brdg_hr","msv_intrpl_yn"]


def call(key, date, rte, users, page=1, rows=1000):
    p = {"serviceKey": key, "pageNo": page, "numOfRows": rows, "dataType": "JSON",
         "opr_ymd": date, "rte_id": rte, "users_type_cd": users, "ride_ctpv_cd": RIDE_CTPV_ULSAN}
    url = BASE + "?" + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    if "Error" in data:
        raise RuntimeError(f"API Error: {data['Error']}")
    hdr = data["Response"]["header"]
    if hdr.get("resultCode") not in ("200", "00"):
        raise RuntimeError(f"resultMsg: {hdr.get('resultMsg')} ({hdr.get('resultCode')})")
    body = data["Response"]["body"]
    items = body.get("items") or {}
    item = items.get("item") if isinstance(items, dict) else None
    if item is None:
        return [], int(body.get("totalCount", 0))
    if isinstance(item, dict):
        item = [item]
    return item, int(body.get("totalCount", 0))


def collect_slice(key, date, rte, users, rows=1000, pause=0.2):
    out, page = [], 1
    while True:
        items, total = call(key, date, rte, users, page, rows)
        out.extend(items)
        if page * rows >= total or not items:
            break
        page += 1
        time.sleep(pause)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key")
    ap.add_argument("--date", required=True, help="운행일자 YYYYMMDD")
    ap.add_argument("--routes", required=True, help="쉼표구분 rte_id 목록")
    ap.add_argument("--users", default="01", help="쉼표구분 users_type_cd 목록")
    ap.add_argument("--rows", type=int, default=1000)
    a = ap.parse_args()

    routes = [r.strip() for r in a.routes.split(",") if r.strip()]
    users = [u.strip() for u in a.users.split(",") if u.strip()]
    all_rows = []
    for rte in routes:
        for u in users:
            try:
                rows = collect_slice(a.key, a.date, rte, u, a.rows)
                print(f"  rte {rte} user {u}: {len(rows)} rows")
                all_rows.extend(rows)
            except Exception as e:
                print(f"  rte {rte} user {u}: ERROR {e}")

    out = f"card_od_{a.date}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
        for r in all_rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    print(f"TOTAL {len(all_rows)} rows -> {out}")


if __name__ == "__main__":
    main()
