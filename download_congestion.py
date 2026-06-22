"""울산 노선별 혼잡도(시간대·정류장순번별) 전량 수집
국토부 노선별 혼잡도: 1613000/RouteCongestionLevel/getRouteCongestionLevel
- 필수: opr_ymd, ctpv_cd(=31 울산), sgg_cd(시군구)  → 시군구 5개 × 페이지네이션(약 96회)
- 응답 핵심: rte_id, sttn_seq, sttn_id, tzon(시간대), cgst(혼잡도값), dow_nm(요일)
실행: python3 download_congestion.py <서비스키> --date 20260407
산출: congestion_<date>.csv  (rte_id/sttn_seq/tzon별 cgst → 노선 정보 패널 '구간 혼잡' 정확값)
"""
from __future__ import annotations
import sys, csv, json, time, argparse, urllib.request, urllib.parse, urllib.error

URL = "https://apis.data.go.kr/1613000/RouteCongestionLevel/getRouteCongestionLevel"
CTPV = "31"
SGGS = {"31110": "중구", "31140": "남구", "31170": "동구", "31200": "북구", "31710": "울주군"}
FIELDS = ["rte_id", "sttn_seq", "sttn_id", "tzon", "cgst", "dow_nm", "sgg_cd", "emd_nm", "opr_trntm"]

_last = [0.0]
def get(url, interval, retries=6):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last = None
    for a in range(retries):
        w = interval - (time.time() - _last[0])
        if w > 0: time.sleep(w)
        _last[0] = time.time()
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try: body = e.read().decode("utf-8", "ignore")[:200]
            except: pass
            if e.code == 429 or "EXCEEDS" in body.upper() or "트래픽" in body:
                raise SystemExit(f"[중단] 일일 한도 초과(HTTP {e.code}). 내일 다시: {body}")
            last = e; back = 15 * (a + 1)
            print(f"    (재시도 {a+1}/{retries}: HTTP {e.code} {body[:80]} → {back}s)"); time.sleep(back)
        except Exception as e:
            last = e; back = 15 * (a + 1)
            print(f"    (재시도 {a+1}/{retries}: {type(e).__name__} → {back}s)"); time.sleep(back)
    raise last

def items_total(d):
    b = d.get("Response", {}).get("body", {})
    it = (b.get("items") or {}).get("item")
    if it is None: it = []
    elif isinstance(it, dict): it = [it]
    return it, int(b.get("totalCount", 0) or 0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key"); ap.add_argument("--date", required=True)
    ap.add_argument("--interval", type=float, default=0.4)
    a = ap.parse_args()
    out = f"congestion_{a.date}.csv"
    rows = []
    for sgg, nm in SGGS.items():
        page = 1
        while True:
            p = {"serviceKey": a.key, "pageNo": page, "numOfRows": 1000, "dataType": "JSON",
                 "opr_ymd": a.date, "ctpv_cd": CTPV, "sgg_cd": sgg}
            d = get(URL + "?" + urllib.parse.urlencode(p), a.interval)
            if "Error" in d: print(f"  [{nm}] {d['Error']}"); break
            it, tot = items_total(d)
            rows.extend(it)
            print(f"  [{nm}] p{page}: +{len(it)} (구 {tot}, 누적 {len(rows)})")
            if page * 1000 >= tot or not it: break
            page += 1
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(FIELDS)
        for r in rows: w.writerow([r.get(k, "") for k in FIELDS])
    print(f"\n완료: {len(rows)}행 / 노선 {len({r.get('rte_id') for r in rows})}개 -> {out}")

if __name__ == "__main__":
    main()
