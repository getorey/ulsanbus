"""모든 분석 지도 build 스크립트에 줌/팬(휠 확대·드래그 이동·더블클릭 초기화) 일괄 추가"""
HANDLERS = (
 "let Z=1,TX=0,TY=0;"
 "addEventListener('wheel',e=>{if(e.target.closest&&e.target.closest('.panel'))return;e.preventDefault();"
 "const cx=e.clientX,cy=e.clientY,f=e.deltaY<0?1.15:1/1.15,Zn=Math.min(25,Math.max(1,Z*f));"
 "TX=cx-(cx-TX)/Z*Zn;TY=cy-(cy-TY)/Z*Zn;Z=Zn;},{passive:false});"
 "let _dg=null;"
 "addEventListener('mousedown',e=>{if(e.target.closest&&e.target.closest('.panel'))return;_dg=[e.clientX,e.clientY,TX,TY];});"
 "addEventListener('mousemove',e=>{if(_dg){TX=_dg[2]+(e.clientX-_dg[0]);TY=_dg[3]+(e.clientY-_dg[1]);}});"
 "addEventListener('mouseup',()=>_dg=null);"
 "addEventListener('dblclick',e=>{if(e.target.closest&&e.target.closest('.panel'))return;Z=1;TX=0;TY=0;});"
)

# (파일, 기존PX/PY, 새PX/PY)  — arrow 형식
ARROW = [
 ("build_demand_dashboard.py","build_route_improvement.py","build_top_routes_map.py","build_anchor_stops.py"),
]
def patch(fn):
    s=open(fn,encoding="utf-8").read()
    if "let Z=1,TX=0,TY=0;" in s:
        print(fn,"이미 적용됨, 건너뜀"); return
    before=s
    # arrow 형식(mnLon)
    s=s.replace(
     "const PX=lon=>ox+(lon-mnLon)*kx*sc, PY=lat=>H-(oy+(lat-mnLat)*sc);",
     HANDLERS+"const PX=lon=>(ox+(lon-mnLon)*kx*sc)*Z+TX, PY=lat=>(H-(oy+(lat-mnLat)*sc))*Z+TY;")
    # arrow 형식(B.mnLon) - stop_boarding
    s=s.replace(
     "const PX=lon=>ox+(lon-B.mnLon)*kx*sc, PY=lat=>H-(oy+(lat-B.mnLat)*sc);",
     HANDLERS+"const PX=lon=>(ox+(lon-B.mnLon)*kx*sc)*Z+TX, PY=lat=>(H-(oy+(lat-B.mnLat)*sc))*Z+TY;")
    # function 형식 - time_anim
    s=s.replace(
     "function PX(lon,lat){return ox+(lon-B.mnLon)*kx*sc;}\nfunction PY(lon,lat){return H-(oy+(lat-B.mnLat)*sc);}",
     HANDLERS+"function PX(lon,lat){return (ox+(lon-B.mnLon)*kx*sc)*Z+TX;}\nfunction PY(lon,lat){return (H-(oy+(lat-B.mnLat)*sc))*Z+TY;}")
    # 격자 셀 크기 줌 반영
    s=s.replace("(100/111000*sc)*1.5","(100/111000*sc)*1.5*Z")
    if s==before:
        print(fn,"!! 매칭 실패(수동 확인 필요)")
    else:
        open(fn,"w",encoding="utf-8").write(s); print(fn,"패치 완료")

for fn in ["build_time_anim.py","build_demand_dashboard.py","build_route_improvement.py",
           "build_top_routes_map.py","build_stop_boarding.py","build_anchor_stops.py"]:
    patch(fn)
