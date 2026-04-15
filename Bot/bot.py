from flask import Flask, request, render_template_string, session, redirect
import requests, json, os

app = Flask(__name__)
app.secret_key = "supersecret"

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"users":{"admin":{"password":"1234","token":"","groups":[]}}}
    with open(CONFIG_FILE,"r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE,"w") as f:
        json.dump(data,f,indent=2)

@app.route("/login", methods=["GET","POST"])
def login():
    config = load_config()
    if request.method == "POST":
        u = request.form["user"]
        p = request.form["pw"]
        if u in config["users"] and config["users"][u]["password"] == p:
            session["user"] = u
            return redirect("/")
    return """
    <style>
    body{background:#0b0b0b;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh}
    .box{background:#1a1a1a;padding:40px;border-radius:20px;width:320px}
    input{width:100%;padding:12px;margin:10px 0;border-radius:10px;border:none}
    button{width:100%;padding:12px;background:gold;border:none;border-radius:10px}
    </style>
    <div class="box">
    <h2>LOGIN</h2>
    <form method="post">
    <input name="user" placeholder="Username">
    <input name="pw" type="password" placeholder="Password">
    <button>Login</button>
    </form>
    </div>
    """

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

            result = f"ส่งสำเร็จ {ok} กลุ่ม"

        save_config(config)

    return render_template_string("""
<style>
body{background:#0b0b0b;color:#fff;font-family:sans-serif;padding:20px}
.card{background:#1a1a1a;padding:20px;border-radius:15px;margin:20px 0}
input,textarea{width:100%;padding:12px;margin:8px 0;border-radius:10px;border:none}
button{background:gold;border:none;padding:10px;border-radius:10px}
.drop{border:2px dashed gold;padding:20px;text-align:center;border-radius:15px;margin-top:10px}
.preview img,video{max-width:200px;margin-top:10px;border-radius:10px}
</style>

<h2>USER: {{user}}</h2>
<a href="/logout">Logout</a>

<div class="card">
<h3>Token</h3>
<form method="post">
<input name="token" value="{{user_data.token}}">
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

<div class="card">
<h3>Send</h3>
<form method="post" enctype="multipart/form-data" id="form">

{% for g in user_data.groups %}
<label><input type="checkbox" name="gids" value="{{g.id}}"> {{g.name}}</label><br>
{% endfor %}

<textarea name="msg" placeholder="ข้อความ"></textarea>

<div class="drop" id="drop">
ลากไฟล์มาวาง หรือคลิกเลือก
<input type="file" name="file" id="file" hidden>
</div>

<div class="preview" id="preview"></div>

<button name="action" value="send">Send</button>
</form>
</div>

<h3>{{result}}</h3>

<script>
let drop = document.getElementById("drop");
let fileInput = document.getElementById("file");
let preview = document.getElementById("preview");

drop.onclick = () => fileInput.click();

drop.ondragover = e => {
    e.preventDefault();
    drop.style.background="#222";
};

drop.ondragleave = e => {
    drop.style.background="";
};

drop.ondrop = e => {
    e.preventDefault();
    fileInput.files = e.dataTransfer.files;
    showPreview(fileInput.files[0]);
};

fileInput.onchange = () => {
    showPreview(fileInput.files[0]);
};

function showPreview(file){
    preview.innerHTML="";
    let url = URL.createObjectURL(file);

    if(file.type.includes("image")){
        preview.innerHTML = "<img src='"+url+"'>";
    }else if(file.type.includes("video")){
        preview.innerHTML = "<video src='"+url+"' controls></video>";
    }
}
</script>
""", user=user, user_data=user_data, result=result)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
