# OLX PC Flipping Scanner

Prywatny projekt do wyszukiwania potencjalnie opłacalnych komputerów używanych i szacowania wartości ich podzespołów przy odsprzedaży osobno.

## Aktualny status

**Gotowe:**
- Parser podzespołów z polskich opisów ogłoszeń.
- Obsługa typowych literówek, łamania linii i nietypowych separatorów.
- Rozpoznawanie CPU, GPU, RAM, płyt głównych, dysków, zasilaczy, chłodzeń, obudów i wentylatorów.
- Zachowywanie fragmentu tekstu, który uzasadnia rozpoznanie.
- Kalkulator kosztów, potencjalnego zysku, ROI i maksymalnej ceny zakupu.
- Zabezpieczenie: zysk i ROI nie są wyświetlane, jeśli brakuje wyceny albo kluczowej kategorii sprzętu.
- Panel www w \`docs/\`, który importuje raport JSON, filtruje i sortuje oferty.
- Testy Pythona i kontrola składni JavaScript w GitHub Actions.
- Workflow publikacji panelu przez GitHub Pages.

**Jeszcze niegotowe:**
- Automatyczne pobieranie cudzych ogłoszeń OLX.
- Automatyczne porównywanie cen części na OLX.
- Trwała baza historii ofert i cen.
- Harmonogram cyklicznych skanów oraz alerty Telegram.

Automatyczne pobieranie i przetwarzanie cudzych treści OLX wymaga ustalenia dozwolonego sposobu dostępu z OLX. Obecny projekt nie obchodzi zabezpieczeń serwisu i nie wykonuje scraperów. Architektura importu jest przygotowana tak, aby można było później podłączyć zatwierdzone źródło danych.

## Struktura projektu

- \`config.example.json\` — przykładowe frazy i ustawienia kalkulatora.
- \`data/listings.example.json\` — przykładowy import (wartości demonstracyjne, nie aktualny rynek).
- \`src/olx_pc_flipping/component_parser.py\` — parser podzespołów.
- \`src/olx_pc_flipping/analyzer.py\` — kalkulator opłacalności.
- \`scripts/parse_description.py\` — parser pojedynczego pliku TXT.
- \`scripts/analyze_import.py\` — analiza paczki ogłoszeń JSON.
- \`docs/\` — statyczny panel wyników.
- \`tests/\` — testy jednostkowe.

## Uruchomienie lokalne (Windows)

Wymagany Python 3.11 lub nowszy. Kalkulator korzysta z biblioteki standardowej Pythona; nie trzeba instalować dodatkowych paczek.

W PowerShell, po pobraniu repozytorium:

\`\`\`powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
\`\`\`

### Test parsera na opisie tekstowym

Zapisz opis komputera do pliku, np. \`my-description.txt\`, a następnie:

\`\`\`powershell
py scripts/parse_description.py my-description.txt --output parsed-components.json
\`\`\`

### Analiza paczki ofert

Przygotuj plik JSON według struktury \`data/listings.example.json\`. Każdy rekord powinien zawierać przynajmniej cenę zakupu oraz opis lub listę podzespołów.

\`\`\`powershell
py scripts/analyze_import.py my-listings.json --output reports/report.json
\`\`\`

Otwórz \`docs/index.html\` w przeglądarce i wczytaj \`reports/report.json\`.

### Publikacja panelu na GitHub Pages

Workflow \`.github/workflows/pages.yml\` publikuje zawartość \`docs/\` po zmianach na gałęzi \`main\`. W ustawieniach repozytorium GitHub Pages musi być użyte źródło **GitHub Actions**. Po udanym wdrożeniu strona będzie dostępna pod adresem GitHub Pages repozytorium.

## Format importu

Główny format to JSON:

\`\`\`json
{
  "schema_version": 1,
  "source": "manual",
  "exported_at": "2026-11-21T12:00:00+01:00",
  "listings": [
    {
      "id": "listing-001",
      "title": "Komputer gamingowy",
      "url": "https://www.olx.pl/d/oferta/...",
      "price": 1500,
      "currency": "PLN",
      "location": "Bielsko-Biała",
      "date_added": null,
      "collected_at": "2026-11-21T12:00:00+01:00",
      "status": "unverified",
      "description": "Pełny opis podzespołów..."
    }
  ]
}
\`\`\`

Nie wpisuj tekstu typu \`1 500 zł\` w pole \`price\`; użyj liczby \`1500\`. Nie dodawaj do publicznego repozytorium prywatnych danych sprzedawców ani niepublikowanych eksportów.

## Zasady wyceny

- Ceny ofertowe nie są potwierdzonymi cenami sprzedaży.
- Nieznany model nie otrzymuje ceny na podstawie zgadywania.
- Wycena powinna mieć datę aktualizacji, liczbę porównywalnych ofert i poziom pewności.
- Brak kluczowego podzespołu lub jego wyceny powoduje status niekompletnej analizy; program nie pokazuje wtedy zysku ani ROI.
- Zasilacz nie jest uznawany za jakościowy wyłącznie na podstawie oznaczenia 80 PLUS.
- Wartości w plikach \`*.example.json\` są demonstracyjne.

## Testy

GitHub Actions uruchamia:

\`\`\`powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
node --check docs/app.js
\`\`\`
