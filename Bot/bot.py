from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"
os.makedirs("Bot", exist_ok=True)

# ---------- INIT ----------
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
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

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(d):
    with open(CONFIG_FILE, "w") as f:
        json.dump(d, f, indent=2)

# ---------- LOGO ----------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------- LANG ----------
TEXT = {
 "th":{"login":"เข้าสู่ระบบ","user":"ผู้ใช้","pass":"รหัสผ่าน","token":"โทเคน","save":"บันทึก","add_group":"เพิ่มกลุ่ม","group":"กลุ่ม","send":"ส่งข้อความ","logout":"ออกจากระบบ","msg":"ข้อความ","report":"ส่งสำเร็จ","add_user":"เพิ่มยูส","change_pass":"เปลี่ยนรหัส"},
 "en":{"login":"Login","user":"User","pass":"Password","token":"Token","save":"Save","add_group":"Add Group","group":"Groups","send":"Send","logout":"Logout","msg":"Message","report":"Success","add_user":"Add User","change_pass":"Change Password"}
}

def t(k):
    return TEXT.get(session.get("lang","th"))[k]

@app.route("/set_lang/<lang>")
def set_lang(lang):
    if lang not in ["th","en"]: lang="th"
    session["lang"]=lang
    return redirect(request.referrer or "/panel")

# ---------- LOGIN ----------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        d=load_config()
        u=request.form["user"]
        p=request.form["password"]
        if u in d["users"] and d["users"][u]["password"]==p:
            session["user"]=u
            return redirect("/panel")

    return f"""
    <div style="text-align:center;margin-top:100px">
    <img src="/logo" width=150>
    <h2>Telegram Panel</h2>
    <form method="post">
    <input name="user" placeholder="{t("user")}"><br>
    <input type="password" name="password" placeholder="{t("pass")}"><br>
    <button>{t("login")}</button>
    </form>
    </div>
    """

# ---------- PANEL ----------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    d=load_config()
    user=session["user"]
    u=d["users"][user]
    report=session.pop("report","")

    # group
    group_html=""
    for g in u["groups"]:
        group_html+=f"""
        <div>
        <input type="checkbox" name="gid" value="{g["id"]}">
        {g["name"]}
        <a href="/del_group/{g["id"]}">❌</a>
        </div>
        """

    # admin user list
    user_html=""
    if u["role"]=="admin":
        for uname,ud in d["users"].items():
            if uname=="admin": continue
            user_html+=f"""
            <div>
            {uname}
            <form method="post" action="/change_pass" style="display:inline">
            <input name="user" value="{uname}" hidden>
            <input name="newpass" placeholder="new pass">
            <button>✔</button>
            </form>
            <a href="/del_user/{uname}">❌</a>
            </div>
            """

    return f"""
<style>
body{{background:#000;color:white;font-family:sans-serif}}
.box{{max-width:500px;margin:auto}}
.card{{background:#111;padding:15px;margin:10px;border-radius:10px}}
input,textarea{{width:100%;padding:10px;margin:5px}}
button{{background:#facc15;border:none;padding:10px}}
</style>

<div class="box">

<img src="/logo" width=120>

<div>
<a href="/set_lang/th">TH</a> | <a href="/set_lang/en">EN</a>
</div>

{f"<div style='color:lime'>{report}</div>" if report else ""}

<div class="card">
<form method="post" action="/save_token">
<h3>{t("token")}</h3>
<input name="token" value="{u["token"]}">
<button>{t("save")}</button>
</form>
</div>

<div class="card">
<form method="post" action="/add_group">
<input name="gid" placeholder="ID">
<input name="name" placeholder="Name">
<button>{t("add_group")}</button>
</form>
</div>

<div class="card">
<form method="post" action="/send">
<label><input type="checkbox" onclick="allg(this)"> ALL</label>
{group_html}
<textarea name="msg"></textarea>
<button>{t("send")}</button>
</form>
</div>

{"<div class='card'><h3>"+t("add_user")+"""</h3>
<form method="post" action="/add_user">
<input name="user">
<input name="pass">
<button>Add</button>
</form>
"""+user_html+"</div>" if u["role"]=="admin" else ""}

<a href="/logout">{t("logout")}</a>

</div>

<script>
function allg(s){{
let c=document.getElementsByName("gid");
for(let i=0;i<c.length;i++)c[i].checked=s.checked;
}}
</script>
"""

# ---------- USER MANAGEMENT ----------
@app.route("/add_user", methods=["POST"])
def add_user():
    d=load_config()
    if d["users"][session["user"]]["role"]!="admin":
        return redirect("/panel")

    u=request.form["user"]
    p=request.form["pass"]

    if u not in d["users"]:
        d["users"][u]={"password":p,"role":"user","token":"","groups":[]}
        save_config(d)

    return redirect("/panel")

@app.route("/del_user/<u>")
def del_user(u):
    d=load_config()
    if d["users"][session["user"]]["role"]=="admin":
        if u in d["users"]:
            del d["users"][u]
            save_config(d)
    return redirect("/panel")

@app.route("/change_pass", methods=["POST"])
def change_pass():
    d=load_config()
    if d["users"][session["user"]]["role"]=="admin":
        u=request.form["user"]
        d["users"][u]["password"]=request.form["newpass"]
        save_config(d)
    return redirect("/panel")

# ---------- GROUP ----------
@app.route("/add_group", methods=["POST"])
def add_group():
    d=load_config()
    d["users"][session["user"]]["groups"].append({
        "id":request.form["gid"],
        "name":request.form["name"]
    })
    save_config(d)
    return redirect("/panel")

@app.route("/del_group/<gid>")
def del_group(gid):
    d=load_config()
    u=session["user"]
    d["users"][u]["groups"]=[g for g in d["users"][u]["groups"] if g["id"]!=gid]
    save_config(d)
    return redirect("/panel")

# ---------- TOKEN ----------
@app.route("/save_token", methods=["POST"])
def save_token():
    d=load_config()
    d["users"][session["user"]]["token"]=request.form["token"]
    save_config(d)
    return redirect("/panel")

# ---------- SEND ----------
@app.route("/send", methods=["POST"])
def send():
    d=load_config()
    u=d["users"][session["user"]]

    selected=request.form.getlist("gid")
    msg=request.form["msg"]

    success=0

    for g in u["groups"]:
        if g["id"] not in selected: continue
        try:
            requests.post(
                f"https://api.telegram.org/bot{u['token']}/sendMessage",
                data={"chat_id":g["id"],"text":msg}
            )
            success+=1
        except: pass

    session["report"]=f"✅ {t('report')} {success}"
    return redirect("/panel")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- RUN ----------
if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
