from flask import Flask, request, session, redirect, render_template_string, send_from_directory
import json, os, requests

app = Flask(__name__)
app.secret_key = "supersecretkey"

APP_NAME = "Telegram Master Panel 🚀"
CONFIG_FILE = "Bot/config.json"

# ---------------- LOGO ROUTE ----------------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------------- CONFIG ----------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {}}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}}

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
        font-family:sans-serif;
        display:flex;
        justify-content:center;
        align-items:center;
        height:100vh;
        color:white;
    }}
    .box {{
        background:#111;
        padding:40px;
        border-radius:16px;
        width:340px;
        text-align:center;
    }}
    .logo {{
        width:220px;
        margin-bottom:10px;
        filter: drop-shadow(0 0 15px #00d9ff);
    }}
    input {{
        width:100%;
        padding:12px;
        margin:8px 0;
        border-radius:8px;
        border:none;
        background:#222;
        color:white;
    }}
    button {{
        width:100%;
        padding:12px;
        background:gold;
        border:none;
        border-radius:8px;
        cursor:pointer;
    }}
    </style>

    <div class="box">
        <img src="/logo" class="logo">
        <h2>{APP_NAME}</h2>
        <h3>🚀 Login</h3>

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

    user_data = config["users"].get(user, {"token":"","groups":[]})
    result = ""

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_token":
            user_data["token"] = request.form.get("token")

        elif action == "add_group":
            user_data["groups"].append({
                "id": request.form.get("gid"),
                "name": request.form.get("gname")
            })

        elif action == "send":
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

            result = f"✅ ส่งสำเร็จ {ok} กลุ่ม"

        config["users"][user] = user_data
        save_config(config)

    HTML = """
    <style>
    body {background:#0b0f14;color:white;font-family:sans-serif;}
    .box {max-width:600px;margin:auto;padding:20px;}
    .logo {width:200px;display:block;margin:auto;filter: drop-shadow(0 0 10px #00d9ff);}
    input,textarea {width:100%;padding:10px;margin:5px 0;border-radius:8px;border:none;background:#222;color:white;}
    button {background:gold;border:none;padding:10px;border-radius:8px;cursor:pointer;}
    </style>

    <div class="box">
        <img src="/logo" class="logo">
        <h2 style="text-align:center;">Telegram Master Panel 🚀</h2>

        <a href="/logout">Logout</a><br><br>

        <form method="POST" enctype="multipart/form-data">

        <h3>Token</h3>
        <input name="token" value="{{user_data.token}}">
        <button name="action" value="save_token">Save</button>

        <h3>Add Group</h3>
        <input name="gid" placeholder="Group ID">
        <input name="gname" placeholder="Name">
        <button name="action" value="add_group">Add</button>

        <h3>Send</h3>

        <label><input type="checkbox" id="all"> ALL</label><br>

        {% for g in user_data.groups %}
            <label><input type="checkbox" name="gids" value="{{g.id}}" class="g"> {{g.name}}</label><br>
        {% endfor %}

        <textarea name="msg"></textarea>
        <input type="file" name="file">

        <button name="action" value="send">🚀 Send</button>
        </form>

        <h3>{{result}}</h3>
    </div>

    <script>
    document.getElementById("all").onchange = function(){
        document.querySelectorAll(".g").forEach(e=>e.checked=this.checked)
    }
    </script>
    """

    return render_template_string(HTML, user_data=user_data, result=result)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
