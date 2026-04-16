from flask import Flask, request, session, redirect, send_from_directory, render_template_string
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"
os.makedirs("Bot", exist_ok=True)

# ---------- INIT CONFIG ----------
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

# ---------- LOGO ----------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------- CONFIG ----------
def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(d):
    with open(CONFIG_FILE, "w") as f:
        json.dump(d, f, indent=2)

# ---------- LANGUAGE ----------
TEXT = {
    "th":{"login":"เข้าสู่ระบบ","user":"ผู้ใช้","pass":"รหัสผ่าน","token":"โทเคน","save":"บันทึก","add_group":"เพิ่มกลุ่ม","group":"กลุ่ม","send":"ส่งข้อความ","logout":"ออกจากระบบ","msg":"ข้อความ","report":"ส่งสำเร็จ"},
    "en":{"login":"Login","user":"User","pass":"Password","token":"Token","save":"Save","add_group":"Add Group","group":"Groups","send":"Send","logout":"Logout","msg":"Message","report":"Success"}
}

def t(k):
    return TEXT[session.get("lang","th")][k]

@app.route("/lang/<l>")
def lang(l):
    session["lang"] = l if l in ["th","en"] else "th"
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

    return render_template_string("""
    <style>
    body{background:#020617;color:white;text-align:center;font-family:sans-serif}
    input{padding:15px;width:280px;margin:10px;border-radius:10px}
    button{padding:12px 30px;background:#facc15;border:none;border-radius:10px}
    </style>

    <div style="position:absolute;top:10px;right:20px">
    <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
    </div>

    <div style="margin-top:120px">
    <img src="/logo" width=150>
    <h2>Telegram Panel</h2>
    <form method="post">
    <input name="user" placeholder="{{t('user')}}"><br>
    <input name="password" type="password" placeholder="{{t('pass')}}"><br>
    <button>{{t('login')}}</button>
    </form>
    </div>
    """, t=t)

# ---------- PANEL ----------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    d=load_config()
    u=d["users"][session["user"]]
    report=session.pop("report","")

    return render_template_string("""
    <style>
    body{background:#000;color:white;font-family:sans-serif}
    .box{max-width:500px;margin:auto;padding:15px}
    .card{background:#111;padding:15px;border-radius:10px;margin-bottom:10px}
    input,textarea{width:100%;padding:10px;margin:5px;border-radius:10px}
    button{background:#facc15;border:none;padding:10px;border-radius:10px;width:100%}
    </style>

    <div style="position:absolute;top:10px;right:20px">
    <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
    </div>

    <div class="box">

    <img src="/logo" width=120 style="display:block;margin:auto">

    {% if report %}
    <div style="color:lime">{{report}}</div>
    {% endif %}

    <div class="card">
    <form method="post" action="/save_token">
    <h3>{{t("token")}}</h3>
    <input name="token" value="{{u['token']}}">
    <button>{{t("save")}}</button>
    </form>
    </div>

    <div class="card">
    <form method="post" action="/add_group">
    <input name="gid" placeholder="ID">
    <input name="name" placeholder="Name">
    <button>Add</button>
    </form>
    </div>

    <div class="card">

    <label><input type="checkbox" onclick="allg(this)"> ALL</label>

    <form method="post" action="/send">
    {% for g in u['groups'] %}
    <div>
    <input type="checkbox" name="gid" value="{{g['id']}}">
    {{g['name']}}
    <a href="/del_group/{{g['id']}}">❌</a>
    </div>
    {% endfor %}

    <textarea name="msg" placeholder="{{t('msg')}}"></textarea>

    <button>{{t("send")}}</button>
    </form>

    </div>

    <a href="/logout">{{t("logout")}}</a>

    </div>

    <script>
    function allg(s){
        let c=document.getElementsByName("gid");
        for(let i=0;i<c.length;i++) c[i].checked=s.checked;
    }
    </script>
    """, u=u, t=t, report=report)

# ---------- SAVE ----------
@app.route("/save_token", methods=["POST"])
def save_token():
    d=load_config()
    d["users"][session["user"]]["token"]=request.form["token"]
    save_config(d)
    return redirect("/panel")

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

# ---------- SEND ----------
@app.route("/send", methods=["POST"])
def send():
    d=load_config()
    u=d["users"][session["user"]]

    selected=request.form.getlist("gid")
    msg=request.form["msg"]

    success=0

    for g in u["groups"]:
        if g["id"] not in selected:
            continue
        try:
            requests.post(
                f"https://api.telegram.org/bot{u['token']}/sendMessage",
                data={"chat_id":g["id"],"text":msg}
            )
            success+=1
        except:
            pass

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
