"""라이트 모드 개선: 캔버스 색반전 제거 + 라이트 모드는 밝은 배경에 기존 색 사용
(저밀도 인구 셀이 밝은 배경에서 또렷이 보이도록)"""
FILES=["build_time_anim.py","build_demand_dashboard.py","build_route_improvement.py",
       "build_top_routes_map.py","build_stop_boarding.py","build_anchor_stops.py","build_usertype_demand.py"]
INVERT="body.light #c{filter:invert(1) hue-rotate(180deg)}"
OLDBG="fillStyle='#070b16';x.fillRect(0,0,W,H)"
NEWBG="fillStyle=(document.body.classList.contains('light')?'#e9edf4':'#070b16');x.fillRect(0,0,W,H)"
for fn in FILES:
    s=open(fn,encoding="utf-8").read()
    ch=False
    if INVERT in s: s=s.replace(INVERT,""); ch=True
    if OLDBG in s and NEWBG not in s: s=s.replace(OLDBG,NEWBG); ch=True
    if ch: open(fn,"w",encoding="utf-8").write(s); print(fn,"수정")
    else: print(fn,"변경없음")
