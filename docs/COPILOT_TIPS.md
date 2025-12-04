# Wskazówki do pracy z GitHub Copilot w RUSSINT

Aby ułatwić analizę postów przy użyciu GitHub Copilot, przygotowaliśmy kilka usprawnień.

## 1. Dashboard (Streamlit)

W aplikacji `post_viewer_app.py` dodaliśmy sekcję **"🤖 Copilot Context"**.
1. Uruchom aplikację: `streamlit run src/ui/post_viewer_app.py` (lub użyj Taska w VS Code).
2. Znajdź interesujący Cię post.
3. Rozwiń sekcję "🤖 Copilot Context" pod screenshotem.
4. Skopiuj gotowy tekst i wklej go do czatu Copilot.
5. Jeśli masz screenshot w schowku, wklej go również.

## 2. Skrypt w terminalu

Jeśli pracujesz bezpośrednio w VS Code i znasz ID posta lub fragment nazwy pliku:

1. Otwórz terminal.
2. Wpisz: `python scripts/get_context.py [szukana_fraza]`
   np. `python scripts/get_context.py post_123`
3. Skrypt wyświetli sformatowany JSON, który możesz skopiować do czatu.

## 3. VS Code Task

Dodaliśmy zadanie do łatwego uruchamiania Dashboardu.
1. Naciśnij `Ctrl+Shift+P`.
2. Wpisz `Tasks: Run Task`.
3. Wybierz `Run RUSSINT Dashboard`.

## Przykładowy Prompt dla Copilot

```markdown
Przeanalizuj ten obraz (screenshot posta).
Wykorzystaj poniższe metadane JSON, aby poprawnie zidentyfikować datę, autora i linki.
[WKLEJ JSON TUTAJ]

Zadanie:
1. Wyodrębnij wszystkie encje (Osoby, Organizacje, Wydarzenia).
2. Określ relacje między nimi.
3. Zwróć wynik w formacie JSON zgodnym z `schemas/analysis_output.json`.
```
