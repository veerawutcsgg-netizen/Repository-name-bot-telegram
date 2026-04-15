from flask import Flask, request, render_template_string, session, redirect
import requests, json, os

app = Flask(__name__)
app.secret_key = "supersecret"

CONFIG_FILE = "Bot/config.json"

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
    error = ""

    if request.method == "POST":
        user = request.form.get("user")
        pw = request.form.get("pw")

        if user in config["users"] and config["users"][user]["password"] == pw:
            session["user"] = user
            return redirect("/")
        else:
            error = "❌ Login ผิด"

    return render_template_string("""
    <style>
    body{background:#0d0d0d;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;font-size:18px;}
    .box{background:#1a1a1a;padding:30px;border-radius:15px;width:350px;text-align:center;}
    input{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:none;}
    button{width:100%;padding:12px;background:gold;border:none;border-radius:8px;}
    </style>

    <div class="box">
        <h2>LOGIN</h2>
        <form method="post">
        <input name="user" placeholder="Username">
        <input name="pw" type="password" placeholder="Password">
        <button>Login</button>
        </form>
        <p>{{error}}</p>
    </div>
    """, error=error)

# ---------------- MAIN ----------------
@app.route("/", methods=["GET","POST"])
def home():
    if "user" not in session:
        return redirect("/login")

    config = load_config()
    user = session["user"]
    user_data = config["users"][user]
    result = ""

    if request.method == "POST":
        action = request.form.get("action")

        # ADMIN ONLY
        if action == "add_user" and user == "admin":
            u = request.form.get("new_user")
            p = request.form.get("new_pw")

            if not u or not p:
                result = "❌ กรอกไม่ครบ"
            elif u in config["users"]:
                result = "❌ user ซ้ำ"
            else:
                config["users"][u] = {"password":p,"token":"","groups":[]}
                result = f"✅ เพิ่ม {u} สำเร็จ"

        elif action == "change_user_pw" and user == "admin":
            target = request.form.get("target_user")
            newpw = request.form.get("newpw")
            config["users"][target]["password"] = newpw
            result = f"✅ เปลี่ยนรหัส {target}"

        elif action == "delete_user" and user == "admin":
            target = request.form.get("target_user")
            if target != "admin":
                config["users"].pop(target)
                result = f"🗑 ลบ {target}"

        # USER SELF
        elif action == "change_pw":
            user_data["password"] = request.form.get("newpw")
            result = "✅ เปลี่ยนรหัสแล้ว"

        elif action == "save_token":
            user_data["token"] = request.form.get("token")

        elif action == "add_group":
            user_data["groups"].append({
                "id": request.form.get("gid"),
                "name": request.form.get("gname")
            })

        elif request.form.get("del"):
            gid = request.form.get("del")
            user_data["groups"] = [g for g in user_data["groups"] if g["id"] != gid]

        elif action == "send":
            token = user_data["token"]
            gids = request.form.getlist("gids")
            msg = request.form.get("msg")

            ok = 0
            for gid in gids:
                try:
                    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                  data={"chat_id": gid, "text": msg})
                    ok += 1
                except:
                    pass

            result = f"ส่งสำเร็จ {ok} กลุ่ม"

        save_config(config)

    return render_template_string("""
    <style>
    body{background:#0d0d0d;color:#fff;font-family:sans-serif;padding:20px;font-size:18px;}
    .card{background:#1a1a1a;padding:20px;margin:15px 0;border-radius:15px;}
    input,textarea{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:none;}
    button{background:gold;border:none;padding:10px;border-radius:8px;margin:3px;}
    </style>

    <h2>👑 USER: {{user}}</h2>
    <a href="/logout">Logout</a>

    {% if user == "admin" %}
    <div class="card">
    <h3>👑 จัดการ USER</h3>

    <form method="post">
    <input name="new_user" placeholder="Username">
    <input name="new_pw" placeholder="Password">
    <button name="action" value="add_user">➕ Add</button>
    </form>

    <hr>

    {% for u in config["users"] %}
        {% if u != "admin" %}
        <form method="post">
        <b>{{u}}</b><br>
        <input name="newpw" placeholder="New Password">
        <input type="hidden" name="target_user" value="{{u}}">
        <button name="action" value="change_user_pw">🔑 เปลี่ยนรหัส</button>
        <button name="action" value="delete_user">🗑 ลบ</button>
        </form>
        <hr>
        {% endif %}
    {% endfor %}

    </div>
    {% endif %}

    <div class="card">
    <h3>🔐 เปลี่ยนรหัสตัวเอง</h3>
    <form method="post">
    <input name="newpw" placeholder="New Password">
    <button name="action" value="change_pw">Change</button>
    </form>
    </div>

    <div class="card">
    <h3>📢 Send</h3>
    <form method="post">
    {% for g in user_data.groups %}
    <label><input type="checkbox" name="gids" value="{{g.id}}"> {{g.name}}</label><br>
    {% endfor %}
    <textarea name="msg"></textarea>
    <button name="action" value="send">Send</button>
    </form>
    </div>

    <h3>{{result}}</h3>
    """, user=user, user_data=user_data, config=config, result=result)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
