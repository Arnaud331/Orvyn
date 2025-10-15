import os
import threading
from bot.bot import bot
from utils.flask_app import app

def run_flask():
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes", "on")
    app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Missing env var: DISCORD_TOKEN")
    bot.run(token)
