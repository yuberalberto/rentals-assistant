import sys

from rentals_assistant.bot import start_bot
from rentals_assistant.config import configure_logging, load_config
from rentals_assistant.scheduler import start

configure_logging(load_config().log_level)

if "--bot" in sys.argv:
    start_bot()
else:
    start()
