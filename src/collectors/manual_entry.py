import json
import uuid
from datetime import datetime
from pathlib import Path
import os

def get_multiline_input(prompt):
    print(prompt + " (zakończ wpisując pustą linię lub Ctrl+Z/Ctrl+D):")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)

def main():
    print("="*60)
    print("RUSSINT - Ręczne wprowadzanie danych (Manual Entry)")
    print("="*60)

    base_dir = Path(__file__).parent.parent.parent
    raw_dir = base_dir / "data" / "raw" / "manual"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 1. Dane profilu / źródła
    print("\n--- Konfiguracja sesji ---")
    profile_name = input("Nazwa profilu/źródła (np. BraterstwaLudziWolnych): ").strip()
    profile_url = input("URL profilu (opcjonalnie): ").strip()
    if not profile_url and profile_name:
        profile_url = f"https://www.facebook.com/{profile_name}"

    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"manual_{profile_name}_{session_timestamp}.json"
    output_path = raw_dir / filename

    posts = []

    while True:
        print(f"\n--- Dodawanie posta #{len(posts) + 1} ---")
        
        # Generowanie ID
        post_id = str(uuid.uuid4())
        print(f"ID: {post_id}")

        # Link do posta
        post_url = input("Link do posta (URL): ").strip()

        # Data
        post_date = input("Data posta (tekst, np. '2025-11-24' lub '2 godz.'): ").strip()

        # Treść
        print("Treść posta (wpisz tekst, zakończ pustą linią):")
        content_lines = []
        while True:
            line = input()
            if not line:
                break
            content_lines.append(line)
        text = "\n".join(content_lines)

        # Link zawarty (zewnętrzny/repost)
        external_url = input("Link zawarty w poście (zewnętrzny/repost) [Enter by pominąć]: ").strip()

        # Autor
        author = input(f"Autor posta [Domyślnie: {profile_name}]: ").strip()
        if not author:
            author = profile_name

        # Zdjęcia
        images_input = input("Linki do zdjęć (oddzielone przecinkiem) [Enter by pominąć]: ").strip()
        images = [img.strip() for img in images_input.split(',')] if images_input else []

        # Konstrukcja obiektu posta
        post_obj = {
            "id": post_id,
            "post_url": post_url,
            "text": text,
            "date": post_date,
            "content_url": external_url if external_url else None,
            "author": author,
            "images": images,
            "timestamp": datetime.now().isoformat(),
            "manual_entry": True
        }

        posts.append(post_obj)
        print("Post dodany.")

        cont = input("\nCzy chcesz dodać kolejny post? [T/n]: ").lower().strip()
        if cont == 'n':
            break

    # Zapis do pliku
    data = {
        "name": profile_name,
        "url": profile_url,
        "scraped_at": datetime.now().isoformat(),
        "type": "manual_entry",
        "posts": posts
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("="*60)
    print(f"Zapisano {len(posts)} postów do pliku:")
    print(f"{output_path}")
    print("="*60)

if __name__ == "__main__":
    main()
