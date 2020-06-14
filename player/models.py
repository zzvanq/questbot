from django.db import models
from django.conf import settings


class Player(models.Model):
    first_name = models.CharField("Имя пользователя 1", max_length=256, default="")
    second_name = models.CharField("Имя пользователя 2", max_length=256, default="")
    user_login = models.CharField(
        "Логин/Контакт для связи",
        max_length=256,
        null=True,
        blank=True
    )
    add_contact = models.CharField("Доп. Контакт для связи", max_length=256, null=True, blank=True)
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

    @property
    def name(self):
        return self.first_name + " " + self.second_name

    def get_quest_by_pk(self, quest, select_related=None, prefetch_related=None):
        try:
            qs = self.player_quests

            if select_related:
                qs = qs.select_related(*select_related)

            if prefetch_related:
                qs = qs.prefetch_related(*prefetch_related)

            player_quest = qs.get(quest=quest)
            return player_quest
        except self.player_quests.model.DoesNotExist:
            return False
        except self.player_quests.model.MultipleObjectsReturned:
            qs = self.player_quests.filter(quest=quest)

            if select_related:
                qs = qs.select_related(*select_related)

            if prefetch_related:
                qs = qs.prefetch_related(*prefetch_related)

            first_quest = qs.first()

            qs.exclude(quest=first_quest).delete()

            return first_quest

    def get_active_quest(self, select_related=None, prefetch_related=None, only=None):
        try:
            qs = self.player_quests

            if select_related:
                qs.select_related(*select_related)

            if prefetch_related:
                qs.prefetch_related(*prefetch_related)

            if only:
                qs.only(*only)

            player_quest = qs.get(is_active=True)
            return player_quest
        except self.player_quests.model.DoesNotExist:
            return None
        except self.player_quests.model.MultipleObjectsReturned:
            qs = self.player_quests.filter(is_active=True)

            if select_related:
                qs.select_related(*select_related)

            if prefetch_related:
                qs.prefetch_related(*prefetch_related)

            if only:
                qs.only(*only)

            player_quest = qs.first()

            player_quest.is_active = True
            player_quest.save()
            return player_quest

    def get_my_quests(self, select_related=None, prefetch_related=None):
        qs = self.player_quests.all()

        if select_related:
            qs = qs.select_related(*select_related)

        if prefetch_related:
            qs = qs.prefetch_related(*prefetch_related)

        return qs

    @property
    def has_quests(self):
        return self.player_quests.exists()

    def set_contact(self, text, save=True):
        self.add_contact = text

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
        if save:
            self.save()

    def end_contact_saving(self, save=True):
        self.is_next_message_contact = False
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

        return player_quest

    def __str__(self):
        return self.first_name + " " + self.second_name

    class Meta:
        verbose_name = "Игрок"
        verbose_name_plural = "Игроки"
