'''Данная программа повторяет функционал sort-favorites.py, но с оптимизацией: 
она удаляет и добавляет только те треки, которые не совпадают с желаемым порядком. 
Это позволяет сократить количество операций и ускорить процесс. 
Нужна, чтобы быстрее выполнять повторную сортировку плейлиста.'''

import time
import json
from yandex_music import Client

TOKEN = "YOUR_YANDEX_MUSIC_TOKEN"

def get_sort_key(track):
    artist = ""
    if track.artists and len(track.artists) > 0 and track.artists[0].name:
        artist = track.artists[0].name.lower()
    title = track.title.lower() if track.title else ""
    return (artist, title)

def main():
    client = Client(TOKEN).init()
    
    print("1. Анализ плейлиста...")
    likes = client.users_likes_tracks()
    current_tracks = likes.fetch_tracks()
    
    if not current_tracks:
        print("Плейлист пуст.")
        return

    desired_tracks = sorted(current_tracks, key=get_sort_key)

    current_ids = [str(t.id) for t in current_tracks]
    desired_ids = [str(t.id) for t in desired_tracks]

    if current_ids == desired_ids:
        print("Плейлист уже отсортирован.")
        return

    match_index = len(current_ids)
    while match_index > 0:
        if current_ids[match_index - 1] == desired_ids[match_index - 1]:
            match_index -= 1
        else:
            break

    tracks_to_reorder = desired_ids[:match_index]
    
    print(f"Всего треков в коллекции: {len(current_ids)}")
    print(f"Требуется перезаписать: {len(tracks_to_reorder)}")

    with open("likes_backup_sync.json", "w", encoding="utf-8") as f:
        json.dump(current_ids, f, indent=2)

    print("\n2. Удаление треков...")
    batch_size = 100
    for i in range(0, len(tracks_to_reorder), batch_size):
        batch = tracks_to_reorder[i:i + batch_size]
        client.users_likes_tracks_remove(batch)
        time.sleep(0.3)

    print("3. Запись треков...")
    total = len(tracks_to_reorder)
    for i, track_id in enumerate(reversed(tracks_to_reorder), 1):
        client.users_likes_tracks_add(track_id)
        print(f"  [{i}/{total}] Обновлен ID: {track_id}")
        time.sleep(0.35)

    print("\nТреки отсортированы.")

if __name__ == "__main__":
    main()
