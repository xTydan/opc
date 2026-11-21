# OLX PC Flipping Scanner

Prywatny projekt do wyszukiwania potencjalnie opłacalnych komputerów używanych i szacowania wartości ich podzespołów przy odsprzedaży osobno.

## Aktualny status

**Gotowe:**
- Parser podzespołów z polskich opisów ogłoszeń.
- Importer otwartych baz benchmarków CPU/GPU/SSD/RAM z CSV/JSON, z obowiązkowym zachowaniem źródła, licencji, daty aktualizacji, liczby próbek i metodologii.
- Obsługa typowych literówek, łamania linii i nietypowych separatorów.
- Rozpoznawanie CPU, GPU, RAM, płyt głównych, dysków, zasilaczy, chłodzeń, obudów i wentylatorów.
- Zachowywanie fragmentu tekstu, który uzasadnia rozpoznanie.
- Kalkulator kosztów, potencjalnego zysku, ROI i maksymalnej ceny zakupu.
- Import zbiorczy JSON i CSV (separator przecinek lub średnik; polskie formaty cen).
- Konserwatywny silnik wyceny z podanych porównywalnych ogłoszeń OLX: dopasowanie dokładnego modelu lub podobieństwa specyfikacji (np. pojemność/interfejs SSD, generacja i pojemność RAM, wydajność GPU/CPU z wynikiem benchmarku), aktywny status, odczyt z ostatnich 24 godzin, minimum 5 porównań, filtrowanie wartości odstających i korekta bezpieczeństwa.
- Zabezpieczenie: zysk i ROI nie są wyświetlane, jeśli brakuje wyceny albo kluczowej kategorii sprzętu.
- Panel www w \`docs/\`, który importuje raport JSON, filtruje i sortuje oferty.
- Testy Pythona i kontrola składni JavaScript w GitHub Actions.
- Workflow publikacji panelu przez GitHub Pages.

**Jeszcze niegotowe:**
- Automatyczne pobieranie cudzych ogłoszeń OLX.
- Automatyczne pobieranie cen rynkowych z OLX lub innego polskiego marketplace.
- Automatyczne zbieranie porównywalnych ogłoszeń OLX; silnik wyceniania obsługuje już dopasowanie specyfikacji, ale potrzebuje danych porównawczych dostarczonych z dozwolonego źródła.
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

Workflow \`.github/workflows/pages.yml\` publikuje zawartość \`docs/\` po zmianach na gałęzi \`main\`. W ustawieniach repozytorium GitHub Pages musi być użyte źródło **GitHub Actions**. Dla tego repozytorium otwórz [Settings → Pages](https://github.com/xTydan/opc/settings/pages), a w sekcji **Build and deployment → Source** wybierz **GitHub Actions**. Integracja nie mogła utworzyć witryny Pages automatycznie, więc ten jednorazowy wybór musi wykonać właściciel repozytorium. Po zapisaniu ustawienia ponów workflow **Deploy dashboard** w zakładce Actions. Późniejsze zmiany w `docs/` będą publikowane automatycznie.

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

## Format porównywalnych ofert części

Silnik wyceniania przyjmuje porównania wewnątrz obiektu komponentu. Przykładowy rekord (wartości demonstracyjne):

```json
{
  "category": "gpu",
  "model": "ZOTAC RTX 3050 8GB",
  "comparables": [
    {
      "id": "demo-gpu-01",
      "marketplace": "olx",
      "model": "ZOTAC RTX 3050 8GB",
      "price": 550,
      "status": "active",
      "collected_at": "2026-11-21T11:00:00+00:00",
      "url": "https://www.olx.pl/d/oferta/demo"
    }
  ]
}
```

Każda oferta musi mieć kategorię, status aktywny, cenę PLN, czas odczytu z określoną strefą czasową i identyfikator lub URL. Można dopasować dokładny model albo podać specyfikacje w polach porównawczych. Przykładowo SSD może być porównany z inną marką, jeśli zgadzają się typ/interfejs i zbliżona pojemność. GPU/CPU wymagają porównywalnego wyniku benchmarku; sama nazwa rodziny lub liczba watów nie wystarcza. Zasilacze różnych marek wymagają niezależnej oceny jakości. Korekty cen między modelami są ograniczone, a wynik dopasowania specyfikacji nie otrzymuje najwyższego poziomu pewności. Domyślnie do wyceny potrzeba minimum 5 aktualnych porównań z OLX. Jeśli ich brakuje, program nie wymyśla ceny. W przypadku podania `comparables` ich wynik ma pierwszeństwo przed ręcznie wpisanym `estimated_sale_price`.

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


### Dopasowanie między różnymi modelami

Silnik nie wymaga tej samej marki dla każdej części. Dopasowuje porównania według parametrów ważnych dla danej kategorii. Przykładowe pola, które można umieścić bezpośrednio w rekordzie porównawczym:
- SSD: `capacity_gb`, `storage_type`, `interface`, opcjonalnie `performance_score`.
- RAM: `memory_type`, `capacity_gb`, opcjonalnie `speed_mhz`.
- CPU/GPU: `benchmark_score`; dla GPU dodatkowo `vram_gb`, dla CPU opcjonalnie `socket`.
- Płyta główna: `socket`, `memory_type`, `form_factor`, opcjonalnie `chipset_tier`.
- Zasilacz: `wattage` i niezależnie oceniony `quality_tier`.

Nieznane parametry nie są dopowiadane. Gdy nie ma wystarczających danych, silnik odrzuca porównanie lub pozostawia wycenę pustą. Korekta ceny przy dopasowaniu specyfikacji jest celowo ograniczona do 15% w górę lub w dół; to bezpiecznik, a nie model pełnej ekonomicznej wyceny. Wyniki benchmarków i oceny jakości muszą pochodzić z wiarygodnego, udokumentowanego źródła.


## Bezpłatne źródła danych sprzętowych

Projekt ma korzystać wyłącznie z bezpłatnych źródeł. Nie zakładamy, że darmowe źródło obejmuje wszystkie modele ani że można dowolnie kopiować każdą opublikowaną tabelę.

Kandydaci do zasilania katalogu:
- [TechPowerUp Hardware Databases](https://www.techpowerup.com/database-licensing/) — bezpłatne, ograniczone API bez klucza dla wybranych kart GPU, procesorów i SSD; pełna baza jest licencjonowana. Zakres bezpłatnego zbioru trzeba sprawdzać, a nie zakładać pełne pokrycie.
- [Open GPU Benchmarks](https://opengpubenchmarks.com/) — publiczne dane wyników GPU na licencji CC BY 4.0; przy wykorzystaniu wymagane jest przypisanie autorstwa i link do źródła.
- [FINALBENCH](https://finalbench.org/) — archiwum historycznych wyników CPU/GPU/SSD; przydatne jako pomocnicze źródło porównawcze, ale zakres dat i metodologie testów muszą być widoczne.

Importer `hardware_benchmarks.py` przyjmuje lokalne pliki CSV/JSON i wymaga jawnego pola `source`, `license` i `updated_at`. Nie pobiera samodzielnie danych z tych serwisów i nie obchodzi ich limitów. Przykładowy format znajduje się w `data/benchmarks.example.json`.

Ważne ograniczenie: benchmarki opisują wydajność, a nie wartość rynkową. Nie wolno przeliczać wyniku benchmarku bezpośrednio na złotówki. Służy on wyłącznie do wyboru sensownych odpowiedników; cena musi pochodzić z aktualnych ofert rynkowych.

## Bezpłatne źródła cen

Na dziś nie mamy potwierdzonego, bezpłatnego i dozwolonego API, które dostarczałoby komplet aktualnych ogłoszeń używanych części z OLX. Dlatego automatyczne wyceny cenowe pozostają nieukończone. Nie zastępujemy ich cenami nowych produktów ani fikcyjnymi wartościami. Kolejny etap wymaga znalezienia legalnego darmowego kanału cenowego albo importu porównywalnych ofert dostarczonych przez użytkownika.
