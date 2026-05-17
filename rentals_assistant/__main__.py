import sys

from rentals_assistant.bot import start_bot
from rentals_assistant.scheduler import start

if "--bot" in sys.argv:
    start_bot()
else:
    start()
