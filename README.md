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
- Pobieranie publicznych stron ogłoszeń OLX z listy linków podanej przez użytkownika (skrypt `fetch_olx_listings.py`); automatyczne wyszukiwanie nowych ogłoszeń nie jest częścią tego etapu.
- Automatyczne pobieranie cen rynkowych z OLX lub innego polskiego marketplace.
- Automatyczne zbieranie porównywalnych ogłoszeń OLX; silnik wyceniania obsługuje już dopasowanie specyfikacji, ale potrzebuje danych porównawczych dostarczonych z dozwolonego źródła.
- Trwała baza historii ofert i cen.
- Harmonogram cyklicznych skanów oraz alerty Telegram.

Pobieranie opisów działa przez zwykłe, sekwencyjne żądania HTTP do publicznych stron ogłoszeń, z domyślną przerwą 3 sekundy między stronami. Skrypt nie loguje się i nie omija CAPTCHA, blokad ani innych mechanizmów dostępu. OLX może odmówić dostępu (np. HTTP 403/429); wtedy zapisujemy status błędu zamiast obchodzić blokadę. Przed regularnym lub masowym użyciem należy sprawdzić aktualne warunki OLX i respektować ograniczenia serwisu.

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

### Automatyczne pobieranie opisów z listy linków OLX\n\n1. Wyszukaj komputery na OLX i skopiuj adresy interesujących ogłoszeń.\n2. Utwórz plik `olx-urls.txt`, wklejając jeden pełny link w każdym wierszu.\n3. Uruchom:\n\n```powershell\npy scripts/fetch_olx_listings.py olx-urls.txt --output data/imports/olx-listings.json\n```\n\nSkrypt kolejno pobiera publiczne strony przez HTTP i próbuje odczytać opis, tytuł, cenę oraz lokalizację z danych strukturalnych strony i metadanych. Wynik zapisuje w JSON zgodnym z importerem. Domyślna przerwa między żądaniami to 3 sekundy; można ją zwiększyć przez `--delay 5`.\n\nNastępnie uruchom analizę:\n\n```powershell\npy scripts/analyze_import.py data/imports/olx-listings.json --output reports/report.json\n```\n\nSprawdź pola `fetch_status`, `description_complete` i `fetch_error`. Przy HTTP 403, 429 lub stronie weryfikacyjnej skrypt nie omija zabezpieczeń — oznacza ogłoszenie jako niedostępne. Nie uruchamia wielu równoległych pobrań. Skrypt nie wyszukuje sam nowych ofert; listę linków wybierasz ręcznie.\n### Wygodniejszy tryb: rozszerzenie Chrome\n\nMożesz zbierać linki bez ręcznego kopiowania. W folderze `browser-extension/` znajduje się rozszerzenie Chrome/Chromium. Po jego instalacji otwierasz wyniki wyszukiwania OLX i klikasz ikonę rozszerzenia → **Zbierz i pobierz ogłoszenia**. Rozszerzenie odczytuje linki do ofert widoczne na aktualnej stronie wyników i wysyła je do lokalnego programu, który pobiera opisy sekwencyjnie.\n\n1. Uruchom lokalny serwer w folderze projektu: `py scripts/olx_local_server.py` (pozostaw okno otwarte).\n2. W Chrome otwórz `chrome://extensions`, włącz tryb programisty, wybierz **Załaduj rozpakowane** i wskaż folder `browser-extension/`.\n3. Otwórz wyniki wyszukiwania OLX i kliknij ikonę rozszerzenia.\n4. Wynik znajdziesz w `data/imports/olx-listings.json`; potem uruchom analizę jak wyżej.\n\nRozszerzenie zbiera linki tylko z aktualnie otwartej strony wyników. Aby objąć kolejną stronę paginacji, przejdź na nią i uruchom zbieranie ponownie. Nie klika automatycznie w każdą kartę — lokalny program pobiera strony ogłoszeń bezpośrednio, po jednej co 3 sekundy. Nie omija zabezpieczeń ani blokad OLX.\n### Analiza paczki ofert

Przygotuj plik JSON według struktury \`data/listings.example.json\`. Każdy rekord powinien zawierać przynajmniej cenę zakupu oraz opis lub listę podzespołów.

\`\`\`powershell
py scripts/analyze_import.py my-listings.json --output reports/report.json

# Opcjonalnie: dołącz lokalną bazę benchmarków z udokumentowaną licencją
py scripts/analyze_import.py my-listings.json --benchmarks data/my-benchmarks.json --output reports/report.json
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

Importer `hardware_benchmarks.py` przyjmuje lokalne pliki CSV/JSON i wymaga jawnego pola `source`, `license` i `updated_at`. W CSV te trzy metadane muszą być osobnymi kolumnami powtórzonymi identycznie w każdym wierszu, obok `category`, `model`, `benchmark` i `score`. Nie pobiera samodzielnie danych z tych serwisów i nie obchodzi ich limitów. Przykładowy format znajduje się w `data/benchmarks.example.json`.

Ważne ograniczenie: benchmarki opisują wydajność, a nie wartość rynkową. Nie wolno przeliczać wyniku benchmarku bezpośrednio na złotówki. Służy on wyłącznie do wyboru sensownych odpowiedników; cena musi pochodzić z aktualnych ofert rynkowych.

## Bezpłatne źródła cen

Na dziś nie mamy potwierdzonego, bezpłatnego i dozwolonego API, które dostarczałoby komplet aktualnych ogłoszeń używanych części z OLX. Dlatego automatyczne wyceny cenowe pozostają nieukończone. Nie zastępujemy ich cenami nowych produktów ani fikcyjnymi wartościami. Kolejny etap wymaga znalezienia legalnego darmowego kanału cenowego albo importu porównywalnych ofert dostarczonych przez użytkownika.


### Użycie benchmarków przy dopasowaniu CPU/GPU

Obsługa benchmarków jest już podłączona do analizatora. Przekaż plik przez `--benchmarks`, a w `config.json` ustaw identyfikator testu dla kategorii, np. `analysis.benchmark_names.gpu = "gpu_3dmark"`. Nazwa testu musi być taka sama dla docelowego podzespołu i ofert porównawczych — wyniki różnych metodologii nie są mieszane. Wynik jest dopisywany do komponentu i do raportu wraz ze źródłem, licencją, datą aktualizacji, liczbą próbek i linkiem. Dopasowanie między różnymi modelami CPU/GPU zostanie odrzucone, jeśli nie ma zgodnych wyników tego samego benchmarku. 

Przykład:
```powershell
py scripts/analyze_import.py my-listings.json --config config.json --benchmarks data/my-benchmarks.json --output reports/report.json
```

Ważne: przykładowe nazwy `cpu_mark`, `gpu_3dmark`, `storage_index`, `memory_index` w konfiguracji są tylko identyfikatorami oczekiwanych kolumn w Twoim zbiorze. Nie oznaczają, że dołączona przykładowa baza zawiera rzeczywiste lub kompletne wyniki. Dataset musi zawierać te same identyfikatory i rzeczywiste wyniki ze wskazanego źródła.


Przykładowy nagłówek CSV dla benchmarków:
```csv
source,license,updated_at,category,model,benchmark,score,samples,url
Open GPU Benchmarks,CC-BY-4.0,2026-11-20,gpu,NVIDIA GeForce RTX 3050 8GB,gaming_index,62.5,120,https://opengpubenchmarks.com/
```
Wartości powyżej są przykładowe i nie są prawdziwym wynikiem karty. Metadane źródła/licencji/datę powtarzaj w każdym wierszu.
