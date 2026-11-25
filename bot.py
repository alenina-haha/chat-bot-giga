import os
import uuid
import requests
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
VK_GROUP_ID = int(os.getenv("VK_GROUP_ID"))  # Читаем ID группы из .env

# --- НАСТРОЙКИ GIGACHAT ---
# Актуальный адрес API (с 17 июля 2026)
OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://api.giga.chat/v1/chat/completions"  # ИСПРАВЛЕНО
GIGACHAT_MODEL = "GigaChat-3-Ultra"

SYSTEM_PROMPT = """
Ты — опытный шеф-повар ресторана. Твоя задача — помогать поварам разнообразить меню.
Отвечай кратко, по делу, структурированно. Предлагай новые рецепты или вариации существующих блюд.
Если повар спрашивает рецепт, указывай ингредиенты и последовательность приготовления.
Не давай медицинских или опасных советов. Если вопрос не связан с кулинарией, вежливо верни разговор к еде.
"""

def get_gigachat_token() -> str:
    """Получает временный Access Token для GigaChat API."""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {GIGACHAT_AUTH_KEY}"
    }
    payload = {"scope": "GIGACHAT_API_PERS"}
    try:
        response = requests.post(OAUTH_URL, headers=headers, data=payload, timeout=15, verify=False)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"[AUTH ERROR] Не удалось получить токен GigaChat: {e}")
        return None

def ask_ai(user_question: str) -> str:
    """Отправляет вопрос в GigaChat и возвращает ответ."""
    token = get_gigachat_token()
    if not token:
        return "Извини, сейчас не могу подключиться к кухонной нейросети. Попробуй позже."

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "model": GIGACHAT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_question}
        ],
        "temperature": 0.7,
        "max_tokens": 1500,
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[AI ERROR] {e}")
        return "Извини, сейчас не могу придумать рецепт. Попробуй переформулировать вопрос чуть позже."

def main():
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, group_id=VK_GROUP_ID)  # Используем переменную

    print("Бот запущен и слушает сообщения...")

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            message = event.object.message
            user_id = message['from_id']
            text = message['text'].strip()

            if not text:
                continue

            print(f"Вопрос от {user_id}: {text}")
            ai_answer = ask_ai(text)

            try:
                vk.messages.send(
                    user_id=user_id,
                    message=ai_answer,
                    random_id=0
                )
            except Exception as e:
                print(f"[VK SEND ERROR] {e}")

if __name__ == "__main__":
    main()
