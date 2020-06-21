from django.db import models

from django.core.exceptions import ValidationError
from django.utils import timezone

from player.models import Player


class Quest(models.Model):
    name = models.CharField("Название", max_length=256)
    is_active = models.BooleanField("Активный квест", default=False)
    price = models.DecimalField(
        "Цена в рублях", max_digits=15, decimal_places=2, default=0
    )
    max_attempts = models.PositiveIntegerField(
        "Максимальное количество попыток", default=1
    )
    date_sale_end = models.DateTimeField(
        "Дата окончания продажи", null=True, blank=True
    )
    players_with_access = models.ManyToManyField(
        Player, related_name="permitted_quests", through="QuestPermittedPlayers"
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
        return self.step_set.filter(is_first=True).first()

    def check_permission(self, player) -> bool:
        if player.is_staff:
            return True

        if not self.is_active:
            return False

        if player.permissions.filter(quest_id=self.id).exists():
            return True

        if self.date_sale_end:
            if timezone.now() > self.date_sale_end:
                return False

        return True

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Квест"
        verbose_name_plural = "Квесты"


class QuestPermittedPlayers(models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="permissions")

    def __str__(self):
        return f"{self.quest.name[:8]} - {self.player.name}"

    class Meta:
        unique_together = ("quest", "player")
        verbose_name = "Доступ к квесту"
        verbose_name_plural = "Доступы к квестам"


class Option(models.Model):
    text = models.CharField("Текст опции", max_length=256, db_index=True)
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
        return str(self.pk) + " - " + self.text[:8]

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
    attempts_num = models.PositiveIntegerField("Количество попыток", default=0)
    changes = models.ManyToManyField(Option, verbose_name="Изменяет опции", blank=True)
    date_started = models.DateTimeField(auto_now_add=True)
    date_changed = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField("Играет прямо сейчас", default=False)
    is_complete = models.BooleanField("Завершил", default=False)

    @property
    def is_paid(self) -> bool:
        if self.quest.price == 0:
            return True

        if self.player.is_staff:
            return True

        return self.permitted_quests.exists()

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
                # Awarding is over
                return True
        else:
            return False

    @property
    def is_attempts_exceeded(self):
        if self.player.is_staff:
            return False

        return self.attempts_num >= self.quest.max_attempts

    def set_active(self, save=True):
        if self.is_paid:
            self.is_active = True
            if save:
                self.save()

    def get_current_step(self):
        return self.current_step

    def set_current_step(self, next_step, save=True):
        current = self.get_current_step()
        if next_step != current:
            self.current_step = next_step

            if save:
                self.save()

    def clear_game(self, is_paid=True, save=True, clear_date=False):
        quest = self.quest
        current_step = Step.objects.filter(quest=quest, is_first=True).first()
        self.current_step = current_step
        self.is_complete = False
        self.changes.clear()

        if clear_date:
            self.date_started = timezone.now()

        if save:
            self.save()

    def increment_attempts(self, save=True):
        self.attempts_num += 1

        if save:
            self.save()

    def lost_game(self, save=True):
        self.increment_attempts(save=False)
        self.is_complete = True

        if save:
            self.save()

    def won_game(self, option, save=True):
        record = PlayersQuestCompleted(
            player=self.player,
            quest=self.quest,
            is_in_awarding_time=self.quest.is_awarding,
            option=option,
        )
        record.save()
        self.increment_attempts(save=False)
        self.is_complete = True

        if save:
            self.save()

    def save(self, *args, **kwargs):
        if self.is_active:
            active_quest = PlayersQuest.objects.filter(
                player=self.player, is_active=True
            ).exclude(pk=self.pk)

            if active_quest:
                active_quest.update(is_active=False)

        super(PlayersQuest, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.quest.name[:8]} - {self.player.name}"

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
