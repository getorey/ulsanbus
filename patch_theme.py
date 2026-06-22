"""모든 보드 HTML에 다크/라이트 모드 토글 추가 (build 스크립트 패치)"""
CSS = (
"#themeBtn{position:absolute;z-index:30;top:34px;left:50%;transform:translateX(-50%);"
"background:#0d1530cc;color:#eaf0ff;border:1px solid #ffffff33;border-radius:9px;padding:6px 12px;font-size:12.5px;cursor:pointer}"
"body.light{background:#eef1f7}"
"body.light #c{filter:invert(1) hue-rotate(180deg)}"
"body.light .panel{background:#ffffffe0;border-color:#0000001f;color:#1b2640;box-shadow:0 2px 10px #00000014}"
"body.light .panel *{color:#1b2640 !important}"
"body.light #themeBtn{background:#ffffffe0;color:#1b2640;border-color:#0000002a}"
"body.light #tabs button,body.light #utf button,body.light #bar button,body.light #list td,body.light select{background:#e9edf6}"
"body.light #tabs button.on{background:#3a6bd5 !important}body.light #tabs button.on *{color:#fff !important}"
"body.light #utf button.on{background:#2aa17a !important}body.light #utf button.on *{color:#fff !important}"
"body.light #tabs button.on,body.light #utf button.on{color:#fff !important}"
)
JS = (";(function(){var b=document.createElement('button');b.id='themeBtn';b.textContent='☀ 라이트';"
"(document.getElementById('wrap')||document.body).appendChild(b);"
"b.onclick=function(){document.body.classList.toggle('light');"
"b.textContent=document.body.classList.contains('light')?'🌙 다크':'☀ 라이트';};})();")

FILES = ["build_time_anim.py","build_demand_dashboard.py","build_route_improvement.py",
         "build_top_routes_map.py","build_stop_boarding.py","build_anchor_stops.py","build_usertype_demand.py"]
for fn in FILES:
    try: s=open(fn,encoding="utf-8").read()
    except FileNotFoundError: print(fn,"없음"); continue
    if "#themeBtn" in s: print(fn,"이미 적용"); continue
    if "</style>" not in s or "</script></body></html>" not in s:
        print(fn,"!! 마커 없음"); continue
    s=s.replace("</style>", CSS+"</style>", 1)
    s=s.replace("</script></body></html>", JS+"</script></body></html>", 1)
    open(fn,"w",encoding="utf-8").write(s); print(fn,"패치 완료")
