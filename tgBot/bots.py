from functools import partial
from abc import ABC, abstractmethod

from django.conf import settings
from telegram import KeyboardButton, ReplyKeyboardMarkup

from tgAPI import utils as tg_utils
from vkAPI import utils as vk_utils

from constance import config
from slugify import slugify
from payment import payments
from questApp import quest_utils
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard


# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tgBot.settings")
# sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
#
# django.setup()

# Every commands in list corresponds to an index in 'BOT_MENU'
commands = settings.BOT_MENU


class BaseBot(ABC):
    @abstractmethod
    def send_quest_info(self, player_quest):
        ...

    @abstractmethod
    def start_main_menu(self, text=None):
        ...

    @abstractmethod
    def start_my_quests_menu(self):
        ...

    @abstractmethod
    def start_all_quests_menu(self):
        ...

    @abstractmethod
    def start_ask_to_start_menu(self):
        ...

    @abstractmethod
    def start_ask_to_restart_menu(self):
        ...

    @abstractmethod
    def start_confirm_restart_menu(self):
        ...

    @abstractmethod
    def start_game_menu(self):
        ...

    @abstractmethod
    def start_settings_menu(self):
        ...

    @abstractmethod
    def start_cancel_contact_menu(self):
        ...

    @abstractmethod
    def start_add_contact_menu(self):
        ...

    @abstractmethod
    def start_playerquest(self, player_quest, quest):
        ...

    @abstractmethod
    def handle_game_title(self):
        ...

    @abstractmethod
    def handle_game_option(self):
        ...

    COMMAND_TABLE = NotImplemented

    @classmethod
    def get_command(cls, message, ctx):
        """Returns method corresponding to the given self.message.

        :returns: Corresponding Method if it was found, 'None' otherwise
        """
        if not message:
            return None

        splitted = message.split()

        emj = splitted[0]

        # Try to get command by emoji
        command = cls.COMMAND_TABLE.get(emj, None)

        # If couldn't find method, that corresponds to the given emoji, then return 'handle_game_title'
        if not command:
            return partial(cls.handle_game_option, self=ctx)

        # If returned 'dict', then get method from that 'dict' by 'text'
        if type(command) is dict:
            text = " ".join(splitted[1:])
            command = command.get(text, None)

            if not command:
                return None

        # 'command' is Class-method. Decorate it with instance param
        return partial(command, self=ctx)


class TGBot(BaseBot):
    def __init__(self, message, bot, update, job_queue, args=None):
        self.message = message
        self.bot = bot
        self.update = update
        self.job_queue = job_queue
        self.player, self.is_created = tg_utils.get_or_create_player(bot, update, args)

    def send_quest_info(self, player_quest):
        if not player_quest.is_paid:
            payment_url = payments.make_payment(
                self.player.user_id,
                player_quest.quest_id,
                player_quest.quest.price
            )
            self.start_main_menu(
                text=f"{config.BUY_LINK_TEXT}{payment_url}"
            )

        awarding_description = (
            config.QUEST_IS_ON_AWARDING + "\n" + player_quest.quest.awarding_descr
            if player_quest.quest.is_awarding
            else ""
        )
        quest_description = (
            config.QUEST_DESCRIPTION + "\n" + player_quest.quest.description
        )

        if awarding_description:
            if player_quest.quest.image_award:
                self.bot.send_photo(
                    self.update.message.chat_id, photo=player_quest.quest.image_award,
                )

            self.bot.send_message(self.update.message.chat_id, awarding_description)

        if quest_description:
            if player_quest.quest.image_descr:
                self.bot.send_photo(
                    self.update.message.chat_id, photo=player_quest.quest.image_descr,
                )

            self.bot.send_message(self.update.message.chat_id, quest_description)

    def start_main_menu(self, text=config.MAIN_MENU_TEXT):
        player_quests = self.player.has_quests

        if player_quests:
            button_list = [
                KeyboardButton(quest_utils.menu_text_full("MY_GAMES")),
                KeyboardButton(quest_utils.menu_text_full("ALL_GAMES")),
                KeyboardButton(quest_utils.menu_text_full("SETTINGS")),
            ]
        else:
            button_list = [
                KeyboardButton(quest_utils.menu_text_full("ALL_GAMES")),
                KeyboardButton(quest_utils.menu_text_full("SETTINGS")),
            ]

        reply_markup = ReplyKeyboardMarkup(
            tg_utils.build_menu(button_list, n_cols=1), resize_keyboard=True
        )

        self.bot.send_message(
            self.update.message.chat_id, text, reply_markup=reply_markup
        )

    def start_my_quests_menu(self):
        player_quests = self.player.get_my_quests(select_related=("quest",))
        if player_quests:
            button_list = [
                KeyboardButton(commands["GAME"] + " " + player_quest.quest.name)
                for player_quest in player_quests
                if player_quest.quest.check_permission(self.player)
            ]
            button_list.append(KeyboardButton(quest_utils.menu_text_full("MAIN_MENU")))
            reply_markup = ReplyKeyboardMarkup(
                tg_utils.build_menu(button_list, n_cols=1), resize_keyboard=True
            )

            self.bot.send_message(
                self.update.effective_chat.id,
                config.PLAYER_QUESTS_LIST,
                reply_markup=reply_markup,
            )

    def start_all_quests_menu(self):
        quests = quest_utils.get_all_quests()
        button_list = [
            KeyboardButton(commands["GAME"] + " " + quest.name)
            for quest in quests
            if quest.check_permission(self.player)
        ]
        button_list.append(KeyboardButton(quest_utils.menu_text_full("MAIN_MENU")))
        reply_markup = ReplyKeyboardMarkup(
            tg_utils.build_menu(button_list, n_cols=1), resize_keyboard=True
        )

        self.bot.send_message(
            self.update.effective_chat.id, config.QUESTS_ALL, reply_markup=reply_markup,
        )

    def start_ask_to_start_menu(self):
        button_list = [
            KeyboardButton(quest_utils.menu_text_full("START_GAME")),
            KeyboardButton(quest_utils.menu_text_full("ALL_GAMES")),
            KeyboardButton(quest_utils.menu_text_full("MAIN_MENU")),
        ]
        reply_markup = ReplyKeyboardMarkup(
            tg_utils.build_menu(button_list, n_cols=1), resize_keyboard=True
        )
        self.bot.send_message(
            self.update.effective_chat.id,
            config.GAME_START_BUTTON
            + ' "'
            + quest_utils.menu_text_full("START_GAME")
            + '"',
            reply_markup=reply_markup,
        )

    def start_ask_to_restart_menu(self):
        button_list = [
            KeyboardButton(quest_utils.menu_text_full("CONFIRM_TO_RESTART")),
            KeyboardButton(quest_utils.menu_text_full("RETURN_TO_GAME")),
        ]
        reply_markup = ReplyKeyboardMarkup(
            tg_utils.build_menu(button_list, n_cols=1), resize_keyboard=True
        )
        self.bot.send_message(
            self.update.effective_chat.id,
            config.QUEST_CONFIRM_RESTART,
            reply_markup=reply_markup,
        )

    def start_confirm_restart_menu(self):
        active_quest = self.player.get_active_quest(select_related=("quest",))

        if active_quest:
            if not active_quest.is_attempts_exceeded:
                if active_quest.is_paid:
                    active_quest.clear_game()

                    if active_quest.quest.check_permission(self.player):
                        self.start_playerquest(active_quest, active_quest.quest)
                    else:
                        self.start_main_menu(text=config.QUEST_IS_NOT_AVAILABLE)
                else:
                    self.send_quest_info(active_quest)
            else:
                self.start_main_menu(text=config.QUEST_ATTEMPTS_EXCEEDED)

    def start_game_menu(self):
        active_quest = self.player.get_active_quest(
            select_related=("quest",),
            prefetch_related=(
                "changes",
                "current_step__options",
                "current_step__quest",
            ),
        )

        if active_quest:
            tg_utils.build_step(
                self.bot,
                self.update,
                active_quest.get_current_step(),
                self.job_queue,
                active_quest,
            )

    def start_settings_menu(self):
        active_quest = self.player.get_active_quest(select_related=("quest",))
        button_list = [
            KeyboardButton(quest_utils.menu_text_full("ADD_CONTACT")),
            KeyboardButton(quest_utils.menu_text_full("MAIN_MENU")),
        ]
        reply_text = config.PLAYER_NO_QUESTS

        if active_quest:
            button_list_start = [
                KeyboardButton(quest_utils.menu_text_full("ASK_TO_RESTART")),
                KeyboardButton(quest_utils.menu_text_full("RETURN_TO_GAME")),
            ]
            button_list_start.extend(button_list)

            button_list = button_list_start

            reply_text = (
                config.PLAYER_PLAYING
                + ' "'
                + active_quest.quest.name
                + '"\n\n'
                + config.PLAYER_REFERRAL
                + "\n"
                + self.player.referral_link
            )

        reply_markup = ReplyKeyboardMarkup(
            tg_utils.build_menu(button_list, n_cols=1), resize_keyboard=True
        )
        self.bot.send_message(
            self.update.message.chat_id, reply_text, reply_markup=reply_markup
        )

    def start_cancel_contact_menu(self):
        if self.player.is_next_message_contact:
            self.player.end_contact_saving()

        self.start_main_menu()

    def start_add_contact_menu(self):
        self.player.start_contact_saving()
        contact = self.player.add_contact
        text = ""
        if self.player.add_contact:
            text = config.PLAYER_CONTACT + " " + contact + "\n"

        button_list = [KeyboardButton(quest_utils.menu_text_full("CANCEL_CONTACT"))]
        reply_markup = ReplyKeyboardMarkup(
            tg_utils.build_menu(button_list, n_cols=1), resize_keyboard=True
        )

        self.bot.send_message(
            self.update.message.chat_id,
            text + config.PLAYER_CONTACT_SET,
            reply_markup=reply_markup,
        )

    def handle_game_title(self):
        # remove emoji and space
        self.message = self.message.replace(commands["GAME"] + " ", "")
        quest = quest_utils.get_quest_by_name(name=self.message)

        if quest:
            if quest.check_permission(player=self.player):
                active_quest = self.player.get_active_quest(
                    select_related=("quest",),
                    prefetch_related=("current_step__options", "changes"),
                )

                if active_quest:
                    # Player has active quest
                    current_step = active_quest.get_current_step()

                    if active_quest.quest.name == quest.name:
                        # Player chooses his active quest
                        if current_step:
                            # Player quest is not ended, so just continue
                            if active_quest.is_paid:
                                tg_utils.build_step(
                                    self.bot,
                                    self.update,
                                    current_step,
                                    self.job_queue,
                                    active_quest,
                                )
                            else:
                                self.send_quest_info(active_quest)
                        else:
                            # Quest ended, so suggest to replay it
                            if active_quest.is_paid:
                                button_list = [
                                    KeyboardButton(
                                        quest_utils.menu_text_full("MAIN_MENU")
                                    ),
                                    KeyboardButton(
                                        quest_utils.menu_text_full("ASK_TO_RESTART")
                                    ),
                                ]

                                reply_markup = ReplyKeyboardMarkup(
                                    tg_utils.build_menu(button_list, n_cols=1),
                                    resize_keyboard=True,
                                )

                                self.bot.send_message(
                                    self.update.message.chat_id,
                                    config.QUEST_ASK_RESTART
                                    + ' "'
                                    + quest_utils.menu_text_full("CONFIRM_TO_RESTART")
                                    + '"',
                                    reply_markup=reply_markup,
                                )
                    else:
                        # Player chooses another quest
                        player_quest = self.player.get_quest_by_pk(quest=quest)
                        self.start_playerquest(player_quest, quest)
                else:
                    # Player has no active quest and chooses one to start
                    new_player_quest = self.player.get_quest_by_pk(
                        quest, select_related=("current_step",)
                    )
                    self.start_playerquest(new_player_quest, quest)
            else:
                self.start_main_menu(text=config.QUEST_IS_NOT_AVAILABLE)

    def start_playerquest(self, player_quest, quest):
        if player_quest:
            # Player has PlayerQuest object of that quest
            if player_quest.is_paid:
                player_quest.set_active()
                tg_utils.build_step(
                    self.bot,
                    self.update,
                    player_quest.get_current_step(),
                    self.job_queue,
                    player_quest,
                )
            else:
                self.send_quest_info(player_quest)
        else:
            # Player has no PlayerQuest object of that quest
            player_quest = self.player.create_player_quest(quest)
            self.send_quest_info(player_quest)
            self.start_ask_to_start_menu()

    def handle_game_option(self):
        # Message is Option text or Unknown command
        if self.player.is_next_message_contact:
            quest_utils.handle_contact_message(self.player, self.message)
            self.start_main_menu(text=config.PLAYER_CONTACT_SET_DONE)
        else:
            player_quest = self.player.get_active_quest(
                select_related=("quest", "current_step", "player"),
                prefetch_related=("changes",),
            )
            quest = player_quest.quest

            if player_quest and quest.check_permission(player=self.player):
                # Player has active quest
                if player_quest.is_paid:
                    # if player has active quest and it's paid
                    current_step = player_quest.get_current_step()

                    if current_step:
                        # Quest is not done
                        option = (
                            current_step.options.filter(text=self.message)
                            .select_related("next_step")
                            .prefetch_related("changes", "next_step__options",)
                            .first()
                        )

                        if option:
                            (
                                is_winning,
                                current_step,
                            ) = quest_utils.handle_option_message(player_quest, option)
                            result_text = (
                                config.GAME_WIN_TEXT
                                if is_winning
                                else config.GAME_LOST_TEXT
                            )

                            tg_utils.build_step(
                                self.bot,
                                self.update,
                                current_step,
                                self.job_queue,
                                player_quest,
                                text=result_text,
                            )
                else:
                    self.send_quest_info(player_quest)
                    # Not paid or Unknown command

    COMMAND_TABLE = {
        commands["MY_GAMES"]: start_my_quests_menu,
        commands["ALL_GAMES"]: start_all_quests_menu,
        commands["MAIN_MENU"]: start_main_menu,
        # If one emoji used twice, then return dict of commands corresponding to given text
        commands["ASK_TO_RESTART"]: {
            config.ASK_TO_RESTART: start_ask_to_restart_menu,
            config.CONFIRM_TO_RESTART: start_confirm_restart_menu,
        },
        commands["RETURN_TO_GAME"]: start_game_menu,
        # commands["START_WO_REFERRER"]:
        commands["START_GAME"]: start_game_menu,
        commands["SETTINGS"]: start_settings_menu,
        commands["CANCEL_CONTACT"]: start_cancel_contact_menu,
        commands["ADD_CONTACT"]: start_add_contact_menu,
        commands["GAME"]: handle_game_title,
    }


class VKBot(BaseBot):
    def __init__(self, message, bot, update, job_queue, upload, args=None):
        self.message = message
        self.bot = bot
        self.update = update
        self.job_queue = job_queue
        self.upload = upload
        self.player, self.is_created = vk_utils.get_or_create_player(bot, update, args)

    def start_main_menu(self, text=config.MAIN_MENU_TEXT, args=None):
        player_quests = self.player.has_quests

        button_list = VkKeyboard()
        if player_quests:
            button_list.add_button(quest_utils.menu_text_full("MY_GAMES"))
            button_list.add_line()
        button_list.add_button(quest_utils.menu_text_full("ALL_GAMES"))
        button_list.add_line()
        button_list.add_button(quest_utils.menu_text_full("SETTINGS"))
        self.bot.messages.send(
            peer_id=self.update.obj.from_id,
            random_id=get_random_id(),
            message=text,
            keyboard=button_list.get_keyboard(),
        )

    def start_my_quests_menu(self):
        player_quests = self.player.get_my_quests(select_related=("quest",))
        if player_quests:
            button_list = VkKeyboard()
            for item in player_quests:
                if item.quest.check_permission(self.player):
                    button_list.add_button(commands["GAME"] + " " + item.quest.name)
                    button_list.add_line()
            button_list.add_button(quest_utils.menu_text_full("MAIN_MENU"))

            self.bot.messages.send(
                peer_id=self.update.obj.from_id,
                random_id=get_random_id(),
                message=config.QUESTS_ALL,
                keyboard=button_list.get_keyboard(),
            )

    def start_all_quests_menu(self):
        quests = quest_utils.get_all_quests()
        button_list = VkKeyboard()
        for item in quests:
            if item.check_permission(self.player):
                button_list.add_button(commands["GAME"] + " " + item.name)
                button_list.add_line()
        button_list.add_button(quest_utils.menu_text_full("MAIN_MENU"))

        self.bot.messages.send(
            peer_id=self.update.obj.from_id,
            random_id=get_random_id(),
            message=config.QUESTS_ALL,
            keyboard=button_list.get_keyboard(),
        )

    def start_ask_to_start_menu(self):
        button_list = VkKeyboard()
        button_list.add_button(quest_utils.menu_text_full("START_GAME"))
        button_list.add_line()
        button_list.add_button(quest_utils.menu_text_full("ALL_GAMES"))
        button_list.add_line()
        button_list.add_button(quest_utils.menu_text_full("MAIN_MENU"))

        self.bot.messages.send(
            peer_id=self.update.obj.from_id,
            random_id=get_random_id(),
            message=(
                config.GAME_START_BUTTON
                + ' "'
                + quest_utils.menu_text_full("START_GAME")
                + '"'
            ),
            keyboard=button_list.get_keyboard(),
        )

    def send_quest_info(self, player_quest):
        if not player_quest.is_paid:
            payment_url = payments.make_payment(
                self.player.user_id,
                player_quest.quest_id,
                player_quest.quest.price
            )
            self.start_main_menu(
                text=f"{config.BUY_LINK_TEXT}{payment_url}"
            )

        awarding_description = (
            config.QUEST_IS_ON_AWARDING + "\n" + player_quest.quest.awarding_descr
            if player_quest.quest.is_awarding
            else ""
        )
        quest_description = (
            config.QUEST_DESCRIPTION + "\n" + player_quest.quest.description
        )

        if awarding_description:
            if player_quest.quest.image_award:
                image = vk_utils.get_or_upload_photo(
                    self.upload,
                    player_quest.quest,
                    "image_award",
                    player_quest.quest.image_award,
                )

                self.bot.messages.send(
                    peer_id=self.update.obj.from_id,
                    random_id=get_random_id(),
                    attachment=image,
                )

            self.bot.messages.send(
                peer_id=self.update.obj.from_id,
                random_id=get_random_id(),
                message=awarding_description,
            )

        if quest_description:
            if player_quest.quest.image_descr:
                image = vk_utils.get_or_upload_photo(
                    self.upload,
                    player_quest.quest,
                    "image_descr",
                    player_quest.quest.image_descr,
                )

                self.bot.messages.send(
                    peer_id=self.update.obj.from_id,
                    random_id=get_random_id(),
                    attachment=image,
                )

            self.bot.messages.send(
                peer_id=self.update.obj.from_id,
                random_id=get_random_id(),
                message=quest_description,
            )

    def start_wo_referrer_menu(self):
        self.player.is_next_message_referral = False
        self.player.save()
        self.start_main_menu()

    def start_ask_to_restart_menu(self):
        button_list = VkKeyboard()
        button_list.add_button(quest_utils.menu_text_full("CONFIRM_TO_RESTART"))
        button_list.add_line()
        button_list.add_button(quest_utils.menu_text_full("RETURN_TO_GAME"))
        self.bot.messages.send(
            peer_id=self.update.obj.from_id,
            random_id=get_random_id(),
            message=config.QUEST_CONFIRM_RESTART,
            keyboard=button_list.get_keyboard(),
        )

    def start_confirm_restart_menu(self):
        active_quest = self.player.get_active_quest(select_related=("quest",))

        if active_quest:
            if active_quest.is_paid:
                active_quest.clear_game()
                if active_quest.quest.check_permission(self.player):
                    self.start_playerquest(active_quest, active_quest.quest)
                else:
                    self.start_main_menu(text=config.QUEST_IS_NOT_AVAILABLE)
            else:
                self.send_quest_info(active_quest)

    def start_game_menu(self):
        active_quest = self.player.get_active_quest(
            select_related=("quest",),
            prefetch_related=(
                "changes",
                "current_step__options",
                "current_step__quest",
            ),
        )
        if active_quest:
            vk_utils.build_step(
                self.bot,
                self.update,
                self.upload,
                self.job_queue,
                active_quest.get_current_step(),
                active_quest,
            )

    def start_settings_menu(self):
        active_quest = self.player.get_active_quest(select_related=("quest",))
        button_list = VkKeyboard()

        reply_text = config.PLAYER_NO_QUESTS

        if active_quest:
            button_list.add_button(quest_utils.menu_text_full("ASK_TO_RESTART"))
            button_list.add_line()
            button_list.add_button(quest_utils.menu_text_full("RETURN_TO_GAME"))
            button_list.add_line()
            reply_text = config.PLAYER_PLAYING + ' "' + active_quest.quest.name + '"'
        button_list.add_button(quest_utils.menu_text_full("ADD_CONTACT"))
        button_list.add_line()
        button_list.add_button(quest_utils.menu_text_full("MAIN_MENU"))

        self.bot.messages.send(
            peer_id=self.update.obj.from_id,
            random_id=get_random_id(),
            message=reply_text,
            keyboard=button_list.get_keyboard(),
        )

    def start_cancel_contact_menu(self):
        if self.player.is_next_message_contact:
            self.player.end_contact_saving()

        self.start_main_menu()

    def start_add_contact_menu(self):
        self.player.start_contact_saving()
        contact = self.player.add_contact
        text = ""
        if self.player.add_contact:
            text = config.PLAYER_CONTACT + " " + contact + "\n"

        button_list = VkKeyboard()
        button_list.add_button(quest_utils.menu_text_full("CANCEL_CONTACT"))
        self.bot.messages.send(
            peer_id=self.update.obj.from_id,
            random_id=get_random_id(),
            message=(text + config.PLAYER_CONTACT_SET),
            keyboard=button_list.get_keyboard(),
        )

    def handle_game_title(self):
        # remove emoji and space
        self.message = self.message.replace(commands["GAME"] + " ", "")
        quest = quest_utils.get_quest_by_name(name=self.message)

        if quest:
            if quest.check_permission(player=self.player):
                active_quest = self.player.get_active_quest(
                    select_related=("quest",),
                    prefetch_related=("current_step__options", "changes"),
                )

                if active_quest:
                    # Player has active quest
                    current_step = active_quest.get_current_step()

                    if active_quest.quest.name == quest.name:
                        # Player chooses his active quest
                        if current_step:
                            # Player quest is not ended, so just continue
                            if active_quest.is_paid:
                                vk_utils.build_step(
                                    self.bot,
                                    self.update,
                                    self.upload,
                                    self.job_queue,
                                    current_step,
                                    active_quest,
                                )
                            else:
                                self.send_quest_info(active_quest)
                        else:
                            # Quest ended, so suggest to replay it
                            if active_quest.is_paid:
                                button_list = VkKeyboard()
                                button_list.add_button(
                                    quest_utils.menu_text_full("MAIN_MENU")
                                )
                                button_list.add_line()
                                button_list.add_button(
                                    quest_utils.menu_text_full("ASK_TO_RESTART")
                                )

                                self.bot.messages.send(
                                    peer_id=self.update.obj.from_id,
                                    random_id=get_random_id(),
                                    message=(
                                        config.QUEST_ASK_RESTART
                                        + ' "'
                                        + quest_utils.menu_text_full(
                                            "CONFIRM_TO_RESTART"
                                        )
                                        + '"'
                                    ),
                                    keyboard=button_list.get_keyboard(),
                                )
                    else:
                        # Player chooses another quest
                        player_quest = self.player.get_quest_by_pk(quest=quest)
                        self.start_playerquest(player_quest, quest)
                else:
                    # Player has no active quest and chooses one to start
                    new_player_quest = self.player.get_quest_by_pk(
                        quest, select_related=("current_step",)
                    )
                    self.start_playerquest(new_player_quest, quest)
            else:
                self.start_main_menu(text=config.QUEST_IS_NOT_AVAILABLE)

    def start_playerquest(self, player_quest, quest):
        if player_quest:
            # Player has PlayerQuest object of that quest
            if player_quest.is_paid:
                player_quest.set_active()
                vk_utils.build_step(
                    self.bot,
                    self.update,
                    self.upload,
                    self.job_queue,
                    player_quest.get_current_step(),
                    player_quest,
                )
            else:
                self.send_quest_info(player_quest)
        else:
            # Player has no PlayerQuest object of that quest
            player_quest = self.player.create_player_quest(quest)
            self.send_quest_info(player_quest)
            self.start_ask_to_start_menu()

    def handle_game_option(self):
        # Message is Option text or Unknown command
        if self.player.is_next_message_contact:
            quest_utils.handle_contact_message(self.player, self.message)
            self.start_main_menu(text=config.PLAYER_CONTACT_SET_DONE)
        elif self.player.is_next_message_referral:
            was_set = self.player.set_referral(self.message)
            if was_set:
                self.start_main_menu(text=config.PLAYER_REFERRAL_SET)
            else:
                vk_utils.send_referral_input(self.bot, self.update)
        else:
            player_quest = self.player.get_active_quest(
                select_related=("quest", "current_step", "player"),
                prefetch_related=("changes",),
            )
            quest = player_quest.quest

            if player_quest and quest.check_permission(player=self.player):
                # Player has active quest
                if player_quest.is_paid:
                    # if player has active quest and it's paid
                    current_step = player_quest.get_current_step()

                    if current_step:
                        # Quest is not done
                        option = (
                            current_step.options.filter(text=self.message)
                            .select_related("next_step")
                            .prefetch_related("changes", "next_step__options",)
                            .first()
                        )

                        if option:
                            (
                                is_winning,
                                current_step,
                            ) = quest_utils.handle_option_message(player_quest, option)
                            result_text = (
                                config.GAME_WIN_TEXT
                                if is_winning
                                else config.GAME_LOST_TEXT
                            )

                            vk_utils.build_step(
                                self.bot,
                                self.update,
                                self.upload,
                                self.job_queue,
                                current_step,
                                player_quest,
                                text=result_text,
                            )
                else:
                    self.send_quest_info(player_quest)
                    # Not paid or Unknown command

    COMMAND_TABLE = {
        commands["MY_GAMES"]: start_my_quests_menu,
        commands["ALL_GAMES"]: start_all_quests_menu,
        commands["MAIN_MENU"]: start_main_menu,
        # If one emoji used twice, then return dict of commands corresponding to given text
        commands["ASK_TO_RESTART"]: {
            config.ASK_TO_RESTART: start_ask_to_restart_menu,
            config.CONFIRM_TO_RESTART: start_confirm_restart_menu,
        },
        commands["RETURN_TO_GAME"]: start_game_menu,
        commands["START_WO_REFERRER"]: start_wo_referrer_menu,
        commands["START_GAME"]: start_game_menu,
        commands["SETTINGS"]: start_settings_menu,
        commands["CANCEL_CONTACT"]: start_cancel_contact_menu,
        commands["ADD_CONTACT"]: start_add_contact_menu,
        commands["GAME"]: handle_game_title,
    }
