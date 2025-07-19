import os
import re
from pyrogram import Client, filters

# ---- Configuration ----
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")  # e.g., "@yourchannel"
OWNER_ID = int(os.environ.get("OWNER_ID"))  # Your Telegram user ID

TEMPLATES_ENV = os.environ.get("TEMPLATES_TO_REMOVE", "")
TEMPLATES_TO_REMOVE = [tmpl.strip() for tmpl in TEMPLATES_ENV.split(",") if tmpl.strip()]

# ---- Initialize Bot ----
app = Client(
    "template_remover_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
)

# ---- Filename Cleanup ----
def clean_filename(filename):
    for template in TEMPLATES_TO_REMOVE:
        filename = filename.replace(template, "")
    filename = re.sub(r"[\s_-]+", " ", filename).strip()
    return filename

# ---- File Handler ----
@app.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def rename_and_send(client, message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ Access denied. You're not authorized to use this bot.")
        return

    media = message.document or message.video or message.audio
    old_name = media.file_name if media and media.file_name else None

    if not old_name:
        await message.reply_text("Couldn't detect filename.")
        return

    new_name = clean_filename(old_name)
    downloaded_path = await message.download(file_name=new_name)

    # Send to user
    await message.reply_document(
        document=downloaded_path,
        file_name=new_name,
        caption=f"✅ Renamed:\n`{old_name}` ➜ `{new_name}`"
    )

    # Send to channel
    if TARGET_CHANNEL:
        try:
            await client.send_document(
                chat_id=TARGET_CHANNEL,
                document=downloaded_path,
                file_name=new_name,
                caption=f"`{new_name}` uploaded by bot"
            )
        except Exception as e:
            await message.reply_text(f"❌ Failed to send to channel: {e}")

    os.remove(downloaded_path)

# ---- /templates Command ----
@app.on_message(filters.command("templates"))
async def show_templates(client, message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ Access denied.")
        return

    if TEMPLATES_TO_REMOVE:
        templates = "\n".join(f"- `{t}`" for t in TEMPLATES_TO_REMOVE)
        await message.reply_text(f"Currently removing templates:\n{templates}")
    else:
        await message.reply_text("No templates set in `TEMPLATES_TO_REMOVE` env variable.")

# ---- /start Command ----
@app.on_message(filters.command("start"))
async def start(client, message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ Access denied.")
        return

    await message.reply_text(
        "👋 Hi! Send me a file and I’ll remove defined templates from the filename, send it back"
        " to you and forward it to the target channel."
    )

# ---- Optional Flask (for Koyeb health check) ----
if os.environ.get("PORT"):
    from flask import Flask
    from threading import Thread

    web_app = Flask("healthcheck")

    @web_app.route("/")
    def index():
        return "Bot Alive", 200

    def run_web():
        web_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

    Thread(target=run_web).start()

# ---- Run Bot ----
app.run()
