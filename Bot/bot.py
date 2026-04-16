from flask import Flask, request, session, redirect, send_from_directory
import json, os, time, random
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

app = Flask(__name__)
app.secret_key = "secret123"

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
    .box{margin-top:120px}
    input{padding:14px;margin:8px;border-radius:8px;border:none;width:280px}
    button{padding:12px 40px;background:#ffd700;border:none;border-radius:8px}
    img{width:260px}
    </style>

    <div class="box">
    <img src="/logo">
    <h1>Telegram Master Panel 🚀</h1>
    <form method="post">
    <input name="user"><br>
    <input name="password"><br>
    <button>Login</button>
    </form>
    </div>
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
    for g in u.get("groups", []):
        groups_html += f"<label><input type='checkbox' name='groups' value='{g['id']}'> {g['name']}</label><br>"

    return f"""
    <style>
    body{{background:#0b0f1a;color:white;font-family:sans-serif}}
    .box{{max-width:500px;margin:auto;padding-top:30px}}
    input,textarea{{width:100%;padding:14px;margin:6px 0;border:none;border-radius:8px}}
    button{{background:#ffd700;padding:14px;border:none;border-radius:8px;width:100%}}
    </style>

    <div class="box">
    <img src="/logo" style="display:block;margin:auto;width:200px">
    <h2>👑 USER: {user}</h2>

    <h3>🔑 Token</h3>
    <form method="post" action="/save_token">
    <input name="token" value="{u.get("token","")}">
    <button>Save</button></form>

    <h3>UserBot API</h3>
    <form method="post" action="/save_api">
    <input name="api_id" value="{u.get("api_id","")}">
    <input name="api_hash" value="{u.get("api_hash","")}">
    <button>Save</button></form>

    <h3>Login UserBot</h3>
    <form method="post" action="/send_code">
    <input name="phone" value="{session.get("phone","")}" placeholder="+855xxxxxxxx">
    <button>Send Code</button></form>

    <form method="post" action="/verify">
    <input name="code" placeholder="OTP">
    <button>Verify</button></form>

    <form method="post" action="/fetch">
    <button>Fetch Groups</button></form>

    <h3>📢 Send</h3>
    <form method="post" action="/send" enctype="multipart/form-data">
    {groups_html}
    <textarea name="msg"></textarea>
    <input type="file" name="file">
    <button>Send</button></form>

    <a href="/logout">Logout</a>
    </div>
    """

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

# ---------------- SEND CODE ---------------- #
@app.route("/send_code", methods=["POST"])
def send_code():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    phone = request.form["phone"]

    if not phone:
        return "❌ ใส่เบอร์ก่อน"

    session["phone"] = phone

    try:
        client = TelegramClient(
            f"{SESSION_DIR}/{user}.session",
            int(u["api_id"]),
            u["api_hash"]
        )
        client.connect()

        if client.is_user_authorized():
            return "⚠️ login อยู่แล้ว"

        client.send_code_request(phone)

        return redirect("/panel")

    except Exception as e:
        return f"❌ ERROR: {str(e)}"

# ---------------- VERIFY ---------------- #
@app.route("/verify", methods=["POST"])
def verify():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    phone = session.get("phone")
    code = request.form["code"]

    if not phone:
        return "❌ กด Send Code ก่อน"

    try:
        client = TelegramClient(
            f"{SESSION_DIR}/{user}.session",
            int(u["api_id"]),
            u["api_hash"]
        )

        client.connect()
        client.sign_in(phone, code)

        return redirect("/panel")

    except Exception as e:
        return f"❌ ERROR: {str(e)}"

# ---------------- FETCH (FIXED) ---------------- #
@app.route("/fetch", methods=["POST"])
def fetch():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    try:
        client = TelegramClient(
            f"{SESSION_DIR}/{user}.session",
            int(u["api_id"]),
            u["api_hash"]
        )

        client.connect()

        if not client.is_user_authorized():
            return "❌ ยังไม่ได้ login"

        groups = []
        for d in client.get_dialogs():
            if d.is_group:
                groups.append({
                    "id": str(d.id),
                    "name": d.name
                })

        data["users"][user]["groups"] = groups
        save_config(data)

        return redirect("/panel")

    except Exception as e:
        return f"❌ FETCH ERROR: {str(e)}"

# ---------------- SEND ---------------- #
@app.route("/send", methods=["POST"])
def send():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    msg = request.form["msg"]
    selected = request.form.getlist("groups")
    file = request.files.get("file")

    try:
        client = TelegramClient(
            f"{SESSION_DIR}/{user}.session",
            int(u["api_id"]),
            u["api_hash"]
        )
        client.connect()

        ok, fail = 0, 0

        for gid in selected:
            try:
                if file and file.filename:
                    path = "temp"
                    file.save(path)
                    client.send_file(int(gid), path, caption=msg)
                    os.remove(path)
                else:
                    client.send_message(int(gid), msg)

                ok += 1
                time.sleep(random.uniform(1, 2))

            except:
                fail += 1

        return f"<h2>✅ {ok} success | ❌ {fail} fail</h2><a href='/panel'>Back</a>"

    except Exception as e:
        return f"❌ SEND ERROR: {str(e)}"

# ---------------- LOGOUT ---------------- #
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
