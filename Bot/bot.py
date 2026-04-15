from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests

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
    <body style='background:#0b0f1a;color:white;text-align:center;font-family:sans-serif'>
    <img src='/logo' width='200'><h2>Telegram Master Panel 🚀</h2>
    <form method='post'>
    <input name='user' placeholder='User'><br><br>
    <input name='password' placeholder='Password'><br><br>
    <button>Login</button>
    </form></body>
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
        groups_html += f"<input type='checkbox' name='groups' value='{g['id']}'> {g['name']}<br>"

    return f"""
    <body style='background:#0b0f1a;color:white;font-family:sans-serif'>
    <img src='/logo' width='150'>
    <h2>Telegram Master Panel 🚀</h2>

    <h3>Bot Token</h3>
    <form method='post' action='/save_token'>
    <input name='token' value='{u.get("token","")}'><button>Save</button></form>

    <h3>UserBot API</h3>
    <form method='post' action='/save_api'>
    <input name='api_id' placeholder='API_ID'>
    <input name='api_hash' placeholder='API_HASH'>
    <button>Save</button></form>

    <h3>Login UserBot</h3>
    <form method='post' action='/send_code'>
    <input name='phone' placeholder='+855xxxx'><button>Send Code</button></form>

    <form method='post' action='/verify_code'>
    <input name='code' placeholder='OTP'><button>Verify</button></form>

    <h3>Fetch Groups</h3>
    <form method='post' action='/fetch'><button>Fetch</button></form>

    <h3>Send</h3>
    <form method='post' action='/send'>
    {groups_html}
    <textarea name='msg'></textarea><br>
    <button>Send</button></form>

    <br><a href='/logout'>Logout</a>
    </body>
    """

# ---------------- SAVE TOKEN ---------------- #

@app.route("/save_token", methods=["POST"])
def save_token():
    user = session["user"]
    data = load_config()
    data["users"][user]["token"] = request.form["token"]
    save_config(data)
    return redirect("/panel")

# ---------------- SAVE API ---------------- #

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
    session["phone"] = phone

    client = TelegramClient(f"{SESSION_DIR}/{u['session']}", int(u["api_id"]), u["api_hash"])
    client.connect()
    client.send_code_request(phone)

    return redirect("/panel")

# ---------------- VERIFY ---------------- #

@app.route("/verify_code", methods=["POST"])
def verify_code():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    phone = session.get("phone")
    code = request.form["code"]

    client = TelegramClient(f"{SESSION_DIR}/{u['session']}", int(u["api_id"]), u["api_hash"])
    client.connect()

    try:
        client.sign_in(phone, code)
    except SessionPasswordNeededError:
        return "2FA Required"

    return redirect("/panel")

# ---------------- FETCH GROUPS ---------------- #

@app.route("/fetch", methods=["POST"])
def fetch():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    client = TelegramClient(f"{SESSION_DIR}/{u['session']}", int(u["api_id"]), u["api_hash"])
    client.connect()

    groups = []
    for dialog in client.get_dialogs():
        if dialog.is_group:
            groups.append({"id": str(dialog.id), "name": dialog.name})

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

    for gid in selected:
        client.send_message(int(gid), msg)

    return redirect("/panel")

# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ---------------- #

import os

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
