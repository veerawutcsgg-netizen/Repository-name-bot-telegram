from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"
UPLOAD_FOLDER = "Bot/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- CONFIG ----------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {}}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------- LANGUAGE ----------
TEXT = {
    "th": {
        "login":"เข้าสู่ระบบ","user":"ผู้ใช้","pass":"รหัสผ่าน",
        "token":"โทเคน","save":"บันทึก","add_group":"เพิ่มกลุ่ม",
        "groups":"กลุ่ม","send":"ส่งข้อความ","logout":"ออกจากระบบ"
    },
    "en": {
        "login":"Login","user":"User","pass":"Password",
        "token":"Token","save":"Save","add_group":"Add Group",
        "groups":"Groups","send":"Send","logout":"Logout"
    }
}

def t(k):
    return TEXT.get(session.get("lang","th"))[k]

@app.route("/lang/<l>")
def lang(l):
    session["lang"] = l
    return redirect("/")

# ---------- LOGO ----------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

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

    return f"""
    <style>
    body{{background:#020617;color:white;font-family:sans-serif;text-align:center}}
    .box{{margin-top:100px}}
    input{{padding:15px;width:300px;margin:10px;border-radius:10px}}
    button{{padding:12px 30px;background:#facc15;border:none;border-radius:10px}}
    img{{width:180px;margin-bottom:10px}}
    </style>

    <div style='position:absolute;top:10px;right:20px'>
        <a href='/lang/th'>TH</a> | <a href='/lang/en'>EN</a>
    </div>

    <div class='box'>
        <img src='/logo'>
        <h1>🚀 Telegram Master Panel</h1>
        <form method='post'>
            <input name='user' placeholder='{t("user")}'><br>
            <input name='password' type='password' placeholder='{t("pass")}'><br>
            <button>{t("login")}</button>
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

    groups_html = ""
    for g in u["groups"]:
        groups_html += f"""
        <div style='margin:5px'>
        <input type='checkbox' name='gid' value='{g["id"]}'>
        {g["name"]} ({g["id"]})
        <a href='/del_group/{g["id"]}' style='color:red'>❌</a>
        </div>
        """

    return f"""
    <style>
    body{{background:#020617;color:white;font-family:sans-serif;padding:20px}}
    input,textarea{{width:100%;padding:10px;margin:5px;border-radius:10px}}
    button{{background:#facc15;border:none;padding:10px;border-radius:10px}}
    img{{width:140px}}
    </style>

    <div style='position:absolute;top:10px;right:20px'>
        <a href='/lang/th'>TH</a> | <a href='/lang/en'>EN</a>
    </div>

    <img src='/logo'>
    <h2>👑 USER: {session["user"]}</h2>

    {f"<div style='color:lime'>{report}</div>" if report else ""}

    <form method='post' action='/save_token'>
        <h3>🔑 {t("token")}</h3>
        <input name='token' value='{u["token"]}'>
        <button>{t("save")}</button>
    </form>

    <h3>➕ {t("add_group")}</h3>
    <form method='post' action='/add_group'>
        <input name='gid' placeholder='Group ID'>
        <input name='name' placeholder='Group Name'>
        <button>Add</button>
    </form>

    <h3>📋 {t("groups")}</h3>
    <label><input type='checkbox' onclick='toggle(this)'> ALL</label>
    {groups_html}

    <form method='post' action='/send' enctype='multipart/form-data'>
        <h3>📤 {t("send")}</h3>
        <textarea name='msg'></textarea>
        <input type='file' name='file'>
        <button>Send</button>
    </form>

    <br><a href='/logout'>{t("logout")}</a>

    <script>
    function toggle(source){{
        let checkboxes = document.getElementsByName('gid');
        for(let i=0;i<checkboxes.length;i++) {{
            checkboxes[i].checked = source.checked;
        }}
    }}
    </script>
    """

# ---------- TOKEN ----------
@app.route("/save_token", methods=["POST"])
def save_token():
    data = load_config()
    data["users"][session["user"]]["token"] = request.form["token"]
    save_config(data)
    return redirect("/panel")

# ---------- GROUP ----------
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

    session["report"] = f"✅ ส่งสำเร็จ {success} กลุ่ม"
    return redirect("/panel")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
