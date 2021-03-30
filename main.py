#!/usr/bin/env python
# pylint: disable=C0116

import logging
import random
from datetime import datetime
from typing import Dict

import pylast
import requests
import ujson
import toml

from telegram import Update
from telegram.constants import PARSEMODE_HTML
from telegram.ext import Updater, CommandHandler, CallbackContext

# Load config
with open("config/config.toml", "r") as config_file:
    CONFIG = toml.load(config_file)

# Network setup
network = pylast.LastFMNetwork(api_key=CONFIG["api"]["lastfm_api_key"],
                               api_secret=CONFIG["api"]["lastfm_api_secret"])

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)

logger = logging.getLogger(__name__)


def get_lastfm_users() -> Dict[str, str]:
    with open("config/lastfm_users.json", "r") as json_file:
        data = ujson.load(json_file)
    json_file.close()
    return data


def get_lastfm_user(update: Update, username: str) -> str:
    with open("config/lastfm_users.json", "r") as json_file:
        data = ujson.load(json_file)
    json_file.close()
    try:
        lastfm_user = data[username]
        return lastfm_user
    except KeyError:
        update.message.reply_text(
            "Establecé tu nombre de usuario de last.fm usando "
            "/setlastfm <username>")
        raise


def set_lastfm_users(data: Dict[str, str]) -> None:
    with open("config/lastfm_users.json", "w") as json_file:
        ujson.dump(data, json_file)
    return


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text("Buenas, vengo a reemplazar a otouto. RIP.")


def help_command(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text("Preguntale a akka.")


def weather(update: Update, _: CallbackContext) -> None:
    """Get weather forecast"""
    location: str = update.message.text.split("/weather")[-1].strip()
    if not location:
        location = "Buenos Aires"

    url = f"http://api.openweathermap.org/data/2.5/weather?q=" \
          f"{location}&units=metric&lang=es&appid=" \
          f"{CONFIG['api']['openweathermap_token']}"
    r = requests.get(url).json()
    temperature = r["main"]["temp"]
    description = r["weather"][0]["description"]
    icon = r["weather"][0]["icon"]
    with open("config/weather_emojis.json", "r") as weather_file:
        weather_emojis = ujson.load(weather_file)
    weather_file.close()
    try:
        weather_emoji = weather_emojis[icon]
    except KeyError:
        weather_emoji = ""
    update.message.reply_text(
        f"{location.title()}: {weather_emoji} {round(temperature)}°,"
        f" {description}")


def shout(update: Update, _: CallbackContext) -> None:
    text = update.message.text.split("/shout")[-1].strip()
    update.message.reply_text(f"{' '.join(list(text.upper()))}")


def setlastfm(update: Update, _: CallbackContext) -> None:
    lastfm_username = update.message.text.split("/setlastfm")[-1].strip()

    if lastfm_username:
        data = get_lastfm_users()
        data[update.message.from_user.username] = lastfm_username
        set_lastfm_users(data)
    else:
        update.message.reply_text(
            "Ingresá nombre de usuario de last.fm")
        return
    update.message.reply_text("Nombre de usuario establecido.")


def npfull(update: Update, _: CallbackContext) -> None:
    """Show playing song using last.fm API"""

    user = update.message.from_user
    lastfm_user = network.get_user(get_lastfm_user(update, user.username))
    now_playing = lastfm_user.get_now_playing()
    if not now_playing:
        now_playing = lastfm_user.get_recent_tracks(1)[0].track
        now_playing_text = f"{user.full_name} escuchó por última vez:"
    else:
        now_playing_text = f"{user.full_name} está escuchando:"

    album = now_playing.get_album()
    album_art = album.get_cover_image()
    if not album_art:
        album_art = "https://i.ibb.co/wLh5Gsc/image.png"

    song_info = f"""
{now_playing_text}
🎵 {now_playing.title}
💿 {album.title}
👤 {album.artist}
<a href="{album_art}">&#8205;</a>
"""
    update.message.reply_text(song_info, parse_mode=PARSEMODE_HTML)


def recommend(update: Update, _: CallbackContext) -> None:
    """Recommend a song to user"""
    user = update.message.from_user.username
    lastfm_user = get_lastfm_user(update, user)

    url = f"https://www.last.fm/player/station/user/{lastfm_user}/recommended"
    r = requests.get(url).json()
    random_songs = random.choices(r["playlist"], k=5)
    random_songs = [f"{song['artists'][0]['name']} - {song['name']}" for song in random_songs]
    update.message.reply_text("\n".join(random_songs))


def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(CONFIG["api"]["bot_key"])

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("setlastfm", setlastfm))
    dispatcher.add_handler(CommandHandler("npfull", npfull))
    dispatcher.add_handler(CommandHandler("recommend", recommend))
    dispatcher.add_handler(CommandHandler("weather", weather))
    dispatcher.add_handler(CommandHandler("shout", shout))

    # on noncommand i.e message - echo the message on Telegram
    # dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command,
    # echo))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
