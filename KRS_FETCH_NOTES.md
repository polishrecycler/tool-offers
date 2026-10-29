# Pobieranie i kwalifikacja wyników

## Przyczyny naprawione 29 października 2026 r.

Sprawdzono rzeczywiste odpowiedzi publicznego rejestru, w tym przykłady
ze zrzutu ekranu użytkownika. Dokumentacja źródła:
https://prs.ms.gov.pl/krs/openApi

1. Nagłówek odpisu przedsiębiorcy ma oznaczenie `RejP`, a nie tylko `P`.
   Poprzednie porównanie odrzucało poprawne nowe rejestracje. Teraz parser
   obsługuje `RejP` / `P` oraz `RejS` / `S`, sprawdzając również numer odpisu.
2. Biuletyn obejmuje przedsiębiorców i stowarzyszenia. Przykładowo
   0000002664 i 0000002667 nie mają odpisu w części P (odpowiedź 404),
   ale mają odpis w części S. To nie jest brak połączenia z serwerem.
3. Numery 0000005142 i 0000006864 zwracają 204, czyli odpowiedź bez treści
   dla odpisu aktualnego. Nie próbujemy odczytywać jej jak dokumentu JSON
   (formatu danych zwracanego przez rejestr). Odpis pełny pozwala potwierdzić
   starą rejestrację i wykluczyć podmiot z raportu nowych firm.
4. Pełna historia ma `naglowekP` i listę `wpis`. Do ustalenia pierwszej
   rejestracji używamy wpisu numer 1. Nie odczytujemy historycznych kodów jako
   aktualnych. Nowa firma bez aktualnego odpisu pozostaje nieweryfikowana,
   zamiast znikać jako rzekomo niezgodna z filtrami.
5. Rejestr zwraca kody na poziomie działu, grupy, klasy i podklasy, np.
   `33`, `93.1`, `38.11`, `38.11.Z`. Szeroki wpis nie przerywa sprawdzania
   dokładnych kodów. Sam dział lub grupa nie potwierdza wybranej podklasy.
6. Nieczytelne odpowiedzi są ponawiane maksymalnie trzykrotnie. Pozostałe
   błędy zachowują kod odpowiedzi serwera, zamiast sugerować zawsze brak
   dostępu do sieci. Odpowiedzi przejściowe i ograniczenia tempa są ponawiane
   przez klienta z opóźnieniem oraz uwzględnieniem wskazówek serwera.

## Co pokazuje aplikacja

Tabela, kontakty i eksportowane firmy obejmują wyłącznie podmioty:

- z potwierdzoną pierwszą rejestracją w wybranym dniu;
- z rejestru przedsiębiorców lub stowarzyszeń (od wersji 2026-10-29.4);
- ze zgodnym wybranym kodem w działalności przeważającej lub dodatkowej.

Nie wyświetlamy długiej listy niezweryfikowanych numerów jako wyników.
Podsumowanie techniczne jest zwinięte i pokazuje liczby oraz pogrupowane
przyczyny problemów, bez listy numerów. Błędy źródła nadal oznaczają raport
niepełny: brak potwierdzonych dopasowań nie oznacza wtedy braku nowych firm.
Przy zerowej liczbie dopasowań nie pokazujemy pustych eksportów ani kontaktów.

Zmiana daty lub wybranych kodów usuwa z widoku poprzedni raport. Użytkownik
musi uruchomić pobieranie dla nowych ustawień. Przycisk eksportu nie może
wtedy pobrać danych pasujących do poprzedniego wyboru.

Wyszukiwanie kontaktów to osobny etap. Jego niepowodzenie nie zmienia
potwierdzonej daty rejestracji i dopasowania kodów, dlatego problemy kontaktów
są przechowywane oddzielnie od błędów weryfikacji rejestru. Szczegóły błędów
pozostają w zapisanym raporcie i w diagnostycznej części eksportów.

## Weryfikacja na żywo

Ograniczona próba dziewięciu numerów, obejmująca przykłady powyżej,
nową zgodną firmę 0001275848 i nową niezgodną firmę 0001275898:
9 rozpatrzonych numerów, 1 zgodna firma, 0 błędów. Sprawdzono też eksport
do Excela i PDF (dokumentu do czytania i drukowania).

To nie jest potwierdzenie pobrania całego dziennego biuletynu ani gwarancja
stałej dostępności zewnętrznego serwera. Program nadal musi pobrać dane
nieznanych firm przed sprawdzeniem kodów; ta zmiana nie dodaje trwałej bazy
ani nie usuwa konieczności skanowania biuletynu.

## Weryfikacja pełnego biuletynu z 10 października 2026 r.

Sprawdzono wszystkie 321 różnych numerów (514 pozycji przed usunięciem
powtórzeń). Wynik: 319 przedsiębiorców z inną datą pierwszej rejestracji oraz
2 podmioty rejestru stowarzyszeń. Nie znaleziono pierwszej rejestracji
przedsiębiorcy z 10 października. Dla tego biuletynu wynik 0 pozostaje poprawny
także przy wszystkich wybranych kodach. Najpóźniejsza potwierdzona data
pierwszej rejestracji przedsiębiorcy w tej liście to 9 października.

Raport zapisuje teraz liczniki kwalifikacji: inna data, inna część rejestru,
nowe rejestracje przed filtrem działalności i brak dopasowania wybranych kodów.
Interfejs rozróżnia brak nowych rejestracji od braku dopasowania branży.
Liczniki trafiają również do eksportów.

Osobno poprawiono przypadek nowej firmy z wyłącznie szerokim wpisem działu,
grupy lub klasy. Przy wyborze wszystkich 728 kodów jest ona uwzględniana jako
dowolna branża; przy konkretnym kodzie nadal wymagamy potwierdzenia tej
podklasy. Brak jakichkolwiek kodów przy wyborze wszystkich branż oznacza
niezweryfikowane dane, a nie kompletny pusty wynik.

Sprawdzenie po zmianie: ponowne przetworzenie wszystkich 321 odpisów
zapisanych podczas badania na żywo odtworzyło wynik 319 + 2 bez błędów.
Kontrola dodatnia na rzeczywistym odpisie nowej firmy 0001275848 z 28 października
zwróciła jedną zgodną firmę przy wszystkich wybranych kodach.

## Wersja 2026-10-29.4 — przedsiębiorcy i stowarzyszenia

Zakres rozszerzono na obie części rejestru, zgodnie ze zmianą wymagań.
Data filtrowania pochodzi z `naglowekA.dataRejestracjiWKRS` odpisu właściwej
części (P lub S), nie z daty ostatniej zmiany. Potwierdzono tę datę na nowych
wpisach z 28.10.2026. Przy wszystkich branżach podmioty bez ujawnionych kodów
również trafiają do wyników; przy konkretnych kodach wymagane jest dopasowanie.

Obsłużono `danePodmiotuZagranicznego` i `siedzibaIAdresPodmiotuZagranicznego`.
Bez tego odpis nowego przedsiębiorcy 0001275317 kończył się błędem mimo
poprawnej daty. Eksport zawiera informację o części rejestru.

Pełna weryfikacja 3200 różnych numerów z biuletynu 28.10.2026: 245 nowych
przedsiębiorców i 22 nowe stowarzyszenia, razem 267 wyników; 2933 podmioty
z inną datą. Zweryfikowano również 218 przypadków bez aktualnego odpisu,
korzystając z pełnej historii. Końcowy raport ma 3200 rozpatrzonych numerów
bez błędów. Wynik odtworzono z zapisanych odpowiedzi, pokazano 267 wierszy
w interfejsie i sprawdzono oba eksporty.

W działającym hoście aktualizacja samego pliku aplikacji nie może pozostawić
starego zaimportowanego modułu odczytu. Aplikacja sprawdza numer wersji
parsera i w razie niezgodności przeładowuje moduł. Raporty utworzone przez
starszą wersję są usuwane z sesji. Numer wersji jest widoczny w lewym panelu.
To zabezpieczenie wdrożenia; nie ustalono bezpośrednio wersji modułu działającego
w sesji użytkownika, która wyświetliła zero.
