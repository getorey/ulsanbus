"""
울산 교통카드 합성데이터(승하차+시각+정류장) 4월 7일 전 노선 일괄 수집
-----------------------------------------------------------------
국토부 OpenAPI: getUlsanTransportationCardUsageSyntheticData
- 노선(rte_id)별 호출 → 울산 전 노선(ulsan_routes_<date>.csv, 925개)을 순회해 전체 수집
- 응답 레코드 필드(원천):
    ride_dt    승차 일시 (YYYYMMDDHHMMSS)
    ride_sttn_id 승차 정류장ID
    goff_dt    하차 일시
    goff_sttn_id 하차 정류장ID
    utztn_nope 이용 인원
    utztn_dstnc 이용 거리(m)
    brdg_hr    소요 시간(초)
    trnf_cnt   환승 횟수
  → users_type_cd(이용자유형)별로 따로 옴 → 유형 루프 후 합쳐서 저장(컬럼 users_type_cd 추가)

검증 기준값(이전 라이브 테스트):
  필수 파라미터 = opr_ymd, rte_id, users_type_cd, ride_ctpv_cd
  ride_ctpv_cd(울산, data.go.kr 시도코드) = 31
  resultCode 200 = SUCCESS

실행(맥 터미널):
  cd ~/Documents/Claude/Projects/"Ulsan Bus"
  python3 download_card_records.py <서비스키> --date 20260407
  # 옵션:
  #   --routes ulsan_routes_20260407.csv   (노선목록 파일, 기본=ulsan_routes_<date>.csv)
  #   --users 01,02,03,04,05,06            (이용자유형 코드, 기본=아래 USER_TYPES)
  #   --interval 0.4                        (호출 간 최소 간격 초, 차단 시 늘리기)
  #   --resume                              (이미 받은 rte_id는 건너뛰고 이어받기)
산출: card_records_<date>.csv   (한 줄 = 통행 1건)
"""
from __future__ import annotations
import sys, os, csv, json, time, argparse, urllib.request, urllib.parse, urllib.error

URL = ("https://apis.data.go.kr/1613000/RegionalTransportationCardUsageSyntheticData/"
       "getUlsanTransportationCardUsageSyntheticData")
CTPV = "31"  # 울산 (data.go.kr 시도코드)
# 이용자유형: 01 일반 / 02 청소년 / 03 어린이 / 04 경로 / 05 장애 / 06 국가유공 (제공 유형만 자동 수집)
USER_TYPES = ["01", "02", "03", "04", "05", "06"]
REC_FIELDS = ["ride_dt", "ride_sttn_id", "goff_dt", "goff_sttn_id",
              "utztn_nope", "utztn_dstnc", "brdg_hr", "trnf_cnt"]
OUT_FIELDS = ["rte_id", "users_type_cd"] + REC_FIELDS

_last = [0.0]


class Blocked(Exception):
    """재시도해도 회복 불가(차단/한도초과) → 진행분 저장 후 종료"""


def get(url, interval, retries=6):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last = None
    for attempt in range(retries):
        wait = interval - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # 서버가 HTTP 오류코드를 명시적으로 반환 → 본문을 읽어 원인 식별
            try:
                body = e.read().decode("utf-8", "ignore")[:300]
            except Exception:
                body = ""
            up = body.upper()
            # data.go.kr 일일 트래픽 한도 초과 = 영구(오늘 더 못 부름) → 즉시 중단
            if e.code == 429 or "LIMITED_NUMBER_OF_SERVICE_REQUESTS" in up or "EXCEEDS" in up or "트래픽" in body:
                raise Blocked(f"HTTP {e.code} / 트래픽·호출한도 초과로 보임\n      서버응답: {body}")
            last = e
            back = 20 * (attempt + 1)
            print(f"      (재시도 {attempt+1}/{retries}: HTTP {e.code} → {back}s 대기 | 응답: {body[:120]})")
            time.sleep(back)
        except Exception as e:                      # 타임아웃/연결끊김 → 백오프 재시도
            last = e
            back = 20 * (attempt + 1)
            print(f"      (재시도 {attempt+1}/{retries}: {type(e).__name__} → {back}s 대기)")
            time.sleep(back)
    raise Blocked(f"재시도 {retries}회 모두 실패: {type(last).__name__} {last}")


def parse(d):
    """응답 → (items, totalCount, resultCode, resultMsg)"""
    if "Error" in d:                                 # 일부 오류는 {'Error':...} 로 옴
        return [], 0, "ERR", str(d["Error"])
    r = d.get("response") or d.get("Response") or {}
    hdr = r.get("header", {})
    body = r.get("body", {})
    it = (body.get("items") or {})
    it = it.get("item") if isinstance(it, dict) else it
    if it is None:
        it = []
    elif isinstance(it, dict):
        it = [it]
    return it, int(body.get("totalCount", 0) or 0), str(hdr.get("resultCode", "")), str(hdr.get("resultMsg", ""))


def load_routes(path):
    ids = []
    seen = set()
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rid = (r.get("rte_id") or "").strip()
            if rid and rid not in seen:
                seen.add(rid); ids.append(rid)
    return ids


def done_routes(out_csv, done_file):
    """--resume: 이미 '완료한' rte_id 집합.
    .done 매니페스트(데이터 0건 노선 포함)를 우선 사용. 없으면 CSV로 보강."""
    s = set()
    if os.path.exists(done_file):
        with open(done_file, encoding="utf-8") as f:
            s |= {ln.strip() for ln in f if ln.strip()}
    if os.path.exists(out_csv):
        # rte_id 는 항상 첫 컬럼 → 헤더 키 의존 없이 위치로 읽어 BOM/헤더 문제 회피
        with open(out_csv, encoding="utf-8-sig", newline="") as f:
            rd = csv.reader(f)
            header = next(rd, None)
            for row in rd:
                if row and row[0].strip():
                    s.add(row[0].strip())
    return s


def fetch_route_type(key, date, rid, ut, rows, interval, sink):
    """노선+유형 1조합 전건 수집(안전 페이지네이션). 행은 sink(list)에 모음.
    returns (호출수, 저장건수, 첫응답 totalCount). 중단 시 sink는 버려져 중복 방지."""
    page, calls, saved, total0 = 1, 0, 0, None
    while True:
        p = {"serviceKey": key, "pageNo": page, "numOfRows": rows, "dataType": "JSON",
             "opr_ymd": date, "rte_id": rid, "users_type_cd": ut, "ride_ctpv_cd": CTPV}
        d = get(URL + "?" + urllib.parse.urlencode(p), interval)
        calls += 1
        items, tot, code, msg = parse(d)
        if total0 is None:
            total0 = tot
        if code not in ("200", "00", "0", "") and not items:
            if code not in ("03", "99", "ERR") and page == 1:
                print(f"    [{rid}/{ut}] code={code} {msg[:40]}")
            break
        for it in items:
            sink.append([rid, ut] + [it.get(k, "") for k in REC_FIELDS])
        saved += len(items)
        if not items or saved >= tot:   # 서버가 numOfRows 줄여도 안전(누적 기준)
            break
        page += 1
    return calls, saved, (total0 or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key")
    ap.add_argument("--date", required=True)
    ap.add_argument("--routes", default=None)
    ap.add_argument("--users", default=",".join(USER_TYPES))
    ap.add_argument("--interval", type=float, default=0.4)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--rows", type=int, default=1000, help="numOfRows(페이지당 행수)")
    ap.add_argument("--all-users", action="store_true",
                    help="스마트 게이팅 끄기(빈 노선도 전 유형 호출). 기본은 켜짐")
    ap.add_argument("--tag", default="", help="출력/매니페스트 파일 접미사(다른 유형 따로 받을 때)")
    ap.add_argument("--routes-from", default=None,
                    help="이 CSV(예: 01 수집분)에 나오는 rte_id 만 대상으로(데이터 있는 노선만 → 호출 절약)")
    a = ap.parse_args()

    routes_file = a.routes or f"ulsan_routes_{a.date}.csv"
    out_csv = f"card_records_{a.date}{a.tag}.csv"
    done_file = f"card_records_{a.date}{a.tag}.done"
    users = [u.strip() for u in a.users.split(",") if u.strip()]
    rte_ids = load_routes(routes_file)
    if a.routes_from and os.path.exists(a.routes_from):
        keep = set()
        with open(a.routes_from, encoding="utf-8-sig", newline="") as rf:
            rd = csv.reader(rf); next(rd, None)
            for row in rd:
                if row and row[0].strip(): keep.add(row[0].strip())
        rte_ids = [r for r in rte_ids if r in keep]
        print(f"--routes-from: 데이터 있는 {len(rte_ids)}개 노선만 대상")
    skip = done_routes(out_csv, done_file) if a.resume else set()
    todo = [r for r in rte_ids if r not in skip]
    print(f"노선 {len(rte_ids)}개 / 이용자유형 {users} / 대상 {len(todo)}개"
          f"{' (이어받기, 기존 '+str(len(skip))+'개 완료 건너뜀)' if a.resume else ''}")
    if not todo:
        print("이미 전부 완료됨."); return

    mode = "a" if (a.resume and os.path.exists(out_csv)) else "w"
    f = open(out_csv, mode, newline="", encoding="utf-8-sig")
    w = csv.writer(f)
    if mode == "w":
        w.writerow(OUT_FIELDS)
    df = open(done_file, "a", encoding="utf-8")   # 완료 노선 매니페스트(0건 포함)

    # 스마트 게이팅: 노선마다 '01'을 먼저 보고 0건이면 나머지 유형 생략(빈 노선 호출 6→1)
    smart = (not a.all_users) and ("01" in users)
    probe = "01" if smart else users[0]
    rest = [u for u in users if u != probe]
    print(f"  스마트 게이팅: {'ON (01 0건 노선은 나머지 유형 생략)' if smart else 'OFF'} / numOfRows={a.rows}")

    total, calls = 0, 0
    try:
        for n, rid in enumerate(todo, 1):
            buf = []                                  # 노선 단위 버퍼(중단 시 통째로 버려 중복 방지)
            c, s, tot01 = fetch_route_type(a.key, a.date, rid, probe, a.rows, a.interval, buf)
            calls += c; total += s; rcnt = s
            if not (smart and tot01 == 0):           # 01이 0건이면 나머지 유형 스킵
                for ut in rest:
                    c, s, _ = fetch_route_type(a.key, a.date, rid, ut, a.rows, a.interval, buf)
                    calls += c; total += s; rcnt += s
            w.writerows(buf)                          # 노선 완료 후 한 번에 기록
            f.flush()
            df.write(rid + "\n"); df.flush()         # 노선 완료 기록(0건이어도)
            if n % 20 == 0 or n == len(todo):
                print(f"  [{n}/{len(todo)}] rte_id={rid} +{rcnt}건 (누적 {total}건 / 호출 {calls}회)")
    except Blocked as e:
        f.close(); df.close()
        print(f"\n[중단] 서버가 호출을 막았습니다 → {e}")
        print(f"진행분은 저장됨: {out_csv} (+{total}건 / 호출 {calls}회 이번 실행)")
        print("대처:")
        print("  · '트래픽/한도 초과'면 data.go.kr 일일 한도 소진 → 내일(자정 리셋) 다시 실행")
        print("  · 그 외(429/503 일시차단)면 10~30분 쉬었다가 아래로 이어받기:")
        print(f"      python3 {os.path.basename(__file__)} <KEY> --date {a.date} --resume --interval 1.0")
        sys.exit(1)
    f.close(); df.close()
    print(f"\n완료: 이번 실행 +{total}건 -> {out_csv}")
    print("후속: rte_id/시각(ride_dt)/정류장(ride_sttn_id,goff_sttn_id) 로 시간축 애니메이션 구성 가능")


if __name__ == "__main__":
    main()
