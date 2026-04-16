from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"
UPLOAD = "uploads"
os.makedirs("Bot", exist_ok=True)
os.makedirs(UPLOAD, exist_ok=True)

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
    return json.load(open(CONFIG_FILE))

def save_config(d):
    json.dump(d, open(CONFIG_FILE,"w"), indent=2)

# ---------- LOGO ----------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------- LANG ----------
TEXT = {
 "th":{"login":"เข้าสู่ระบบ","user":"ผู้ใช้","pass":"รหัสผ่าน","token":"โทเคน","save":"บันทึก","add_group":"เพิ่มกลุ่ม","send":"ส่งข้อความ","logout":"ออกจากระบบ","msg":"ข้อความ","add_user":"เพิ่มยูส"},
 "en":{"login":"Login","user":"User","pass":"Password","token":"Token","save":"Save","add_group":"Add Group","send":"Send","logout":"Logout","msg":"Message","add_user":"Add User"}
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
        d=load_config()
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

    group_html=""
    for g in u["groups"]:
        group_html+=f"""
        <div class="g">
        <input type="checkbox" name="gid" value="{g["id"]}">
        {g["name"]}
        <a href="/del_group/{g["id"]}">❌</a>
        </div>
        """

    admin_html=""
    if u["role"]=="admin":
        admin_html=f"""
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
.drop{{border:2px dashed #555;padding:20px;text-align:center;border-radius:10px}}
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
<label><input type="checkbox" onclick="allg(this)"> ALL</label>

<form method="post" action="/send" enctype="multipart/form-data">

{group_html}

<textarea name="msg" placeholder="{t("msg")}"></textarea>

<div class="drop" id="drop">Drag & Drop</div>
<input type="file" name="file" id="file" hidden>

<div class="preview" id="preview"></div>

<button>{t("send")}</button>

</form>
</div>

{admin_html}

<a href="/logout">{t("logout")}</a>

</div>

<script>
function allg(s){{
let c=document.getElementsByName("gid");
for(let i=0;i<c.length;i++)c[i].checked=s.checked;
}}

let drop=document.getElementById("drop");
let file=document.getElementById("file");
let preview=document.getElementById("preview");

drop.onclick=()=>file.click();

drop.ondrop=e=>{
e.preventDefault();
file.files=e.dataTransfer.files;
show(file.files[0]);
};

drop.ondragover=e=>e.preventDefault();

file.onchange=()=>show(file.files[0]);

function show(f){{
preview.innerHTML="";
if(!f)return;
if(f.type.startsWith("image"))
preview.innerHTML=`<img src="${{URL.createObjectURL(f)}}">`;
else
preview.innerHTML=`<video controls src="${{URL.createObjectURL(f)}}"></video>`;
}}
</script>
"""

# ---------- USER ----------
@app.route("/add_user", methods=["POST"])
def add_user():
    d=load_config()
    if d["users"][session["user"]]["role"]=="admin":
        u=request.form["user"]
        p=request.form["pass"]
        d["users"][u]={"password":p,"role":"user","token":"","groups":[]}
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
    file=request.files.get("file")

    success=0

    for g in u["groups"]:
        if g["id"] not in selected: continue
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
            success+=1
        except: pass

    return redirect("/panel")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
