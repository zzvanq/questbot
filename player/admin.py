from django.contrib import admin
from .models import Player


class PlayersAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "player_type",
    )
    list_filter = ("player_type",)
    search_fields = ("name",)


admin.site.register(Player, PlayersAdmin)
