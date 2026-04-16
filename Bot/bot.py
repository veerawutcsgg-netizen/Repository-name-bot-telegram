from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"

# ---------------- LOGO ----------------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------------- CONFIG ----------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {"admin": {
            "password": "1234",
            "role": "admin",
            "token": "",
            "groups": []
        }}}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- LANGUAGE ----------------
TEXT = {
    "th": {
        "login":"เข้าสู่ระบบ","user":"ผู้ใช้","pass":"รหัสผ่าน",
        "token":"โทเคน","save":"บันทึก","add_group":"เพิ่มกลุ่ม",
        "group":"กลุ่ม","send":"ส่งข้อความ","logout":"ออกจากระบบ",
        "add_user":"เพิ่มยูส","report":"ส่งสำเร็จ"
    },
    "en": {
        "login":"Login","user":"User","pass":"Password",
        "token":"Token","save":"Save","add_group":"Add Group",
        "group":"Groups","send":"Send","logout":"Logout",
        "add_user":"Add User","report":"Success"
    }
}

def t(k):
    return TEXT.get(session.get("lang","th"))[k]

@app.route("/lang/<l>")
def change_lang(l):
    if l not in ["th","en"]:
        l = "th"
    session["lang"] = l
    return redirect(request.referrer or "/panel")

# ---------------- LOGIN ----------------
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
    body{{background:#020617;color:white;text-align:center;font-family:sans-serif}}
    .box{{margin-top:120px}}
    input{{padding:15px;width:300px;margin:10px;border-radius:10px}}
    button{{padding:15px 30px;background:#facc15;border:none;border-radius:10px}}
    img{{width:200px;margin-bottom:20px}}
    </style>

    <div style="position:absolute;top:10px;right:20px">
        🌐 <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
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

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    data = load_config()
    user = session["user"]
    u = data["users"][user]

    report = session.pop("report","")

    groups_html = ""
    for g in u["groups"]:
        groups_html += f"""
        <div>
        <input type='checkbox' name='gid' value='{g["id"]}'>
        {g["name"]} ({g["id"]})
        <a href='/del_group/{g["id"]}' style='color:red'>❌</a>
        </div>
        """

    admin_html = ""
    if u["role"] == "admin":
        users_list = ""
        for name in data["users"]:
            if name == "admin": continue
            users_list += f"""
            <div style='margin:10px;padding:10px;background:#111'>
                👤 {name}
                <form method='post' action='/change_pass' style='display:inline'>
                    <input type='hidden' name='user' value='{name}'>
                    <input name='newpass' placeholder='New pass'>
                    <button>🔑</button>
                </form>
                <a href='/del_user/{name}'>❌</a>
            </div>
            """

        admin_html = f"""
        <h3>👑 Admin</h3>
        <form method='post' action='/add_user'>
            <input name='user' placeholder='username'>
            <input name='pass' placeholder='password'>
            <button>Add</button>
        </form>
        {users_list}
        """

    return f"""
    <style>
    body{{background:#020617;color:white;font-family:sans-serif;padding:20px}}
    input,textarea{{width:100%;padding:10px;margin:5px;border-radius:10px}}
    button{{background:#facc15;border:none;padding:10px;border-radius:10px}}
    img{{width:150px;margin-bottom:10px}}
    </style>

    <div style="position:absolute;top:10px;right:20px">
        🌐 <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
    </div>

    <img src='/logo'>
    <h2>👑 USER: {user}</h2>

    {f"<div style='color:lime'>{report}</div>" if report else ""}

    <form method='post' action='/save_token'>
        <h3>{t("token")}</h3>
        <input name='token' value='{u["token"]}'>
        <button>{t("save")}</button>
    </form>

    <h3>{t("add_group")}</h3>
    <form method='post' action='/add_group'>
        <input name='gid' placeholder='Group ID'>
        <input name='name' placeholder='Group Name'>
        <button>Add</button>
    </form>

    <h3>{t("group")}</h3>
    <input type='checkbox' onclick='toggle(this)'> ALL
    {groups_html}

    <form method='post' action='/send'>
        <h3>{t("send")}</h3>
        <textarea name='msg'></textarea>
        <button>{t("send")}</button>
    </form>

    {admin_html}

    <br><a href='/logout'>{t("logout")}</a>

    <script>
    function toggle(source){{
        let checkboxes = document.getElementsByName('gid');
        for(let i=0;i<checkboxes.length;i++){{
            checkboxes[i].checked = source.checked;
        }}
    }}
    </script>
    """

# ---------------- SAVE TOKEN ----------------
@app.route("/save_token", methods=["POST"])
def save_token():
    data = load_config()
    data["users"][session["user"]]["token"] = request.form["token"]
    save_config(data)
    return redirect("/panel")

# ---------------- GROUP ----------------
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
    user = session["user"]
    data["users"][user]["groups"] = [g for g in data["users"][user]["groups"] if g["id"] != gid]
    save_config(data)
    return redirect("/panel")

# ---------------- SEND ----------------
@app.route("/send", methods=["POST"])
def send():
    data = load_config()
    u = data["users"][session["user"]]

    success = 0
    for g in u["groups"]:
        try:
            requests.post(
                f"https://api.telegram.org/bot{u['token']}/sendMessage",
                data={"chat_id": g["id"], "text": request.form["msg"]}
            )
            success += 1
        except:
            pass

    session["report"] = f"✅ {t('report')} {success} กลุ่ม"
    return redirect("/panel")

# ---------------- ADMIN ----------------
@app.route("/add_user", methods=["POST"])
def add_user():
    data = load_config()
    if data["users"][session["user"]]["role"] != "admin":
        return "no"

    data["users"][request.form["user"]] = {
        "password": request.form["pass"],
        "role": "user",
        "token": "",
        "groups": []
    }

    save_config(data)
    return redirect("/panel")

@app.route("/change_pass", methods=["POST"])
def change_pass():
    data = load_config()
    if data["users"][session["user"]]["role"] != "admin":
        return "no"

    data["users"][request.form["user"]]["password"] = request.form["newpass"]
    save_config(data)
    return redirect("/panel")

@app.route("/del_user/<u>")
def del_user(u):
    data = load_config()
    if u != "admin":
        data["users"].pop(u, None)
    save_config(data)
    return redirect("/panel")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
