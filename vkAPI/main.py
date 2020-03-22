import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tgBot.settings")
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

django.setup()

import vk_api
import sys

from telegram.ext import JobQueue
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.upload import VkUpload
from vkAPI import utils
from django.conf import settings

from tgBot.bots import VKBot


def handle_message(bot, update, upload, job_queue):
    message = update.obj.text
    bot_ctx = VKBot(
        message=message, bot=bot, update=update, upload=upload, job_queue=job_queue
    )
    # Get command and run
    VKBot.get_command(message, bot_ctx)()


def main():
    try:
        vk_session = vk_api.VkApi(token=settings.VK_ACCESS_TOKEN)
        vk = vk_session.get_api()
        job_queue = JobQueue(vk)
        job_queue.start()
        upload = VkUpload(vk_session)

        long_poll = VkBotLongPoll(vk_session, settings.VK_GROUP_ID)

        for event in long_poll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                handle_message(vk, event, upload, job_queue)
            elif event.type == VkBotEventType.GROUP_JOIN:
                utils.send_referral_input(vk, event)
            elif event.type == VkBotEventType.GROUP_LEAVE:
                pass

    except Exception as exc:
        print(exc, file=sys.stderr)
        main()


if __name__ == "__main__":
    main()
