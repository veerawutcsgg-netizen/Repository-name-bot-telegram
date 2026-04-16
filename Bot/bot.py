from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- LOGO ----------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------- CONFIG ----------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {
            "admin": {
                "password": "1234",
                "role": "admin",
                "token": "",
                "groups": []
            }
        }}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------- LANGUAGE ----------
def t(key):
    lang = session.get("lang","th")
    text = {
        "th": {"send":"ส่ง","token":"โทเคน","group":"กลุ่ม"},
        "en": {"send":"Send","token":"Token","group":"Groups"}
    }
    return text[lang].get(key,key)

@app.route("/lang/<l>")
def lang(l):
    session["lang"] = l
    return redirect(request.referrer or "/panel")

# ---------- LOGIN ----------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        data = load_config()
        u = request.form["user"]
        p = request.form["password"]

        if u in data["users"] and data["users"][u]["password"] == p:
            session["user"] = u
            return redirect("/panel")

    return """
    <style>
    body{background:#000;color:white;text-align:center;font-family:sans-serif}
    .box{margin-top:120px}
    input{padding:15px;width:280px;margin:10px;border-radius:10px}
    button{padding:12px 30px;background:gold;border:none;border-radius:10px}
    </style>

    <div style="position:absolute;top:10px;right:20px">
    <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
    </div>

    <div class='box'>
    <img src='/logo' width=150>
    <h2>Telegram Panel</h2>
    <form method='post'>
    <input name='user'><br>
    <input name='password' type='password'><br>
    <button>Login</button>
    </form>
    </div>
    """

# ---------- PANEL ----------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    data = load_config()
    u = data["users"][session["user"]]
    report = session.pop("report","")

    group_html = ""
    for g in u["groups"]:
        group_html += f"""
        <div>
        <input type='checkbox' name='gid' value='{g["id"]}'>
        {g["name"]}
        <a href='/del_group/{g["id"]}'>❌</a>
        </div>
        """

    return f"""
    <style>
    body{{background:#000;color:white;font-family:sans-serif;padding:15px}}
    input,textarea{{width:100%;padding:10px;margin:5px;border-radius:10px}}
    button{{background:gold;border:none;padding:10px;border-radius:10px}}
    .box{{background:#111;padding:15px;border-radius:10px;margin-bottom:10px}}
    </style>

    <div style="position:absolute;top:10px;right:20px">
    🌐 <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
    </div>

    <img src='/logo' width=120>

    {f"<div style='color:lime'>{report}</div>" if report else ""}

    <div class='box'>
    <form method='post' action='/save_token'>
    <h3>{t("token")}</h3>
    <input name='token' value='{u["token"]}'>
    <button>Save</button>
    </form>
    </div>

    <div class='box'>
    <form method='post' action='/add_group'>
    <input name='gid' placeholder='Group ID'>
    <input name='name' placeholder='Group Name'>
    <button>Add</button>
    </form>
    </div>

    <div class='box'>
    <label><input type='checkbox' onclick='toggle(this)'> ALL</label>
    {group_html}

    <form method='post' action='/send' enctype='multipart/form-data'>
    <textarea name='msg'></textarea>
    <input type='file' name='file'>
    <button>{t("send")}</button>
    </form>
    </div>

    <script>
    function toggle(s){{
    let c=document.getElementsByName('gid');
    for(let i=0;i<c.length;i++)c[i].checked=s.checked;
    }}
    </script>
    """

# ---------- SAVE ----------
@app.route("/save_token", methods=["POST"])
def save_token():
    data = load_config()
    data["users"][session["user"]]["token"] = request.form["token"]
    save_config(data)
    return redirect("/panel")

@app.route("/add_group", methods=["POST"])
def add_group():
    data = load_config()
    data["users"][session["user"]]["groups"].append({
        "id": request.form["gid"],
        "name": request.form["name"]
    })
    save_config(data)
    return redirect("/panel")

@app.route("/del_group/<gid>")
def del_group(gid):
    data = load_config()
    u = session["user"]
    data["users"][u]["groups"] = [g for g in data["users"][u]["groups"] if g["id"] != gid]
    save_config(data)
    return redirect("/panel")

# ---------- SEND ----------
@app.route("/send", methods=["POST"])
def send():
    data = load_config()
    u = data["users"][session["user"]]

    token = u["token"]
    msg = request.form["msg"]
    file = request.files.get("file")

    success = 0

    for g in u["groups"]:
        try:
            if file:
                path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(path)
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendDocument",
                    data={"chat_id": g["id"], "caption": msg},
                    files={"document": open(path,"rb")}
                )
            else:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id": g["id"], "text": msg}
                )
            success += 1
        except:
            pass

    session["report"] = f"ส่งสำเร็จ {success} กลุ่ม"
    return redirect("/panel")

# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
