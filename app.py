from pathlib import Path
from collections import Counter
import importlib

import streamlit as st
import core

# A source update must not retain an older imported parser in a running host.
if getattr(core, "PARSER_VERSION", None) != "2026-10-29.6":
    importlib.reload(core)

from contacts import enrich_contacts, search_url
from core import (DataError, PARSER_VERSION, collect, diagnostics_bytes, inspect_number,
                  normalize_pkd, save_report, yesterday)
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
st.title("Nowi przedsiębiorcy i stowarzyszenia")
st.write("Znajdź podmioty po raz pierwszy wpisane do rejestru przedsiębiorców lub stowarzyszeń w wybranym dniu. "
         "Sprawdź ich PKD, poszukaj kontaktów i pobierz listę.")

with st.sidebar:
    st.header("Ustawienia raportu")
    target = st.date_input("Data wpisu do rejestru przedsiębiorców lub stowarzyszeń",
                           value=yesterday(), max_value=yesterday())
    selected_pkd = pkd_picker()
    pending_pkd = set(st.session_state.get("draft_pkd", selected_pkd)) != set(selected_pkd)
    if pending_pkd:
        st.warning("Wybór kodów został zmieniony, ale nie jest zatwierdzony. "
                   "Kliknij „Zatwierdź” w menu kodów przed pobraniem raportu.")
    if not selected_pkd:
        st.caption("Wybierz co najmniej jeden kod, aby pobrać firmy.")
    web = st.checkbox("Szukaj kontaktów w internecie", value=True,
                      key="search_contacts",
                      help="Sprawdza publiczne wyniki wyszukiwania. Dane z fragmentów stron "
                           "wymagają potwierdzenia i nie zawsze są dostępne.")
    run = st.button("Pobierz firmy z KRS", type="primary", width="stretch", disabled=not selected_pkd or pending_pkd,
                    key="fetch_companies")
    st.caption("„Wczoraj” jest wyliczane według czasu w Polsce. "
               "Pobieranie odpisów dużej liczby firm może potrwać kilka minut.")
    st.caption(f"Wersja aplikacji: {PARSER_VERSION}")

st.info("Lista dotyczy pierwszej rejestracji w KRS. Późniejsze zmiany wpisów są odrzucane. "
        "Kody PKD i kontakty w KRS są odczytywane z odpisu aktualnego.")

if run and selected_pkd and not pending_pkd:
    st.session_state.pop("report", None)
    try:
        filters = tuple(selected_pkd)
        bar = st.progress(0.0, f"Pobieranie danych dla {target.isoformat()} — {len(filters)} zatwierdzonych kodów…")
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
if report and (getattr(report, "parser_version", None) != PARSER_VERSION
               or report.demo or report.main_only or report.target_date != target.isoformat()
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
    st.metric("Potwierdzone nowe podmioty dla wybranego zakresu", len(report.companies))
    qualification = getattr(report, "qualification", {})
    new_registrations = qualification.get("new_registrations", len(report.companies))
    st.caption(f"Nowe wpisy przedsiębiorców i stowarzyszeń w wybranym dniu, przed filtrem kodów: "
               f"{new_registrations}.")
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
        if new_registrations == 0:
            st.info(f"W biuletynie sprawdzono {report.candidates} numerów, ale nie potwierdzono "
                    f"pierwszej rejestracji przedsiębiorcy ani stowarzyszenia w dniu {report.target_date}. "
                    "Biuletyn obejmuje również zmiany istniejących podmiotów. "
                    "Zaznaczenie wszystkich kodów nie wyłącza warunku daty pierwszej rejestracji.")
        else:
            st.info(f"Potwierdzono {new_registrations} pierwszych rejestracji w tym dniu, "
                    "ale nie potwierdzono zgodności z wybranymi kodami działalności.")
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
        st.write(f"Inna data pierwszej rejestracji: {qualification.get('other_registration_date', 0)}. "
                 f"Wśród nowych wpisów stowarzyszenia: {qualification.get('new_associations', 0)}. "
                 f"Nowe firmy bez zgodności z wybranymi kodami: {qualification.get('other_pkd', 0)}.")
        st.caption("Biuletyn obejmuje także zmiany istniejących firm i wpisy stowarzyszeń. "
                   "Do wyników trafiają wyłącznie potwierdzone nowe rejestracje ze zgodnymi kodami. "
                   "Brak odpisu nie jest traktowany jako brak dopasowania.")
        st.caption(f"Wersja odczytu rejestru: {PARSER_VERSION}. "
                   "Wybór wszystkich kodów obejmuje również podmioty bez ujawnionych kodów.")
        reasons = Counter(error.partition(": ")[2] or error for error in report.errors)
        for reason, count in reasons.items():
            st.write(f"{count} przypadków: {reason}")
        st.download_button("Pobierz dane kontroli raportu", diagnostics_bytes(report),
                           file_name=f"kontrola-raportu-{report.target_date}.json",
                           mime="application/json", key="report_diagnostics")
else:
    st.write("Wybierz datę i branże po lewej, a następnie kliknij **Pobierz firmy z KRS**.")

with st.expander("Sprawdź pojedynczy numer w rejestrze", expanded=False):
    st.caption("Ta kontrola używa tej samej daty i zatwierdzonych kodów co raport, "
               "ale pobiera tylko wskazany odpis. Pozwala ustalić dokładną przyczynę pominięcia podmiotu.")
    check_number = st.text_input("Numer Krajowego Rejestru Sądowego", placeholder="Np. 0001272047",
                                 max_chars=10, key="inspect_krs", live=True)
    if st.button("Sprawdź ten numer", disabled=not check_number or not selected_pkd or pending_pkd,
                 key="inspect_krs_run"):
        st.session_state.pop("inspection", None)
        try:
            inspection = inspect_number(check_number, target, tuple(selected_pkd))
            st.session_state["inspection"] = inspection
        except DataError as exc:
            st.error(str(exc))
    inspection = st.session_state.get("inspection")
    if (inspection and inspection.parser_version == PARSER_VERSION
            and inspection.target_date == target.isoformat() and inspection.filters == list(selected_pkd)):
        decision = inspection.audit[0]
        st.write(f"Sprawdzany numer: {decision['krs']}. Data raportu: {inspection.target_date}.")
        st.write(f"Data pierwszej rejestracji odczytana z dokumentu: "
                 f"{decision.get('registration_date_raw', 'brak w aktualnym odpisie')}.")
        if inspection.companies:
            st.success("Podmiot spełnia ustawione warunki i powinien znaleźć się w raporcie, "
                       "jeśli jego numer znajduje się w biuletynie tego dnia.")
            st.dataframe(rows(inspection), hide_index=True, width="stretch")
        elif decision['decision'] == 'different_registration_date':
            st.info("Podmiot pominięto z powodu innej daty pierwszej rejestracji.")
        elif decision['decision'] == 'pkd_not_matched':
            st.info("Podmiot pominięto z powodu braku zgodności z zatwierdzonymi kodami działalności.")
        else:
            st.error("Nie udało się potwierdzić danych podmiotu. Szczegóły są w pliku kontroli.")
        st.download_button("Pobierz dane kontroli tego numeru", diagnostics_bytes(inspection),
                           file_name=f"kontrola-{decision['krs']}.json", mime="application/json",
                           key="inspection_diagnostics")
