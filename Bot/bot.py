from flask import Flask, request, session, redirect
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"
UPLOAD_FOLDER = "Bot/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- CONFIG ---------------- #
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {}}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- LANG ---------------- #
LANG = {
    "th": {
        "login": "เข้าสู่ระบบ",
        "user": "ผู้ใช้",
        "pass": "รหัสผ่าน",
        "token": "โทเคนบอท",
        "save": "บันทึก",
        "add_group": "เพิ่มกลุ่ม",
        "group_id": "ไอดีกลุ่ม",
        "group_name": "ชื่อกลุ่ม",
        "send": "ส่งข้อความ",
        "logout": "ออกจากระบบ",
        "add_user": "เพิ่มยูส",
        "change_pass": "เปลี่ยนรหัส",
        "success": "ส่งสำเร็จ"
    },
    "en": {
        "login": "Login",
        "user": "User",
        "pass": "Password",
        "token": "Bot Token",
        "save": "Save",
        "add_group": "Add Group",
        "group_id": "Group ID",
        "group_name": "Group Name",
        "send": "Send",
        "logout": "Logout",
        "add_user": "Add User",
        "change_pass": "Change Password",
        "success": "Success"
    }
}

def t(key):
    lang = session.get("lang", "th")
    return LANG[lang][key]

# ---------------- LOGIN ---------------- #
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        data = load_config()
        u = request.form["user"]
        p = request.form["password"]

        if u in data["users"] and data["users"][u]["password"] == p:
            session["user"] = u
            return redirect("/panel")
        return "❌ Login failed"

    return f"""
    <style>
    body {{background:#020617;color:white;text-align:center;font-family:sans-serif}}
    .box {{margin-top:100px}}
    input {{padding:15px;width:300px;margin:10px;border-radius:10px}}
    button {{padding:15px 30px;background:#facc15;border:none;border-radius:10px}}
    </style>
    <div class='box'>
        <h1>🚀 Telegram Master Panel</h1>
        <form method='post'>
            <input name='user' placeholder='{t("user")}'><br>
            <input name='password' placeholder='{t("pass")}' type='password'><br>
            <button>{t("login")}</button>
        </form>
        <br>
        <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
    </div>
    """

@app.route("/lang/<l>")
def set_lang(l):
    session["lang"] = l
    return redirect("/")

# ---------------- PANEL ---------------- #
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    data = load_config()
    u = data["users"][session["user"]]

    groups_html = ""
    for g in u["groups"]:
        groups_html += f"""
        <div>
        <input type='checkbox' name='gid' value='{g["id"]}'>
        {g["name"]} ({g["id"]})
        <a href='/del_group/{g["id"]}'>❌</a>
        </div>
        """

    admin_html = ""
    if u["role"] == "admin":
        admin_html = f"""
        <h3>{t("add_user")}</h3>
        <form method='post' action='/add_user'>
            <input name='user'>
            <input name='pass'>
            <button>Add</button>
        </form>
        """

    return f"""
    <style>
    body {{background:#020617;color:white;font-family:sans-serif;padding:20px}}
    input,textarea {{width:100%;padding:10px;margin:5px;border-radius:10px}}
    button {{background:#facc15;border:none;padding:10px;border-radius:10px}}
    </style>

    <h2>👑 USER: {session["user"]}</h2>

    <form method='post' action='/save_token'>
        <h3>{t("token")}</h3>
        <input name='token' value='{u["token"]}'>
        <button>{t("save")}</button>
    </form>

    <h3>{t("add_group")}</h3>
    <form method='post' action='/add_group'>
        <input name='gid' placeholder='ID'>
        <input name='name' placeholder='Name'>
        <button>Add</button>
    </form>

    <h3>Groups</h3>
    <input type='checkbox' onclick='toggle(this)'> ALL
    {groups_html}

    <form method='post' action='/send' enctype='multipart/form-data'>
        <h3>{t("send")}</h3>
        <textarea name='msg'></textarea>
        <input type='file' name='file'>
        <button>Send</button>
    </form>

    {admin_html}

    <br><a href='/logout'>{t("logout")}</a>

    <script>
    function toggle(source) {{
        checkboxes = document.getElementsByName('gid');
        for(var i=0;i<checkboxes.length;i++)
            checkboxes[i].checked = source.checked;
    }}
    </script>
    """

# ---------------- SAVE TOKEN ---------------- #
@app.route("/save_token", methods=["POST"])
def save_token():
    data = load_config()
    u = session["user"]
    data["users"][u]["token"] = request.form["token"]
    save_config(data)
    return redirect("/panel")

# ---------------- GROUP ---------------- #
@app.route("/add_group", methods=["POST"])
def add_group():
    data = load_config()
    u = session["user"]
    data["users"][u]["groups"].append({
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

# ---------------- SEND ---------------- #
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

    return f"✅ ส่งสำเร็จ {success} กลุ่ม"

# ---------------- ADMIN ---------------- #
@app.route("/add_user", methods=["POST"])
def add_user():
    data = load_config()
    if data["users"][session["user"]]["role"] != "admin":
        return "No permission"

    data["users"][request.form["user"]] = {
        "password": request.form["pass"],
        "role": "user",
        "token": "",
        "groups": []
    }
    save_config(data)
    return redirect("/panel")

# ---------------- LOGOUT ---------------- #
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
