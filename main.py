import os
import requests
import datetime
import traceback
import threading
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from telegram import ReplyKeyboardMarkup, KeyboardButton
import pytz
from dotenv import load_dotenv
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "toncoin": "TON",
    "sui": "SUI",
    "xpr-network": "XPR",
    "dogs-token": "DOGS",
    "hamster-kombat": "HMSTR",
    "notcoin": "NOTCOIN"
}
def log_event(message: str):
    print(f"LOG: {message}")
    with open("log.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")
def send_to_telegram(text):
    print("Sending message to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    if not response.ok:
        log_event(f"Telegram Error: {response.text}")
    else:
        print("Message sent successfully.")
def send_start_keyboard(chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    keyboard = {
        "keyboard": [[{"text": "CryptoNews"}]],
        "resize_keyboard": True
    }
    payload = {
        "chat_id": chat_id,
        "text": "Нажми кнопку, чтобы отправить пост:",
        "reply_markup": keyboard
    }
    requests.post(url, json=payload)
def get_prices():
    print("Getting prices from CoinGecko...")
    ids = ",".join(COINS.keys())
    url = f"https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ids,
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
    try:
        r = requests.get(url, params=params)
        data = r.json()
        lines = []
        for coin_id, symbol in COINS.items():
            if coin_id in data:
                price = data[coin_id]["usd"]
                change = data[coin_id].get("usd_24h_change", 0)
                emoji = "РОСТ" if change > 0 else "ПАДЕНИЕ" if change < 0 else "⚪ "
                lines.append(f"{emoji} *{symbol}*: ${price:,.4f} ({change:+.2f}%)")
        print("Prices retrieved successfully.")
        return lines
    except Exception as e:
        log_event(f"Ошибка при получении цен: {str(e)}")
        return []
def generate_gpt_summary(price_lines):
    print("Generating GPT summary...")
    price_text = "\n".join(price_lines)
    prompt = f"""
Ты — AI-помощник криптобота. Не повторяй блок цен.
Вот свежие данные с рынка:
{price_text}
Сформируй Telegram-пост только с аналитикой:
- Заголовок (с эмодзи)
- 3–5 пунктов аналитики
- Короткий вывод
- Подпись: #cryptoRepost и "Мой портфель: http://t.me/Cryptotrackergpsbot"
"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/Onlyfanfarm",
        "X-Title": "CryptoTelegramBot"
    }
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers=headers,
                          json=data)
        r.raise_for_status()
        print("GPT summary generated successfully.")
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log_event(f"GPT Error:\n{traceback.format_exc()}")
        return "*GPT-обзор временно недоступен.*"
def job():
    print("Running scheduled job...")
    price_lines = get_prices()
    if not price_lines:
        send_to_telegram("❌   Не удалось получить данные с CoinGecko.")
        return
    header = f"?? *Курс рынка на {datetime.datetime.now().strftime('%-d %B, %H:%M')}*"
    price_block = "\n".join([header] + price_lines)
    gpt = generate_gpt_summary(price_lines)
    full_post = f"{price_block}\n\n---\n\n{gpt}"
    send_to_telegram(full_post)
    log_event("Пост с данными отправлен.")
def listen_for_commands():
    offset = None
    print("Listening for commands...")
    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        if offset:
            url += f"?offset={offset}"
        try:
            r = requests.get(url)
            data = r.json()
            if not data.get("ok"):
                log_event(f"Telegram API error: {data}")
                time.sleep(5)
                continue
            result = data.get("result", [])
            for update in result:
                offset = update["update_id"] + 1
                if "message" in update and "text" in update["message"]:
                    text = update["message"]["text"].strip().lower()
                    chat_id = update["message"]["chat"]["id"]
                    print(f"Received: {text}")
                    if text == "/start":
                        send_start_keyboard(chat_id)
                    elif text == "/post" or text == "пост cryptonews":
                        job()
                        log_event("Пост отправлен вручную.")
        except Exception as e:
            log_event(f"Ошибка в listen_for_commands: {str(e)}")
        time.sleep(5)
timezone = pytz.timezone('Europe/Moscow')
scheduler = BlockingScheduler(timezone=timezone)
log_event("Бот запущен.")
scheduler.add_job(job, 'cron', hour=8, minute=0)
scheduler.add_job(job, 'cron', hour=14, minute=0)
scheduler.add_job(job, 'cron', hour=21, minute=0)
threading.Thread(target=listen_for_commands, daemon=True).start()
scheduler.start() 
