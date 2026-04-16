from flask import Flask, request, session, redirect
import json, os
from telethon import TelegramClient

app = Flask(__name__)
app.secret_key = "secret123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
SESSION_DIR = os.path.join(BASE_DIR, "sessions")

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

        return "❌ Login Failed"

    return """
    <h2 style='text-align:center'>Telegram Master Panel 🚀</h2>
    <form method="post" style="text-align:center">
        <input name="user" placeholder="User"><br><br>
        <input name="password" placeholder="Password"><br><br>
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
    groups = u.get("groups", [])

    group_html = ""
    for g in groups:
        group_html += f"""
        <div>
            {g['name']} ({g['id']})
            <a href='/del_group?id={g['id']}'>❌</a>
        </div>
        """

    return f"""
    <h2>👑 USER: {user}</h2>

    <h3>🔑 Token</h3>
    <form method="post" action="/save_token">
        <input name="token" value="{u.get("token","")}">
        <button>Save</button>
    </form>

    <h3>UserBot API</h3>
    <form method="post" action="/save_api">
        <input name="api_id" value="{u.get("api_id","")}" placeholder="API_ID">
        <input name="api_hash" value="{u.get("api_hash","")}" placeholder="API_HASH">
        <button>Save</button>
    </form>

    <br>
    <form method="post" action="/fetch">
        <button>Fetch Groups (Auto ≤10)</button>
    </form>

    <h3>➕ Add Group</h3>
    <form method="post" action="/add_group">
        <input name="gid" placeholder="Group ID">
        <input name="name" placeholder="Group Name">
        <button>Add</button>
    </form>

    <h3>📋 Groups</h3>
    {group_html}

    <h3>📤 Send Message</h3>
    <form method="post" action="/send">
        <textarea name="msg"></textarea><br>
        <button>Send</button>
    </form>

    <br><a href="/logout">Logout</a>
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

# ---------------- ADD GROUP ---------------- #

@app.route("/add_group", methods=["POST"])
def add_group():
    user = session["user"]
    data = load_config()

    gid = request.form["gid"]
    name = request.form["name"]

    data["users"][user].setdefault("groups", []).append({
        "id": gid,
        "name": name
    })

    save_config(data)
    return redirect("/panel")

# ---------------- DELETE GROUP ---------------- #

@app.route("/del_group")
def del_group():
    user = session["user"]
    data = load_config()
    gid = request.args.get("id")

    groups = data["users"][user].get("groups", [])
    data["users"][user]["groups"] = [g for g in groups if str(g["id"]) != gid]

    save_config(data)
    return redirect("/panel")

# ---------------- FETCH ---------------- #

@app.route("/fetch", methods=["POST"])
def fetch():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    if not u.get("api_id") or not u.get("api_hash"):
        return "❌ ใส่ API ก่อน"

    try:
        api_id = int(u["api_id"])
    except:
        return "❌ API_ID ต้องเป็นตัวเลข"

    try:
        client = TelegramClient(f"{SESSION_DIR}/{user}", api_id, u["api_hash"])
        client.start()

        dialogs = client.get_dialogs()
        groups = []

        for d in dialogs:
            if d.is_group:
                groups.append({"id": d.id, "name": d.name})

        data["users"][user]["groups"] = groups[:10]
        save_config(data)

        return redirect("/panel")

    except Exception as e:
        return f"❌ ERROR: {str(e)}"

# ---------------- SEND ---------------- #

@app.route("/send", methods=["POST"])
def send():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    msg = request.form["msg"]

    if not msg:
        return "❌ ใส่ข้อความก่อน"

    try:
        api_id = int(u["api_id"])
        client = TelegramClient(f"{SESSION_DIR}/{user}", api_id, u["api_hash"])
        client.start()

        for g in u.get("groups", []):
            client.send_message(int(g["id"]), msg)

        return "✅ ส่งสำเร็จ"

    except Exception as e:
        return f"❌ ERROR: {str(e)}"

# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
