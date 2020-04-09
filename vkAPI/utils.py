import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tgBot.settings")
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

import requests
import django

django.setup()

from django.conf import settings

from vk_api.keyboard import VkKeyboard
from vk_api.utils import get_random_id

from questApp import quest_utils

session = requests.Session()


def get_or_upload_photo(upload, obj, attr, image):
    obj = obj.__class__.objects.only("vk_" + attr).get(pk=obj.pk)
    vk_image = getattr(obj, "vk_" + attr)
    if vk_image:
        return vk_image
    else:
        photo_raw = session.get(image, stream=True).raw
        photo = upload.photo_messages(photos=photo_raw)[0]
        photo = "photo{}_{}".format(photo["owner_id"], photo["id"])

        setattr(obj, "vk_" + attr, photo)
        obj.save()

        return photo


def get_or_create_player(vk, event, args=None, join=False):
    user_id = str(event.obj.user_id) if join else str(event.obj.from_id)
    vk_info = vk.users.get(user_ids=user_id)[0]
    player_type = "VK"
    user_name = str(vk_info["first_name"] or "") + "/" + str(vk_info["last_name"] or "")
    user_login = "VK:" + str(vk_info["id"])

    return quest_utils.get_or_create_player(
        user_name, user_login, user_id, None, player_type
    )


def _send_step_final(vk, job):
    vk.messages.send(
        peer_id=job.context[0],
        random_id=get_random_id(),
        message=job.context[1],
        keyboard=job.context[2],
    )


def _send_step_part(vk, job):
    vk.messages.send(
        peer_id=job.context[0],
        random_id=get_random_id(),
        message=job.context[1],
        keyboard=job.context[2],
    )


def send_step_partly(vk, event, job_queue, keyboard, delay_temp, description):
    step_parts = description.split("_")
    step_parts_len = len(step_parts)
    start = 0
    button_list = VkKeyboard()
    button_list.add_button(quest_utils.menu_text_full("MAIN_MENU"))
    button_list = button_list.get_keyboard()
    keyboard_temp = keyboard.get_keyboard()

    for i, part_temp in enumerate(step_parts):
        part = part_temp.split("~")
        delay = float(part[1]) if len(part) >= 2 else delay_temp
        if i == 0 and i == step_parts_len - 1:
            job_queue.run_once(
                _send_step_final,
                start,
                context=(event.obj.from_id, part[0], keyboard_temp),
            )
        elif i == 0:
            job_queue.run_once(
                _send_step_part,
                start,
                context=(event.obj.from_id, part[0], button_list),
            )
        elif i == step_parts_len - 1:
            start += delay
            job_queue.run_once(
                _send_step_final,
                start,
                context=(event.obj.from_id, part[0], keyboard_temp),
            )
        else:
            start += delay
            job_queue.run_once(
                _send_step_part,
                start,
                context=(event.obj.from_id, part[0], button_list),
            )


def build_step(vk, event, upload, job_queue, step, player_quest, text="Вы победили!"):
    if step:
        print(step)
        if step.image:
            image = get_or_upload_photo(upload, step, "image", step.image)
            vk.messages.send(
                peer_id=event.obj.from_id, random_id=get_random_id(), attachment=image
            )

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
            button_list = VkKeyboard()
            for option in options:
                button_list.add_button(option.text)
                button_list.add_line()
            button_list.add_button(quest_utils.menu_text_full("MAIN_MENU"))
            send_step_partly(
                vk, event, job_queue, button_list, step.delay, step.description
            )
        else:
            # Step has no options - Lose
            button_list = VkKeyboard()
            button_list.add_button(quest_utils.menu_text_full("ASK_TO_RESTART"))
            button_list.add_line()
            button_list.add_button(quest_utils.menu_text_full("MAIN_MENU"))
            vk.messages.send(
                peer_id=event.obj.from_id,
                random_id=get_random_id(),
                message=step.description,
                keyboard=button_list.get_keyboard(),
            )
    else:
        button_list = VkKeyboard()
        button_list.add_button(quest_utils.menu_text_full("ASK_TO_RESTART"))
        button_list.add_line()
        button_list.add_button(quest_utils.menu_text_full("MAIN_MENU"))
        vk.messages.send(
            peer_id=event.obj.from_id,
            random_id=get_random_id(),
            message=(text + "\nНачать заново?"),
            keyboard=button_list.get_keyboard(),
        )


def send_referral_input(vk, event):
    player, created = get_or_create_player(vk, event, join=True)

    if created:
        player.is_next_message_referral = True
        player.save()
        button_list = VkKeyboard()
        button_list.add_button(quest_utils.menu_text_full("START_WO_REFERRED"))
        text = (
            'Укажите ID пользователя, который вас пригласил или нажмите "'
            + quest_utils.menu_text_full("START_WO_REFERRED")
            + '", чтобы пропустить этот этап'
        )
        vk.messages.send(
            peer_id=event.obj.user_id,
            random_id=get_random_id(),
            message=text,
            keyboard=button_list.get_keyboard(),
        )
