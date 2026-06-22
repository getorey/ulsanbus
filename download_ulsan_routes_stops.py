"""
울산(시도코드 31) 전체 '버스노선' + '버스정류장' 마스터 다운로드
- 노선별 일일이 호출 불필요. getBusRoute(노선)·getBusStop(정류장) 페이지 호출만으로 전체 수집.
- 가이드(v1.2) 확인: numOfRows 최대 1000/페이지.
  · getBusRoute 필수: opr_ymd, ctpv_cd  (rte_id 선택)
  · getBusStop  필수: opr_ymd, ctpv_cd, sgg_cd  (sttn_id/emd_cd 선택)

실행(맥 터미널):
  cd ~/Documents/Claude/Projects/"Ulsan Bus"
  python3 download_ulsan_routes_stops.py <서비스키>            # 기본 2026-04-07
  python3 download_ulsan_routes_stops.py <서비스키> --date 20260407
산출: ulsan_routes_<date>.csv (노선), ulsan_busstops_<date>.csv (정류장)
"""
from __future__ import annotations
import sys, csv, json, argparse, urllib.request, urllib.parse

CTPV = "31"  # 울산
SGG = {"31110": "중구", "31140": "남구", "31170": "동구", "31200": "북구", "31710": "울주군"}
ROUTE = "https://apis.data.go.kr/1613000/BusRoute/getBusRoute"
STOP = "https://apis.data.go.kr/1613000/BusStop/getBusStop"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def items(d):
    b = d.get("Response", {}).get("body", {})
    it = (b.get("items") or {}).get("item")
    if it is None: return [], int(b.get("totalCount", 0))
    if isinstance(it, dict): it = [it]
    return it, int(b.get("totalCount", 0))


def fetch_all(base, fixed):
    out, page = [], 1
    while True:
        p = dict(fixed); p.update({"pageNo": page, "numOfRows": 1000, "dataType": "JSON"})
        d = get(base + "?" + urllib.parse.urlencode(p))
        if "Error" in d:
            raise RuntimeError(f"{base}: {d['Error']} params={fixed}")
        it, tot = items(d)
        out.extend(it)
        if page * 1000 >= tot or not it: break
        page += 1
    return out


def save(rows, path):
    if not rows:
        print("  (빈 결과)", path); return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow({k: r.get(k, "") for k in keys})
    print(f"  -> {path} ({len(rows)}행)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key")
    ap.add_argument("--date", default="20260407")
    a = ap.parse_args()

    print(f"[1] 버스노선 (울산 ctpv_cd=31, {a.date}) ...")
    routes = fetch_all(ROUTE, {"serviceKey": a.key, "opr_ymd": a.date, "ctpv_cd": CTPV})
    save(routes, f"ulsan_routes_{a.date}.csv")

    print(f"[2] 버스정류장 (울산 5개 시군구, {a.date}) ...")
    stops = []
    for sgg, nm in SGG.items():
        s = fetch_all(STOP, {"serviceKey": a.key, "opr_ymd": a.date, "ctpv_cd": CTPV, "sgg_cd": sgg})
        print(f"    {nm}({sgg}): {len(s)}")
        stops.extend(s)
    save(stops, f"ulsan_busstops_{a.date}.csv")
    print("완료. 호출 횟수: 노선 1~2 + 정류장 5 ≈ 6~7회 (일일 한도 내).")


if __name__ == "__main__":
    main()
