from django.db import models
from questApp.models import Player, Quest

# Create your models here.


class Payment(models.Model):
    player = models.ForeignKey(
        Player,
        related_name="payments",
        verbose_name="Пользователь",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    quest = models.ForeignKey(
        Quest,
        related_name="payments",
        verbose_name="Квест",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    value = models.DecimalField("Сумма с комиссией", max_digits=7, decimal_places=3)
    value_wo = models.DecimalField("Сумма без комиссии", max_digits=7, decimal_places=3)
    method = models.CharField("ID способа оплаты", max_length=256)
    payment_id = models.CharField("ID заказа", max_length=256)
    agreement = models.CharField("ID соглашения", max_length=256)
    date_created = models.DateTimeField("Дата оплаты")
    is_is_awarding_time = models.BooleanField("Во время розыгрыша", default=False)

    def __str__(self):
        return self.player.name + " " + self.quest.name

    class Meta:
        unique_together = ("player", "quest")
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
