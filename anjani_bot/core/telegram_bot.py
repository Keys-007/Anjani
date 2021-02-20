""" PyroClient """
# Copyright (C) 2020 - 2021  UserbotIndo Team, <https://github.com/userbotindo.git>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import importlib
import logging
import os
import pkgutil
from typing import TYPE_CHECKING, Any, Optional, Union

import pyrogram
from pyrogram import types

from .base import Base
from .client import Client
if TYPE_CHECKING:
    from .anjani import Anjani


LOG = logging.getLogger(__name__)


class TelegramBot(Base):
    client: pyrogram.Client

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        self.staff = {}

        super().__init__(**kwargs)

    async def init_client(self: "Anjani") -> None:
        """ Initialize pyrogram client """
        try:
            api_id = int(self.get_config("API_ID"))
        except ValueError:
            raise TypeError("API ID is not a valid integer")

        api_hash = self.get_config("API_HASH")
        if not isinstance(api_hash, str):
            raise TypeError("API HASH must be a string")

        bot_token = self.get_config("BOT_TOKEN")
        if not isinstance(bot_token, str):
            raise TypeError("BOT TOKEN must be a string")

        self.client = Client(
            self,
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token,
            session_name=":memory:"
        )
        try:
            owner = int(self.get_config("OWNER_ID"))
        except ValueError:
            owner = 0

        self.staff = {"owner": owner}

    async def start(self: "Anjani"):
        """ Start client """
        LOG.info("Starting Bot Client...")
        await self.init_client()
        await self.connect_db("AnjaniBot")
        self._load_language()
        subplugins = [
            importlib.import_module("anjani_bot.plugins." + info.name, __name__)
            for info in pkgutil.iter_modules(["anjani_bot/plugins"])
        ]
        self.load_all_modules(subplugins)
        await self.client.start()
        await self._load_all_attribute()
        await self.channel_log("Bot started successfully...")

    async def run(self: "Anjani") -> None:
        """ Run PyroClient """
        try:
            # Start client
            try:
                await self.start()
            except KeyboardInterrupt:
                LOG.warning("Received interrupt while connecting")
                return

            # idle until disconnected
            LOG.info("Idling")
            await pyrogram.idle()
        finally:
            await self.stop()

    @staticmethod
    def get_config(name: str) -> Union[str, int]:
        """ Get variable from Config """
        return os.environ.get(name)

    def redact_message(self, text: str) -> str:
        """ Secure any secret variable"""
        api_id = self.get_config("API_ID")
        api_hash = self.get_config("API_HASH")
        bot_token = self.get_config("BOT_TOKEN")

        if api_id in text:
            text = text.replace(api_id, "[REDACTED]")
        if api_hash in text:
            text = text.replace(api_hash, "[REDACTED]")
        if bot_token in text:
            text = text.replace(bot_token, "[REDACTED]")

        return text

    async def _load_all_attribute(self) -> None:
        """ Load all client attributes """
        bot = await self.client.get_me()
        self.identifier = bot.id
        self.username = bot.username
        if bot.last_name:
            self.name = bot.first_name + " " + bot.last_name
        else:
            self.name = bot.first_name

        _db = self.get_collection("STAFF")
        self.staff.update({'dev': [], 'sudo': []})
        async for i in _db.find():
            self.staff[i["rank"]].append(i["_id"])

    async def channel_log(
            self,
            text: str,
            parse_mode: Optional[str] = object,
            disable_web_page_preview: bool = None,
            disable_notification: bool = None,
            reply_markup: Union[
                "types.InlineKeyboardMarkup",
                "types.ReplyKeyboardMarkup",
                "types.ReplyKeyboardRemove",
                "types.ForceReply"
            ] = None
        ) -> Union["types.Message", None]:
        """Shortcut method to send message to log channel.

        Parameters:
            text (`str`):
                Text of the message to be sent.

            parse_mode (`str`, *optional*):
                By default, texts are parsed using both Markdown and HTML styles.
                You can combine both syntaxes together.
                Pass "markdown" or "md" to enable Markdown-style parsing only.
                Pass "html" to enable HTML-style parsing only.
                Pass None to completely disable style parsing.

            disable_web_page_preview (`bool`, *optional*):
                Disables link previews for links in this message.

            disable_notification (`bool`, *optional*):
                Sends the message silently.
                Users will receive a notification with no sound.

            reply_markup (
                :obj:`~InlineKeyboardMarkup` | :obj:`~ReplyKeyboardMarkup` |
                :obj:`~ReplyKeyboardRemove` | :obj:`~ForceReply`, *optional*
                ):
                Additional interface options. An object for an inline keyboard,
                custom reply keyboard, instructions to remove reply keyboard or
                to force a reply from the user.

        Returns:
            :obj:`~types.Message`: On success, the sent text message is returned.
        """
        try:
            log_channel = int(self.get_config("LOG_CHANNEL"))
        except (TypeError, ValueError):
            LOG.warning(f"LOG_CHANNEL is not exists nor valid, message '{text}' not send.")
            return

        return await self.client.send_message(
            chat_id=log_channel,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            reply_markup=reply_markup
        )
