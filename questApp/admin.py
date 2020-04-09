from django.contrib import admin

from .models import Option, PlayersQuest, PlayersQuestCompleted, Quest, Step, QuestPermittedPlayers

# Register your models here.


class QuestPermittedPlayersInline(admin.TabularInline):
    model = QuestPermittedPlayers
    extra = 5
    can_delete = True


class PlayersQuestAdmin(admin.ModelAdmin):
    list_display = (
        "player",
        "quest"
    )
    list_filter = ("quest__name", "player__player_type")
    search_fields = ("player__name",)
    autocomplete_fields = ["current_step"]
    filter_horizontal = ("changes",)


class PlayersQuestCompletedAdmin(admin.ModelAdmin):
    list_display = ("player_name", "quest_name", "date_won", "is_in_awarding_time")
    list_filter = ("is_in_awarding_time", "date_won")
    search_fields = ("player__name", "quest__name")
    autocomplete_fields = ["option"]
    date_hierarchy = "date_won"

    def player_name(self, obj):
        return obj.player.name

    def quest_name(self, obj):
        return obj.quest.name


class StepAdmin(admin.ModelAdmin):
    list_display = ("quest_name", "step_name")
    list_filter = ("quest", "is_first")
    filter_horizontal = ("options",)
    search_fields = ("quest__name", "description")
    exclude = ("vk_image",)

    def step_name(self, obj):
        return obj.description[:30] + ".."

    def quest_name(self, obj):
        if obj.quest:
            return obj.quest.name
        else:
            return ""


class OptionAdmin(admin.ModelAdmin):
    list_display = ("quest", "steps_list", "opt_text")
    list_filter = ("quest",)
    search_fields = ("quest__name", "step__description", "text")
    filter_horizontal = ("changes",)
    autocomplete_fields = ["next_step"]

    def steps_list(self, obj):
        return ", ".join([step.description[:10] + ".." for step in obj.step_set.all()])

    def opt_text(self, obj):
        return obj.text[:30]


class QuestAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    inlines = (QuestPermittedPlayersInline,)
    exclude = ("vk_image_descr", "vk_image_award")


class QuestPermittedPlayersAdmin(admin.ModelAdmin):
    search_fields = ("quest__name", "players_quest__player__name")
    autocomplete_fields = ("players_quest", "quest")


admin.site.register(Quest, QuestAdmin)
admin.site.register(Step, StepAdmin)
admin.site.register(Option, OptionAdmin)
admin.site.register(PlayersQuest, PlayersQuestAdmin)
admin.site.register(PlayersQuestCompleted, PlayersQuestCompletedAdmin)
admin.site.register(QuestPermittedPlayers, QuestPermittedPlayersAdmin)
