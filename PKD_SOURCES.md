# Pełny katalog Polskiej Klasyfikacji Działalności 2025

## Zakres

Lista w formularzu obejmuje wszystkie **728 szczegółowych kodów (podklas)**
Polskiej Klasyfikacji Działalności 2025, ze wszystkich branż, nie tylko odpadowej.
Użytkownik wpisuje numer lub opis w wyszukiwarce rozwijanej listy i zaznacza
wybrane pozycje. Pierwszy checkbox „Zaznacz wszystkie” obejmuje cały katalog
728 kodów, także pozycje ukryte przez wyszukiwanie. Jego odznaczenie usuwa
całe robocze zaznaczenie. Przycisk „Zatwierdź” jest stale widoczny pod przewijaną
listą, stosuje wybór i zamyka menu. Zamknięcie menu bez zatwierdzenia odrzuca
robocze zmiany i zachowuje aktywny filtr.

Zamknięte pole pokazuje tylko numery kodów. Przy bardzo dużym wyborze pokazuje
pierwsze cztery numery oraz liczbę pozostałych, żeby nie rozciągać panelu przy
zaznaczeniu całego katalogu. Czerwony kosz obok
pola usuwa cały wybór, również pozycje ukryte przez wyszukiwanie.

Pozostawiono wcześniejsze domyślne zaznaczenia: podklasy działów 38 i 39 oraz
46.87.Z. Można je wyczyścić i wybrać dowolne inne kody z pełnego katalogu.
Pusty wybór blokuje pobieranie zamiast uruchamiać nieograniczone wyszukiwanie.

## Urzędowe źródło nazw

- Rozporządzenie Rady Ministrów z 18 grudnia 2024 r., Dz.U. 2024 poz. 1936:
  https://eli.gov.pl/eli/DU/2024/1936/ogl
- Załącznik: struktura klasyfikacji, wyjaśnienia oraz klucze przejścia:
  https://eli.gov.pl/api/acts/DU/2024/1936/text/I/D20241936.pdf
- Sprawdzenie kompletności i nazw: 29 października 2026 r.

Dane zapisano w `data/pkd_2025.json`, a aplikacja wczytuje je lokalnie przez
`pkd_catalog.py`. Wyświetlenie listy nie wymaga zapytania do zewnętrznego serwera.
Każda etykieta ma postać `kod — urzędowa nazwa podklasy`.

Nazwy odczytano z tabeli struktury klasyfikacji i porównano zbiór kodów
z nagłówkami podklas w części wyjaśniającej: oba wykazy zawierają te same 728
kodów. Wiersz 60.10.Z ma nazwę pod numerem kodu, a wyraz
„geologiczno-inżynierskich” w 43.13.Z jest przełamany w źródle między wierszami;
te przypadki uwzględniono przy odczycie. Zachowano wszystkie wcześniej
zweryfikowane nazwy 30 kodów. Nie dodano tekstu objaśnień do samych nazw.

## Zasady dopasowania

Program sprawdza działalność przeważającą i dodatkową. Każdy wynik wymaga
potwierdzenia daty pierwszej rejestracji w wybranym dniu i zgodności kodu.
Sam szeroki wpis działu, grupy lub klasy nie dowodzi zgodności z konkretną
wybraną podklasą. Niektóre podklasy obejmują różne specjalizacje, dlatego kod
nie zastępuje oceny rzeczywistej działalności firmy.

Lista dotyczy wersji 2025, stosowanej do nowych rejestracji od 2025 r.
Nie mieszamy jej bezwarunkowo z wersją 2007, w której niektóre numery oznaczały
inne działalności. Aktualny odpis przedstawia bieżące kody firmy, a nie
historyczny profil działalności w dniu pierwszej rejestracji.

## Wyniki, eksport i sekcje dodatkowe

Oddzielne przyciski pobierają dopasowane firmy do Excela oraz PDF, czyli
dokumentu do czytania i drukowania o stałym układzie. Sekcje kontaktów i
podsumowania pobierania są domyślnie zwinięte. Nie pokazujemy długiej listy
niezweryfikowanych numerów jako wyników. Szczegóły działania pobierania
opisuje `KRS_FETCH_NOTES.md`.
