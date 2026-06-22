# 울산 버스 타이포그래픽 포스터 v2 — 일반(노랑) 굵은 라인 + 라인 위 큰 정류장명
import math
W,H=1000,1414
YEL="#ffc20e"   # 일반 시내버스(노랑)
def ang(p1,p2): return math.degrees(math.atan2(p2[1]-p1[1],p2[0]-p1[0]))
def lerp(p1,p2,f): return (p1[0]+(p2[0]-p1[0])*f, p1[1]+(p2[1]-p1[1])*f)
# 굵은 노랑(일반) 메인 노선: 라인 위에 큰 글자
MAIN=[
 {"no":"307","p1":(60,500),"p2":(950,980),"w":62,"fs":40,"stops":["천상중학교","신복로터리","울산대학교","공업탑","태화강역"],"rf":0.5},
 {"no":"123","p1":(120,1170),"p2":(900,430),"w":58,"fs":38,"stops":["꽃바위","현대중공업","성남동","태화루","천상중"],"rf":0.5},
 {"no":"126","p1":(70,820),"p2":(950,770),"w":50,"fs":34,"stops":["방어진","태화강역","공업탑","덕하"],"rf":0.66},
]
# 가는 유형 액센트 노선
ACC=[
 {"no":"좌석","col":"#8a73d8","p1":(360,1250),"p2":(560,330),"w":9,"fs":19,"stops":["언양","무거동","공업탑"],"rf":0.28},
 {"no":"14","col":"#7ec820","p1":(560,560),"p2":(900,430),"w":12,"fs":20,"stops":["함월","약사","운동장","우신병원"],"rf":0.45},
 {"no":"순환","col":"#e85aa6","p1":(660,1240),"p2":(960,580),"w":8,"fs":17,"stops":["명촌","진장","농수산물"],"rf":0.5},
 {"no":"지선","col":"#2f7fe0","p1":(150,560),"p2":(560,1180),"w":8,"fs":17,"stops":["야음","신정","법원"],"rf":0.6},
]
s=[]
s.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="\'Arial Narrow\',\'Apple SD Gothic Neo\',sans-serif">')
s.append(f'<rect width="{W}" height="{H}" fill="#f4f2ea"/>')
for x in range(0,W+1,40): s.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#cfd8e6" stroke-width="0.5"/>')
for y in range(0,H+1,40): s.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#cfd8e6" stroke-width="0.5"/>')
for x in (60,940): s.append(f'<line x1="{x}" y1="40" x2="{x}" y2="{H-40}" stroke="#141414" stroke-width="1.6"/>')
for y in (40,360,1235,H-40): s.append(f'<line x1="60" y1="{y}" x2="940" y2="{y}" stroke="#141414" stroke-width="1.6"/>')
# 색 블록(오렌지/연두)
s.append(f'<rect x="60" y="40" width="120" height="320" fill="#f07d0c"/>')
s.append(f'<rect x="820" y="40" width="120" height="320" fill="#7ec820"/>')
s.append(f'<text x="720" y="1180" font-size="460" font-weight="900" fill="#000" opacity="0.045" text-anchor="middle">307</text>')
def draw_main(r):
    p1,p2=r["p1"],r["p2"]; a=ang(p1,p2)
    s.append(f'<line x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}" stroke="#141414" stroke-width="{r["w"]+8}" stroke-linecap="round"/>')
    s.append(f'<line x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}" stroke="{YEL}" stroke-width="{r["w"]}" stroke-linecap="round"/>')
    n=len(r["stops"])
    for i,st in enumerate(r["stops"]):
        f=0.08+0.84*(i/(n-1)) if n>1 else 0.5
        x,y=lerp(p1,p2,f)
        off=r["fs"]*0.34
        dx=math.sin(math.radians(a))*off; dy=-math.cos(math.radians(a))*off
        s.append(f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" font-size="{r["fs"]}" font-weight="900" fill="#141414" text-anchor="middle" transform="rotate({a:.1f} {x+dx:.1f} {y+dy:.1f})" letter-spacing="0.5">{st}</text>')
    rx,ry=lerp(p1,p2,r["rf"])
    s.append(f'<circle cx="{rx:.0f}" cy="{ry:.0f}" r="40" fill="#fff" stroke="#141414" stroke-width="6"/>')
    s.append(f'<text x="{rx:.0f}" y="{ry+14:.0f}" font-size="38" font-weight="900" fill="#141414" text-anchor="middle">{r["no"]}</text>')
def draw_acc(r):
    p1,p2=r["p1"],r["p2"]; a=ang(p1,p2); col=r["col"]
    s.append(f'<line x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}" stroke="#f4f2ea" stroke-width="{r["w"]+5}" stroke-linecap="round"/>')
    s.append(f'<line x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}" stroke="{col}" stroke-width="{r["w"]}" stroke-linecap="round"/>')
    n=len(r["stops"])
    for i,st in enumerate(r["stops"]):
        f=0.1+0.8*(i/(n-1)) if n>1 else 0.5
        x,y=lerp(p1,p2,f); off=-(r["w"]/2+7)
        dx=math.sin(math.radians(a))*off; dy=-math.cos(math.radians(a))*off
        s.append(f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" font-size="{r["fs"]}" font-weight="800" fill="{col}" transform="rotate({a:.1f} {x+dx:.1f} {y+dy:.1f})">{st}</text>')
    rx,ry=lerp(p1,p2,r["rf"])
    s.append(f'<circle cx="{rx:.0f}" cy="{ry:.0f}" r="20" fill="#f4f2ea" stroke="{col}" stroke-width="3"/>')
    s.append(f'<text x="{rx:.0f}" y="{ry+6:.0f}" font-size="16" font-weight="900" fill="{col}" text-anchor="middle">{r["no"]}</text>')
for r in ACC: draw_acc(r)
for r in MAIN: draw_main(r)
# 타이틀(오렌지/연두)
s.append(f'<text x="210" y="120" font-size="20" font-weight="800" fill="#141414" letter-spacing="3">울산광역시 시내버스 · ULSAN CITY BUS</text>')
s.append(f'<text x="210" y="150" font-size="15" font-weight="700" fill="#f07d0c" letter-spacing="2">데이터 시각화 · 노선 재도입 분석 리포트</text>')
s.append(f'<text x="200" y="275" font-size="125" font-weight="900" letter-spacing="2"><tspan fill="#f07d0c">울산</tspan> <tspan fill="#5bb318">버스</tspan></text>')
s.append(f'<text x="205" y="338" font-size="33" font-weight="800" fill="#141414">폐지노선 재도입 — <tspan fill="#f07d0c">123</tspan> · <tspan fill="#c01f6b">126</tspan> · <tspan fill="#e8381f">307</tspan></text>')
s.append(f'<text x="700" y="120" font-size="22" font-weight="900" fill="#141414" text-anchor="end">2026.04.07</text>')
# 범례
ly=1262
s.append(f'<text x="70" y="{ly}" font-size="16" font-weight="800" fill="#141414">노선 유형 · 색</text>')
leg=[("일반",YEL),("좌석","#8a73d8"),("지선","#2f7fe0"),("마을","#7ec820"),("순환","#e85aa6"),("리무진","#e23b2e")]
x=70
for nm,c in leg:
    s.append(f'<rect x="{x}" y="{ly+12}" width="24" height="15" fill="{c}" stroke="#141414" stroke-width="0.8"/>')
    s.append(f'<text x="{x+30}" y="{ly+25}" font-size="15" font-weight="700" fill="#141414">{nm}</text>')
    x+=120
s.append(f'<text x="70" y="{ly+62}" font-size="14" font-weight="600" fill="#444">굵은 노랑 = 일반 시내버스 · 정류장명은 노선을 따라 표기 · 원 안 숫자 = 노선번호</text>')
s.append(f'<text x="930" y="{H-58}" font-size="30" font-weight="900" text-anchor="end"><tspan fill="#141414">ULSAN</tspan><tspan fill="#f07d0c">BUS</tspan></text>')
s.append(f'<text x="930" y="{H-34}" font-size="13" font-weight="600" fill="#444" text-anchor="end">getorey.github.io/ulsanbus</text>')
s.append('</svg>')
SVG="\n".join(s)
html=f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>울산 버스 — 첫페이지 시안</title><style>html,body{{margin:0;background:#22252b;display:flex;justify-content:center}}svg{{width:min(96vw,720px);height:auto;margin:18px auto;box-shadow:0 10px 40px #0008}}</style></head><body>{SVG}</body></html>'
open("ulsan_cover.html","w",encoding="utf-8").write(html); open("ulsan_cover.svg","w",encoding="utf-8").write(SVG)
print("저장 완료", len(SVG))
