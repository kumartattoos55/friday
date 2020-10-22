import asyncio
import os
import pathlib
import time
import urllib

import aiohttp
import pyrogram

from bot import logger
from helper_funcs import gdriveTools
from helper_funcs.bot_utils import get_readable_file_size
from helper_funcs.extract_link_from_message import extract_link
from helper_funcs.shortlink_generator import generate_short_link
from plugins.dl_button import download_coroutine
from translation import Translation
from datetime import datetime

# the secret configuration specific things
if bool(os.environ.get("WEBHOOK", False)):
    from sample_config import Config
else:
    from config import Config

@pyrogram.Client.on_message(pyrogram.Filters.command(["gleech"]))
async def gdrive_upload(bot, update):
    dl_url, custom_file_name, _, _ = await extract_link(update.reply_to_message, "GLEECH")
    logger.info(dl_url)
    logger.info(custom_file_name)
    reply_message = await bot.send_message(
        text=Translation.DOWNLOAD_START,
        chat_id=update.chat.id,
        reply_to_message_id=update.message_id
    )
    tmp_directory_for_each_user = f"{Config.DOWNLOAD_LOCATION}{update.message_id}"
    if not os.path.isdir(tmp_directory_for_each_user):
        os.makedirs(tmp_directory_for_each_user)
    if custom_file_name is None:
        if dl_url.find('workers.dev') > -1:
            custom_file_name = dl_url[dl_url.rindex("/")+1:]
        elif dl_url.find('seedr') > -1:
            custom_file_name = dl_url[int(dl_url.rindex("/")) + 1:int(dl_url.rindex("?"))]
        else:
            if dl_url.rindex("/") > -1 and dl_url.rindex("?") > -1:
                custom_file_name = dl_url[int(dl_url.rindex("/")) + 1:int(dl_url.rindex("?"))]
            else:
                custom_file_name = dl_url[dl_url.rindex("/") + 1:]
        custom_file_name = urllib.parse.unquote(custom_file_name)
    download_directory = tmp_directory_for_each_user + "/" + custom_file_name
    async with aiohttp.ClientSession() as session:
        c_time = time.time()
        try:
            await download_coroutine(
                bot,
                session,
                dl_url,
                download_directory,
                reply_message.chat.id,
                reply_message.message_id,
                c_time
            )
        except :
            await bot.edit_message_text(
                text=Translation.SLOW_URL_DECED,
                chat_id=reply_message.chat.id,
                message_id=reply_message.message_id
            )
            return False
    if os.path.exists(download_directory):
        end_one = datetime.now()
        up_name = pathlib.PurePath(download_directory).name
        size= get_readable_file_size(get_path_size(download_directory))
        try:
            await bot.edit_message_text(
                text="Download Completed!!!\n Upload in progress",
                chat_id=reply_message.chat.id,
                message_id=reply_message.message_id
            )
        except Exception as e:
            logger.info(str(e))
            pass
        logger.info(f"Upload Name : {up_name}")
        drive = gdriveTools.GoogleDriveHelper(up_name)
        gd_url,index_url=drive.upload(download_directory)
        button = []
        button.append([pyrogram.InlineKeyboardButton(text="☁️ CloudUrl ☁️", url=f"{gd_url}")])
        if Config.INDEX_URL:
            logger.info(index_url)
            button.append([pyrogram.InlineKeyboardButton(text="ℹ️ IndexUrl ℹ️", url=f"{index_url}")])
        button_markup = pyrogram.InlineKeyboardMarkup(button)
        await bot.send_message(
            text=f"🤖: <b>{up_name}</b> has been Uploaded successfully to your Cloud🤒 \n📀 Size: {size}",
            chat_id=update.chat.id,
            reply_to_message_id=update.message_id,
            reply_markup=button_markup)
        if Config.INDEX_URL:
            await generate_short_link(reply_message, index_url, custom_file_name)
        await reply_message.delete()


def get_path_size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    total_size = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            abs_path = os.path.join(root, f)
            total_size += os.path.getsize(abs_path)
    return total_size