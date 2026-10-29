# Lista branż w formularzu

PKD oznacza Polską Klasyfikację Działalności. Katalog w `pkd_catalog.py`
zawiera 30 szczegółowych kodów PKD 2025. Każda etykieta wyboru ma postać
`kod — urzędowa nazwa podklasy`. Nazwy są przepisane z dokumentu źródłowego,
bez zastępowania ich własnymi opisami marketingowymi.

## Źródło

- Rozporządzenie Rady Ministrów z 18 grudnia 2024 r. w sprawie Polskiej
  Klasyfikacji Działalności, Dz.U. 2024 poz. 1936:
  https://eli.gov.pl/eli/DU/2024/1936/ogl
- Przeszukiwalny załącznik: wykaz, wyjaśnienia i klucze przejścia:
  https://eli.gov.pl/api/acts/DU/2024/1936/text/I/D20241936.pdf
- Data sprawdzenia nazw i zakresów: 29 października 2026 r.

## Dobór kodów

Uwzględniono gospodarkę odpadami, odzysk, recykling, baterie i akumulatory,
produkcję i obrót opakowaniami oraz ich przygotowanie do ponownego użycia.
Szersze kody są uwzględnione tam, gdzie urzędowe wyjaśnienia wprost wskazują
daną działalność. Nie oznacza to, że każda firma z takim kodem specjalizuje
się w odpadach, opakowaniach lub bateriach do samochodów elektrycznych.

| Kody | Uzasadnienie na podstawie wyjaśnień do podklas |
| --- | --- |
| 37.00.Z | Ścieki, opróżnianie i czyszczenie szamb, osadników i dołów gnilnych. |
| 38.11.Z, 38.12.Z | Zbieranie odpadów innych niż niebezpieczne oraz niebezpiecznych; obejmuje również zużyte baterie. |
| 38.21.Z | Odzysk surowców: sortowanie, przetwarzanie odpadów na surowce wtórne, demontaż, odzysk materiałów opakowaniowych, kompostowanie. |
| 38.22.Z, 38.23.Z | Odzysk energii oraz pozostały odzysk związany z odpadami. |
| 38.31.Z, 38.32.Z, 38.33.Z | Spalanie bez odzysku energii, składowanie i pozostałe unieszkodliwianie odpadów. |
| 39.00.Z | Rekultywacja i pozostałe usługi związane z gospodarką odpadami. |
| 46.87.Z | Hurtowy obrót odpadami i złomem. |
| 20.16.Z | Produkcja tworzyw w formach podstawowych, w tym granulatów i płatków z odzyskanych odpadów z tworzyw sztucznych. |
| 22.11.Z | Bieżnikowanie i regenerowanie opon; kod obejmuje również produkcję nowych opon. |
| 27.20.Z | Baterie i akumulatory, w tym litowe i do pojazdów; nie istnieje tu odrębna podklasa wyłącznie dla samochodów elektrycznych. |
| 33.14.Z | Naprawa i konserwacja baterii galwanicznych i akumulatorowych; również innych urządzeń elektrycznych. |
| 46.72.Z, 47.82.Z | Hurtowa i detaliczna sprzedaż części i akcesoriów samochodowych, obejmująca akumulatory; kody nie identyfikują wyłącznie sprzedawców baterii. |
| 16.24.Z | Opakowania drewniane, palety, beczki i podobne wyroby. |
| 16.28.Z | Między innymi korki do butelek i opakowania z materiałów do wyplatania. |
| 17.21.Z | Papier i tektura falista oraz opakowania papierowe i tekturowe. |
| 17.25.Z | Między innymi formowane i prasowane opakowania z masy celulozowej, w tym korytka do jajek. |
| 22.22.Z | Produkcja opakowań z tworzyw sztucznych. |
| 23.13.Z | Między innymi butelki i pozostałe pojemniki ze szkła. |
| 25.91.Z, 25.92.Z | Pojemniki metalowe i lekkie opakowania metalowe. |
| 25.99.Z | Między innymi worki z folii metalowej. |
| 33.19.Z | Między innymi naprawa worków, odnawianie palet drewnianych, bębnów transportowych i beczek. |
| 46.86.Z, 47.78.Z | Między innymi hurtowa sprzedaż artykułów do pakowania i detaliczna sprzedaż opakowań. |
| 82.92.Z | Pakowanie wykonywane na zlecenie. |

W wyjaśnieniach do działu 38 wprost wskazano także organizacje realizujące
obowiązki producentów w zakresie zagospodarowania odpadów, zwrotu, zbierania
i odzysku zużytych opakowań. Nie wymyślamy dla nich osobnego kodu.

Nie dodano ogólnych kodów transportu, doradztwa, badań ani całego przemysłu
wykorzystującego surowce wtórne. Samo świadczenie usług na rzecz branży nie
identyfikuje działalności odpadowej lub opakowaniowej. Zastosowanie wyłącznie
kodów nie zastępuje weryfikacji specjalizacji konkretnej firmy.

## Wyszukiwanie i wersje klasyfikacji

Domyślnie zaznaczone są podklasy działów 38 i 39 oraz 46.87.Z. Inne kody
można wyszukać po numerze lub urzędowej nazwie i zaznaczyć na liście wewnątrz
rozwijanego menu. Zamknięte pole pokazuje wyłącznie numery wybranych kodów.
Przycisk obok pola usuwa cały wybór, również kody ukryte przez wyszukiwanie.
Program sprawdza zarówno działalność przeważającą, jak i dodatkową. Pusty wybór
blokuje pobieranie zamiast uruchamiać nieograniczone wyszukiwanie.

Lista dotyczy PKD 2025, stosowanej do nowych rejestracji od 2025 r.
Załącznik zawiera także klucze przejścia z PKD 2007. Nie dodajemy starych
numerów jako bezwarunkowych zamienników: np. 38.21.Z miało inne znaczenie,
a hurt odpadami przeniesiono z 46.77.Z do 46.87.Z. Aktualny odpis pokazuje
bieżące kody firmy, więc raport nie odtwarza historycznego profilu działalności.

## Eksport

Przy tabeli wyników znajdują się oddzielne przyciski eksportu do Excela
oraz PDF, czyli dokumentu do czytania i drukowania o stałym układzie.
Oba obejmują cały wygenerowany raport, jego status i źródła kontaktów.
