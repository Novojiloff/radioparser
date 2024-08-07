import telebot
import schedule
from loguru import logger
import sys
from config import token, chat_id, radio_url, monitoring_chat_id
import requests
import os
import asyncio
from shazamio import Shazam
import nest_asyncio
from time import sleep

logger.remove()
logger.add("./log/log.log", rotation="100 MB")
logger.add(sink=sys.stderr, format="{time:D MMMM YYYY > HH:mm:ss} | {level} | {message}")
bot = telebot.TeleBot(token)
prev_artist = ''
prev_track = ''
nest_asyncio.apply()


def check(artist, track):
    global prev_artist
    global prev_track
    logger.info('Проверяем совпадает ли распознанные артист и трэк с предыдущими')
    if artist != prev_artist and track != prev_track:
        logger.info(f'Распознано. Исполнитель: {artist}, трэк: {track}')
        logger.info('Артист и трэк не совпадают с предыдущими. Фиксируем новые данные.')
        prev_artist = artist
        prev_track = track
        return True
    logger.info(f'Распознано. Исполнитель: {artist}, трэк: {track}')
    logger.info('Артист и трэк совпадают с предыдущими. Игнорим.')
    return False


def send(message, photo=None):
    count = 5
    if photo:
        while count > 0:
            try:
                bot.send_photo(chat_id, photo=photo, caption=message, disable_notification=True, parse_mode="html", protect_content=True)
                break
            except Exception:
                logger.warning('Что-то пошло не так. Ждем 10 секунд...')
                logger.warning(e)
                sleep(10)
                count -= 1
    else:
        while count > 0:
            try:
                bot.send_message(monitoring_chat_id,  text=message)
                break
            except Exception as e:
                logger.warning('Что-то пошло не так. Ждем 10 секунд...')
                logger.warning(e)
                sleep(10)
                count -= 1


async def recognize():
    shazam = Shazam()
    logger.info('Распознаем записанный аудиофайл')
    text = await shazam.recognize('radio_stream.mp3')
    # logger.info('Проверяем удалось ли распознать музыку из файла')
    try:
        if text.get('matches'):
            logger.info('Удалось распознать. Получаем имя исполнителя, название трэка и фото')
            artist = text.get('track').get('subtitle')
            track = text.get('track').get('title')
            photo = text.get('track').get('images').get('background')

            if check(artist=artist, track=track):
                logger.info('Формируем сообщение и отправляем в телеграм канал')
                message = f'🎙 Исполнитель: <b>{artist}</b>\n\n🎶 Название трэка: <b>{track}</b>'
                send(message=message, photo=photo)
        else:
            logger.info('Распознать не удалось.')
    except AttributeError as e:
        # send(message="Что-то я ничего не получил в ответ. Попробуем в следующий раз")
        # logger.warning('Что-то я ничего не получил в ответ. Попробуем в следующий раз')
        logger.warning(e)


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
        logger.info('-' * 30)
        logger.info('Поключаемся к аудио потоку')
        filename = "radio_stream.mp3"
        response = requests.get(radio_url, headers=headers, stream=True)
        response.raise_for_status()

        with open(filename, "wb") as f:
            logger.info('Открываем файл для записи, пишем поток в файл')
            for chunk in response.iter_content(chunk_size=32):
                if chunk:
                    f.write(chunk)
                    if os.path.getsize("radio_stream.mp3") >= 524288:
                        logger.info('Размер файла достаточный для распознавания. Выходим')
                        break
    except Exception:
        # send(message="Что-то пошло не так. Ждем 15 секунд...")
        logger.warning('Что-то пошло не так. Ждем 15 секунд...')
        sleep(15)


def job():
    record()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(recognize())
    

def main():
    schedule.every(90).seconds.do(job)
    while True:
        schedule.run_pending()


if __name__ == "__main__":
    try:
        logger.info('Программа запущена')
        send(message="Бот успешно запущен")
        main()
    except KeyboardInterrupt:
        logger.warning('Программа завершена пользователем')
    except Exception as e:
        logger.critical(e)
    finally:
        send(message="Программа завершилась с ошибкой!!! Перезапускаем бота")
        logger.info('Программа завершена')
