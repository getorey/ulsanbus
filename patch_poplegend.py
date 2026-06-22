# -*- coding: utf-8 -*-
"""인구 격자 범례 추가 + 라이트 모드 인구색을 초록 계열로 (푸른색 대신)"""
PG=("function PG(t,a){t=Math.min(1,Math.max(0,t));var A=[223,236,216],B=[120,180,110],C=[28,104,58],r,g,b;"
    "if(t<.55){var f=t/.55;r=A[0]+(B[0]-A[0])*f;g=A[1]+(B[1]-A[1])*f;b=A[2]+(B[2]-A[2])*f;}"
    "else{var f=(t-.55)/.45;r=B[0]+(C[0]-B[0])*f;g=B[1]+(C[1]-B[1])*f;b=B[2]+(C[2]-B[2])*f;}"
    "return 'rgba('+(r|0)+','+(g|0)+','+(b|0)+','+(a==null?1:a)+')';}\n")
LITE="if(document.body.classList.contains('light'))return PG(t"
CSS=(".popgrad{display:inline-block;width:90px;height:9px;border-radius:3px;vertical-align:-1px;margin:0 5px;"
 "background:linear-gradient(90deg,#14283c,#3a96a0,#ebcd6e)}"
 "body.light .popgrad{background:linear-gradient(90deg,#dfeed8,#78b46e,#1c683a)}")
JS=(";(function(){var t=document.getElementById('title');if(!t)return;var d=document.createElement('div');"
 "d.style.cssText='margin-top:7px;font-size:11px;opacity:.85';"
 "d.innerHTML='배경=인구밀도 낮음<span class=\"popgrad\"></span>높음';t.appendChild(d);})();")

# 파일별 pcol 라이트 분기 삽입 지점(원본 → 치환)
REPL={
 "build_demand_dashboard.py":("Math.log(1+pmax));const A=", "Math.log(1+pmax));"+LITE+",a);const A="),
 "build_route_improvement.py":("Math.log(1+pmax));return `rgba(${30+40*t", "Math.log(1+pmax));"+LITE+",a);return `rgba(${30+40*t"),
 "build_top_routes_map.py":("Math.log(1+pmax));return `rgb(${16+34*t", "Math.log(1+pmax));"+LITE+");return `rgb(${16+34*t"),
 "build_stop_boarding.py":("Math.log(1+pmax));return `rgb(${14+22*t", "Math.log(1+pmax));"+LITE+");return `rgb(${14+22*t"),
 "build_anchor_stops.py":("Math.log(1+pmax));return `rgb(${16+30*t", "Math.log(1+pmax));"+LITE+");return `rgb(${16+30*t"),
 "build_usertype_demand.py":("Math.log(1+pmax));return `rgb(${14+22*t", "Math.log(1+pmax));"+LITE+");return `rgb(${14+22*t"),
 "build_time_anim.py":("/Math.log(1+D.maxv);t=Math.min(1,t);", "/Math.log(1+D.maxv);t=Math.min(1,t);"+LITE+");"),
}
for fn,(old,new) in REPL.items():
    s=open(fn,encoding="utf-8").read()
    if "function PG(" in s: print(fn,"이미 적용"); continue
    if old not in s: print(fn,"!! pcol 지점 못찾음"); continue
    s=s.replace("function pcol","function pcol",1)              # noop anchor
    s=s.replace(old,new,1)                                       # 라이트 분기
    s=s.replace("function pcol", PG+"function pcol", 1)          # PG 정의를 pcol 앞에
    s=s.replace("</style>", CSS+"</style>", 1)                   # 범례 CSS
    s=s.replace("</script></body></html>", JS+"</script></body></html>", 1)  # 범례 주입
    open(fn,"w",encoding="utf-8").write(s); print(fn,"패치 완료")
