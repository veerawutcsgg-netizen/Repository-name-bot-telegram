from flask import Flask, request, session, redirect, render_template_string
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {}}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    config = load_config()
    if request.method == "POST":
        u = request.form.get("user")
        p = request.form.get("pw")

        if u in config["users"] and config["users"][u]["password"] == p:
            session["user"] = u
            return redirect("/")
        return "❌ Login ผิด"

    return """
    <style>
    body{background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}
    .box{background:#111;padding:30px;border-radius:10px;width:300px}
    input{width:100%;padding:10px;margin:10px 0}
    button{width:100%;padding:10px;background:#FFD700;border:none}
    </style>

    <div class="box">
    <h2>Login</h2>
    <form method="post">
    <input name="user" placeholder="Username">
    <input name="pw" type="password" placeholder="Password">
    <button>Login</button>
    </form>
    </div>
    """

# ---------------- HOME ----------------
@app.route("/", methods=["GET","POST"])
def home():
    if "user" not in session:
        return redirect("/login")

    config = load_config()
    user = session["user"]
    is_admin = (user == "admin")

    if user not in config["users"]:
        config["users"][user] = {"password":"1234","token":"","groups":[]}

    udata = config["users"][user]
    result = ""

    if request.method == "POST":
        action = request.form.get("action")

        # ---------------- ADMIN ----------------
        if is_admin:
            if action == "add_user":
                u = request.form.get("newuser")
                p = request.form.get("newpass")
                if u in config["users"]:
                    result = "❌ user ซ้ำ"
                else:
                    config["users"][u] = {"password":p,"token":"","groups":[]}
                    result = "✅ เพิ่ม user"

            if action == "del_user":
                du = request.form.get("target")
                if du != "admin":
                    config["users"].pop(du, None)

            if action == "admin_pw":
                tu = request.form.get("target")
                np = request.form.get("newpw_admin")
                if tu in config["users"]:
                    config["users"][tu]["password"] = np

        # ---------------- USER ----------------
        if action == "self_pw":
            udata["password"] = request.form.get("newpw")

        if action == "save_token":
            udata["token"] = request.form.get("token")

        if action == "add_group":
            gid = request.form.get("gid")
            gname = request.form.get("gname")
            if gid and gname:
                udata["groups"].append({"id":gid,"name":gname})

        if action == "send":
            token = udata["token"]
            gids = request.form.getlist("gids")
            msg = request.form.get("msg")
            file = request.files.get("file")

            ok = 0

            for gid in gids:
                try:
                    if file and file.filename:
                        file.stream.seek(0)

                        if "video" in file.mimetype:
                            url=f"https://api.telegram.org/bot{token}/sendVideo"
                            requests.post(url,data={"chat_id":gid,"caption":msg},
                            files={"video":(file.filename,file.stream,file.mimetype)})
                        else:
                            url=f"https://api.telegram.org/bot{token}/sendPhoto"
                            requests.post(url,data={"chat_id":gid,"caption":msg},
                            files={"photo":(file.filename,file.stream,file.mimetype)})
                    else:
                        url=f"https://api.telegram.org/bot{token}/sendMessage"
                        requests.post(url,data={"chat_id":gid,"text":msg})

                    ok+=1
                except:
                    pass

            result=f"ส่ง {ok} กลุ่ม"

        save_config(config)

    return render_template_string("""
    <style>
    body{background:#000;color:#fff;font-family:sans-serif;padding:20px}
    .card{background:#111;padding:20px;margin:15px 0;border-radius:10px}
    input,textarea{width:100%;padding:10px;margin:5px 0;background:#222;color:#fff;border:none}
    button{background:#FFD700;padding:8px;border:none;margin-top:5px}
    </style>

    <h2>USER: {{user}}</h2>
    <a href="/logout">Logout</a>

    <div class="card">
    <h3>Token</h3>
    <form method="post">
    <input name="token" value="{{udata.token}}">
    <button name="action" value="save_token">Save</button>
    </form>
    </div>

    <div class="card">
    <h3>Add Group</h3>
    <form method="post">
    <input name="gid" placeholder="Group ID">
    <input name="gname" placeholder="Name">
    <button name="action" value="add_group">Add</button>
    </form>
    </div>

    {% if is_admin %}
    <div class="card">
    <h3>Manage Users</h3>

    <form method="post">
    <input name="newuser" placeholder="Username">
    <input name="newpass" placeholder="Password">
    <button name="action" value="add_user">Add</button>
    </form>

    <hr>

    {% for u in config.users %}
        {% if u != "admin" %}
        <form method="post">
        <b>{{u}}</b>
        <input name="target" value="{{u}}" hidden>
        <input name="newpw_admin" placeholder="New Password">
        <button name="action" value="admin_pw">Change</button>
        <button name="action" value="del_user">Delete</button>
        </form>
        {% endif %}
    {% endfor %}

    </div>
    {% endif %}

    <div class="card">
    <h3>Change Password</h3>
    <form method="post">
    <input name="newpw" placeholder="New Password">
    <button name="action" value="self_pw">Change</button>
    </form>
    </div>

    <div class="card">
    <h3>Send</h3>
    <form method="post" enctype="multipart/form-data">

    {% for g in udata.groups %}
        <label><input type="checkbox" name="gids" value="{{g.id}}"> {{g.name}}</label><br>
    {% endfor %}

    <textarea name="msg"></textarea>
    <input type="file" name="file">

    <button name="action" value="send">Send</button>
    </form>
    </div>

    <h3>{{result}}</h3>
    """, user=user, udata=udata, config=config, is_admin=is_admin, result=result)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
