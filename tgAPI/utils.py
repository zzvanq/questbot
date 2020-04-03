import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tgBot.settings")
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

import django

django.setup()

from django.conf import settings

from questApp.models import Player
from questApp import quest_utils
from telegram import KeyboardButton, ReplyKeyboardMarkup


def build_menu(
    buttons, n_cols, header_buttons: list = None, footer_buttons: list = None
):
    menu = [buttons[i : i + n_cols] for i in range(0, len(buttons), n_cols)]

    if header_buttons:
        menu = [*header_buttons, *menu]

    if footer_buttons:
        menu.extend(footer_buttons)

    return menu


def get_or_create_player(bot, update, args=None):
    user = update.effective_user
    referred_by = None

    if args:
        referred_by = Player.objects.filter(user_id=args[0]).first()

    user_name = str(user.first_name or "") + "/" + str(user.last_name or "")

    if user.username:
        user_login = "TG:" + user.username
    else:
        user_login = None

    user_id = user.id
    player_type = "TG"

    return quest_utils.get_or_create_player(
        user_name, user_login, user_id, referred_by, player_type
    )


def _send_step_final(bot, job):
    bot.send_message(
        job.context[0].effective_chat.id, job.context[1], reply_markup=job.context[2]
    )


def _send_step_part(bot, job):
    bot.send_message(
        job.context[0].effective_chat.id, job.context[1], reply_markup=job.context[2]
    )


def send_step_partly(bot, update, job_queue, description, delay_temp, reply_markup):
    step_parts = description.split("_")
    step_parts_len = len(step_parts)
    start = 0
    reply_part = ReplyKeyboardMarkup(
        build_menu([quest_utils.menu_text_full("MAIN_MENU")], n_cols=1),
        resize_keyboard=True,
    )

    for i, part_temp in enumerate(step_parts):
        part = part_temp.split("~")
        delay = float(part[1]) if len(part) >= 2 else delay_temp
        if i == 0 and i == step_parts_len - 1:
            bot.send_message(
                update.effective_chat.id, part[0], reply_markup=reply_markup
            )
        elif i == 0:
            bot.send_message(update.effective_chat.id, part[0], reply_markup=reply_part)
        elif i == step_parts_len - 1:
            start += delay
            job_queue.run_once(
                _send_step_final, start, context=(update, part[0], reply_markup)
            )
        else:
            start += delay
            job_queue.run_once(
                _send_step_part, start, context=(update, part[0], reply_part)
            )


def build_step(bot, update, step, job_queue, player_quest, text="Вы победили!"):
    if step:
        if step.image:
            bot.send_photo(update.message.chat_id, photo=step.image)

        options_temp = step.options.all()
        options = []
        changes = player_quest.changes.all()
        for option in options_temp:
            is_hidden = option.is_hidden
            if option in changes:
                is_hidden = not option.is_hidden
            if not is_hidden:
                options.append(option)

        if options:
            button_list = [KeyboardButton(option.text) for option in options]
            button_list.append(KeyboardButton(quest_utils.menu_text_full("MAIN_MENU")))
            reply_markup = ReplyKeyboardMarkup(
                build_menu(button_list, n_cols=1),
                resize_keyboard=True,
                one_time_keyboard=True,
            )
            send_step_partly(
                bot,
                update,
                job_queue,
                step.description,
                step.delay,
                reply_markup=reply_markup,
            )
        else:
            # Step has no options - Lose
            button_list = [
                KeyboardButton(quest_utils.menu_text_full("ASK_TO_RESTART")),
                KeyboardButton(quest_utils.menu_text_full("MAIN_MENU")),
            ]
            reply_markup = ReplyKeyboardMarkup(
                build_menu(button_list, n_cols=1), resize_keyboard=True
            )
            bot.send_message(
                update.effective_chat.id, step.description, reply_markup=reply_markup
            )
    else:
        button_list = [
            KeyboardButton(quest_utils.menu_text_full("ASK_TO_RESTART")),
            KeyboardButton(quest_utils.menu_text_full("MAIN_MENU")),
        ]
        reply_markup = ReplyKeyboardMarkup(
            build_menu(button_list, n_cols=1), resize_keyboard=True
        )
        bot.send_message(
            update.effective_chat.id,
            text + "\nНачать заново?",
            reply_markup=reply_markup,
        )
