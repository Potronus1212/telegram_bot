import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import asyncio
from datetime import datetime
import pytz
import re
import os

# Ваш токен Telegram API (полученный от @BotFather)
TELEGRAM_TOKEN = '7211774190:AAGmM01CGSDEI0_E283A8-Wdt_-uxQBSSts'  # Ваш токен
# Ваш Telegram ID (чтобы бот отправлял сообщения только вам)
CHAT_ID = '271302892'  # Ваш ID

# URL сайтов, которые будем мониторить
URLS = [
    'https://www.olx.pl/oferty/q-Buds%203%20Pro/?min_id=970344460&reason=observed_search&search%5Border%5D=created_at%3Adesc',
    'https://www.olx.pl/elektronika/telefony/q-s24/?min_id=970379694&reason=observed_search&search%5Bfilter_float_price%3Afrom%5D=900&search%5Bfilter_float_price%3Ato%5D=2900&search%5Border%5D=created_at%3Adesc',
    'https://www.olx.pl/elektronika/telefony/q-s23/?min_id=970389891&reason=observed_search&search%5Bfilter_float_price%3Afrom%5D=900&search%5Bfilter_float_price%3Ato%5D=2700&search%5Border%5D=created_at%3Adesc',
]

# Инициализируем Telegram-бота
bot = Bot(token=TELEGRAM_TOKEN)

# Путь к файлу, где будут храниться ID уже обработанных объявлений
PROCESSED_ADS_FILE = 'processed_ads.txt'

# Ваша текущая временная зона (например, Московское время)
local_tz = pytz.timezone('Europe/Moscow')  # Замените на нужный вам часовой пояс

# Функция для загрузки обработанных ID объявлений
def load_processed_ads():
    if os.path.exists(PROCESSED_ADS_FILE):
        with open(PROCESSED_ADS_FILE, 'r') as file:
            return set(file.read().splitlines())
    return set()

# Функция для сохранения обработанных ID в файл
def save_processed_ads(processed_ads):
    with open(PROCESSED_ADS_FILE, 'w') as file:
        file.write('\n'.join(processed_ads))

# Функция для преобразования времени в нужный часовой пояс
def convert_time_to_local(time_str):
    # Преобразуем строку "Dzisiaj o 15:51" в локальное время
    match = re.search(r'o (\d{1,2}):(\d{2})', time_str)
    if match:
        # Берем текущее время, обновляем его на время из строки
        hour = int(match.group(1))
        minute = int(match.group(2))
        today = datetime.now(local_tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
        return today.strftime('%H:%M %d %B %Y')
    else:
        return time_str

async def get_new_ads(processed_ads):
    """
    Парсит сайт и возвращает список новых объявлений.
    """
    new_ads = []

    for url in URLS:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем блоки объявлений
        ads = soup.select('.css-l9drzq')

        for ad in ads:
            # Ссылка на объявление
            link = ad.select('a.css-qo0cxu')[0]['href']
            
            # Название объявления
            title = ad.select('h4.css-1s3qyje')[0].text.strip()
            
            # Цена
            price = ad.select('p.css-13afqrm')[0].text.strip()
            
            # Местоположение и дата
            location_date = ad.select('p.css-1mwdrlh')[0].text.strip()

            # Проверяем, если это новое объявление
            ad_id = link.split('-')[-1]
            if ad_id not in processed_ads:
                processed_ads.add(ad_id)
                new_ads.append({
                    'title': title,
                    'link': link,
                    'price': price,
                    'location_date': location_date,
                    'url': url
                })

    return new_ads, processed_ads

async def send_telegram_message(message):
    """
    Отправляет сообщение в Telegram.
    """
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")

async def main():
    """
    Основной асинхронный цикл работы бота.
    """
    processed_ads = load_processed_ads()  # Загружаем ID обработанных объявлений

    while True:
        try:
            # Получаем новые объявления
            new_ads, processed_ads = await get_new_ads(processed_ads)
            for ad in new_ads:
                # Помечаем объявления по типу (наушники, S 24, S 23)
                if 'Buds 3' in ad['url']:
                    title_tag = "Наушники Buds 3"
                elif 's24' in ad['url']:
                    title_tag = "S 24"
                elif 's23' in ad['url']:
                    title_tag = "S 23"
                else:
                    title_tag = "Новое объявление"

                # Конвертируем дату в нужный часовой пояс
                localized_time = convert_time_to_local(ad['location_date'])

                # Отправляем сообщение с правильным временем
                await send_telegram_message(f"<b>{title_tag}:</b> {ad['title']}\n"
                                             f"<b>Ссылка:</b> <a href='https://www.olx.pl{ad['link']}'>Ссылка на объявление</a>\n"
                                             f"<b>Цена:</b> {ad['price']}\n"
                                             f"<b>Местоположение:</b> {ad['location_date']}\n"
                                             f"<b>Дата:</b> {localized_time}")
            
            # Сохраняем обновленные ID в файл
            save_processed_ads(processed_ads)

            # Ждём 60 секунд перед следующим запросом
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(60)

# Запускаем асинхронный цикл
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
