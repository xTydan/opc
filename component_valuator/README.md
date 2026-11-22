# OLX Component Valuator

Druga, niezależna aplikacja do wyceny podzespołów na podstawie pliku JSON z pierwszego scrapera i aktualnych ofert części OLX.

## Uruchomienie w Windows
1. Uruchom start.bat (Python 3.11+).
2. Otwórz http://127.0.0.1:8766.
3. Zaimportuj olx-listings.json z pierwszej aplikacji.
4. Kliknij wyszukiwanie OLX przy danym komponencie.
5. W Chrome otwórz chrome://extensions, włącz tryb programisty i załaduj rozpakowany folder extension.
6. Na stronie wyników OLX kliknij rozszerzenie i Zbierz widoczne oferty. Powtórz dla kolejnych stron wyników.

## Ograniczenia pierwszej wersji
- Zbierane są wyłącznie widoczne karty bieżącej strony. Użytkownik otwiera wyszukiwanie i kolejne strony; rozszerzenie nie omija CAPTCHA, logowania, limitów ani blokad.
- Struktura OLX może się zmieniać, więc selektory kart mogą wymagać aktualizacji.
- Rozszerzenie klasyfikuje kategorię na podstawie frazy w adresie wyszukiwania. Jeśli nie rozpozna kategorii, nie zapisuje wyników.
- To wersja bazowa: parser tytułów i klasyfikacja odpowiedników wymagają dalszego rozszerzenia; nie każda karta z wyników będzie pasować do danego modelu.
- Minimum 5 dopasowanych ofert; przy mniejszej próbce nie pokazuje ceny.
- Są to ceny ofertowe, nie potwierdzone ceny transakcyjne.

## Metodologia
- RAM: ta sama generacja DDR i pojemność; taktowanie ±12%.
- Dyski: zgodny typ/interfejs i pojemność ±20%.
- CPU/GPU: modele różne można porównywać dopiero po dodaniu wyników tego samego benchmarku.
- Płyty główne: zgodny socket i rodzaj pamięci.
- Zasilacze: zbliżona moc; klasa jakości musi być rozpoznana osobno.
- Mediana po filtrze IQR; brak wystarczających danych oznacza brak ceny, nie zgadywanie.

Dane zbierane są z publicznie widocznych wyników OLX w przeglądarce. Należy przestrzegać warunków OLX i nie obchodzić mechanizmów ograniczających dostęp.
