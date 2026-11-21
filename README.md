# OLX PC Flipping Scanner

Projekt do wyszukiwania potencjalnie opłacalnych komputerów używanych i szacowania wartości ich podzespołów przy odsprzedaży osobno.

## Założenia

- Użytkownik definiuje frazy i filtry wyszukiwania.
- Dane ogłoszeń są dostarczane do programu z dopuszczonego źródła lub przez import pliku.
- Program analizuje tytuł, cenę, lokalizację, datę i pełny opis.
- Podzespoły są wyceniane na podstawie rzeczywistych, porównywalnych danych z OLX, z widoczną liczbą porównań i datą odświeżenia.
- Program oblicza konserwatywny przychód, koszty, potencjalny zysk, ROI i maksymalną cenę zakupu.
- Program nie traktuje ceny ofertowej jako potwierdzonej ceny transakcyjnej.
- Brak danych lub niepewna identyfikacja nie są zastępowane zgadywaną ceną.

## Status projektu

**Etap 1 — szkielet i format danych.**

Na tym etapie przygotowujemy import danych oraz kalkulator. Nie ma jeszcze modułu pobierającego ogłoszenia z OLX. Automatyczne pozyskiwanie i przetwarzanie cudzych ogłoszeń wymaga wcześniej ustalenia dozwolonego sposobu dostępu z OLX.

## Struktura

- `config.example.json` — przykładowe ustawienia wyszukiwań i kalkulacji.
- `data/listings.example.json` — przykładowy format importu (dane demonstracyjne).
- `src/olx_pc_flipping/analyzer.py` — kalkulator opłacalności.
- `scripts/analyze_import.py` — analiza pliku JSON z ofertami.
- `tests/` — testy jednostkowe.

## Uruchomienie lokalne (Windows)

Wymagany Python 3.11 lub nowszy.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py scripts/analyze_import.py data/listings.example.json --output reports/example-report.json
```

Kalkulator korzysta wyłącznie z biblioteki standardowej Pythona.

## Ważne

Plik przykładowy zawiera dane demonstracyjne, a nie aktualne oferty OLX ani aktualne wyceny rynkowe. Nie należy podejmować na ich podstawie decyzji zakupowych.
