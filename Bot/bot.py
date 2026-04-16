from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- LOGO ----------------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------------- CONFIG ----------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users":{
            "admin":{
                "password":"1234",
                "role":"admin",
                "token":"",
                "groups":[]
            }
        }}
    with open(CONFIG_FILE,"r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE,"w") as f:
        json.dump(data,f,indent=2)

# ---------------- LANGUAGE ----------------
TEXT = {
    "th":{
        "login":"เข้าสู่ระบบ","user":"ผู้ใช้","pass":"รหัสผ่าน",
        "token":"โทเคน","save":"บันทึก","add_group":"เพิ่มกลุ่ม",
        "group":"กลุ่ม","send":"ส่งข้อความ","logout":"ออกจากระบบ",
        "msg":"ข้อความ","report":"ส่งสำเร็จ"
    },
    "en":{
        "login":"Login","user":"User","pass":"Password",
        "token":"Token","save":"Save","add_group":"Add Group",
        "group":"Groups","send":"Send","logout":"Logout",
        "msg":"Message","report":"Success"
    }
}

def t(k):
    return TEXT.get(session.get("lang","th"))[k]

@app.route("/lang/<l>")
def change_lang(l):
    session["lang"] = l if l in ["th","en"] else "th"
    return redirect(request.referrer or "/panel")

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        data=load_config()
        u=request.form["user"]
        p=request.form["password"]

        if u in data["users"] and data["users"][u]["password"]==p:
            session["user"]=u
            return redirect("/panel")

    return f"""
    <style>
    body{{background:#020617;color:white;text-align:center;font-family:sans-serif}}
    input{{padding:15px;width:280px;margin:10px;border-radius:10px}}
    button{{padding:12px 30px;background:#facc15;border:none;border-radius:10px}}
    </style>

    <div style="position:absolute;top:10px;right:20px">
    <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
    </div>

    <div style="margin-top:120px">
    <img src="/logo" width=150>
    <h2>Telegram Panel</h2>
    <form method="post">
    <input name="user" placeholder="{t("user")}"><br>
    <input type="password" name="password" placeholder="{t("pass")}"><br>
    <button>{t("login")}</button>
    </form>
    </div>
    """

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    data=load_config()
    user=session["user"]
    u=data["users"][user]
    report=session.pop("report","")

    group_html=""
    for g in u["groups"]:
        group_html+=f"""
        <div class="g">
        <label>
        <input type="checkbox" name="gid" value="{g["id"]}">
        {g["name"]}
        </label>
        <a href="/del_group/{g["id"]}">❌</a>
        </div>
        """

    return f"""
<style>
body{{background:#000;color:white;font-family:sans-serif}}
.container{{max-width:500px;margin:auto;padding:15px}}
.card{{background:#111;padding:15px;border-radius:15px;margin-bottom:15px}}
input,textarea{{width:100%;padding:12px;margin:5px;border-radius:10px}}
button{{background:#facc15;border:none;padding:10px;border-radius:10px;width:100%}}
.drop{{border:2px dashed #555;padding:20px;text-align:center;border-radius:10px}}
.preview img,video{{width:100%;margin-top:10px}}
</style>

<div style="position:absolute;top:10px;right:20px">
🌐 <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
</div>

<div class="container">

<img src="/logo" width=120 style="display:block;margin:auto">

{f"<div style='color:lime'>{report}</div>" if report else ""}

<div class="card">
<h3>{t("token")}</h3>
<form method="post" action="/save_token">
<input name="token" value="{u["token"]}">
<button>{t("save")}</button>
</form>
</div>

<div class="card">
<h3>{t("add_group")}</h3>
<form method="post" action="/add_group">
<input name="gid" placeholder="ID">
<input name="name" placeholder="Name">
<button>Add</button>
</form>
</div>

<div class="card">
<label><input type="checkbox" onclick="allg(this)"> ALL</label>

<form method="post" action="/send" enctype="multipart/form-data">

{group_html}

<textarea name="msg" placeholder="{t("msg")}"></textarea>

<div class="drop" id="drop">
Drag & Drop
<input type="file" name="file" id="file" hidden>
</div>

<div class="preview" id="preview"></div>

<button>{t("send")}</button>

</form>
</div>

<a href="/logout">{t("logout")}</a>

</div>

<script>
function allg(s){{
let c=document.getElementsByName("gid");
for(let i=0;i<c.length;i++)c[i].checked=s.checked;
}}

let d=document.getElementById("drop");
let f=document.getElementById("file");
let p=document.getElementById("preview");

d.onclick=()=>f.click();

d.ondrop=e=>{
e.preventDefault();
f.files=e.dataTransfer.files;
show(f.files[0]);
};

d.ondragover=e=>e.preventDefault();

f.onchange=()=>show(f.files[0]);

function show(x){{
p.innerHTML="";
if(!x)return;
if(x.type.startsWith("image"))
p.innerHTML=`<img src="${{URL.createObjectURL(x)}}">`;
else
p.innerHTML=`<video controls src="${{URL.createObjectURL(x)}}"></video>`;
}}
</script>
"""

# ---------------- SAVE TOKEN ----------------
@app.route("/save_token", methods=["POST"])
def save_token():
    data=load_config()
    data["users"][session["user"]]["token"]=request.form["token"]
    save_config(data)
    return redirect("/panel")

# ---------------- GROUP ----------------
@app.route("/add_group", methods=["POST"])
def add_group():
    data=load_config()
    data["users"][session["user"]]["groups"].append({
        "id":request.form["gid"],
        "name":request.form["name"]
    })
    save_config(data)
    return redirect("/panel")

@app.route("/del_group/<gid>")
def del_group(gid):
    data=load_config()
    u=session["user"]
    data["users"][u]["groups"]=[g for g in data["users"][u]["groups"] if g["id"]!=gid]
    save_config(data)
    return redirect("/panel")

# ---------------- SEND ----------------
@app.route("/send", methods=["POST"])
def send():
    data=load_config()
    u=data["users"][session["user"]]

    selected=request.form.getlist("gid")
    msg=request.form["msg"]
    file=request.files.get("file")

    success=0

    for g in u["groups"]:
        if g["id"] not in selected:
            continue

        try:
            if file:
                path=os.path.join(UPLOAD_FOLDER,file.filename)
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
            success+=1
        except:
            pass

    session["report"]=f"✅ {t('report')} {success}"
    return redirect("/panel")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
