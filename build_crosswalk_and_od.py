"""
카드 OD → 좌표 크로스워크 → OD 이동선 생성 (전체 자동화)
검증 기반(2026-06-15):
  - 카드 ride_sttn_id == 국토교통부 BusStop sttn_id (10/10 일치)
  - getBusStop 필수: opr_ymd, ctpv_cd, sgg_cd  (응답: sttn_id, sttn_nm, emd_nm ...)
  - 좌표는 정류장명으로 위치파일/BIS와 매칭

실행(로컬, API 접근 가능 환경):
  # 울산 전노선(919개) 전체 다운로드 — 기본값 ALL
  python3 build_crosswalk_and_od.py <서비스키> --date 20260101
  # 특정 노선만:
  python3 build_crosswalk_and_od.py <서비스키> --date 20260101 --routes 31001122,31001182
입력파일: ulsan_stop_coords_master.csv (stop_name, lon, lat) — 이미 보유
산출: stop_crosswalk.csv(sttn_id,sttn_nm,emd_nm,lon,lat), od_lines.geojson, od_edges.csv
시도코드(ctpv_cd): 울산 = 31  (11서울 26부산 27대구 28인천 29광주 30대전 31울산 36세종 ...)
노선목록: getBusRoute(ctpv_cd=31) → 울산 919개 (필수: opr_ymd, ctpv_cd)
경고: 전노선 × 이용자유형 = 수천 회 호출. 일일 트래픽(개발 1000)·차단 주의, 운영계정/분할 권장.

주의: apis.data.go.kr 는 일부 환경(IP)에서 차단될 수 있음. 등록 IP/브라우저 환경에서 실행.
"""
from __future__ import annotations
import sys, csv, json, argparse, urllib.request, urllib.parse
from collections import Counter, defaultdict

CARD = ("https://apis.data.go.kr/1613000/RegionalTransportationCardUsageSyntheticData"
        "/getUlsanTransportationCardUsageSyntheticData")
BUSSTOP = "https://apis.data.go.kr/1613000/BusStop/getBusStop"
BUSROUTE = "https://apis.data.go.kr/1613000/BusRoute/getBusRoute"
# 시도코드(ctpv_cd): 11서울 26부산 27대구 28인천 29광주 30대전 31울산 ...  → 울산 = 31
CTPV = "31"
SGG = {"31110": "중구", "31140": "남구", "31170": "동구", "31200": "북구", "31710": "울주군"}
RIDE_CTPV = "31"
# 이용자유형(users_type_cd) 코드들 — 합산 수집
USER_TYPES = ["01", "02", "03", "04", "05", "06"]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def _items(d):
    body = d.get("Response", {}).get("body", {})
    it = (body.get("items") or {}).get("item")
    if it is None:
        return [], int(body.get("totalCount", 0))
    if isinstance(it, dict):
        it = [it]
    return it, int(body.get("totalCount", 0))


def fetch_busstops(key, date):
    """울산 전체 정류장: sttn_id -> (sttn_nm, emd_nm)."""
    out = {}
    for sgg in SGG:
        page = 1
        while True:
            p = {"serviceKey": key, "pageNo": page, "numOfRows": 1000, "dataType": "JSON",
                 "opr_ymd": date, "ctpv_cd": "31", "sgg_cd": sgg}
            d = _get(BUSSTOP + "?" + urllib.parse.urlencode(p))
            if "Error" in d:
                raise RuntimeError(f"BusStop {sgg}: {d['Error']}")
            items, tot = _items(d)
            for r in items:
                out[str(r["sttn_id"])] = (r.get("sttn_nm", ""), r.get("emd_nm", ""))
            if page * 1000 >= tot or not items:
                break
            page += 1
    return out


def fetch_routes(key, date):
    """울산 전체 노선 ID 목록 (getBusRoute, ctpv_cd=31). 필수: opr_ymd, ctpv_cd."""
    out, page = [], 1
    while True:
        p = {"serviceKey": key, "pageNo": page, "numOfRows": 1000, "dataType": "JSON",
             "opr_ymd": date, "ctpv_cd": CTPV}
        d = _get(BUSROUTE + "?" + urllib.parse.urlencode(p))
        if "Error" in d:
            raise RuntimeError(f"BusRoute: {d['Error']}")
        items, tot = _items(d)
        out.extend(str(r["rte_id"]) for r in items)
        if page * 1000 >= tot or not items:
            break
        page += 1
    return out


def load_coords(path="ulsan_stop_coords_master.csv"):
    """정류장명 -> (lon, lat). 동명 다수면 첫 좌표."""
    name2 = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            nm = (r.get("stop_name") or "").strip()
            try:
                lon, lat = float(r["lon"]), float(r["lat"])
            except Exception:
                continue
            name2.setdefault(nm, (lon, lat))
    return name2


def build_crosswalk(busstops, name2coord):
    """sttn_id -> (sttn_nm, emd_nm, lon, lat)."""
    cw, miss = {}, 0
    for sid, (nm, emd) in busstops.items():
        c = name2coord.get(nm)
        if c:
            cw[sid] = (nm, emd, c[0], c[1])
        else:
            miss += 1
    print(f"  crosswalk: {len(cw)} matched / {miss} name-miss (of {len(busstops)})")
    return cw


def fetch_card_od(key, date, routes, users=("01",)):
    rows = []
    for rte in routes:
        for u in users:
            page = 1
            while True:
                p = {"serviceKey": key, "pageNo": page, "numOfRows": 1000, "dataType": "JSON",
                     "opr_ymd": date, "rte_id": rte, "users_type_cd": u, "ride_ctpv_cd": RIDE_CTPV}
                d = _get(CARD + "?" + urllib.parse.urlencode(p))
                if "Error" in d:
                    print(f"  card {rte}/{u}: {d['Error']}"); break
                items, tot = _items(d)
                rows.extend(items)
                if page * 1000 >= tot or not items:
                    break
                page += 1
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key")
    ap.add_argument("--date", required=True)
    ap.add_argument("--routes", default="ALL", help="쉼표구분 rte_id, 또는 ALL(getBusRoute로 전노선)")
    ap.add_argument("--users", default=",".join(USER_TYPES))
    a = ap.parse_args()
    users = [u.strip() for u in a.users.split(",") if u.strip()]

    if a.routes.upper() == "ALL":
        print("0) BusRoute 전노선 목록 수집 (울산 ctpv_cd=31) ...")
        routes = fetch_routes(a.key, a.date)
        print(f"   노선 {len(routes)}개")
    else:
        routes = [r.strip() for r in a.routes.split(",") if r.strip()]

    print("1) BusStop 정류장 수집 ...")
    busstops = fetch_busstops(a.key, a.date)
    print(f"   정류장 {len(busstops)}개")

    print("2) 좌표 매칭(정류장명) ...")
    cw = build_crosswalk(busstops, load_coords())
    with open("stop_crosswalk.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["sttn_id", "sttn_nm", "emd_nm", "lon", "lat"])
        for sid, (nm, emd, lon, lat) in cw.items():
            w.writerow([sid, nm, emd, lon, lat])
    print("   -> stop_crosswalk.csv")

    print("3) 카드 OD 수집 ...")
    od_rows = fetch_card_od(a.key, a.date, routes, users)
    print(f"   OD 레코드 {len(od_rows)}건")

    print("4) OD 이동선 생성 ...")
    edges = Counter()
    for r in od_rows:
        o, d = str(r["ride_sttn_id"]), str(r["goff_sttn_id"])
        edges[(o, d)] += int(r.get("utztn_nope", 1) or 1)
    feats, mapped, unmapped = [], 0, 0
    for (o, d), c in edges.items():
        if o in cw and d in cw and o != d:
            feats.append({"type": "Feature", "properties": {"trips": c, "o": o, "d": d},
                          "geometry": {"type": "LineString",
                                       "coordinates": [[cw[o][2], cw[o][3]], [cw[d][2], cw[d][3]]]}})
            mapped += 1
        else:
            unmapped += 1
    json.dump({"type": "FeatureCollection", "features": feats},
              open("od_lines.geojson", "w", encoding="utf-8"), ensure_ascii=False)
    with open("od_edges.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["origin", "dest", "trips"])
        for (o, d), c in edges.most_common():
            w.writerow([o, d, c])
    print(f"   od_lines.geojson: {mapped} lines (unmapped {unmapped}) / od_edges.csv")
    print("완료.")


if __name__ == "__main__":
    main()
