# RUSSINT - Baza Danych OSINT

## Struktura Projektu

- **`data/`**: Główny katalog z danymi.
  - **`raw/`**: Surowe dane pobrane z sieci (HTML, JSON z API), nieprzetworzone.
  - **`processed/`**: Wyczyszczone i ustrukturyzowane pliki JSON gotowe do analizy.
  - **`evidence/`**: Dowody w formie plików (zrzuty ekranu, PDFy, raporty).
- **`src/`**: Kod źródłowy narzędzi.
  - **`collectors/`**: Skrypty do pobierania danych (scrapers, API clients).
  - **`analysis/`**: Skrypty do analizy powiązań i generowania raportów.
  - **`utils/`**: Funkcje pomocnicze.
- **`schemas/`**: Wzorce i schematy danych (np. JSON Schema).
- **`docs/`**: Dokumentacja projektu i notatki ze śledztw.

## Format Danych

Dane przechowywane są w formacie JSON. Główny schemat znajduje się w `schemas/example_entity.json`.
