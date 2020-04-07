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

    amount = models.DecimalField("Сумма к оплате", max_digits=15, decimal_places=3)
    profit = models.DecimalField("Зачисленино на ваш счет", max_digits=15, decimal_places=3, default=0)
    transaction_id = models.CharField("ID заказа", max_length=256, null=True, blank=True)
    date_create = models.DateTimeField("Дата создания", auto_now_add=True)
    date_pay = models.DateTimeField("Дата оплаты", null=True, blank=True)
    is_awarding_time = models.BooleanField("Во время розыгрыша", default=False)

    def __str__(self):
        return self.player.name + " " + self.quest.name

    class Meta:
        unique_together = ("player", "quest")
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
