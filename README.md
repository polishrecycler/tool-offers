# Tool Offers — nowe firmy KRS

Aplikacja po polsku do wyszukiwania podmiotów po raz pierwszy zarejestrowanych w KRS
w wybranym dniu, z filtrem PKD, publicznym wyszukiwaniem kontaktów i eksportem XLSX/PDF.
Domyślna data to wczoraj w strefie `Europe/Warsaw`.

## Co jest gotowe, a co wymaga pierwszego testu

- Gotowe: ekran aplikacji, filtrowanie daty pierwszej rejestracji i PKD,
  wyszukiwanie kontaktów w publicznych wynikach RSS Bing, eksporty i interfejs do automatyzacji.
- Testy lokalne sprawdzają logikę na danych testowych oraz ekran i eksport przykładu.
- **Nie potwierdzono jeszcze integracji na żywo z KRS i Bing.** Obecne środowisko
  blokuje te domeny. Zapisano projekt ustawień dostępu do sieci; wymaga zastosowania.
  Po odblokowaniu trzeba wykonać rzeczywisty raport i potwierdzić bieżący kontrakt API,
  zakres godzin biuletynu i dostępność RSS. To warunek używania wyników operacyjnie.
- Nie skonfigurowano codziennego harmonogramu ani publicznego hostingu.
  Uruchomiony proces w środowisku deweloperskim nie jest stałą usługą.

## 1. Dostęp do internetu w środowisku Codex

W ustawieniach środowiska przejrzyj i zapisz przygotowane zmiany, następnie opublikuj
środowisko. Lista dozwolonych domen została rozszerzona o:

- `api-krs.ms.gov.pl` — oficjalne API KRS,
- `www.bing.com` — publiczne wyniki wyszukiwania,
- `www.gov.pl` — dostęp do oficjalnej dokumentacji.

Dotychczasowe zestawy domen menedżerów pakietów pozostają zachowane.
Zapis projektu ustawień sam w sobie nie zmienia dostępu działającej maszyny.
W tej wersji nie trzeba wpisywać klucza API ani hasła.

## 2. Uruchomienie

W terminalu środowiska Linux:

```bash
cd /workspace/tool-offers
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Biblioteki są już zainstalowane w bieżącym środowisku. Dostępność portu w przeglądarce
zależy od hostingu; sam panel konfiguracji środowiska Codex nie udostępnia podglądu WWW.
Możesz użyć interfejsu poleceń opisanego poniżej, aby uzyskać pliki bez przeglądarki.

Jeżeli uruchamiasz projekt na swoim komputerze z Windows, zainstaluj Python 3.12,
skopiuj folder projektu bez `.venv` i w terminalu w tym folderze wykonaj:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m streamlit run app.py --browser.gatherUsageStats false
```

Na własnym komputerze otwórz adres wyświetlony przez Streamlit. Na Windows system
może nie mieć bazy stref czasowych; zależność `tzdata` jest w pliku blokady.

## 3. Korzystanie z aplikacji

1. Zostaw wczorajszą datę lub wybierz wcześniejszy dzień.
2. Domyślne PKD to `37, 38, 39`: ścieki, odpady/odzysk, rekultywacja.
   Jeśli interesuje Cię również zaopatrzenie w wodę, dodaj dział `36`.
   Możesz podać szczegółowe kody, np. `38.11.Z`.
3. Opcjonalnie zaznacz „Tylko działalność przeważająca”. Bez tego aplikacja
   uwzględnia również pozostałe kody ujawnione w odpisie.
4. Kliknij „Pobierz firmy z KRS”. Sprawdzanie wszystkich odpisów z biuletynu
   może potrwać kilka minut. API ma ponawianie żądań po błędach 429/5xx.
5. Sprawdź status kompletności, błędy oraz źródła kontaktów.
6. Pobierz Excel lub PDF. Excel ma osobne arkusze informacji, błędów i źródeł.

Przycisk przykładu pokazuje wyłącznie **fikcyjne dane**, oznaczone także w eksportach.

## Raport bez przeglądarki

```bash
cd /workspace/tool-offers
# Rzeczywisty raport za wczoraj, z wyszukiwaniem kontaktów:
.venv/bin/python cli.py

# Sam KRS, bez internetu do kontaktów:
.venv/bin/python cli.py --no-web

# Konkretny dzień i tylko przeważające PKD:
.venv/bin/python cli.py --date 2026-10-27 --pkd 37,38,39 --main-only

# Test bez połączenia z API, dane fikcyjne:
.venv/bin/python cli.py --demo
```

Pliki JSON, XLSX i PDF trafiają do `reports/` z unikalnym czasem wykonania;
kolejne uruchomienia nie nadpisują poprzednich raportów.
Kody zakończenia: `0` — zakończone sprawdzanie lub jawne demo;
`1` — błąd uniemożliwiający raport; `2` — raport niepełny.

## Jak odróżniamy nową firmę od zmiany wpisu

1. Pobranie `GET /api/krs/Biuletyn/YYYY-MM-DD?godzinaOd=0&godzinaDo=23`.
2. Usunięcie powtarzających się numerów KRS.
3. Pobranie `GET /api/krs/OdpisAktualny/{KRS}?rejestr=P&format=json` dla kandydatów.
4. Porównanie **`naglowekA.dataRejestracjiWKRS`** z wybraną datą.
   Data ostatniego wpisu nie służy do kwalifikacji.
5. Dopasowanie PKD w `dzial3.przedmiotDzialalnosci`.

Pierwsza rejestracja w KRS nie musi być datą podpisania umowy spółki i może
dotyczyć podmiotu powstałego w wyniku przekształcenia. To raport nowych rejestracji
w KRS, a nie gwarantowana lista firm ekonomicznie powstałych tego dnia.
KRS nie obejmuje wszystkich przedsiębiorców — np. jednoosobowe działalności
rejestruje się w CEIDG.

Używany jest odpis **aktualny**, więc przy pobieraniu starszej daty PKD i kontakty
mogły zmienić się od pierwszej rejestracji. Działy 37–39 obejmują zarówno
odpowiednie kody PKD 2007, jak i PKD 2025, ale szczegółowe znaczenia kodów
trzeba oceniać według klasyfikacji podmiotu i opisu w odpisie.
Filtr obejmuje ten wybrany zakres działalności, nie wszystkie możliwe usługi
powiązane z ochroną środowiska, np. doradztwo środowiskowe wymaga osobnego zakresu.

Błąd pojedynczego odpisu jest widoczny w raporcie i oznacza niepełne wyniki.
Brak biuletynu, blokada sieci lub nieznany format nie są zamieniane w pustą listę
udającą prawidłowy raport. Wpisy, których nie uda się pobrać z rejestru P,
pozostają błędami do wyjaśnienia; nie zgadujemy ich daty lub rodzaju.

## Kontakty — zakres pierwszej wersji

- E-mail i WWW z KRS są pokazywane oddzielnie jako dane rejestrowe.
- W internecie aplikacja szuka nazwy wraz z NIP albo KRS w publicznych wynikach Bing RSS.
- Odczytuje e-maile i wyraźnie opisane telefony z **fragmentów wyników**;
  ta wersja nie przeszukuje całej zawartości witryn firm.
- Każdy wynik ma URL, fragment źródła i sposób dopasowania: NIP/KRS albo nazwa.
  Dopasowanie samej nazwy jest słabsze; wszystkie kontakty internetowe wymagają potwierdzenia.
- Świeżo zarejestrowana firma może jeszcze nie mieć strony lub nie być zaindeksowana.
  RSS wyszukiwarki może być niedostępny lub ograniczony. W takim przypadku
  aplikacja pokazuje błąd, a użytkownik może użyć przycisku wyszukiwania ręcznego.

## Codzienne wykonywanie — późniejszy krok

Najpierw należy potwierdzić prawdziwy raport. Potem na stale działającym serwerze
można uruchamiać `cli.py` codziennie o 08:00 w strefie Europe/Warsaw.
Przykład dla cron **z obsługą `CRON_TZ`** (nie dodano go automatycznie):

```cron
CRON_TZ=Europe/Warsaw
0 8 * * * cd /workspace/tool-offers && .venv/bin/python cli.py >> reports/daily.log 2>&1
```

Przed włączeniem utwórz `reports/`. Zwykła sesja Codex może zostać zatrzymana;
do niezawodnego harmonogramu potrzebny jest stały serwer lub usługa harmonogramu.

## Sprawdzenie kodu

```bash
.venv/bin/python -m pytest -q
```

Testy korzystają z jawnie testowych odpowiedzi; ich przejście nie potwierdza
działania zewnętrznego API. Font DejaVu z polskimi znakami i jego licencja
są w `assets/`.
