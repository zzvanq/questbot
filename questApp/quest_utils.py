import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tgBot.settings")
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

import django

django.setup()

from django.conf import settings
from django.core.cache import cache
from slugify import slugify
from questApp.models import Player, PlayersQuestCompleted, Quest


def handle_option_message(player, player_quest, option):
    # if player has active quest and it's paid
    is_hidden = option.is_hidden
    cached_changes = cache.get(
        "player:"
        + str(player.user_id)
        + ":player_quest:"
        + str(player_quest.pk)
        + ":changes"
    )
    if cached_changes is not None:
        if option in cached_changes:
            is_hidden = not is_hidden
    else:
        changes = player_quest.changes.all()
        cache.set(
            "player:"
            + str(player.user_id)
            + ":player_quest:"
            + str(player_quest.pk)
            + ":changes",
            changes,
            settings.CACHING_TIMEOUTS["PLAYER_QUEST"]["TIMEOUT"],
        )
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
                cache.set(
                    "player:"
                    + str(player.user_id)
                    + ":player_quest:"
                    + str(player_quest.pk)
                    + ":changes",
                    player_quest.changes,
                    settings.CACHING_TIMEOUTS["PLAYER_QUEST"]["TIMEOUT"],
                )

        if option.is_winning:
            record = PlayersQuestCompleted(
                player=player_quest.player,
                quest=player_quest.quest,
                is_in_awarding_time=player_quest.quest.is_awarding,
                option=option,
            )
            record.save()
            is_winning = True
        else:
            if not option.next_step.options.exists() and player_quest.quest.is_awarding:
                player_quest.lost_awarding_game(save=False)
        player_quest.set_current_step(option.next_step, save=False)
        player_quest.save()
        return is_winning, option.next_step
    else:
        pass  # Tried to send hidden option


def handle_contact_message(player, message):
    player.set_contact(message, save=False)
    player.end_contact_saving()


def get_all_quests(select_related=None, prefetch_related=None):
    cached_quest = cache.get("quest:all")

    if cached_quest is not None:
        return cached_quest
    else:
        qs = Quest.objects.all()

        if select_related:
            if type(select_related) == list:
                for item in select_related:
                    qs = qs.select_related(item)
            else:
                qs = qs.select_related(select_related)

        if prefetch_related:
            if type(prefetch_related) == list:
                for item in prefetch_related:
                    qs = qs.prefetch_related(item)
            else:
                qs = qs.prefetch_related(prefetch_related)

        cache.set("quest:all", qs, settings.CACHING_TIMEOUTS["QUEST"]["TIMEOUT"])
        return qs


def get_quest_by_name(name, select_related=None, prefetch_related=None):
    cached_quest = cache.get("quest:" + slugify(name))
    if cached_quest is not None:
        return cached_quest
    else:
        try:
            qs = Quest.objects

            if select_related:
                if type(select_related) == list:
                    for item in select_related:
                        qs = qs.select_related(item)
                else:
                    qs = qs.select_related(select_related)

            if prefetch_related:
                if type(prefetch_related) == list:
                    for item in prefetch_related:
                        qs = qs.prefetch_related(item)
                else:
                    qs = qs.prefetch_related(prefetch_related)

            quest = qs.get(name=name)
            cache.set(
                "quest:" + slugify(name),
                quest,
                settings.CACHING_TIMEOUTS["QUEST"]["TIMEOUT"],
            )
            return quest
        except Quest.DoesNotExist:
            return False
        except Quest.MultipleObjectsReturned:
            return False


def get_or_create_player(user_name, user_login, user_id, referred_by, player_type):
    cached_player = cache.get("player:" + str(user_id))
    if cached_player is not None:
        return cached_player, False
    else:
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
            cache.set(
                "player:" + str(user_id),
                player,
                settings.CACHING_TIMEOUTS["PLAYER"]["TIMEOUT"],
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
            cache.set(
                "player:" + str(user_id),
                player,
                settings.CACHING_TIMEOUTS["PLAYER"]["TIMEOUT"],
            )
            return player, created


def menu_text_full(name):
    menu = settings.BOT_MENU[name]
    return menu["EMOJI"] + " " + menu["TEXT"]
