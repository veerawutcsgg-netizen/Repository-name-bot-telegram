from flask import Flask, request, session, redirect, render_template_string, send_from_directory
import json, os, requests
from telethon.sync import TelegramClient

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
        return {"users": {}}
    try:
        return json.load(open(CONFIG_FILE))
    except:
        return {"users": {}}

def save_config(data):
    json.dump(data, open(CONFIG_FILE, "w"), indent=2)

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

    return "<h2>Login</h2>"

# ---------------- HOME ----------------
@app.route("/", methods=["GET","POST"])
def home():
    if "user" not in session:
        return redirect("/login")

    config = load_config()
    user = session["user"]

    user_data = config["users"].get(user, {
        "token":"",
        "api_id":"",
        "api_hash":"",
        "groups":[]
    })

    result = ""

    if request.method == "POST":
        action = request.form.get("action")

        # -------- SAVE --------
        if action == "save_token":
            user_data["token"] = request.form.get("token")

        elif action == "save_userbot":
            user_data["api_id"] = request.form.get("api_id")
            user_data["api_hash"] = request.form.get("api_hash")

        elif action == "add_group":
            user_data["groups"].append({
                "id": request.form.get("gid"),
                "name": request.form.get("gname")
            })

        # -------- FETCH GROUP --------
        elif action == "fetch_groups":
            try:
                client = TelegramClient("Bot/userbot", int(user_data["api_id"]), user_data["api_hash"])
                client.connect()

                dialogs = client.get_dialogs()

                groups = []
                for d in dialogs:
                    if d.is_group or d.is_channel:
                        groups.append({
                            "id": d.id,
                            "name": d.title
                        })

                user_data["groups"] = groups
                result = f"✅ ดึง {len(groups)} กลุ่ม"

                client.disconnect()
            except Exception as e:
                result = f"❌ {e}"

        # -------- SEND --------
        elif action == "send":
            token = user_data.get("token")
            gids = request.form.getlist("gids")
            msg = request.form.get("msg")

            ok = 0
            fail = 0

            # userbot
            client = None
            try:
                client = TelegramClient("Bot/userbot", int(user_data["api_id"]), user_data["api_hash"])
                client.connect()
            except:
                client = None

            for gid in gids:
                try:
                    sent = False

                    # -------- BOT TRY --------
                    if token:
                        try:
                            r = requests.post(
                                f"https://api.telegram.org/bot{token}/sendMessage",
                                data={"chat_id": gid, "text": msg}
                            )

                            if r.status_code == 200:
                                sent = True
                        except:
                            pass

                    # -------- USERBOT FALLBACK --------
                    if not sent and client:
                        client.send_message(int(gid), msg)
                        sent = True

                    if sent:
                        ok += 1
                    else:
                        fail += 1

                except Exception as e:
                    fail += 1
                    print("ERROR:", e)

            if client:
                client.disconnect()

            result = f"✅ สำเร็จ {ok} | ❌ ล้มเหลว {fail}"

        config["users"][user] = user_data
        save_config(config)

    HTML = """
    <h2>Telegram Panel 🚀</h2>

    <form method="POST">

    <h3>Bot Token</h3>
    <input name="token" value="{{user_data.token}}">
    <button name="action" value="save_token">Save</button>

    <h3>UserBot</h3>
    <input name="api_id" placeholder="API_ID" value="{{user_data.api_id}}">
    <input name="api_hash" placeholder="API_HASH" value="{{user_data.api_hash}}">
    <button name="action" value="save_userbot">Save</button>

    <br><br>
    <button name="action" value="fetch_groups">🔄 ดึงกลุ่มอัตโนมัติ</button>

    <h3>Groups</h3>
    {% for g in user_data.groups %}
        <label><input type="checkbox" name="gids" value="{{g.id}}"> {{g.name}}</label><br>
    {% endfor %}

    <textarea name="msg"></textarea><br>
    <button name="action" value="send">🚀 Send</button>

    </form>

    <h3>{{result}}</h3>
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
