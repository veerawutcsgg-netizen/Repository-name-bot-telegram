from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests

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
    return send_from_directory(".", "logo.png")

# ---------- LANG ----------
TEXT = {
 "th":{
  "login":"เข้าสู่ระบบ","user":"ผู้ใช้","pass":"รหัสผ่าน","token":"โทเคน",
  "save":"บันทึก","add_group":"เพิ่มกลุ่ม","send":"ส่งข้อความ",
  "logout":"ออกจากระบบ","msg":"ข้อความ","add_user":"เพิ่มยูส",
  "groups":"กลุ่ม","preview":"ตัวอย่าง"
 },
 "en":{
  "login":"Login","user":"User","pass":"Password","token":"Token",
  "save":"Save","add_group":"Add Group","send":"Send",
  "logout":"Logout","msg":"Message","add_user":"Add User",
  "groups":"Groups","preview":"Preview"
 }
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
<h2>Telegram Master Panel 🚀</h2>
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

    d=load()
    user=session["user"]
    u=d["users"][user]

    groups=""
    for g in u["groups"]:
        groups+=f"""
        <div>
        <input type="checkbox" name="gid" value="{g["id"]}">
        {g["name"]}
        <a href="/del_group/{g["id"]}">❌</a>
        </div>
        """

    admin=""
    if u["role"]=="admin":
        admin=f"""
        <div class="card">
        <h3>{t("add_user")}</h3>
        <form method="post" action="/add_user">
        <input name="user">
        <input name="pass">
        <button>Add</button>
        </form>
        </div>
        """

    return f"""
<style>
body{{background:#000;color:white;font-family:sans-serif}}
.container{{max-width:500px;margin:auto;padding:10px}}
.card{{background:#111;padding:15px;margin:10px;border-radius:15px}}
input,textarea{{width:100%;padding:12px;margin:5px;border-radius:10px}}
button{{background:#facc15;border:none;padding:10px;border-radius:10px;width:100%}}
.preview img,video{{width:100%;margin-top:10px;border-radius:10px}}
</style>

<div style="position:absolute;top:10px;right:20px">
🌐 <a href="/set_lang/th">TH</a> | <a href="/set_lang/en">EN</a>
</div>

<div class="container">

<img src="/logo" width=120 style="display:block;margin:auto">

<div class="card">
<form method="post" action="/save_token">
<input name="token" value="{u["token"]}" placeholder="{t("token")}">
<button>{t("save")}</button>
</form>
</div>

<div class="card">
<form method="post" action="/add_group">
<input name="gid" placeholder="Group ID">
<input name="name" placeholder="Name">
<button>{t("add_group")}</button>
</form>
</div>

<div class="card">
<h3>{t("groups")}</h3>
<label><input type="checkbox" onclick="allg(this)"> ALL</label>

<form method="post" action="/send" enctype="multipart/form-data">

{groups}

<textarea name="msg" placeholder="{t("msg")}"></textarea>

<input type="file" name="file" id="file">

<div class="preview" id="preview"></div>

<button>{t("send")}</button>
</form>
</div>

{admin}

<a href="/logout">{t("logout")}</a>

</div>

<script>
function allg(s){{
let c=document.getElementsByName("gid");
for(let i=0;i<c.length;i++)c[i].checked=s.checked;
}}

document.getElementById("file").onchange = function(e){{
let f=e.target.files[0];
let p=document.getElementById("preview");
p.innerHTML="";
if(!f)return;
let url=URL.createObjectURL(f);
if(f.type.startsWith("image")){{
p.innerHTML='<img src="'+url+'">';
}}else{{
p.innerHTML='<video controls src="'+url+'"></video>';
}}
}}
</script>
"""

# ---------- BACKEND ----------
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

@app.route("/del_group/<gid>")
def del_group(gid):
    d=load()
    u=session["user"]
    d["users"][u]["groups"]=[g for g in d["users"][u]["groups"] if g["id"]!=gid]
    save(d)
    return redirect("/panel")

@app.route("/add_user", methods=["POST"])
def add_user():
    d=load()
    if d["users"][session["user"]]["role"]=="admin":
        u=request.form["user"]
        p=request.form["pass"]
        d["users"][u]={"password":p,"role":"user","token":"","groups":[]}
        save(d)
    return redirect("/panel")

@app.route("/send", methods=["POST"])
def send():
    d=load()
    u=d["users"][session["user"]]

    gids=request.form.getlist("gid")
    msg=request.form["msg"]
    file=request.files.get("file")

    for g in u["groups"]:
        if g["id"] not in gids: continue
        try:
            if file:
                path=os.path.join(UPLOAD,file.filename)
                file.save(path)
                requests.post(
                    f"https://api.telegram.org/bot{u['token']}/sendDocument",
                    data={"chat_id":g["id"],"caption":msg},
                    files={"document":open(path,"rb")}
                )
            else:
                requests.post(
                    f"https://api.telegram.org/bot{u['token']}/sendMessage",
                    data={"chat_id":g["id"],"text":msg}
                )
        except:
            pass

    return redirect("/panel")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
