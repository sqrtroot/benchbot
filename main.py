from consts import TOKEN
from db import init_db
from bot import bot
from score_watcher import FileWatcher

init_db()
FileWatcher().start()
bot.run(TOKEN)
