import csv,statistics,json
from collections import defaultdict
W=6*60  # 배차창(초)
seq=defaultdict(dict); rid2no={}; maxseq={}
for r in csv.DictReader(open("ulsan_route_stops_20260407.csv",encoding="utf-8-sig")):
    s=int(r["sttn_seq"]); seq[r["rte_id"]][r["sttn_id"]]=s; rid2no[r["rte_id"]]=r["rte_no"]
    maxseq[r["rte_id"]]=max(maxseq.get(r["rte_id"],0),s)
def secs(s):
    s=s.strip(); return int(s[8:10])*3600+int(s[10:12])*60+int(s[12:14]) if len(s)>=14 else None
rec=defaultdict(list)
for path,hdr in [("card_records_20260407.csv",False),("card_records_20260407_etc.csv",True)]:
    rd=csv.reader(open(path,encoding="utf-8-sig"))
    if hdr:next(rd)
    for x in rd:
        if len(x)<7:continue
        rid=x[0]; rs=secs(x[2]); rsq=seq[rid].get(x[3])
        if rs is None or rsq is None:continue
        gs=secs(x[4]); gsq=seq[rid].get(x[5])
        try:n=int(x[6] or 1)
        except:n=1
        try:br=int(x[8] or 0)
        except:br=0
        if gs is None: gs=rs+(br if br>0 else 600)
        try:ut=int(x[1])
        except:ut=1
        rec[rid].append((rs,rsq,gs,gsq if gsq else rsq,n,ut))
# 노선별 τ, 버스 복원
buses=[]; tot_on=[]
for rid,rs in rec.items():
    taus=[(gs-r)/(gq-rq) for r,rq,gs,gq,n,ut in rs if gq>rq and gs>r]
    tau=statistics.median(taus) if taus else 90
    tau=min(max(tau,30),180)
    grp=defaultdict(list)
    for r,rq,gs,gq,n,ut in rs:
        dep=r-rq*tau; grp[round(dep/W)].append((r,rq,gs,gq,n,ut))
    for b,riders in grp.items():
        dep=b*W
        peak=0
        # onboard 최대(만차 판정용): 이벤트 스캔
        ev=[]
        for r,rq,gs,gq,n,ut in riders: ev.append((r,n)); ev.append((gs,-n))
        ev.sort(); cur=0
        for t,d in ev:
            cur+=d; peak=max(peak,cur)
        tot_on.append(peak)
        buses.append({"rid":rid,"dep":dep,"tau":round(tau,1),"ms":maxseq[rid],
                      "r":[[r,gs,n,ut] for r,rq,gs,gq,n,ut in riders]})
print("총 복원 버스:",len(buses))
print("버스 최대 재차(카드) 분포: 중앙%d 90%%=%d 최대%d"%(statistics.median(tot_on),sorted(tot_on)[int(len(tot_on)*0.9)],max(tot_on)))
json.dump({"buses":buses,"rid2no":rid2no},open("buses_recon.json","w"),separators=(",",":"),ensure_ascii=False)
import os;print("buses_recon.json",round(os.path.getsize("buses_recon.json")/1e6,2),"MB")
