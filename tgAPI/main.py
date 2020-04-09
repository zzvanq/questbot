import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tgBot.settings")
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

django.setup()

import telegram.bot
import logging

from django.conf import settings
from telegram.utils.request import Request
from telegram.ext import messagequeue as mq
from constance import config

from questApp import quest_utils
from tgBot.bots import TGBot
from tgAPI import utils
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import KeyboardButton, ReplyKeyboardMarkup

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

ACCESS_TOKEN = settings.TG_ACCESS_TOKEN


def error(bot, update, err):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, err)


def incoming_commands(bot, update, job_queue):
    message = update.message.text
    bot_ctx = TGBot(message, bot, update, job_queue)

    # Get command and run
    command = TGBot.get_command(message, bot_ctx)
    if command:
        command()


def start_main_menu(bot, update, args=None):
    player, _ = utils.get_or_create_player(bot, update, args=args)
    player_quests = player.has_quests

    if player_quests:
        button_list = [
            KeyboardButton(quest_utils.menu_text_full("MY_GAMES")),
            KeyboardButton(quest_utils.menu_text_full("ALL_GAMES")),
            KeyboardButton(quest_utils.menu_text_full("SETTINGS")),
        ]
    else:
        button_list = [
            KeyboardButton(quest_utils.menu_text_full("ALL_GAMES")),
            KeyboardButton(quest_utils.menu_text_full("SETTINGS")),
        ]

    reply_markup = ReplyKeyboardMarkup(
        utils.build_menu(button_list, n_cols=1), resize_keyboard=True
    )
    bot.send_message(update.message.chat_id, config.MAIN_MENU_TEXT, reply_markup=reply_markup)


class MQBot(telegram.bot.Bot):
    """A subclass of Bot which delegates send method handling to MQ"""

    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or mq.MessageQueue()

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass
        super(MQBot, self).__del__()

    @mq.queuedmessage
    def send_message(self, *args, **kwargs):
        """Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments"""
        return super(MQBot, self).send_message(*args, **kwargs)


def main():
    # Create the EventHandler and pass it your bot's token.
    print("server is starting...")
    request = Request(con_pool_size=20, proxy_url=settings.TG_PROXY_URL)
    bot = MQBot(ACCESS_TOKEN, request=request)
    updater = Updater(bot=bot, workers=10)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # simple start function
    dp.add_handler(CommandHandler("start", start_main_menu, pass_args=True))

    dp.add_handler(MessageHandler(Filters.all, incoming_commands, pass_job_queue=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    print("server is started!")
    updater.idle()


if __name__ == "__main__":
    main()
