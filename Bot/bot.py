from flask import Flask, request, session, redirect, send_from_directory
import json, os, random, time
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

app = Flask(__name__)
app.secret_key = "secretkey"

CONFIG_FILE = "Bot/config.json"
SESSION_DIR = "Bot/sessions"
os.makedirs(SESSION_DIR, exist_ok=True)

# ---------------- CONFIG ---------------- #
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {}}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- LOGO ---------------- #
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------------- LOGIN ---------------- #
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]
        data = load_config()

        if user in data["users"] and data["users"][user]["password"] == password:
            session["user"] = user
            return redirect("/panel")

    return """
    <style>
    body{background:#0b0f1a;color:white;text-align:center;font-family:sans-serif}
    input{padding:10px;margin:5px;border-radius:5px;border:none}
    button{padding:10px 20px;background:#ffd700;border:none;border-radius:5px}
    img{width:200px;margin-top:50px}
    </style>

    <img src="/logo">
    <h1>Telegram Master Panel 🚀</h1>
    <form method="post">
    <input name="user" placeholder="User"><br>
    <input name="password" placeholder="Password"><br>
    <button>Login</button>
    </form>
    """

# ---------------- PANEL ---------------- #
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    user = session["user"]
    data = load_config()
    u = data["users"][user]

    groups_html = ""
    for g in u["groups"]:
        groups_html += f"<label><input type='checkbox' name='groups' value='{g['id']}'> {g['name']}</label><br>"

    return f"""
    <style>
    body{{background:#0b0f1a;color:white;font-family:sans-serif}}
    .box{{max-width:500px;margin:auto}}
    input,textarea{{width:100%;padding:10px;margin:5px 0;border:none;border-radius:6px}}
    button{{background:#ffd700;padding:10px;border:none;border-radius:6px;width:100%}}
    </style>

    <div class="box">
    <img src="/logo" width="150">
    <h2>👑 USER: {user}</h2>

    <h3>🔑 Token</h3>
    <form method="post" action="/save_token">
    <input name="token" value="{u.get("token","")}">
    <button>Save</button></form>

    <h3>➕ Add User</h3>
    <form method="post" action="/add_user">
    <input name="newuser" placeholder="Username">
    <input name="newpass" placeholder="Password">
    <button>Add</button></form>

    <h3>🔒 Change Password</h3>
    <form method="post" action="/change_pass">
    <input name="newpass" placeholder="New Password">
    <button>Change</button></form>

    <h3>UserBot</h3>
    <form method="post" action="/save_api">
    <input name="api_id" placeholder="API_ID">
    <input name="api_hash" placeholder="API_HASH">
    <button>Save</button></form>

    <form method="post" action="/send_code">
    <input name="phone" placeholder="+855xxx">
    <button>Send Code</button></form>

    <form method="post" action="/verify">
    <input name="code" placeholder="OTP">
    <button>Verify</button></form>

    <form method="post" action="/fetch">
    <button>Fetch Groups</button></form>

    <h3>📢 Send Message</h3>
    <form method="post" action="/send">
    {groups_html}
    <textarea name="msg"></textarea>
    <button>Send</button></form>

    <a href="/logout">Logout</a>
    </div>
    """

# ---------------- USER ---------------- #
@app.route("/add_user", methods=["POST"])
def add_user():
    if session["user"] != "admin":
        return "No permission"

    data = load_config()
    data["users"][request.form["newuser"]] = {
        "password": request.form["newpass"],
        "token": "",
        "api_id": "",
        "api_hash": "",
        "session": request.form["newuser"],
        "groups": []
    }
    save_config(data)
    return redirect("/panel")

@app.route("/change_pass", methods=["POST"])
def change_pass():
    user = session["user"]
    data = load_config()
    data["users"][user]["password"] = request.form["newpass"]
    save_config(data)
    return redirect("/panel")

# ---------------- SAVE ---------------- #
@app.route("/save_token", methods=["POST"])
def save_token():
    user = session["user"]
    data = load_config()
    data["users"][user]["token"] = request.form["token"]
    save_config(data)
    return redirect("/panel")

@app.route("/save_api", methods=["POST"])
def save_api():
    user = session["user"]
    data = load_config()
    data["users"][user]["api_id"] = request.form["api_id"]
    data["users"][user]["api_hash"] = request.form["api_hash"]
    save_config(data)
    return redirect("/panel")

# ---------------- USERBOT ---------------- #
@app.route("/send_code", methods=["POST"])
def send_code():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    phone = request.form["phone"]
    session["phone"] = phone

    client = TelegramClient(f"{SESSION_DIR}/{u['session']}", int(u["api_id"]), u["api_hash"])
    client.connect()
    client.send_code_request(phone)

    return redirect("/panel")

@app.route("/verify", methods=["POST"])
def verify():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    client = TelegramClient(f"{SESSION_DIR}/{u['session']}", int(u["api_id"]), u["api_hash"])
    client.connect()

    try:
        client.sign_in(session["phone"], request.form["code"])
    except SessionPasswordNeededError:
        return "2FA Required"

    return redirect("/panel")

# ---------------- FETCH ---------------- #
@app.route("/fetch", methods=["POST"])
def fetch():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    client = TelegramClient(f"{SESSION_DIR}/{u['session']}", int(u["api_id"]), u["api_hash"])
    client.connect()

    groups = []
    for d in client.get_dialogs():
        if d.is_group:
            groups.append({"id": str(d.id), "name": d.name})

    data["users"][user]["groups"] = groups
    save_config(data)
    return redirect("/panel")

# ---------------- SEND ---------------- #
@app.route("/send", methods=["POST"])
def send():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    msg = request.form["msg"]
    selected = request.form.getlist("groups")

    client = TelegramClient(f"{SESSION_DIR}/{u['session']}", int(u["api_id"]), u["api_hash"])
    client.connect()

    success = 0
    fail = 0

    for gid in selected:
        try:
            client.send_message(int(gid), msg)
            success += 1
            time.sleep(random.uniform(1, 2))
        except:
            fail += 1

    return f"<h2>ส่งสำเร็จ {success} กลุ่ม | ล้มเหลว {fail}</h2><a href='/panel'>กลับ</a>"

# ---------------- LOGOUT ---------------- #
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
