# OLX Component Valuator

Druga, niezależna aplikacja do wyceny podzespołów na podstawie pliku JSON z pierwszego scrapera i aktualnych ofert części OLX.

## Uruchomienie w Windows
1. Uruchom start.bat (Python 3.11+).
2. Otwórz http://127.0.0.1:8766.
3. Zaimportuj olx-listings.json z pierwszej aplikacji.
4. W Chrome otwórz chrome://extensions, włącz tryb programisty i załaduj rozpakowany folder `component_valuator/extension`.
5. Kliknij ikonę rozszerzenia i wybierz „Uruchom automatyczne zbieranie”. Rozszerzenie przejdzie kolejno przez wyszukiwania z kolejki i pobierze widoczne karty z pierwszej strony każdego wyszukiwania.
6. Postęp i wynik sprawdzisz na pulpicie aplikacji. Nie musisz otwierać każdego wyszukiwania ręcznie.

## Ograniczenia pierwszej wersji
- Rozszerzenie automatyzuje kolejno wyszukiwania, ale w tej wersji zbiera tylko widoczne karty z pierwszej strony każdego wyszukiwania. Nie omija CAPTCHA, logowania, limitów ani blokad.
- Struktura OLX może się zmieniać, więc selektory kart mogą wymagać aktualizacji.
- Kategoria jest przekazywana z kolejki aplikacji, więc nie zależy od heurystycznego rozpoznawania frazy URL.
- To wersja bazowa: parser tytułów i klasyfikacja odpowiedników wymagają dalszego rozszerzenia; nie każda karta z wyników będzie pasować do danego modelu.
- Minimum 5 dopasowanych ofert; przy mniejszej próbce nie pokazuje ceny.
- Są to ceny ofertowe, nie potwierdzone ceny transakcyjne.

## Metodologia
- RAM: ta sama generacja DDR i pojemność; taktowanie ±12%.
- Dyski: zgodny typ/interfejs i pojemność ±20%.
- CPU/GPU: dokładny model można porównać bez benchmarku; modele zastępcze wymagają zgodnych wyników tego samego benchmarku.
- Płyty główne: zgodny socket i rodzaj pamięci.
- Zasilacze: zbliżona moc; klasa jakości musi być rozpoznana osobno.
- Mediana po filtrze IQR; brak wystarczających danych oznacza brak ceny, nie zgadywanie.

Dane zbierane są z publicznie widocznych wyników OLX w przeglądarce. Należy przestrzegać warunków OLX i nie obchodzić mechanizmów ograniczających dostęp.
