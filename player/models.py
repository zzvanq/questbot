from django.db import models
from django.conf import settings
from django.core.cache import cache


class Player(models.Model):
    name = models.CharField("Имя пользователя", max_length=256)
    user_login = models.CharField(
        "Логин/Контакт для связи",
        max_length=256,
        null=True,
        blank=True,
        default="Нет контакта для связи",
    )
    user_id = models.CharField("User id", max_length=256, unique=True)
    referred_by = models.ForeignKey(
        "self",
        related_name="referrals",
        verbose_name="Пригласил",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    is_next_message_contact = models.BooleanField(
        "Следующее сообщение - Контакт для связи", default=False
    )
    is_next_message_referral = models.BooleanField(
        "Следующее сообщение - Пригласивший", default=False
    )
    player_type = models.CharField("Тип пользователя", max_length=256)
    is_staff = models.BooleanField("Повышенные права", default=False)

    @property
    def referral_link(self):
        return settings.TG_JOIN_URL + settings.BOT_TG_ID[1:] + "?start=" + self.user_id

    def get_quest_by_pk(self, quest, select_related=None, prefetch_related=None):
        try:
            qs = self.player_quests

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

            player_quest = qs.get(quest=quest)
            return player_quest
        except self.player_quests.model.DoesNotExist:
            return False
        except self.player_quests.model.MultipleObjectsReturned:
            duplicates = self.player_quests.filter(quest=quest)
            first_quest = duplicates.first()
            duplicates.exclude(quest=first_quest).delete()
            return first_quest

    def get_active_quest(self, select_related=None, prefetch_related=None):
        quest_cached = cache.get("player:" + str(self.user_id) + ":player_quest:active")
        if quest_cached is not None:
            return quest_cached
        else:
            try:
                qs = self.player_quests

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

                player_quest = qs.get(is_active=True)
                cache.set(
                    "player:" + str(self.user_id) + ":player_quest:active",
                    player_quest,
                    settings.CACHING_TIMEOUTS["PLAYER_QUEST"]["TIMEOUT"],
                )
                return player_quest
            except self.player_quests.model.DoesNotExist:
                return False
            except self.player_quests.model.MultipleObjectsReturned:
                player_quest = self.player_quests.filter(is_active=True).first()
                player_quest.save(is_active=True)
                return player_quest

    def get_my_quests(self, select_related=None, prefetch_related=None):
        quests_cached = cache.get("player:" + str(self.user_id) + ":player_quests")
        if quests_cached is not None:
            return quests_cached
        else:
            qs = self.player_quests.all()

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

            cache.set(
                "player:" + str(self.user_id) + ":player_quests",
                qs,
                settings.CACHING_TIMEOUTS["PLAYER_QUEST"]["TIMEOUT"],
            )
            return qs

    @property
    def has_quests(self):
        return self.player_quests.exists()

    def set_contact(self, text, save=True):
        self.user_login = text
        if save:
            self.save()

    def set_referral(self, text, save=True):
        try:
            if not self.referred_by:
                referral = Player.objects.get(user_id=text)
                self.is_next_message_referral = False
                self.referred_by = referral
                if save:
                    self.save()
                return True
        except Player.DoesNotExist:
            return None

    def start_contact_saving(self, save=True):
        self.is_next_message_contact = True
        cache.set(
            "player:" + str(self.user_id),
            self,
            settings.CACHING_TIMEOUTS["PLAYER"]["TIMEOUT"],
        )
        if save:
            self.save()

    def end_contact_saving(self, save=True):
        self.is_next_message_contact = False
        cache.set(
            "player:" + str(self.user_id),
            self,
            settings.CACHING_TIMEOUTS["PLAYER"]["TIMEOUT"],
        )
        if save:
            self.save()

    def create_player_quest(self, quest, current_step=None, is_active=True, save=True):
        if not current_step:
            current_step = quest.first_step
        player_quest = self.player_quests.create(
            player=self, quest=quest, current_step=current_step, is_active=is_active
        )
        if save:
            player_quest.save()
        cache.set(
            "player:" + str(self.user_id) + ":player_quests",
            self.player_quests.all(),
            settings.CACHING_TIMEOUTS["PLAYER"]["TIMEOUT"],
        )

        return player_quest

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Игрок"
        verbose_name_plural = "Игроки"
