from flask import Flask, request, session, redirect
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# ---------- CONFIG ----------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {}}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

        return "❌ Login Failed"

    return ui_login()

# ---------- PANEL ----------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    user = session["user"]
    data = load_config()
    u = data["users"][user]

    group_html = ""
    for g in u.get("groups", []):
        group_html += f"""
        <div class="group">
            {g['name']} ({g['id']})
            <a href="/del_group?id={g['id']}">❌</a>
        </div>
        """

    admin_html = ""
    if u.get("role") == "admin":
        for name in data["users"]:
            admin_html += f"""
            <div class="group">
                {name}
                <a href="/del_user?u={name}">❌</a>
            </div>
            """

    return ui_panel(user, u, group_html, admin_html)

# ---------- SAVE ----------
@app.route("/save_token", methods=["POST"])
def save_token():
    user = session["user"]
    data = load_config()
    data["users"][user]["token"] = request.form["token"]
    save_config(data)
    return redirect("/panel")

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

@app.route("/del_group")
def del_group():
    user = session["user"]
    data = load_config()
    gid = request.args.get("id")

    data["users"][user]["groups"] = [
        g for g in data["users"][user]["groups"] if str(g["id"]) != gid
    ]

    save_config(data)
    return redirect("/panel")

# ---------- SEND ----------
@app.route("/send", methods=["POST"])
def send():
    user = session["user"]
    data = load_config()
    u = data["users"][user]

    msg = request.form["msg"]

    if not u.get("token"):
        return "❌ ใส่ Token ก่อน"

    for g in u.get("groups", []):
        try:
            requests.post(
                f"https://api.telegram.org/bot{u['token']}/sendMessage",
                data={"chat_id": g["id"], "text": msg}
            )
        except:
            pass

    return redirect("/panel")

# ---------- ADMIN ----------
@app.route("/add_user", methods=["POST"])
def add_user():
    user = session["user"]
    data = load_config()

    if data["users"][user]["role"] != "admin":
        return "❌ ไม่มีสิทธิ์"

    u = request.form["username"]
    p = request.form["password"]

    data["users"][u] = {
        "password": p,
        "role": "user",
        "token": "",
        "groups": []
    }

    save_config(data)
    return redirect("/panel")

@app.route("/del_user")
def del_user():
    user = session["user"]
    data = load_config()

    if data["users"][user]["role"] != "admin":
        return "❌ ไม่มีสิทธิ์"

    u = request.args.get("u")

    if u != "admin":
        data["users"].pop(u, None)

    save_config(data)
    return redirect("/panel")

@app.route("/change_password", methods=["POST"])
def change_password():
    user = session["user"]
    data = load_config()

    data["users"][user]["password"] = request.form["new"]
    save_config(data)
    return redirect("/panel")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- UI ----------
def ui_login():
    return """
    <style>
    body{background:#0b0f1a;color:white;text-align:center;font-family:sans-serif}
    input{padding:10px;margin:5px;width:200px}
    button{padding:10px 20px;background:#ffd700;border:none}
    </style>
    <h1>Telegram Panel 🚀</h1>
    <form method="post">
    <input name="user"><br>
    <input name="password" type="password"><br>
    <button>Login</button>
    </form>
    """

def ui_panel(user,u,group_html,admin_html):
    return f"""
    <style>
    body{{background:#0b0f1a;color:white;font-family:sans-serif;padding:20px}}
    input,textarea{{width:100%;padding:10px;margin:5px}}
    button{{background:#ffd700;padding:10px;border:none;width:100%}}
    .box{{background:#111;padding:15px;margin:10px 0;border-radius:10px}}
    </style>

    <h2>👑 {user}</h2>

    <div class="box">
    <h3>Token</h3>
    <form method="post" action="/save_token">
    <input name="token" value="{u.get("token","")}">
    <button>Save</button>
    </form>
    </div>

    <div class="box">
    <h3>Add Group</h3>
    <form method="post" action="/add_group">
    <input name="gid" placeholder="Group ID">
    <input name="name" placeholder="Group Name">
    <button>Add</button>
    </form>
    </div>

    <div class="box">
    <h3>Groups</h3>
    {group_html}
    </div>

    <div class="box">
    <h3>Send Message</h3>
    <form method="post" action="/send">
    <textarea name="msg"></textarea>
    <button>Send</button>
    </form>
    </div>

    <div class="box">
    <h3>Change Password</h3>
    <form method="post" action="/change_password">
    <input name="new">
    <button>Change</button>
    </form>
    </div>

    <div class="box">
    <h3>Admin Panel</h3>
    {admin_html}
    <form method="post" action="/add_user">
    <input name="username">
    <input name="password">
    <button>Add User</button>
    </form>
    </div>

    <a href="/logout">Logout</a>
    """

# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
