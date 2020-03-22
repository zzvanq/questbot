# import os

from django.db import models

# from django.dispatch import receiver
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone
from slugify import slugify

from player.models import Player


class Quest(models.Model):
    name = models.CharField("Название", max_length=256)
    is_active = models.BooleanField("Активный квест", default=False)
    price = models.DecimalField(
        "Цена в рублях", max_digits=7, decimal_places=2, default=0
    )
    price_per_unit = models.DecimalField(
        "Снижение цены за 1 шт. в рублях", max_digits=7, decimal_places=2, default=0
    )
    image_descr = models.URLField(
        "Ссылка на Картинку в описании квеста:", null=True, blank=True
    )
    description = models.TextField(
        "Описание", null=True, blank=True, default="", max_length=4096
    )
    date_awarding_start = models.DateTimeField(
        "Дата начала розыгрыша", null=True, blank=True
    )
    date_awarding_end = models.DateTimeField(
        "Дата окончания розыгрыша", null=True, blank=True
    )
    image_award = models.URLField(
        "Ссылка на Картинку в описании розыгрыша:", null=True, blank=True
    )
    awarding_descr = models.TextField(
        "Описание розыгрыша", null=True, blank=True, default="", max_length=4096
    )
    vk_image_descr = models.CharField(
        "vk_image_descr", max_length=256, null=True, blank=True
    )
    vk_image_award = models.CharField(
        "vk_image_award", max_length=256, null=True, blank=True
    )

    @property
    def is_awarding(self):
        if self.date_awarding_start and self.date_awarding_end:
            date_now = timezone.now()
            if self.date_awarding_start <= date_now <= self.date_awarding_end:
                return True
            else:
                return False
        else:
            return False

    @property
    def first_step(self):
        first_step_cache = cache.get("quest:" + str(self.pk) + ":first_step")
        if first_step_cache is not None:
            return first_step_cache
        else:
            first_step = self.step_set.filter(is_first=True).first()
            cache.set(
                "quest:" + str(self.pk) + ":first_step",
                first_step,
                settings.CACHING_TIMEOUTS["STEP"]["TIMEOUT"],
            )
            return first_step

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Квест"
        verbose_name_plural = "Квесты"


class Option(models.Model):
    text = models.CharField("Текст опции", max_length=256)

    quest = models.ForeignKey(Quest, verbose_name="Квест", on_delete=models.CASCADE)

    next_step = models.ForeignKey(
        "Step",
        verbose_name="Следующий шаг",
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    changes = models.ManyToManyField(
        "self", verbose_name="Изменяет опции", symmetrical=False, blank=True
    )

    is_hidden = models.BooleanField("Скрытый", default=False)
    is_winning = models.BooleanField("Победный вариант", default=False)
    index = models.PositiveSmallIntegerField("Индекс отображения", default=1)

    def __str__(self):
        return self.pk + " - " + self.text[:8]

    class Meta:
        ordering = ["text"]
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"


class Step(models.Model):
    description = models.TextField("Текст:\nтекст~время_текст~время\n", max_length=4096)
    image = models.URLField("Ссылка на картинку:", null=True, blank=True)
    vk_image = models.CharField("vk_image", max_length=256, null=True, blank=True)
    is_first = models.BooleanField("Первый шаг", default=False)
    delay = models.FloatField("Стандартная задержка (сек)", default=1)
    quest = models.ForeignKey(
        Quest, verbose_name="Квест", on_delete=models.CASCADE, blank=True, null=True
    )

    options = models.ManyToManyField(
        Option, verbose_name="Варианты ответов", blank=True
    )

    def clean(self, *args, **kwargs):
        if self.is_first:
            is_unique = Step.objects.filter(quest=self.quest, is_first=True).first()
            if not is_unique:
                super(Step, self).clean(*args, **kwargs)
            else:
                if is_unique.pk == self.pk:
                    super(Step, self).clean(*args, **kwargs)
                else:
                    raise ValidationError("Первый шаг уже установлен")

    def get_option_by_text(self, text, select_related=None, prefetch_related=None):
        option_cached = cache.get("step:" + str(self.pk) + ":option:" + slugify(text))
        if option_cached is not None:
            return option_cached
        else:
            try:
                qs = self.options

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

                option = qs.get(text=text)
                cache.set(
                    "step:" + str(self.pk) + ":option:" + slugify(text),
                    option,
                    settings.CACHING_TIMEOUTS["OPTION"]["TIMEOUT"],
                )
                return option
            except self.options.model.DoesNotExist:
                return False
            except self.options.model.MultipleObjectsReturned:
                return False

    def __str__(self):
        return self.description[:30]

    class Meta:
        ordering = ["description"]
        verbose_name = "Шаг"
        verbose_name_plural = "Шаги"


class PlayersQuest(models.Model):
    quest = models.ForeignKey(Quest, verbose_name="Квест", on_delete=models.CASCADE)

    player = models.ForeignKey(
        Player,
        verbose_name="Игрок",
        related_name="player_quests",
        on_delete=models.CASCADE,
    )

    current_step = models.ForeignKey(
        Step,
        verbose_name="Текущий шаг",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    changes = models.ManyToManyField(Option, verbose_name="Изменяет опции", blank=True)

    date_started = models.DateTimeField(auto_now_add=True)
    date_changed = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField("Играет прямо сейчас", default=False)
    attempts_num = models.PositiveIntegerField(
        "Количество попыток в розыгрыше", default=0
    )

    @property
    def is_paid(self):
        if self.attempts_num > 0:
            return True
        else:
            if self.quest.price == 0:
                self.attempts_num = 1 if self.attempts_num == 0 else self.attempts_num
                self.save()
                return True
            return False

    @property
    def is_expired(self):
        if self.quest.date_awarding_start and self.quest.date_awarding_end:
            if (
                self.quest.date_awarding_start
                <= self.date_started
                <= self.quest.date_awarding_end
            ):
                return False
            else:
                if self.is_paid and self.attempts_num > 1:
                    self.attempts_num = 1
                    self.save()
                return True
        else:
            return False

    def set_active(self, save=True):
        if self.is_paid:
            self.is_active = True
            if save:
                self.save()
            else:
                cache.set(
                    "player:" + str(self.player.user_id) + ":player_quest:active",
                    self,
                    settings.CACHING_TIMEOUTS["PLAYER"]["TIMEOUT"],
                )

    def get_current_step(self):
        cached_current = cache.get(
            "player:"
            + str(self.player.user_id)
            + ":player_quest:"
            + str(self.pk)
            + ":current"
        )
        if cached_current is not None:
            return cached_current
        else:
            current_step = (
                self.__class__.objects.only("current_step")
                .filter(pk=self.pk)
                .first()
                .current_step
            )
            cache.set(
                "player:"
                + str(self.player.user_id)
                + ":player_quest:"
                + str(self.pk)
                + ":current",
                current_step,
                settings.CACHING_TIMEOUTS["STEP"]["TIMEOUT"],
            )
            return current_step

    def set_current_step(self, next_step, save=True):
        current = self.get_current_step()
        if next_step != current:
            self.current_step = next_step
            cache.set(
                "player:"
                + str(self.player.user_id)
                + ":player_quest:"
                + str(self.pk)
                + ":current",
                self.current_step,
                settings.CACHING_TIMEOUTS["STEP"]["TIMEOUT"],
            )
            if save:
                self.save()

    def lost_awarding_game(self, save=True):
        if self.quest.price != 0 and self.attempts_num > 0:
            self.attempts_num -= 1
            if save:
                self.save()

    def get_price(self, attempts_num=None):
        if attempts_num and attempts_num != 1:
            return self.quest.price + (self.quest.price_per_unit * (attempts_num - 1))
        else:
            return self.quest.price

    def clear_game(self, is_paid=True, save=True, clear_date=False):
        quest = self.quest
        current_step = Step.objects.filter(quest=quest, is_first=True).first()
        self.current_step = current_step
        self.changes.clear()
        if not is_paid:
            self.attempts_num = 0
        if clear_date:
            self.date_started = timezone.now()
        if save:
            self.save()
            cache.set(
                "player:"
                + str(self.player.user_id)
                + ":player_quest:"
                + str(self.pk)
                + ":current",
                None,
                settings.CACHING_TIMEOUTS["STEP"]["TIMEOUT"],
            )
        else:
            cache.set(
                "player:" + str(self.player.user_id) + ":player_quest:active",
                self,
                settings.CACHING_TIMEOUTS["PLAYER"]["TIMEOUT"],
            )
            cache.set(
                "player:"
                + str(self.player.user_id)
                + ":player_quest:"
                + str(self.pk)
                + ":current",
                None,
                settings.CACHING_TIMEOUTS["STEP"]["TIMEOUT"],
            )

    def save(self, *args, **kwargs):
        if self.is_active:
            active_quest = PlayersQuest.objects.filter(
                player=self.player, is_active=True
            ).exclude(pk=self.pk)
            if active_quest:
                active_quest.update(is_active=False)

        if self.quest.price == 0:
            self.attempts_num = 1 if self.attempts_num == 0 else self.attempts_num
        super(PlayersQuest, self).save(*args, **kwargs)
        if self.is_active:
            cache.set(
                "player:" + str(self.player.user_id) + ":player_quest:active",
                self,
                settings.CACHING_TIMEOUTS["PLAYER"]["TIMEOUT"],
            )

    class Meta:
        unique_together = ("player", "quest")
        verbose_name = "Активная игра"
        verbose_name_plural = "Активные игры"


class PlayersQuestCompleted(models.Model):
    quest = models.ForeignKey(
        Quest,
        verbose_name="Квест",
        related_name="players_quests_completed",
        on_delete=models.CASCADE,
    )

    player = models.ForeignKey(
        Player,
        verbose_name="Игрок",
        related_name="player_quests_completed",
        on_delete=models.CASCADE,
    )

    option = models.ForeignKey(
        Option,
        verbose_name="Вариант ответа",
        related_name="player_quests_completed",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    date_won = models.DateTimeField("Дата окончания квеста", auto_now_add=True)
    is_in_awarding_time = models.BooleanField(
        "Проходил во время розыгрыша", default=False
    )

    class Meta:
        verbose_name = "Победа игрока"
        verbose_name_plural = "Победы игроков"


# @receiver(models.signals.pre_save, sender=Step)
# def auto_delete_file_on_change_step(sender, instance, **kwargs):
#     """
#     Deletes old file from filesystem
#     when corresponding `MediaFile` object is updated
#     with new file.
#     """
#     if not instance.pk:
#         return False

#     try:
#         old_file = getattr(Step.objects.get(pk=instance.pk), 'image', None)
#     except Step.DoesNotExist:
#         return False

#     new_file = getattr(instance, 'image', None)
#     if not old_file == new_file:
#         if os.path.isfile(old_file.path):
#             os.remove(old_file.path)


# @receiver(models.signals.pre_save, sender=Quest)
# def auto_delete_file_on_change_quest(sender, instance, **kwargs):
#     """
#     Deletes old file from filesystem
#     when corresponding `MediaFile` object is updated
#     with new file.
#     """
#     if not instance.pk:
#         return False

#     try:
#         old_file_descr = getattr(Quest.objects.get(pk=instance.pk), 'image_descr', None)
#         old_file_award = getattr(Quest.objects.get(pk=instance.pk), 'image_award', None)
#     except Quest.DoesNotExist:
#         return False

#     new_file_descr = getattr(instance, 'image_descr', None)
#     new_file_award = getattr(instance, 'image_award', None)
#     if old_file_descr and not old_file_descr == new_file_descr:
#         if os.path.isfile(old_file_descr.path):
#             os.remove(old_file_descr.path)

#     if old_file_award and not old_file_award == new_file_award:
#         if os.path.isfile(old_file_award.path):
#             os.remove(old_file_award.path)
