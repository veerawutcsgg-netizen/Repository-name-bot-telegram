from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests, urllib.parse

app = Flask(__name__)
app.secret_key = "secret123"

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
UPLOAD = os.path.join(BASE, "uploads")

os.makedirs(UPLOAD, exist_ok=True)

# ---------- INIT ----------
if not os.path.exists(CONFIG):
    with open(CONFIG, "w") as f:
        json.dump({
            "users":{
                "admin":{
                    "password":"1234",
                    "role":"admin",
                    "token":"",
                    "groups":[]
                }
            }
        }, f, indent=2)

def load():
    return json.load(open(CONFIG))

def save(d):
    json.dump(d, open(CONFIG,"w"), indent=2)

# ---------- LOGO ----------
@app.route("/logo")
def logo():
    return send_from_directory(BASE, "logo.png")

# ---------- LANG ----------
TEXT = {
 "th":{"login":"เข้าสู่ระบบ","user":"ผู้ใช้","pass":"รหัสผ่าน","token":"โทเคน","save":"บันทึก","add_group":"เพิ่มกลุ่ม","send":"ส่งข้อความ","logout":"ออกจากระบบ","msg":"ข้อความ","add_user":"เพิ่มยูส","users":"รายการยูส"},
 "en":{"login":"Login","user":"User","pass":"Password","token":"Token","save":"Save","add_group":"Add Group","send":"Send","logout":"Logout","msg":"Message","add_user":"Add User","users":"User List"}
}

def t(k):
    return TEXT.get(session.get("lang","th"))[k]

@app.route("/set_lang/<l>")
def set_lang(l):
    session["lang"] = l
    return redirect(request.referrer or "/panel")

# ---------- LOGIN ----------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        d=load()
        u=request.form["user"]
        p=request.form["password"]
        if u in d["users"] and d["users"][u]["password"]==p:
            session["user"]=u
            return redirect("/panel")

    return f"""
    <style>
    body{{background:#020617;color:white;text-align:center;font-family:sans-serif}}
    input{{padding:15px;width:260px;margin:10px;border-radius:10px}}
    button{{padding:10px 30px;background:#facc15;border:none;border-radius:10px}}
    </style>

    <div style="position:absolute;top:10px;right:20px">
    <a href="/set_lang/th">TH</a> | <a href="/set_lang/en">EN</a>
    </div>

    <div style="margin-top:120px">
    <img src="/logo" width=150>
    <h2>Telegram Panel</h2>
    <form method="post">
    <input name="user"><br>
    <input type="password" name="password"><br>
    <button>Login</button>
    </form>
    </div>
    """

# ---------- PANEL ----------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    d=load()
    user=session["user"]
    u=d["users"][user]

    report = session.pop("report", "")

    groups=""
    for g in u["groups"]:
        gid_encoded = urllib.parse.quote(g["id"])
        groups+=f"""
        <div>
        <input type="checkbox" name="gid" value="{g["id"]}">
        {g["name"]}
        <a href="/del_group/{gid_encoded}">❌</a>
        </div>
        """

    admin=""
    if u["role"]=="admin":
        user_list=""
        for uname,info in d["users"].items():
            user_list+=f"""
            <div>
            <b>{uname}</b>
            <form method="post" action="/edit_user">
            <input type="hidden" name="user" value="{uname}">
            <input name="pass" placeholder="New Password">
            <button>แก้รหัส</button>
            </form>
            </div>
            """

        admin=f"""
        <div class="card">
        <h3>เพิ่มยูส</h3>
        <form method="post" action="/add_user">
        <input name="user">
        <input name="pass">
        <button>Add</button>
        </form>
        </div>

        <div class="card">
        <h3>รายการยูส</h3>
        {user_list}
        </div>
        """

    return f"""
<style>
body{{background:#000;color:white;font-family:sans-serif}}
.container{{max-width:500px;margin:auto}}
.card{{background:#111;padding:15px;margin:10px;border-radius:15px}}
input,textarea{{width:100%;padding:10px;margin:5px;border-radius:10px}}
button{{background:#facc15;border:none;padding:10px;border-radius:10px;width:100%}}
</style>

<div class="container">

<img src="/logo" width=120>

{f'<div style="background:#16a34a;padding:10px;border-radius:10px">{report}</div>' if report else ''}

<div class="card">
<form method="post" action="/save_token">
<input name="token" value="{u["token"]}">
<button>Save</button>
</form>
</div>

<div class="card">
<form method="post" action="/add_group">
<input name="gid" placeholder="Group ID">
<input name="name" placeholder="Name">
<button>Add</button>
</form>
</div>

<div class="card">
<label><input type="checkbox" onclick="allg(this)"> ALL</label>

<form method="post" action="/send" enctype="multipart/form-data">

{groups}

<textarea name="msg"></textarea>
<input type="file" name="file" id="file">
<button>Send</button>

</form>
</div>

{admin}

<a href="/logout">Logout</a>

</div>

<script>
function allg(s){{
let c=document.getElementsByName("gid");
for(let i=0;i<c.length;i++)c[i].checked=s.checked;
}}
</script>
"""

# ---------- FIX DELETE ----------
@app.route("/del_group/<gid>")
def del_group(gid):
    d=load()
    gid = urllib.parse.unquote(gid)
    u=session["user"]

    d["users"][u]["groups"]=[g for g in d["users"][u]["groups"] if g["id"]!=gid]

    save(d)
    session["report"] = "🗑 ลบกลุ่มสำเร็จ"
    return redirect("/panel")

# ---------- SEND FIX ----------
@app.route("/send", methods=["POST"])
def send():
    d=load()
    u=d["users"][session["user"]]

    gids=request.form.getlist("gid")
    msg=request.form["msg"]
    file=request.files.get("file")

    success=0
    fail=0

    for g in u["groups"]:
        if g["id"] not in gids: continue

        try:
            if file and file.filename!="":
                file.stream.seek(0)

                requests.post(
                    f"https://api.telegram.org/bot{u['token']}/sendDocument",
                    data={"chat_id":g["id"],"caption":msg},
                    files={"document":(file.filename,file.stream)}
                )
            else:
                requests.post(
                    f"https://api.telegram.org/bot{u['token']}/sendMessage",
                    data={"chat_id":g["id"],"text":msg}
                )

            success+=1
        except:
            fail+=1

    session["report"]=f"✅ ส่งสำเร็จ {success} | ❌ ล้มเหลว {fail}"
    return redirect("/panel")

# ---------- OTHER ----------
@app.route("/save_token", methods=["POST"])
def save_token():
    d=load()
    d["users"][session["user"]]["token"]=request.form["token"]
    save(d)
    return redirect("/panel")

@app.route("/add_group", methods=["POST"])
def add_group():
    d=load()
    d["users"][session["user"]]["groups"].append({
        "id":request.form["gid"],
        "name":request.form["name"]
    })
    save(d)
    return redirect("/panel")

@app.route("/add_user", methods=["POST"])
def add_user():
    d=load()
    if d["users"][session["user"]]["role"]=="admin":
        d["users"][request.form["user"]] = {
            "password":request.form["pass"],
            "role":"user",
            "token":"",
            "groups":[]
        }
        save(d)
    return redirect("/panel")

@app.route("/edit_user", methods=["POST"])
def edit_user():
    d=load()
    if d["users"][session["user"]]["role"]=="admin":
        d["users"][request.form["user"]]["password"]=request.form["pass"]
        save(d)
    return redirect("/panel")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
