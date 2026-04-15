from flask import Flask, request, session, redirect, render_template_string
import sqlite3, requests, os

app = Flask(__name__)
app.secret_key = "secret123"

APP_NAME = "Sender SaaS"
LOGO = "https://cdn-icons-png.flaticon.com/512/906/906334.png"

DB = "data.db"

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, token TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS groups(id TEXT, name TEXT, owner TEXT)")

    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES ('admin','1234','')")

    conn.commit()
    conn.close()

init_db()

def db():
    return sqlite3.connect(DB)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form.get("user")
        p = request.form.get("pw")

        con = db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        res = cur.fetchone()
        con.close()

        if res:
            session["user"] = u
            return redirect("/")
        return "❌ Login Failed"

    return """
    <style>
    body{background:#0d0d0d;color:#fff;font-family:sans-serif;
    display:flex;justify-content:center;align-items:center;height:100vh}
    .box{background:#1a1a1a;padding:40px;border-radius:15px;width:320px;text-align:center}
    input{width:100%;padding:12px;margin:10px 0;border:none;border-radius:8px}
    button{width:100%;padding:12px;background:gold;border:none;border-radius:8px}
    </style>

    <div class="box">
    <h2>🚀 Login</h2>
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

    user = session["user"]
    is_admin = user == "admin"

    con = db()
    cur = con.cursor()

    result = ""

    # โหลดข้อมูล
    cur.execute("SELECT token FROM users WHERE username=?", (user,))
    token = cur.fetchone()[0]

    cur.execute("SELECT id,name FROM groups WHERE owner=?", (user,))
    groups = cur.fetchall()

    # -------- ACTION --------
    if request.method == "POST":
        action = request.form.get("action")

        # ADMIN
        if is_admin:
            if action == "add_user":
                u = request.form.get("newuser")
                p = request.form.get("newpass")
                cur.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (u,p,""))

            if action == "del_user":
                u = request.form.get("target")
                cur.execute("DELETE FROM users WHERE username=?", (u,))
                cur.execute("DELETE FROM groups WHERE owner=?", (u,))

        # USER
        if action == "save_token":
            t = request.form.get("token")
            cur.execute("UPDATE users SET token=? WHERE username=?", (t,user))

        if action == "add_group":
            cur.execute("INSERT INTO groups VALUES (?,?,?)",
                        (request.form.get("gid"),request.form.get("gname"),user))

        if action == "send":
            gids = request.form.getlist("gids")
            msg = request.form.get("msg")
            file = request.files.get("file")

            ok = 0
            for gid in gids:
                try:
                    if file and file.filename:
                        file.stream.seek(0)
                        if "video" in file.mimetype:
                            requests.post(f"https://api.telegram.org/bot{token}/sendVideo",
                                data={"chat_id":gid,"caption":msg},
                                files={"video":file})
                        else:
                            requests.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                                data={"chat_id":gid,"caption":msg},
                                files={"photo":file})
                    else:
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                            data={"chat_id":gid,"text":msg})
                    ok+=1
                except:
                    pass
            result = f"🚀 Sent {ok}"

        con.commit()

        # reload
        cur.execute("SELECT id,name FROM groups WHERE owner=?", (user,))
        groups = cur.fetchall()

    # admin users
    cur.execute("SELECT username FROM users")
    users = cur.fetchall()

    con.close()

    return render_template_string("""
<style>
body{margin:0;background:#0d0d0d;color:#fff;font-family:sans-serif}
.sidebar{width:220px;background:#111;height:100vh;position:fixed;padding:20px}
.main{margin-left:240px;padding:20px}
.logo{width:40px}
.card{background:#1a1a1a;padding:20px;border-radius:10px;margin-bottom:20px}
input,textarea{width:100%;padding:10px;margin:5px 0;background:#222;color:#fff;border:none}
button{background:gold;border:none;padding:10px;margin-top:5px;border-radius:6px}
.drop{border:2px dashed gold;padding:20px;text-align:center;margin-top:10px}
img,video{max-width:100%;margin-top:10px}
</style>

<div class="sidebar">
<img src="{{logo}}" class="logo">
<h3>{{app}}</h3>
<p>👤 {{user}}</p>
<a href="/logout" style="color:red">Logout</a>
</div>

<div class="main">

<div class="card">
<h3>Token</h3>
<form method="post">
<input name="token" value="{{token}}">
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
<form method="post" enctype="multipart/form-data">

<label><input type="checkbox" id="all"> ALL</label><br>

{% for g in groups %}
<label><input type="checkbox" name="gids" value="{{g[0]}}" class="g"> {{g[1]}}</label><br>
{% endfor %}

<textarea name="msg"></textarea>

<div class="drop" onclick="file.click()">
ลากไฟล์
<input id="file" type="file" name="file" hidden onchange="preview(this)">
</div>

<img id="img" style="display:none">
<video id="vid" controls style="display:none"></video>

<button name="action" value="send">Send</button>
</form>
</div>

{% if is_admin %}
<div class="card">
<h3>Manage Users</h3>
<form method="post">
<input name="newuser">
<input name="newpass">
<button name="action" value="add_user">Add</button>
</form>

{% for u in users %}
{% if u[0] != "admin" %}
<form method="post">
<b>{{u[0]}}</b>
<input name="target" value="{{u[0]}}" hidden>
<button name="action" value="del_user">Delete</button>
</form>
{% endif %}
{% endfor %}
</div>
{% endif %}

<h3>{{result}}</h3>
</div>

<script>
document.getElementById("all").addEventListener("change",function(){
 document.querySelectorAll(".g").forEach(cb=>cb.checked=this.checked)
})

function preview(f){
 let file=f.files[0]
 if(!file)return
 let url=URL.createObjectURL(file)
 if(file.type.includes("image")){
  img.src=url; img.style.display="block"
  vid.style.display="none"
 }else{
  vid.src=url; vid.style.display="block"
  img.style.display="none"
 }
}
</script>
""", user=user, token=token, groups=groups, users=users,
       is_admin=is_admin, result=result, app=APP_NAME, logo=LOGO)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
