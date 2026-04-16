from flask import Flask, request, session, redirect, render_template_string, send_from_directory
import json, os, requests

app = Flask(__name__)
app.secret_key = "supersecretkey"

APP_NAME = "Telegram Master Panel 🚀"
CONFIG_FILE = "Bot/config.json"

# ---------------- LOGO ----------------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------------- CONFIG ----------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        default = {
            "users": {
                "admin": {
                    "password": "1234",
                    "token": "",
                    "groups": []
                }
            }
        }
        os.makedirs("Bot", exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f, indent=2)
        return default

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
        user = request.form.get("user")
        pw = request.form.get("pw")

        if user in config["users"] and config["users"][user]["password"] == pw:
            session["user"] = user
            return redirect("/")
        else:
            return "❌ Login ผิด"

    return f"""
    <style>
    body {{
        background:#0b0f14;
        display:flex;justify-content:center;align-items:center;height:100vh;
        color:white;font-family:sans-serif;
    }}
    .box {{background:#111;padding:40px;border-radius:16px;width:340px;text-align:center;}}
    input {{width:100%;padding:10px;margin:6px 0;background:#222;border:none;color:white;border-radius:8px;}}
    button {{width:100%;padding:10px;background:gold;border:none;border-radius:8px;}}
    </style>

    <div class="box">
        <img src="/logo" style="width:200px"><br>
        <h2>{APP_NAME}</h2>
        <form method="post">
            <input name="user" placeholder="Username">
            <input type="password" name="pw" placeholder="Password">
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
    is_admin = user == "admin"

    user_data = config["users"][user]
    result = ""

    if request.method == "POST":
        action = request.form.get("action")

        # -------- USER MANAGEMENT --------
        if is_admin:
            if action == "add_user":
                u = request.form.get("new_user")
                p = request.form.get("new_pw")

                if u in config["users"]:
                    result = "❌ user ซ้ำ"
                else:
                    config["users"][u] = {"password": p, "token":"", "groups":[]}
                    result = "✅ เพิ่ม user แล้ว"

            elif action == "delete_user":
                u = request.form.get("del_user")
                if u != "admin":
                    config["users"].pop(u, None)

            elif action == "edit_user_pw":
                u = request.form.get("edit_user")
                pw = request.form.get("edit_pw")
                config["users"][u]["password"] = pw

        # -------- USER CHANGE PASSWORD --------
        if action == "change_my_pw":
            user_data["password"] = request.form.get("mypw")

        # -------- TOKEN --------
        if action == "save_token":
            user_data["token"] = request.form.get("token")

        # -------- GROUP --------
        if action == "add_group":
            user_data["groups"].append({
                "id": request.form.get("gid"),
                "name": request.form.get("gname")
            })

        # -------- SEND --------
        if action == "send":
            token = user_data["token"]
            gids = request.form.getlist("gids")
            msg = request.form.get("msg")
            file = request.files.get("file")

            ok = 0

            for gid in gids:
                try:
                    if file and file.filename:
                        file.stream.seek(0)

                        if "video" in file.mimetype:
                            url = f"https://api.telegram.org/bot{token}/sendVideo"
                            requests.post(url,
                                data={"chat_id": gid, "caption": msg},
                                files={"video": file}
                            )
                        else:
                            url = f"https://api.telegram.org/bot{token}/sendPhoto"
                            requests.post(url,
                                data={"chat_id": gid, "caption": msg},
                                files={"photo": file}
                            )
                    else:
                        url = f"https://api.telegram.org/bot{token}/sendMessage"
                        requests.post(url,
                            data={"chat_id": gid, "text": msg}
                        )

                    ok += 1
                except:
                    pass

            result = f"✅ ส่ง {ok} กลุ่ม"

        save_config(config)

    HTML = """
    <style>
    body {background:#0b0f14;color:white;font-family:sans-serif;}
    .box {max-width:700px;margin:auto;padding:20px;}
    input,textarea {width:100%;padding:10px;margin:5px 0;border-radius:8px;border:none;background:#222;color:white;}
    button {background:gold;border:none;padding:10px;border-radius:8px;}
    </style>

    <div class="box">
        <img src="/logo" style="width:200px">
        <h2>{{app}}</h2>

        <a href="/logout">Logout</a>

        {% if is_admin %}
        <h3>👑 Manage Users</h3>

        <form method="post">
            <input name="new_user" placeholder="Username">
            <input name="new_pw" placeholder="Password">
            <button name="action" value="add_user">Add</button>
        </form>

        <br>

        {% for u in config.users %}
            {% if u != "admin" %}
            <form method="post">
                {{u}}
                <input name="edit_pw" placeholder="New Password">
                <input type="hidden" name="edit_user" value="{{u}}">
                <button name="action" value="edit_user_pw">Edit</button>
                <button name="action" value="delete_user" name="del_user" value="{{u}}">Delete</button>
            </form>
            {% endif %}
        {% endfor %}
        {% endif %}

        <h3>Change Password</h3>
        <input name="mypw">
        <button name="action" value="change_my_pw">Change</button>

        <h3>Token</h3>
        <input name="token" value="{{user_data.token}}">
        <button name="action" value="save_token">Save</button>

        <h3>Add Group</h3>
        <input name="gid">
        <input name="gname">
        <button name="action" value="add_group">Add</button>

        <h3>Send</h3>

        <label><input type="checkbox" id="all"> ALL</label><br>

        {% for g in user_data.groups %}
            <label><input type="checkbox" name="gids" value="{{g.id}}" class="g"> {{g.name}}</label><br>
        {% endfor %}

        <textarea name="msg"></textarea>
        <input type="file" name="file">

        <button name="action" value="send">Send</button>

        <h3>{{result}}</h3>
    </div>

    <script>
    document.getElementById("all").onchange = function(){
        document.querySelectorAll(".g").forEach(e=>e.checked=this.checked)
    }
    </script>
    """

    return render_template_string(HTML,
        user_data=user_data,
        config=config,
        is_admin=is_admin,
        result=result,
        app=APP_NAME
    )

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
