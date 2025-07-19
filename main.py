import os
import re
import json
from pyrogram import Client, filters, enums

# ---- Configuration from Environment ----
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
OWNER_ID = int(os.environ.get("OWNER_ID"))
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")
TEMPLATE_FILE = "templates.json"

# ---- Load & Save Templates ----
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

# ---- Initialize Bot ----
app = Client("template_remover_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ---- Utility ----
def is_authorized(user_id):
    return user_id == OWNER_ID

def clean_filename(name):
    for template in TEMPLATES_TO_REMOVE:
        name = name.replace(template, "")
    name = re.sub(r"[\s_-]+", " ", name).strip()
    return name

# ---- File Handler ----
@app.on_message(filters.private & (filters.document | filters.audio | filters.video))
async def handle_file(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("❌ Access denied.")
        return

    media = message.document or message.audio or message.video
    if not media or not media.file_name:
        await message.reply_text("⚠️ File has no name.")
        return

    old_name = media.file_name
    new_name = clean_filename(old_name)
    downloaded = await message.download(file_name=new_name)

    await message.reply_document(
        document=downloaded,
        file_name=new_name,
        caption=f"✅ Renamed:\n`{old_name}` ➜ `{new_name}`"
    )

    if TARGET_CHANNEL:
        try:
            await client.send_document(
                chat_id=int(TARGET_CHANNEL),
                document=downloaded,
                file_name=new_name,
                caption=f"`{new_name}` uploaded via bot."
            )
        except Exception as e:
            await message.reply_text(f"⚠️ Couldn't forward to channel: {e}")

    os.remove(downloaded)

# ---- /start Command ----
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply_text(
        "**Prefix/Template Remover:**\n"
        "👋 Welcome! Send me a file and I’ll clean its name using the active templates.\n"
        "Use /templates to check or update filters.",
        parse_mode=enums.ParseMode.MARKDOWN
    )

# ---- /templates Command ----
@app.on_message(filters.command("templates"))
async def templates_cmd(client, message):
    if not is_authorized(message.from_user.id):
        return
    if TEMPLATES_TO_REMOVE:
        templates = "\n".join(f"- `{item}`" for item in TEMPLATES_TO_REMOVE)
        await message.reply_text(f"**Current templates:**\n{templates}", parse_mode=enums.ParseMode.MARKDOWN)
    else:
        await message.reply_text("No templates set.")

# ---- /addtemplate Command ----
@app.on_message(filters.command("addtemplate"))
async def add_template(client, message):
    if not is_authorized(message.from_user.id):
        return
    if len(message.command) < 2:
        await message.reply_text("Usage: /addtemplate <text>")
        return
    template = " ".join(message.command[1:])
    if template in TEMPLATES_TO_REMOVE:
        await message.reply_text(f"`{template}` already exists.", parse_mode=enums.ParseMode.MARKDOWN)
        return
    TEMPLATES_TO_REMOVE.append(template)
    save_templates(TEMPLATES_TO_REMOVE)
    await message.reply_text(f"✅ Template `{template}` added.", parse_mode=enums.ParseMode.MARKDOWN)

# ---- /removetemplate Command ----
@app.on_message(filters.command("removetemplate"))
async def remove_template(client, message):
    if not is_authorized(message.from_user.id):
        return
    if len(message.command) < 2:
        await message.reply_text("Usage: /removetemplate <text>")
        return
    template = " ".join(message.command[1:])
    if template not in TEMPLATES_TO_REMOVE:
        await message.reply_text(f"`{template}` not found.", parse_mode=enums.ParseMode.MARKDOWN)
        return
    TEMPLATES_TO_REMOVE.remove(template)
    save_templates(TEMPLATES_TO_REMOVE)
    await message.reply_text(f"✅ Template `{template}` removed.", parse_mode=enums.ParseMode.MARKDOWN)

# ---- /help Command ----
@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply_text(
        "**Template Management Help**\n\n"
        "`/templates` — List current templates.\n"
        "`/addtemplate <text>` — Add a new removal template.\n"
        "`/removetemplate <text>` — Remove existing template.\n"
        "`/help` — Show this help message.\n\n"
        "_Only the owner can use these commands._",
        parse_mode=enums.ParseMode.MARKDOWN
    )

# ---- Koyeb Health Check Server (optional) ----
if os.environ.get("PORT"):
    from flask import Flask
    from threading import Thread

    app_web = Flask(__name__)

    @app_web.route("/")
    def root():
        return "Bot running", 200

    def run_web():
        app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

    Thread(target=run_web).start()

# ---- Run the Bot ----
app.run()
