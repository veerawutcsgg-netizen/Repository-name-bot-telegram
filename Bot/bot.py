from flask import Flask, request, session, redirect, send_from_directory
import json, os, requests

app = Flask(__name__)
app.secret_key = "secret123"

CONFIG_FILE = "Bot/config.json"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- LOGO ----------
@app.route("/logo")
def logo():
    return send_from_directory(".", "logo.png")

# ---------- CONFIG ----------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users": {
            "admin": {
                "password": "1234",
                "role": "admin",
                "token": "",
                "groups": []
            }
        }}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------- LANGUAGE ----------
def t(key):
    lang = session.get("lang","th")
    text = {
        "th": {"send":"ส่ง","token":"โทเคน","group":"กลุ่ม"},
        "en": {"send":"Send","token":"Token","group":"Groups"}
    }
    return text[lang].get(key,key)

@app.route("/lang/<l>")
def lang(l):
    session["lang"] = l
    return redirect(request.referrer or "/panel")

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

    return """
    <style>
    body{background:#000;color:white;text-align:center;font-family:sans-serif}
    .box{margin-top:120px}
    input{padding:15px;width:280px;margin:10px;border-radius:10px}
    button{padding:12px 30px;background:gold;border:none;border-radius:10px}
    </style>

    <div style="position:absolute;top:10px;right:20px">
    <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
    </div>

    <div class='box'>
    <img src='/logo' width=150>
    <h2>Telegram Panel</h2>
    <form method='post'>
    <input name='user'><br>
    <input name='password' type='password'><br>
    <button>Login</button>
    </form>
    </div>
    """

# ---------- PANEL ----------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    data = load_config()
    u = data["users"][session["user"]]
    report = session.pop("report","")

    group_html = ""
    for g in u["groups"]:
        group_html += f"""
        <div>
        <input type='checkbox' name='gid' value='{g["id"]}'>
        {g["name"]}
        <a href='/del_group/{g["id"]}'>❌</a>
        </div>
        """

   return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>

body {{
    margin:0;
    font-family: 'Segoe UI', sans-serif;
    background: linear-gradient(180deg,#000,#020617);
    color:white;
}}

.container {{
    max-width:500px;
    margin:auto;
    padding:15px;
}}

.card {{
    background:#0f172a;
    border-radius:20px;
    padding:15px;
    margin-bottom:15px;
    box-shadow:0 0 20px rgba(255,0,0,0.15);
}}

.logo {{
    display:block;
    margin:auto;
    width:140px;
    margin-bottom:10px;
}}

h2 {{
    text-align:center;
}}

input, textarea {{
    width:100%;
    padding:14px;
    border-radius:12px;
    border:none;
    margin:6px 0;
    background:#1e293b;
    color:white;
}}

button {{
    width:100%;
    padding:14px;
    border:none;
    border-radius:12px;
    background:linear-gradient(180deg,#FFD700,#FFC107);
    font-weight:bold;
}}

.group-row {{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:8px;
    border-bottom:1px solid #333;
}}

.dropzone {{
    border:2px dashed #555;
    padding:20px;
    text-align:center;
    border-radius:15px;
    margin-top:10px;
    cursor:pointer;
}}

.preview img, .preview video {{
    width:100%;
    margin-top:10px;
    border-radius:10px;
}}

.topbar {{
    position:absolute;
    top:10px;
    right:15px;
}}

</style>
</head>

<body>

<div class="topbar">
🌐 <a href="/lang/th">TH</a> | <a href="/lang/en">EN</a>
</div>

<div class="container">

<img src="/logo" class="logo">

<h2>👑 {user}</h2>

{f"<div style='color:#4ade80;text-align:center'>{report}</div>" if report else ""}

<div class="card">
<h3>🔑 Token</h3>
<form method="post" action="/save_token">
<input name="token" value="{u["token"]}">
<button>Save</button>
</form>
</div>

<div class="card">
<h3>➕ Add Group</h3>
<form method="post" action="/add_group">
<input name="gid" placeholder="Group ID">
<input name="name" placeholder="Group Name">
<button>Add</button>
</form>
</div>

<div class="card">
<h3>📋 Groups</h3>

<label><input type="checkbox" onclick="toggle(this)"> ALL</label>

<form method="post" action="/send" enctype="multipart/form-data">

{"".join([f'''
<div class="group-row">
<label>
<input type="checkbox" name="gid" value="{g["id"]}">
{g["name"]}
</label>
<a href="/del_group/{g["id"]}">❌</a>
</div>
''' for g in u["groups"]])}

<h3>📤 Message</h3>
<textarea name="msg"></textarea>

<div class="dropzone" id="drop">
📂 Drag & Drop Image/Video
<input type="file" name="file" id="file" hidden>
</div>

<div class="preview" id="preview"></div>

<button type="submit">🚀 Send</button>

</form>
</div>

{admin_html}

<a href="/logout" style="display:block;text-align:center">Logout</a>

</div>

<script>
function toggle(source){{
    let c=document.getElementsByName('gid');
    for(let i=0;i<c.length;i++) c[i].checked = source.checked;
}}

let drop = document.getElementById('drop');
let file = document.getElementById('file');
let preview = document.getElementById('preview');

drop.onclick = () => file.click();

drop.ondragover = e => e.preventDefault();

drop.ondrop = e => {{
    e.preventDefault();
    file.files = e.dataTransfer.files;
    show(file.files[0]);
}};

file.onchange = () => show(file.files[0]);

function show(f){{
    preview.innerHTML="";
    if(!f) return;

    if(f.type.startsWith("image")){{
        preview.innerHTML = `<img src="${{URL.createObjectURL(f)}}">`;
    }} else if(f.type.startsWith("video")){{
        preview.innerHTML = `<video controls src="${{URL.createObjectURL(f)}}"></video>`;
    }}
}}
</script>

</body>
</html>
"""

# ---------- SAVE ----------
@app.route("/save_token", methods=["POST"])
def save_token():
    data = load_config()
    data["users"][session["user"]]["token"] = request.form["token"]
    save_config(data)
    return redirect("/panel")

@app.route("/add_group", methods=["POST"])
def add_group():
    data = load_config()
    data["users"][session["user"]]["groups"].append({
        "id": request.form["gid"],
        "name": request.form["name"]
    })
    save_config(data)
    return redirect("/panel")

@app.route("/del_group/<gid>")
def del_group(gid):
    data = load_config()
    u = session["user"]
    data["users"][u]["groups"] = [g for g in data["users"][u]["groups"] if g["id"] != gid]
    save_config(data)
    return redirect("/panel")

# ---------- SEND ----------
@app.route("/send", methods=["POST"])
def send():
    data = load_config()
    u = data["users"][session["user"]]

    token = u["token"]
    msg = request.form["msg"]
    file = request.files.get("file")

    success = 0

    for g in u["groups"]:
        try:
            if file:
                path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(path)
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendDocument",
                    data={"chat_id": g["id"], "caption": msg},
                    files={"document": open(path,"rb")}
                )
            else:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id": g["id"], "text": msg}
                )
            success += 1
        except:
            pass

    session["report"] = f"ส่งสำเร็จ {success} กลุ่ม"
    return redirect("/panel")

# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
