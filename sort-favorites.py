'''Данная программа сортирует плейлист "Мне нравится" в Яндекс Музыке 
по алфавиту: сначала по имени исполнителя, затем по названию трека. 
Для работы программы необходимо получить токен Яндекс Музыки и вставить его в переменную TOKEN.'''

import json
import os
import sys
import time
from yandex_music import Client

TOKEN = "YOUR_YANDEX_MUSIC_TOKEN"
STATE_FILE = "sort_state.json"
BACKUP_FILE = "likes_backup.json"


def api_retry(func, retries=5, base_delay=2):
    """Выполняется при сбоях сети"""
    for attempt in range(1, retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == retries:
                raise e
            sleep_time = base_delay * attempt
            print(f"\n[!] Ошибка сети: ({e}). Попытка {attempt}/{retries} через {sleep_time}с...")
            time.sleep(sleep_time)


def get_sort_key(track):
    """Сортировка: Исполнитель (алф. порядок) -> Название трека (алф. порядок)"""
    artist = ""
    if track.artists and len(track.artists) > 0 and track.artists[0].name:
        artist = track.artists[0].name.lower()
    title = track.title.lower() if track.title else ""
    return (artist, title)


def main():
    if TOKEN == "YOUR_YANDEX_MUSIC_TOKEN":
        print("Ошибка: Укажите ваш TOKEN в скрипте.")
        sys.exit(1)

    client = api_retry(lambda: Client(TOKEN).init())

    # --- ШАГ 1: Инициализация или загрузка состояния ---
    if os.path.exists(STATE_FILE):
        print("Обнаружен незавершенный сеанс. Загрузка состояния...")
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        print("1/4. Загрузка избранного из Яндекс Музыки...")
        likes = api_retry(lambda: client.users_likes_tracks())
        tracks = api_retry(lambda: likes.fetch_tracks())

        if not tracks:
            print("Плейлист \"Мне нравится\" пуст.")
            return

        # Полный бэкап исходных данных
        backup_data = [
            {"id": str(t.id), "title": t.title, "artist": t.artists[0].name if t.artists else None}
            for t in tracks
        ]
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        print(f"Сохранен бэкап: {BACKUP_FILE} ({len(tracks)} треков)")

        # Сортировка по алфавиту
        sorted_tracks = sorted(tracks, key=get_sort_key)
        
        # Запись ID (в обратном порядке, так как последний добавленный трек оказывается в начале плейлиста
        target_ids = [str(t.id) for t in reversed(sorted_tracks)]
        original_ids = [str(t.id) for t in tracks]

        state = {
            "status": "CLEARING",
            "original_ids": original_ids,
            "target_ids": target_ids,
            "processed_add_count": 0
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    # --- ШАГ 2: Полная очистка списка лайков ---
    if state["status"] == "CLEARING":
        print("2/4. Очистка текущего списка лайков...")
        orig_ids = state["original_ids"]
        batch_size = 100
        
        for i in range(0, len(orig_ids), batch_size):
            batch = orig_ids[i:i + batch_size]
            api_retry(lambda: client.users_likes_tracks_remove(batch))
            print(f"  Удалено: {min(i + batch_size, len(orig_ids))}/{len(orig_ids)}")
            time.sleep(0.3)

        state["status"] = "ADDING"
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    # --- ШАГ 3: Добавление отсортированных треков ---
    if state["status"] == "ADDING":
        print("3/4. Заполнение отсортированными треками...")
        target_ids = state["target_ids"]
        start_idx = state["processed_add_count"]
        total = len(target_ids)

        for i in range(start_idx, total):
            track_id = target_ids[i]
            
            api_retry(lambda: client.users_likes_tracks_add(track_id))
            
            # Бэкап прогресса после каждого добавленного трека
            state["processed_add_count"] = i + 1
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            print(f"  [{i + 1}/{total}] Добавлен ID: {track_id}")
            # Пауза в 0.35с гарантирует разные временные метки запросов на сервере Яндекса
            time.sleep(0.35)

    # --- ШАГ 4: Завершение ---
    os.remove(STATE_FILE)
    print("\n4/4. Успешно завершено! Перезапустите Яндекс.Музыку.")


if __name__ == "__main__":
    main()
