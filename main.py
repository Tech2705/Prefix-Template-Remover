import os
import re
import json
from pyrogram import Client, filters

# --- Config from environment variables ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
OWNER_ID = int(os.environ.get("OWNER_ID"))
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")
TEMPLATE_FILE = "templates.json"  # File to store templates

# --- Load and Save Templates ---
def load_templates():
    if os.path.exists(TEMPLATE_FILE):
        try:
            with open(TEMPLATE_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_templates(templates):
    with open(TEMPLATE_FILE, "w") as f:
        json.dump(templates, f)

TEMPLATES_TO_REMOVE = load_templates()

# --- Initialize bot ---
app = Client("template_renamer", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# --- Utility function: clean filename templates ---
def clean_filename(name):
    for template in TEMPLATES_TO_REMOVE:
        name = name.replace(template, "")
    name = re.sub(r"[\s_-]+", " ", name).strip()
    return name

# --- Restrict access ---
def is_authorized(user_id):
    return user_id == OWNER_ID

# --- Handle files ---
@app.on_message(filters.private & (filters.document | filters.audio | filters.video))
async def handle_file(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("❌ Access denied.")
        return

    media = message.document or message.audio or message.video
    if not media or not media.file_name:
        await message.reply_text("❌ Error: No filename found.")
        return

    old_name = media.file_name
    new_name = clean_filename(old_name)
    downloaded = await message.download(file_name=new_name)

    # Send to user
    await message.reply_document(
        document=downloaded,
        file_name=new_name,
        caption=f"✅ Renamed:\n`{old_name}` ➜ `{new_name}`"
    )

    # Send to channel
    if TARGET_CHANNEL:
        try:
            await client.send_document(
                chat_id=TARGET_CHANNEL,
                document=downloaded,
                file_name=new_name,
                caption=f"`{new_name}` uploaded via bot."
            )
        except Exception as e:
            await message.reply_text(f"⚠️ Failed to send to channel: {e}")

    os.remove(downloaded)

# --- /start ---
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply_text(
        "👋 Welcome! Send me a file and I’ll clean its name using the active templates.\n"
        "Use /templates to check or update filters."
    )

# --- /templates ---
@app.on_message(filters.command("templates"))
async def list_templates(client, message):
    if not is_authorized(message.from_user.id):
        return
    if TEMPLATES_TO_REMOVE:
        text = "🧹 Current templates being removed:\n" + "\n".join(f"- `{t}`" for t in TEMPLATES_TO_REMOVE)
    else:
        text = "No templates set yet."
    await message.reply_text(text)

# --- /addtemplate <template> ---
@app.on_message(filters.command("addtemplate"))
async def add_template(client, message):
    if not is_authorized(message.from_user.id):
        return
    if len(message.command) < 2:
        await message.reply_text("Usage: /addtemplate <text>")
        return
    template = " ".join(message.command[1:])
    if template in TEMPLATES_TO_REMOVE:
        await message.reply_text("Already exists.")
        return
    TEMPLATES_TO_REMOVE.append(template)
    save_templates(TEMPLATES_TO_REMOVE)
    await message.reply_text(f"✅ Template `{template}` added.")

# --- /removetemplate <template> ---
@app.on_message(filters.command("removetemplate"))
async def remove_template(client, message):
    if not is_authorized(message.from_user.id):
        return
    if len(message.command) < 2:
        await message.reply_text("Usage: /removetemplate <text>")
        return
    template = " ".join(message.command[1:])
    if template not in TEMPLATES_TO_REMOVE:
        await message.reply_text("Not found.")
        return
    TEMPLATES_TO_REMOVE.remove(template)
    save_templates(TEMPLATES_TO_REMOVE)
    await message.reply_text(f"✅ Template `{template}` removed.")

# --- Optional: Flask dummy web server for Koyeb health check ---
if os.environ.get("PORT"):
    from flask import Flask
    from threading import Thread

    app_web = Flask(__name__)

    @app_web.route("/")
    def home():
        return "Bot is live", 200

    def run_web():
        app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

    Thread(target=run_web).start()

# --- Run bot ---
app.run()
