import requests
import openai
import logging
from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler
import os

# === Конфигурация ===
TELEGRAM_BOT_TOKEN = os.environ['7337478240:AAFJV3unK2fKu70eta1NrRd2p4Wu-LwVVDA']
TELEGRAM_CHANNEL_ID = os.environ['-1002159520338']
OPENAI_API_KEY = os.environ['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']
openai.api_key = OPENAI_API_KEY

TOKENS = ['bitcoin', 'ethereum', 'solana', 'the-open-network', 'hamster-kombat', 'dogecoin',
          'bnb', 'cardano', 'avalanche-2', 'polkadot', 'tron', 'chainlink',
          'uniswap', 'pepe', 'arbitrum', 'starknet']

def get_market_data():
    ids = ','.join(TOKENS)
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true'
    response = requests.get(url)
    data = response.json()
    text = ''
    for token in TOKENS:
        info = data.get(token)
        if info:
            price = info['usd']
            change = info['usd_24h_change']
            text += f"{token.title()}: ${price:.2f} ({change:+.2f}%)\n"
    return text

def generate_post(market_text):
    prompt = (
        "Ты крипто-аналитик. Составь короткий пост (макс 200 слов) для Telegram-канала:\n\n"
        f"{market_text}\n\n"
        "Сделай краткий вывод: что это значит для рынка?"
    )
    response = openai.ChatCompletion.create(
        model='gpt-4',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=300,
        temperature=0.7,
    )
    return response['choices'][0]['message']['content']

def post_to_telegram(message):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message)

def job():
    try:
        print("Генерация поста...")
        market_text = get_market_data()
        ai_post = generate_post(market_text)
        post = f"🧠 Актуальная сводка по рынку:\n\n{market_text}\n\n{ai_post}"
        post_to_telegram(post)
        print("Пост отправлен.")
    except Exception as e:
        logging.exception("Ошибка при генерации поста")

# === Запуск ===
scheduler = BlockingScheduler()
scheduler.add_job(job, 'interval', hours=4)
job()  # Первый пост сразу
scheduler.start()
