from flask import Flask, request, render_template_string, session, redirect
import requests, json, os

app = Flask(__name__)
app.secret_key = "supersecret"

CONFIG_FILE = "Bot/config.json"

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
            error = "❌ Login ผิด"
    else:
        error = ""

    return render_template_string("""
    <style>
    body{
        background:#0d0d0d;
        font-family:sans-serif;
        color:#fff;
        display:flex;
        justify-content:center;
        align-items:center;
        height:100vh;
    }
    .box{
        background:#1a1a1a;
        padding:30px;
        border-radius:15px;
        width:300px;
        text-align:center;
        box-shadow:0 0 20px rgba(255,215,0,0.2);
    }
    input{
        width:100%;
        padding:10px;
        margin:5px 0;
        border:none;
        border-radius:8px;
    }
    button{
        width:100%;
        padding:10px;
        background:gold;
        border:none;
        border-radius:8px;
        cursor:pointer;
    }
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

    if user not in config["users"]:
        config["users"][user] = {"password":"1234","token":"","groups":[]}

    user_data = config["users"][user]
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

        elif request.form.get("del"):
            gid = request.form.get("del")
            user_data["groups"] = [g for g in user_data["groups"] if g["id"] != gid]

        elif action == "add_user":
            new_user = request.form.get("new_user")
            new_pw = request.form.get("new_pw")
            if new_user not in config["users"]:
                config["users"][new_user] = {
                    "password": new_pw,
                    "token": "",
                    "groups": []
                }

        elif action == "change_pw":
            user_data["password"] = request.form.get("newpw")

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
                                files={"video": (file.filename, file.stream, file.mimetype)}
                            )
                        else:
                            url = f"https://api.telegram.org/bot{token}/sendPhoto"
                            requests.post(url,
                                data={"chat_id": gid, "caption": msg},
                                files={"photo": (file.filename, file.stream, file.mimetype)}
                            )
                    else:
                        url = f"https://api.telegram.org/bot{token}/sendMessage"
                        requests.post(url,
                            data={"chat_id": gid, "text": msg}
                        )

                    ok += 1
                except:
                    pass

            result = f"ส่งสำเร็จ {ok} กลุ่ม"

        save_config(config)

    return render_template_string("""
    <style>
    body{background:#0d0d0d;color:#fff;font-family:sans-serif;padding:20px;}
    .card{background:#1a1a1a;padding:15px;margin:10px 0;border-radius:10px;}
    input,textarea{width:100%;padding:10px;margin:5px 0;border-radius:8px;border:none;}
    button{background:gold;border:none;padding:8px 15px;border-radius:8px;cursor:pointer;margin:3px;}
    img{max-width:200px;border-radius:10px;margin-top:10px;}
    </style>

    <h2>👑 USER: {{user}}</h2>
    <a href="/logout">Logout</a>

    <div class="card">
    <h3>🔑 Token</h3>
    <form method="post">
    <input name="token" value="{{user_data.token}}">
    <button name="action" value="save_token">Save</button>
    </form>
    </div>

    <div class="card">
    <h3>➕ Add User</h3>
    <form method="post">
    <input name="new_user" placeholder="Username">
    <input name="new_pw" placeholder="Password">
    <button name="action" value="add_user">Add</button>
    </form>
    </div>

    <div class="card">
    <h3>🔐 Change Password</h3>
    <form method="post">
    <input name="newpw" placeholder="New Password">
    <button name="action" value="change_pw">Change</button>
    </form>
    </div>

    <div class="card">
    <h3>📢 Send Message</h3>
    <form method="post" enctype="multipart/form-data">

    <label><input type="checkbox" id="all"> ALL</label><br>

    {% for g in user_data.groups %}
    <label><input type="checkbox" name="gids" value="{{g.id}}" class="g"> {{g.name}}</label>
    <button name="del" value="{{g.id}}">🗑</button><br>
    {% endfor %}

    <textarea name="msg" placeholder="พิมพ์ข้อความ..."></textarea>

    <input type="file" name="file" id="fileInput">
    <img id="preview" style="display:none;">

    <button name="action" value="send">🚀 Send</button>
    </form>

    <h3>{{result}}</h3>
    </div>

    <script>
    document.getElementById("all").onchange=function(){
        document.querySelectorAll(".g").forEach(e=>e.checked=this.checked)
    }

    document.getElementById("fileInput").onchange=function(e){
        const file=e.target.files[0];
        if(file){
            const reader=new FileReader();
            reader.onload=function(e){
                let img=document.getElementById("preview");
                img.src=e.target.result;
                img.style.display="block";
            }
            reader.readAsDataURL(file);
        }
    }
    </script>
    """, user=user, user_data=user_data, result=result)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
