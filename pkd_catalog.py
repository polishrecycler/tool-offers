"""Curated PKD 2025 subclasses. Official titles, not invented sector labels.

Source and selection boundaries: PKD_SOURCES.md.
"""

PKD_SOURCE_URL = "https://eli.gov.pl/eli/DU/2024/1936/ogl"

PKD_OPTIONS = {
    "16.24.Z": "Produkcja opakowań drewnianych",
    "16.28.Z": "Produkcja pozostałych wyrobów z drewna oraz wyrobów z korka, słomy i materiałów używanych do wyplatania",
    "17.21.Z": "Produkcja papieru falistego, tektury falistej oraz opakowań z papieru i tektury",
    "17.25.Z": "Produkcja pozostałych wyrobów z papieru i tektury",
    "20.16.Z": "Produkcja tworzyw sztucznych w formach podstawowych",
    "22.11.Z": "Produkcja, bieżnikowanie i regenerowanie opon z gumy oraz produkcja dętek",
    "22.22.Z": "Produkcja opakowań z tworzyw sztucznych",
    "23.13.Z": "Produkcja szkła gospodarczego",
    "25.91.Z": "Produkcja pojemników metalowych",
    "25.92.Z": "Produkcja lekkich opakowań metalowych",
    "25.99.Z": "Produkcja pozostałych gotowych wyrobów metalowych, gdzie indziej niesklasyfikowana",
    "27.20.Z": "Produkcja baterii i akumulatorów",
    "33.14.Z": "Naprawa i konserwacja urządzeń elektrycznych",
    "33.19.Z": "Naprawa i konserwacja pozostałego sprzętu i wyposażenia",
    "37.00.Z": "Odprowadzanie i oczyszczanie ścieków",
    "38.11.Z": "Zbieranie odpadów innych niż niebezpieczne",
    "38.12.Z": "Zbieranie odpadów niebezpiecznych",
    "38.21.Z": "Odzysk surowców",
    "38.22.Z": "Odzysk energii",
    "38.23.Z": "Pozostały odzysk związany z odpadami",
    "38.31.Z": "Spalanie odpadów bez odzysku energii",
    "38.32.Z": "Składowanie odpadów",
    "38.33.Z": "Pozostałe unieszkodliwianie odpadów",
    "39.00.Z": "Działalność związana z rekultywacją i pozostała działalność usługowa związana z gospodarką odpadami",
    "46.72.Z": "Sprzedaż hurtowa części i akcesoriów do pojazdów silnikowych, z wyłączeniem motocykli",
    "46.86.Z": "Sprzedaż hurtowa pozostałych półproduktów",
    "46.87.Z": "Sprzedaż hurtowa odpadów i złomu",
    "47.78.Z": "Sprzedaż detaliczna pozostałych nowych wyrobów",
    "47.82.Z": "Sprzedaż detaliczna części i akcesoriów do pojazdów silnikowych, z wyłączeniem motocykli",
    "82.92.Z": "Działalność związana z pakowaniem",
}

# Select the core waste sector by default; related industries remain searchable.
DEFAULT_SELECTED_PKD = tuple(
    code for code in PKD_OPTIONS if code.startswith(("38.", "39.")) or code == "46.87.Z"
)


def pkd_label(code: str) -> str:
    return f"{code} — {PKD_OPTIONS[code]}"
