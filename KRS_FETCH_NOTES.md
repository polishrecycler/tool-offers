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

## Wersja 2026-10-29.5 — przypadek 0001272047 z 9 października

Ponownie odczytano biuletyn 09.10.2026: 3358 różnych numerów. Spółka
0001272047 znajduje się zarówno w nim, jak i w biuletynie 10.10.2026.
Hipoteza o braku jej numeru w biuletynie 9 października nie potwierdziła się.
W zapisanym odpisie ma datę rejestracji 09.10.2026 i kod 43.99.Z.
Minimalny wyciąg z rzeczywistej odpowiedzi, bez danych osób i adresów,
zapisano jako przypadek regresyjny w tests/fixtures.

Sprawdzono pozytywne dopasowanie przy 43.99.Z i wszystkich 728 kodach oraz
negatywne przy kodach odpadowych. Test od formularza przez zatwierdzenie do
pobrania i tabeli używa rzeczywistej funkcji collect i zapisanego odpisu.
Nie jest to test pobrania wszystkich 3358 odpisów.

Usunięto pułapkę interfejsu: po zmianie roboczych zaznaczeń przycisk pobierania
był aktywny i pozwalał pobrać raport ze starym, zatwierdzonym wcześniej filtrem.
Teraz wymaga zatwierdzenia lub odrzucenia roboczych zmian. Pasek pobierania
pokazuje datę i liczbę zatwierdzonych kodów. Podniesiono wersję odczytu,
aby nie korzystać z poprzednich wyników sesji. Nie potwierdzono bezpośrednio,
który stan filtrów spowodował zerowy wynik w sesji użytkownika.

## Wersja 2026-10-29.6 — pełna kontrola ścieżki odczytu

Nie odtworzono zerowego wyniku w środowisku wykonawczym na świeżych
odpowiedziach dla 0001272047 (09.10.2026), 0001275848 i 0001275317
(28.10.2026) oraz nowego stowarzyszenia 0001274785 (28.10.2026).
To nie potwierdza poprawności sesji działającej u użytkownika.

Każdy raport zapisuje teraz `audit`: numer, docelową datę, datę i rejestr
odczytane z odpowiedzi, surowe składowe kodów działalności, kwalifikację
oraz końcową decyzję. Przy żądaniach zapisujemy adres publicznego endpointu,
część rejestru, kod odpowiedzi serwera, typ i długość odpowiedzi lub typ
problemu połączenia. Nie zapisujemy nagłówków uwierzytelnienia ani danych
osób z pełnego odpisu. Biuletyn ma osobny zapis żądania.

`verify_number` jest wspólną ścieżką raportu i kontroli pojedynczego numeru.
Nieuzasadnione pominięcie numeru nie zwiększa licznika sprawdzonych:
raport pozostaje niepełny i zapisuje błąd zamiast pokazywać kompletny wynik zero.
Pozostawiono odrębne rozpoznawanie innej daty, innych kodów i braku weryfikacji.

W zwiniętym podsumowaniu można pobrać dane kontroli całego raportu, również
przy zerowej liczbie dopasowań. Dodatkowa zwinięta sekcja sprawdza pojedynczy
numer przy tej samej dacie i zatwierdzonych filtrach. Nie korzysta z biuletynu,
a jedynie z odpisu; jej wynik nie dowodzi obecności numeru w biuletynie.
Pozwala porównać odpowiedź i decyzję na hoście użytkownika bez pełnego skanu.

Sprawdzono trzy formaty dat, części rejestru P/S, brak aktualnego odpisu,
pełną historię, różne poziomy kodów, oddziały zagraniczne, brak kodów,
niepoprawne struktury danych, nieczytelną odpowiedź, odmowę dostępu,
problem czasu oczekiwania, stan filtrów i wyświetlenie wyników w interfejsie.
Nowa kontrola na świeżej odpowiedzi dla 0001272047 potwierdziła odpowiedź
200, typ application/json, datę 09.10.2026, kod 43.99.Z i decyzję included.
Nie sprawdzano witryny online, zgodnie z instrukcją użytkownika.

## Wersja 2026-10-29.7 — kolejność i czas pełnego raportu

Przyczyną utrzymującego się zera podczas długiego pobierania była kolejność.
Numery z biuletynu były sprawdzane rosnąco, chociaż nowe rejestracje skupiają
się przy najwyższych numerach KRS. Dla 28.10.2026 pierwszy z 267 nowych
podmiotów znajdował się dopiero na pozycji 2691 z 3200. Dla 09.10.2026
przykładowa spółka 0001272047 była na pozycji 3301 z 3358. Dodatkowe stałe
opóźnienie 0,2 sekundy na numer oznaczało ponad 11 minut oczekiwania jeszcze
przed doliczeniem czasu odpowiedzi serwera. Przerwanie albo błędy pod koniec
przebiegu dotykały więc właśnie nowych wpisów.

Numery są teraz sprawdzane od najwyższego, a odpisy pobierają trzy ograniczone
wątki z istniejącym ponawianiem błędów przejściowych. Usunięto stałe opóźnienie.
Na świeżych publicznych odpowiedziach dla pełnego dnia 28.10.2026 pierwsze
100 sprawdzeń dało 100 wyników, po 600 był komplet 267, a cały przebieg
zakończył się po około 255 sekundach: 3200 rozpatrzonych, 267 wyników
(245 przedsiębiorców i 22 stowarzyszenia), 0 błędów.

Dodano test kolejności i zachowania znalezionego wyniku przy późniejszym
błędzie oraz test równoległej ścieżki dla przedsiębiorcy, stowarzyszenia
i oddziału zagranicznego. Usunięto z interfejsu niezamówioną sekcję kontroli
pojedynczego numeru.
