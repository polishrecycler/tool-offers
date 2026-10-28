from pathlib import Path

import streamlit as st

from contacts import enrich_contacts, search_url
from core import DataError, collect, pkd_filters, save_report, yesterday
from demo import demo_report
from exports import pdf_bytes, rows, status, xlsx_bytes

ROOT = Path(__file__).parent
st.set_page_config(page_title="Tool Offers — nowe firmy KRS", page_icon="♻️", layout="wide")
st.title("♻️ Nowe firmy: środowisko i odpady")
st.write("Znajdź firmy po raz pierwszy zarejestrowane w KRS w wybranym dniu. "
         "Sprawdź ich PKD, poszukaj kontaktów i pobierz listę.")

with st.sidebar:
    st.header("Ustawienia raportu")
    target = st.date_input("Data pierwszej rejestracji w KRS", value=yesterday(), max_value=yesterday())
    pkd_text = st.text_input("Działy lub kody PKD", "37, 38, 39",
                             help="37: ścieki; 38: odpady i odzysk; 39: rekultywacja. "
                                  "Możesz dodać 36 (woda) lub podać pełne kody, np. 38.11.Z. "
                                  "Działy obejmują kody PKD 2007 i 2025; ich opisy mogą się różnić.")
    main_only = st.checkbox("Tylko działalność przeważająca", value=False)
    web = st.checkbox("Szukaj kontaktów w internecie", value=True,
                      help="Sprawdza publiczne wyniki wyszukiwania. Dane z fragmentów stron "
                           "wymagają potwierdzenia i nie zawsze są dostępne.")
    run = st.button("Pobierz firmy z KRS", type="primary", width="stretch")
    demo = st.button("Zobacz przykład na fikcyjnych danych", width="stretch")
    st.caption("„Wczoraj” jest wyliczane według czasu w Polsce. "
               "Pobieranie odpisów dużej liczby firm może potrwać kilka minut.")

st.info("Lista dotyczy pierwszej rejestracji w KRS. Późniejsze zmiany wpisów są odrzucane. "
        "Kody PKD i kontakty w KRS są odczytywane z odpisu aktualnego.")

if demo:
    st.session_state["report"] = demo_report(target)
if run:
    st.session_state.pop("report", None)
    try:
        filters = pkd_filters(pkd_text)
        bar = st.progress(0.0, "Łączenie z KRS…")
        def update(done, total, message):
            bar.progress(done / total if total else 0.0, message)
        report = collect(target, filters, main_only, enrich_contacts if web else None, update)
        save_report(report, ROOT / "reports")
        st.session_state["report"] = report
        bar.empty()
    except DataError as exc:
        st.error(str(exc))
        st.warning("Nie utworzono raportu. Nie oznacza to braku nowych firm. "
                   "Jeżeli to pierwsze uruchomienie, sprawdź w ustawieniach środowiska "
                   "dostęp do api-krs.ms.gov.pl i www.bing.com.")
    except OSError:
        st.error("Nie udało się zapisać raportu. Sprawdź dostępne miejsce i prawa zapisu w folderze reports.")

report = st.session_state.get("report")
if report:
    st.subheader(f"Raport: {report.target_date}")
    if report.demo:
        st.warning("DEMO — poniższe firmy i dane kontaktowe są fikcyjne.")
    elif not report.complete:
        st.warning(status(report))
    else:
        st.success(status(report))
    a, b, c = st.columns(3)
    a.metric("Wpisy z biuletynu", report.candidates)
    b.metric("Sprawdzone odpisy", report.checked)
    c.metric("Firmy pasujące do PKD", len(report.companies))
    st.caption(f"PKD: {', '.join(report.filters)} · "
               f"{'Tylko przeważające' if report.main_only else 'Wszystkie ujawnione kody'} · "
               f"Wygenerowano: {report.generated_at}")
    records = rows(report)
    if records:
        st.dataframe(records, hide_index=True, width="stretch")
    else:
        st.write("Brak firm spełniających kryteria w sprawdzonych odpisach. "
                 "Przed wyciągnięciem wniosków sprawdź kompletność raportu.")
    with st.expander("Kontakty i źródła"):
        st.write("Adresy e-mail i WWW z KRS są danymi ujawnionymi w rejestrze. "
                 "Kontakty z internetu pochodzą z fragmentów wyników wyszukiwania. "
                 "Sprawdź, czy strona należy do właściwej firmy; brak kontaktu nie oznacza, że firma go nie ma.")
        for company in report.companies:
            st.write(f"**{company.name}** — KRS {company.krs}")
            if not report.demo:
                st.link_button("Sprawdź wyniki wyszukiwania", search_url(company))
            st.write(company.contact_status)
            for source in company.sources:
                st.write({"Źródło": source["url"], "Dopasowanie": source["match"],
                          "Fragment": source["snippet"]})
    if report.errors:
        with st.expander(f"Błędy do sprawdzenia ({len(report.errors)})", expanded=True):
            for error in report.errors:
                st.write(error)
    prefix = "DEMO-" if report.demo else ""
    left, right = st.columns(2)
    left.download_button("Pobierz Excel (.xlsx)", xlsx_bytes(report),
                         file_name=f"{prefix}firmy-krs-{report.target_date}.xlsx",
                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         width="stretch")
    right.download_button("Pobierz PDF", pdf_bytes(report),
                          file_name=f"{prefix}firmy-krs-{report.target_date}.pdf",
                          mime="application/pdf", width="stretch")
else:
    st.write("Wybierz ustawienia po lewej i kliknij **Pobierz firmy z KRS**. "
             "Możesz też obejrzeć przykład na fikcyjnych danych.")
