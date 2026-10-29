from pathlib import Path
from collections import Counter

import streamlit as st

from contacts import enrich_contacts, search_url
from core import DataError, collect, normalize_pkd, save_report, yesterday
from exports import pdf_bytes, rows, status, xlsx_bytes
from pkd_picker import pkd_picker

ROOT = Path(__file__).parent
st.set_page_config(page_title="Tool Offers — nowe firmy KRS", page_icon="♻️", layout="wide")
st.html("""
<style>
@media (min-width: 900px) {
    section[data-testid="stSidebar"] { width: 480px !important; }
}
.st-key-pkd_picker button p {
    text-align: left;
    overflow-wrap: anywhere;
    font-variant-numeric: tabular-nums;
}
.st-key-clear_pkd button {
    color: #b42318;
    border-color: #f2b8b5;
    background-color: #fff5f5;
}
.st-key-clear_pkd button:hover:not(:disabled) {
    color: #912018;
    border-color: #d92d20;
    background-color: #fee4e2;
}
.st-key-clear_pkd button:focus-visible {
    outline: 2px solid #d92d20;
    outline-offset: 2px;
}
.st-key-pkd_footer {
    position: sticky;
    bottom: 0;
    z-index: 2;
    background: var(--st-secondary-background-color, #f0f2f6);
    border-top: 1px solid rgba(128, 128, 128, 0.2);
    padding-top: 8px;
    flex-shrink: 0;
}
</style>
""")
st.title("♻️ Nowe firmy: środowisko i odpady")
st.write("Znajdź firmy po raz pierwszy zarejestrowane w KRS w wybranym dniu. "
         "Sprawdź ich PKD, poszukaj kontaktów i pobierz listę.")

with st.sidebar:
    st.header("Ustawienia raportu")
    target = st.date_input("Data pierwszej rejestracji w KRS", value=yesterday(), max_value=yesterday())
    selected_pkd = pkd_picker()
    if not selected_pkd:
        st.caption("Wybierz co najmniej jeden kod, aby pobrać firmy.")
    web = st.checkbox("Szukaj kontaktów w internecie", value=True,
                      key="search_contacts",
                      help="Sprawdza publiczne wyniki wyszukiwania. Dane z fragmentów stron "
                           "wymagają potwierdzenia i nie zawsze są dostępne.")
    run = st.button("Pobierz firmy z KRS", type="primary", width="stretch", disabled=not selected_pkd,
                    key="fetch_companies")
    st.caption("„Wczoraj” jest wyliczane według czasu w Polsce. "
               "Pobieranie odpisów dużej liczby firm może potrwać kilka minut.")

st.info("Lista dotyczy pierwszej rejestracji w KRS. Późniejsze zmiany wpisów są odrzucane. "
        "Kody PKD i kontakty w KRS są odczytywane z odpisu aktualnego.")

if run and selected_pkd:
    st.session_state.pop("report", None)
    try:
        filters = tuple(selected_pkd)
        bar = st.progress(0.0, "Łączenie z KRS…")
        def update(done, total, message):
            bar.progress(done / total if total else 0.0, message)
        report = collect(target, filters, main_only=False,
                         enrich=enrich_contacts if web else None, progress=update)
        save_report(report, ROOT / "reports")
        st.session_state["report"] = report
    except DataError as exc:
        st.error(str(exc))
        st.warning("Nie utworzono raportu. Nie oznacza to braku nowych firm. "
                   "Spróbuj ponownie; przyczyna problemu jest opisana powyżej.")
    except OSError:
        st.error("Nie udało się zapisać raportu. Sprawdź dostępne miejsce i prawa zapisu w folderze reports.")
    finally:
        bar.empty()

report = st.session_state.get("report")
# Never present a previous query's rows as matches for the current controls.
if report and (report.demo or report.main_only or report.target_date != target.isoformat()
               or {normalize_pkd(code) for code in report.filters}
               != {normalize_pkd(code) for code in selected_pkd}):
    st.session_state.pop("report", None)
    report = None
if report:
    st.subheader(f"Raport: {report.target_date}")
    if not report.complete:
        st.warning(status(report))
    else:
        st.success(status(report))
    st.metric("Potwierdzone firmy zgodne z wybranymi kodami", len(report.companies))
    filter_summary = (", ".join(report.filters) if len(report.filters) <= 20
                      else f"{len(report.filters)} wybranych kodów")
    st.caption(f"PKD: {filter_summary} · "
               f"Działalność przeważająca i dodatkowa · "
               f"Wygenerowano: {report.generated_at}")
    records = rows(report)
    if records:
        st.dataframe(records, hide_index=True, width="stretch")
        st.write("**Eksport dopasowanych firm**")
        left, right = st.columns(2)
        left.download_button("Eksport do Excela (.xlsx)", xlsx_bytes(report),
                             file_name=f"firmy-krs-{report.target_date}.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             width="stretch")
        right.download_button("Eksport do PDF", pdf_bytes(report),
                              file_name=f"firmy-krs-{report.target_date}.pdf",
                              mime="application/pdf", width="stretch")
        with st.expander("Kontakty i źródła dopasowanych firm", expanded=False):
            st.write("Adresy e-mail i WWW z KRS są danymi ujawnionymi w rejestrze. "
                     "Kontakty z internetu wymagają potwierdzenia. Brak kontaktu nie oznacza, że firma go nie ma.")
            for company in report.companies:
                st.write(f"**{company.name}** — KRS {company.krs}")
                st.link_button("Sprawdź wyniki wyszukiwania", search_url(company))
                st.write(company.contact_status)
                for source in company.sources:
                    st.write({"Źródło": source["url"], "Dopasowanie": source["match"],
                              "Fragment": source["snippet"]})
    elif report.complete:
        st.info("Nie znaleziono nowych firm z wybranymi kodami w tym dniu.")
    else:
        st.warning("Nie potwierdzono dotąd żadnej zgodnej firmy. Ponieważ część danych jest "
                   "niedostępna, nie można uznać tego za pełny wynik wyszukiwania.")
    if report.contact_errors:
        st.caption(f"Nie udało się uzupełnić kontaktów dla {len(report.contact_errors)} dopasowanych firm. "
                   "Nie wpływa to na potwierdzenie ich daty rejestracji i kodów działalności.")
    with st.expander("Podsumowanie pobierania", expanded=False):
        st.write(f"Numery firm w dziennym biuletynie: {report.candidates}. "
                 f"Rozpatrzone: {report.checked}. "
                 f"Nieweryfikowane z powodu problemów pobierania: {report.candidates - report.checked}.")
        st.caption("Biuletyn obejmuje także zmiany istniejących firm i wpisy stowarzyszeń. "
                   "Do wyników trafiają wyłącznie potwierdzone nowe rejestracje ze zgodnymi kodami. "
                   "Brak odpisu nie jest traktowany jako brak dopasowania.")
        reasons = Counter(error.partition(": ")[2] or error for error in report.errors)
        for reason, count in reasons.items():
            st.write(f"{count} przypadków: {reason}")
else:
    st.write("Wybierz datę i branże po lewej, a następnie kliknij **Pobierz firmy z KRS**.")
