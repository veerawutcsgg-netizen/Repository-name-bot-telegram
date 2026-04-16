from flask import Flask, request, session, redirect
import json, os, time, random
from telethon import TelegramClient

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

    return """
    <style>
    body{background:#0b0f1a;color:white;text-align:center;font-family:sans-serif}
    input{padding:14px;margin:8px;border-radius:8px;border:none;width:260px}
    button{padding:12px 30px;background:#ffd700;border:none;border-radius:8px}
    </style>

    <h1>Telegram Master Panel 🚀</h1>
    <form method="post">
    <input name="user"><br>
    <input name="password"><br>
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
    for i,g in enumerate(u.get("groups", [])):
        groups_html += f"""
        <div style='margin:6px 0'>
        <input type='checkbox' name='groups' value='{g['id']}'> {g['name']}
        <a href='/del_group/{i}' style='color:red'>❌</a>
        </div>
        """

    return f"""
    <style>
    body{{background:#0b0f1a;color:white;font-family:sans-serif}}
    .box{{max-width:500px;margin:auto}}
    input,textarea{{width:100%;padding:14px;margin:6px 0;border-radius:8px;border:none}}
    button{{background:#ffd700;padding:12px;border:none;border-radius:8px;width:100%}}
    h3{{margin-top:20px}}
    </style>

    <div class="box">
    <h2>👑 {user}</h2>

    <h3>UserBot API</h3>
    <form method="post" action="/save_api">
    <input name="api_id" value="{u.get("api_id","")}" placeholder="API_ID">
    <input name="api_hash" value="{u.get("api_hash","")}" placeholder="API_HASH">
    <button>Save</button>
    </form>

    <h3>Fetch Groups (สูงสุด 10)</h3>
    <form method="post" action="/fetch">
    <button>Fetch</button>
    </form>

    <h3>เพิ่มกลุ่มเอง</h3>
    <form method="post" action="/add_group">
    <input name="gid" placeholder="Group ID">
    <input name="name" placeholder="Group Name">
    <button>Add</button>
    </form>

    <h3>รายการกลุ่ม</h3>
    <form method="post" action="/send" enctype="multipart/form-data">
    {groups_html}

    <h3>📢 ส่งข้อความ</h3>
    <textarea name="msg" placeholder="พิมข้อความ..."></textarea>
    <input type="file" name="file">
    <button>Send</button>
    </form>
    </div>
    """

# ---------------- SAVE API ---------------- #
@app.route("/save_api", methods=["POST"])
def save_api():
    user = session["user"]
    data = load_config()

    data["users"][user]["api_id"] = request.form["api_id"]
    data["users"][user]["api_hash"] = request.form["api_hash"]

    save_config(data)
    return redirect("/panel")

# ---------------- FETCH ---------------- #
@app.route("/fetch", methods=["POST"])
def fetch():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    try:
        client = TelegramClient(
            f"{SESSION_DIR}/{user}",
            int(u["api_id"]),
            u["api_hash"]
        )
        client.connect()

        groups = []
        for d in client.get_dialogs():
            if d.is_group:
                groups.append({
                    "id": str(d.id),
                    "name": d.name
                })

        data["users"][user]["groups"] = groups[:10]
        save_config(data)

        return redirect("/panel")

    except Exception as e:
        return f"❌ FETCH ERROR: {str(e)}"

# ---------------- ADD GROUP ---------------- #
@app.route("/add_group", methods=["POST"])
def add_group():
    user = session["user"]
    data = load_config()

    gid = request.form["gid"]
    name = request.form["name"]

    data["users"][user].setdefault("groups", []).append({
        "id": gid,
        "name": name or gid
    })

    save_config(data)
    return redirect("/panel")

# ---------------- DELETE ---------------- #
@app.route("/del_group/<int:index>")
def del_group(index):
    user = session["user"]
    data = load_config()

    try:
        data["users"][user]["groups"].pop(index)
        save_config(data)
    except:
        pass

    return redirect("/panel")

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
            f"{SESSION_DIR}/{user}",
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
                time.sleep(random.uniform(1, 2.5))

            except:
                fail += 1

        return f"<h2>✅ {ok} สำเร็จ | ❌ {fail} ล้มเหลว</h2><a href='/panel'>กลับ</a>"

    except Exception as e:
        return f"❌ SEND ERROR: {str(e)}"

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
