import argparse
import json
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser(description="Przygotuj prompt dla LLM z danymi posta")
    parser.add_argument("json_path", help="Ścieżka do pliku JSON posta")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    if not json_path.exists():
        print(f"Błąd: Nie znaleziono pliku {json_path}")
        return

    # Ścieżki do plików konfiguracyjnych
    base_dir = Path(__file__).parent.parent.parent
    prompt_path = base_dir / "docs" / "LLM_ANALYSIS_PROMPT.md"
    schema_path = base_dir / "schemas" / "analysis_output.json"

    # Wczytaj dane
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
            
        with open(json_path, 'r', encoding='utf-8') as f:
            post_data = f.read()
            
        # Znajdź ścieżkę do obrazka (dla informacji użytkownika)
        post_json = json.loads(post_data)
        screenshot_name = post_json.get('screenshot')
        handle = post_json.get('handle')
        screenshot_info = ""
        if screenshot_name and handle:
            screenshot_path = base_dir / "data" / "evidence" / "facebook" / handle / screenshot_name
            if screenshot_path.exists():
                screenshot_info = f"\n[!!!] PAMIĘTAJ ABY ZAŁĄCZYĆ PLIK GRAFICZNY:\n{screenshot_path}\n"
            else:
                screenshot_info = f"\n[!] Nie znaleziono pliku screenshotu: {screenshot_path}\n"

    except Exception as e:
        print(f"Błąd podczas odczytu plików: {e}")
        return

    # Złóż wszystko w jeden prompt
    full_prompt = f"""
{screenshot_info}
--- SKOPIUJ PONIŻSZĄ TREŚĆ DO LLM (ChatGPT/Claude) ---

{system_prompt}

## FORMAT DANYCH WYJŚCIOWYCH (JSON SCHEMA)
```json
{schema}
```

## DANE DO ANALIZY (JSON)
```json
{post_data}
```

Przeanalizuj powyższy plik JSON oraz załączony zrzut ekranu zgodnie z instrukcją.
"""
    print(full_prompt)

if __name__ == "__main__":
    main()