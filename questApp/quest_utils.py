import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tgBot.settings")
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

import django

django.setup()

from constance import config
from django.conf import settings
from questApp.models import Player, PlayersQuestCompleted, Quest


def handle_option_message(player, player_quest, option):
    # if player has active quest and it's paid
    is_hidden = option.is_hidden

    changes = player_quest.changes.all()

    if option in changes:
        is_hidden = not is_hidden

    is_winning = False

    if not is_hidden:
        if option.next_step:
            # This Step is not last
            option_changes = option.changes.all()
            if option_changes:
                for change in option_changes:
                    player_quest.changes.add(change)

        if not player_quest.is_complete:
            if option.is_winning:
                player_quest.won_game(option, save=False)
                is_winning = True
            elif not option.next_step:
                player_quest.lost_game(save=False)

        player_quest.set_current_step(option.next_step, save=False)
        player_quest.save()

        return is_winning, option.next_step


def handle_contact_message(player, message):
    player.set_contact(message, save=False)
    player.end_contact_saving()


def get_all_quests(select_related=None, prefetch_related=None):
    qs = Quest.objects.all()

    if select_related:
        qs = qs.select_related(*select_related)

    if prefetch_related:
        qs = qs.prefetch_related(*prefetch_related)

    return qs


def get_quest_by_name(name, select_related=None, prefetch_related=None):
    try:
        qs = Quest.objects

        if select_related:
            qs = qs.select_related(*select_related)

        if prefetch_related:
            qs = qs.prefetch_related(*prefetch_related)

        quest = qs.get(name=name)
        return quest
    except Quest.DoesNotExist:
        return None
    except Quest.MultipleObjectsReturned:
        return None


def get_or_create_player(user_name, user_login, user_id, referred_by, player_type):
    if user_login:
        player, created = Player.objects.update_or_create(
            user_id=user_id,
            defaults={
                "name": user_name,
                "user_login": user_login,
                "referred_by": referred_by,
                "player_type": player_type,
            },
        )
        return player, created
    else:
        player, created = Player.objects.update_or_create(
            user_id=user_id,
            defaults={
                "name": user_name,
                "referred_by": referred_by,
                "player_type": player_type,
            },
        )
        return player, created


def menu_text_full(name):
    return settings.BOT_MENU[name] + " " + getattr(config, name)
