# 울산 버스 — 크레용 격자 + 버스색 박스 포스터 (Pratt 스타일)
import random,textwrap
random.seed(7)
W,H=1000,1414
def crayon(x1,y1,x2,y2,wd=3.2):
    # 직선을 약간 떨리는 폴리라인(크레용 느낌)으로
    dx,dy=x2-x1,y2-y1; L=(dx*dx+dy*dy)**.5
    if L==0: return ""
    ux,uy=dx/L,dy/L; px,py=-uy,ux  # 수직
    n=max(2,int(L/34)); pts=[]
    for i in range(n+1):
        t=i/n; jx=random.gauss(0,2.3) if 0<i<n else 0; jy=random.gauss(0,2.3) if 0<i<n else 0
        pts.append((x1+dx*t+px*jx, y1+dy*t+py*jy))
    d="M"+" L".join(f"{a:.1f},{b:.1f}" for a,b in pts)
    return (f'<path d="{d}" fill="none" stroke="#1a1a17" stroke-width="{wd}" stroke-linecap="round" stroke-linejoin="round" opacity="0.92"/>'
            f'<path d="{d}" fill="none" stroke="#1a1a17" stroke-width="{wd*0.5}" stroke-linecap="round" opacity="0.5"/>')
BOX=[ # x,y,w,h, fill, textcol, 유형, 대표(큰), 개수, 목록
 (60,235,410,385,"#ffc20e","#1a1a17","일반 시내버스","307·123·126","192","111 112 114 115 124 127 132 134 213 215 216 401 412 427 432 ... 외 다수 (재도입 123·126·307)"),
 (470,235,250,190,"#8a73d8","#161022","좌석","1713","18","1114 1144 1154 1411 1421 1452 1713 1723 1733"),
 (470,430,250,190,"#7ec820","#15240a","마을","중구54","34","남구51 동구52 중구53 중구54 중구55 동구54 울주61"),
 (720,235,220,190,"#e23b2e","#fff","리무진","5002","5","5001 5002 5003 5004 5005"),
 (720,430,220,190,"#e85aa6","#3a0f27","순환","울주81","13","울주81 82 83 84 85 86 87 88 89 90"),
 (60,620,410,380,"#2f7fe0","#fff","지선","남구05","93","남구01 02 03 04 05 · 중구01 · 동구01 · 북구01 · 울주01 09 ... 외 다수"),
]
s=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="\'Arial Narrow\',\'Apple SD Gothic Neo\',sans-serif">']
s.append(f'<rect width="{W}" height="{H}" fill="#f4f2ea"/>')
# 색 박스
for x,y,w,h,fill,tc,typ,big,cnt,lst in BOX:
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>')
# 타이틀 박스(단일, 연한 배경 틴트)
s.append(f'<rect x="60" y="40" width="880" height="195" fill="#fde7cf"/>')
# 흰 정보 박스(우중/하단)
s.append(f'<rect x="470" y="620" width="250" height="380" fill="#fffefb"/>')
s.append(f'<rect x="720" y="620" width="220" height="380" fill="#16140f"/>')
s.append(f'<text x="830" y="800" font-size="58" font-weight="900" fill="#fff" text-anchor="middle">전 노선</text>')
s.append(f'<text x="830" y="858" font-size="30" font-weight="800" fill="#ffc20e" text-anchor="middle">6개 유형</text>')
# ---- 크레용 격자(불규칙) ----
g=[]
g.append(crayon(60,40,60,1374)); g.append(crayon(940,40,940,1374))
for X in (470,720): g.append(crayon(X,235,X,1374))
for X in (360,): g.append(crayon(X,620,X,1000))
for Y in (40,235,620,1000,1374): g.append(crayon(60,Y,940,Y))
for seg in ((470,425,720,425),(720,425,940,425),(470,620,720,620)): g.append(crayon(*seg))
s+=g
# ---- 박스 텍스트 ----
def wrap_list(lst,box_w,fs):
    per=max(8,int(box_w/ (fs*0.62)))
    words=lst.split(" "); lines=[]; cur=""
    for w0 in words:
        if len((cur+" "+w0).strip())>per: lines.append(cur.strip()); cur=w0
        else: cur=(cur+" "+w0).strip()
    if cur: lines.append(cur)
    return lines
for x,y,w,h,fill,tc,typ,big,cnt,lst in BOX:
    big_fs = 56 if w>300 else 42
    typ_fs = 28 if w>300 else 20
    lf = 15 if w>300 else 13
    s.append(f'<text x="{x+18}" y="{y+typ_fs+10}" font-size="{typ_fs}" font-weight="900" fill="{tc}">{typ}</text>')
    s.append(f'<text x="{x+w-16}" y="{y+typ_fs+10}" font-size="17" font-weight="800" fill="{tc}" text-anchor="end">{cnt}개</text>')
    s.append(f'<text x="{x+18}" y="{y+typ_fs+10+big_fs}" font-size="{big_fs}" font-weight="900" fill="{tc}" letter-spacing="1">{big}</text>')
    ly=y+typ_fs+10+big_fs+26
    for line in wrap_list(lst,w-30,lf):
        s.append(f'<text x="{x+18}" y="{ly}" font-size="{lf}" font-weight="700" fill="{tc}">{line}</text>'); ly+=lf+5
# 흰 정보 박스 텍스트
s.append(f'<text x="488" y="660" font-size="22" font-weight="900" fill="#1a1a17">노선 한눈에</text>')
for i,t in enumerate(["울산 시내버스 전 노선을","유형별 색으로 정리한","노선도입니다.","","· 굵은 노랑 = 일반","· 색 = 버스 유형","· 큰 숫자 = 대표 노선"]):
    s.append(f'<text x="488" y="{694+i*26}" font-size="15" font-weight="600" fill="#333">{t}</text>')
# ---- 타이틀 ----
s.append(f'<text x="78" y="100" font-size="22" font-weight="900" fill="#1a1a17" letter-spacing="3">ULSAN CITY BUS</text>')
s.append(f'<text x="78" y="190" font-size="96" font-weight="900"><tspan fill="#f07d0c">울산</tspan> <tspan fill="#5bb318">버스</tspan> <tspan fill="#1a1a17">노선도</tspan></text>')
s.append(f'<text x="922" y="100" font-size="20" font-weight="900" fill="#1a1a17" text-anchor="end">2026.04.07</text>')
# ---- 푸터 ----
s.append(f'<text x="78" y="1070" font-size="24" font-weight="900" fill="#f07d0c">데이터 시각화 리포트</text>')
s.append(f'<text x="78" y="1100" font-size="16" font-weight="700" fill="#1a1a17">폐지노선 재도입 분석 — 123 · 126 · 307</text>')
s.append(f'<text x="78" y="1180" font-size="16" font-weight="700" fill="#1a1a17">공개 사이트</text>')
s.append(f'<text x="78" y="1205" font-size="16" font-weight="600" fill="#444">getorey.github.io/ulsanbus</text>')
s.append(f'<text x="78" y="1320" font-size="15" font-weight="700" fill="#1a1a17">자료: 교통카드 합성데이터 · BIS 실노선 ·</text>')
s.append(f'<text x="78" y="1342" font-size="15" font-weight="700" fill="#1a1a17">국토부 혼잡도 · SGIS 인구</text>')
s.append(f'<text x="922" y="1330" font-size="40" font-weight="900" text-anchor="end"><tspan fill="#1a1a17">ULSAN</tspan><tspan fill="#f07d0c">BUS</tspan></text>')
s.append('</svg>')
SVG="\n".join(s)
html=f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>울산 버스 노선도 포스터</title><style>html,body{{margin:0;background:#22252b;display:flex;justify-content:center}}svg{{width:min(96vw,720px);height:auto;margin:18px;box-shadow:0 10px 40px #0008}}</style></head><body>{SVG}</body></html>'
open("ulsan_poster.html","w",encoding="utf-8").write(html); open("ulsan_poster.svg","w",encoding="utf-8").write(SVG)
print("저장",len(SVG))
