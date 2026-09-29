from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import sqlite3, os

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "inspector.db")
POINTS = [(f"P{i:02d}", f"POINT-{i:02d}") for i in range(1,11)]

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    c=conn()
    c.execute("""CREATE TABLE IF NOT EXISTS scans(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      point_id TEXT, inspector_id TEXT, device_id TEXT,
      scan_time TEXT, result TEXT)""")
    c.commit(); c.close()

@app.get("/")
def home(): return render_template_string(DASHBOARD)

@app.get("/api/points")
def get_points():
    c=conn(); out=[]
    for pid,name in POINTS:
        r=c.execute("""SELECT scan_time FROM scans
          WHERE point_id=? AND result='ACCEPTED'
          ORDER BY id DESC LIMIT 1""",(pid,)).fetchone()
        out.append({"point_id":pid,"name":name,"last_scan":r["scan_time"] if r else None})
    c.close(); return jsonify(out)

@app.get("/api/history")
def history():
    c=conn(); rows=c.execute(
      "SELECT * FROM scans ORDER BY id DESC LIMIT 100").fetchall()
    c.close(); return jsonify([dict(r) for r in rows])

@app.post("/api/scan")
def scan():
    d=request.get_json(force=True)
    pid=str(d.get("point_id","")).upper()
    inspector=str(d.get("inspector_id","INSPECTOR-01"))
    device=str(d.get("device_id","PHONE-01"))
    if pid not in [x[0] for x in POINTS]:
        return jsonify(ok=False,message="Unknown point"),400
    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c=conn()
    today=now[:10]
    old=c.execute("""SELECT id FROM scans
      WHERE point_id=? AND inspector_id=? AND date(scan_time)=?
      AND result='ACCEPTED' LIMIT 1""",(pid,inspector,today)).fetchone()
    result="REPEAT" if old else "ACCEPTED"
    c.execute("""INSERT INTO scans(point_id,inspector_id,device_id,scan_time,result)
      VALUES(?,?,?,?,?)""",(pid,inspector,device,now,result))
    c.commit(); c.close()
    return jsonify(ok=True,result=result,point_id=pid,scan_time=now)

DASHBOARD = r"""<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Real Time Inspector</title>
<style>
body{font-family:Arial;margin:0;background:#f4f6f8;color:#17202a}
header{background:#172b4d;color:white;padding:18px 24px}
h1{margin:0;font-size:24px}.wrap{max-width:1100px;margin:22px auto;padding:0 16px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.card{background:white;border-radius:12px;padding:18px;box-shadow:0 2px 10px #0001}
.num{font-size:30px;font-weight:700}table{width:100%;border-collapse:collapse}
th,td{padding:13px;border-bottom:1px solid #eee;text-align:left}
.badge{padding:6px 10px;border-radius:20px;font-size:12px;font-weight:700}
.ok{background:#d9f7e5;color:#137333}.pending{background:#eee;color:#666}
.repeat{background:#fff0c2;color:#8a5a00}
@media(max-width:700px){.cards{grid-template-columns:1fr}}
</style></head><body>
<header><h1>REAL TIME INSPECTOR</h1><div>10-Point Inspection Monitoring Dashboard</div></header>
<div class="wrap"><div class="cards">
<div class="card">TOTAL POINTS<div class="num">10</div></div>
<div class="card">SCANNED TODAY<div class="num" id="scanned">0</div></div>
<div class="card">PENDING<div class="num" id="pending">10</div></div>
</div><br>
<div class="card"><h2>Inspection Points</h2>
<table><thead><tr><th>Point</th><th>Status</th><th>Last Scan</th></tr></thead>
<tbody id="points"></tbody></table></div><br>
<div class="card"><h2>Recent Events</h2>
<table><thead><tr><th>Time</th><th>Point</th><th>Inspector</th><th>Result</th></tr></thead>
<tbody id="history"></tbody></table></div></div>
<script>
async function refresh(){
 let p=await (await fetch('/api/points')).json(), s=p.filter(x=>x.last_scan).length;
 document.querySelector('#scanned').textContent=s;
 document.querySelector('#pending').textContent=p.length-s;
 document.querySelector('#points').innerHTML=p.map(x=>`<tr><td><b>${x.name}</b></td>
 <td><span class="badge ${x.last_scan?'ok':'pending'}">${x.last_scan?'SCANNED':'PENDING'}</span></td>
 <td>${x.last_scan||'—'}</td></tr>`).join('');
 let h=await (await fetch('/api/history')).json();
 document.querySelector('#history').innerHTML=h.map(x=>`<tr><td>${x.scan_time}</td>
 <td>${x.point_id}</td><td>${x.inspector_id}</td>
 <td><span class="badge ${x.result==='ACCEPTED'?'ok':'repeat'}">${x.result}</span></td></tr>`).join('');
}
refresh();setInterval(refresh,2000);
</script></body></html>"""

init()

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
