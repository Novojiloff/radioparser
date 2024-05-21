import telebot
import schedule
from loguru import logger
import sys
from config import token, chat_id, radio_url
import requests
import os
import asyncio
from shazamio import Shazam
import nest_asyncio
from time import sleep

logger.remove()
logger.add("file_{time}.log", rotation="100 MB")
logger.add(sink=sys.stderr, format="{time:D MMMM YYYY > HH:mm:ss} | {level} | {message}")
bot = telebot.TeleBot(token)
prev_artist = ''
prev_track = ''
nest_asyncio.apply()


def check(artist, track):
    global prev_artist
    global prev_track
    
    if artist != prev_artist and track != prev_track:
        prev_artist = artist
        prev_track = track
        return True
    return False


async def recognize():
    shazam = Shazam()
    text = await shazam.recognize('radio_stream.mp3')
    if text.get('matches'):
        artist = text.get('track').get('subtitle')
        track = text.get('track').get('title')
        photo = text.get('track').get('images').get('background')

        if check(artist=artist, track=track):
            caption = f'Исполнитель: <b>{artist}</b>\n\nНазвание трэка: <b>{track}</b>'
            logger.info(f'Stream recognized. Artist: {artist}, track: {track}')
            bot.send_photo(chat_id, photo=photo, caption=caption, parse_mode="html")
        else:
            logger.info(f'Stream recognized. Artist: {artist}, track: {track}')
    else:
        logger.warning('Nothing matched')


def record():
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    try:
        filename = "radio_stream.mp3"
        response = requests.get(radio_url, headers=headers, stream=True)
        response.raise_for_status()

        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=32):
                if chunk:
                    if os.path.getsize("radio_stream.mp3") >= 524288:
                        break
                    f.write(chunk)
    except Exception:
        logger.warning('Что-то пошло не так. Ждем 15 секунд...')
        sleep(15)
        pass


def job():
    record()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(recognize())
    

def main():
    logger.info('Started...')
    schedule.every(90).seconds.do(job)
    while True:
        schedule.run_pending()



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning('Программа завершена пользователем')
    except Exception as e:
        logger.warning(e)
