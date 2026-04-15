from flask import Flask, request, session, redirect, render_template_string
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"

# ---------------- CONFIG ----------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {"admin": {"password":"1234","token":"","groups":[]}}}
    with open(CONFIG_FILE,"r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE,"w") as f:
        json.dump(data,f,indent=2)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    cfg = load_config()

    if request.method=="POST":
        u = request.form.get("user")
        p = request.form.get("pw")

        if u in cfg["users"] and cfg["users"][u]["password"] == p:
            session["user"] = u
            return redirect("/")
        return "❌ Login Failed"

    return '''
    <h2>Login</h2>
    <form method="post">
    <input name="user"><br>
    <input name="pw" type="password"><br>
    <button>Login</button>
    </form>
    '''

# ---------------- HOME ----------------
@app.route("/", methods=["GET","POST"])
def home():
    if "user" not in session:
        return redirect("/login")

    cfg = load_config()
    user = session["user"]
    is_admin = user == "admin"

    data = cfg["users"][user]
    msg = ""

    if request.method=="POST":
        action = request.form.get("action")

        # -------- ADMIN --------
        if is_admin:
            if action == "add_user":
                u = request.form.get("new_user")
                p = request.form.get("new_pw")

                if u in cfg["users"]:
                    msg = "❌ user ซ้ำ"
                else:
                    cfg["users"][u] = {"password":p,"token":"","groups":[]}
                    msg = "✅ เพิ่ม user แล้ว"

            elif action == "delete_user":
                u = request.form.get("del_user")
                if u != "admin":
                    cfg["users"].pop(u, None)

            elif action == "change_user_pw":
                u = request.form.get("edit_user")
                pw = request.form.get("edit_pw")
                if u in cfg["users"]:
                    cfg["users"][u]["password"] = pw

        # -------- USER --------
        if action == "change_my_pw":
            data["password"] = request.form.get("mypw")

        # -------- TOKEN --------
        if action == "save_token":
            data["token"] = request.form.get("token")

        # -------- GROUP --------
        if action == "add_group":
            data["groups"].append({
                "id": request.form.get("gid"),
                "name": request.form.get("gname")
            })

        # -------- SEND --------
        if action == "send":
            token = data["token"]
            gids = request.form.getlist("gids")
            text = request.form.get("msg")
            mode = request.form.get("mode")

            ok = 0

            for g in gids:
                try:
                    if mode == "bot":
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            data={"chat_id":g,"text":text}
                        )
                    else:
                        # user mode (placeholder)
                        # แนะนำให้ทำแบบ manual integration จริง
                        print("User mode send:", g, text)

                    ok += 1
                except:
                    pass

            msg = f"✅ ส่ง {ok} กลุ่ม"

        save_config(cfg)

    return render_template_string("""
    <h2>USER: {{user}}</h2>

    {% if is_admin %}
    <h3>👑 Manage Users</h3>

    <form method="post">
    <input name="new_user" placeholder="user">
    <input name="new_pw" placeholder="password">
    <button name="action" value="add_user">Add</button>
    </form>

    <hr>

    {% for u in cfg.users %}
        {% if u != "admin" %}
        <form method="post">
            {{u}}
            <input name="edit_pw" placeholder="new pw">
            <input type="hidden" name="edit_user" value="{{u}}">
            <button name="action" value="change_user_pw">Edit</button>
            <button name="action" value="delete_user" name="del_user" value="{{u}}">Delete</button>
        </form>
        {% endif %}
    {% endfor %}
    {% endif %}

    <h3>🔒 Change My Password</h3>
    <form method="post">
    <input name="mypw">
    <button name="action" value="change_my_pw">Change</button>
    </form>

    <h3>Token</h3>
    <form method="post">
    <input name="token" value="{{data.token}}">
    <button name="action" value="save_token">Save</button>
    </form>

    <h3>Add Group</h3>
    <form method="post">
    <input name="gid">
    <input name="gname">
    <button name="action" value="add_group">Add</button>
    </form>

    <h3>Send</h3>
    <form method="post">

    <select name="mode">
        <option value="bot">Bot</option>
        <option value="user">User (manual)</option>
    </select><br><br>

    {% for g in data.groups %}
        <input type="checkbox" name="gids" value="{{g.id}}"> {{g.name}}<br>
    {% endfor %}

    <textarea name="msg"></textarea><br>
    <button name="action" value="send">Send</button>
    </form>

    <h3>{{msg}}</h3>
    """, user=user, is_admin=is_admin, cfg=cfg, data=data, msg=msg)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
