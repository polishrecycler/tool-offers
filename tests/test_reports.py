from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook
import requests

from core import (DataError, Report, bulletin_numbers, collect, company_from_extract,
                  current_extract, json_get, pkd_filters, yesterday)
from contacts import enrich_contacts
from demo import demo_report
from exports import pdf_bytes, xlsx_bytes

TARGET = date(2026, 10, 27)


@pytest.fixture
def extract():
    return {"odpis": {
        "naglowekA": {"numerKRS": "0000123456", "rejestr": "RejP",
                      "dataRejestracjiWKRS": "27.10.2026", "dataOstatniegoWpisu": "27.10.2026"},
        "dane": {
            "dzial1": {"danePodmiotu": {"nazwa": "TEST ODPADY SP. Z O.O.",
                                       "identyfikatory": {"nip": "1234567890"}},
                       "siedzibaIAdres": {"adres": {"miejscowosc": "Łódź"}},
                       "adresPocztyElektronicznej": "biuro@example.invalid"},
            "dzial3": {"przedmiotDzialalnosci": {
                "przedmiotPrzewazajacejDzialalnosci": [
                    {"kodDzial": "62", "kodKlasa": "01", "kodPodklasa": "Z", "opis": "IT"}],
                "przedmiotPozostalejDzialalnosci": [
                    {"kodDzial": "38", "kodKlasa": "11", "kodPodklasa": "Z", "opis": "Odpady"}]}}
        }}}


def test_modified_company_is_excluded_even_when_last_entry_is_target(extract):
    extract["odpis"]["naglowekA"]["dataRejestracjiWKRS"] = "26.10.2026"
    assert company_from_extract(extract, "0000123456", TARGET) is None


def test_registration_date_is_not_last_entry_date(extract):
    extract["odpis"]["naglowekA"]["dataOstatniegoWpisu"] = "28.10.2026"
    company = company_from_extract(extract, "0000123456", TARGET)
    assert company.registration_date == "2026-10-27"
    assert company.pkd == ["38.11.Z — Odpady"]
    assert company.emails == ["biuro@example.invalid"]


def test_filter_all_vs_main_and_full_code(extract):
    assert company_from_extract(extract, "0000123456", TARGET, main_only=True) is None
    assert company_from_extract(extract, "0000123456", TARGET, pkd_filters("38.11.Z"))
    assert company_from_extract(extract, "0000123456", TARGET, pkd_filters("39")) is None


def test_missing_registration_date_cannot_be_treated_as_new(extract):
    del extract["odpis"]["naglowekA"]["dataRejestracjiWKRS"]
    with pytest.raises(DataError):
        company_from_extract(extract, "0000123456", TARGET)


def test_extract_identity_must_match_request(extract):
    with pytest.raises(DataError):
        company_from_extract(extract, "0000999999", TARGET)


def test_bulletin_deduplicates_and_rejects_unknown_schema():
    assert bulletin_numbers(["0000123456", "123456"]) == ["0000123456"]
    with pytest.raises(DataError):
        bulletin_numbers({"unexpected": []})


def test_warsaw_midnight_changes_yesterday():
    # In Poland this instant is already 28 October.
    assert yesterday(datetime(2026, 10, 27, 23, 30, tzinfo=timezone.utc)) == TARGET


class Response:
    def __init__(self, payload=None, content=b"", fail=False, status_code=200, invalid_json=False):
        self.payload, self.content, self.fail = payload, content, fail
        self.status_code, self.invalid_json = status_code, invalid_json
    def json(self):
        if self.invalid_json:
            raise requests.exceptions.JSONDecodeError("invalid body", "", 0)
        return self.payload
    def raise_for_status(self):
        if self.fail or self.status_code >= 400:
            raise requests.HTTPError("fixture HTTP error", response=self)


class Client:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return next(self.responses)


@pytest.mark.parametrize("registry", ["P", "RejP"])
def test_real_registry_names_do_not_drop_matching_entrepreneurs(extract, registry):
    extract["odpis"]["naglowekA"]["rejestr"] = registry
    assert company_from_extract(extract, "0000123456", TARGET, ("38.11.Z",))


def test_broad_unrelated_codes_do_not_break_exact_matching(extract):
    entries = extract["odpis"]["dane"]["dzial3"]["przedmiotDzialalnosci"]
    entries["przedmiotPrzewazajacejDzialalnosci"] = [
        {"kodDzial": "33", "opis": "Cały dział"},
        {"kodDzial": "93", "kodKlasa": "1", "opis": "Cała grupa"}]
    assert company_from_extract(extract, "0000123456", TARGET, ("38.11.Z",))
    assert company_from_extract(extract, "0000123456", TARGET, ("33.14.Z",)) is None
    assert company_from_extract(extract, "0000123456", TARGET, ("20.16.Z",)) is None
    assert company_from_extract(extract, "0000123456", TARGET, ("93.11.Z",)) is None


def test_association_is_checked_in_its_own_register(extract, monkeypatch):
    monkeypatch.setattr("core.time.sleep", lambda _: None)
    extract["odpis"]["naglowekA"]["rejestr"] = "RejS"
    client = Client([Response(["123456"]), Response(status_code=404), Response(extract)])
    report = collect(TARGET, client=client)
    assert report.complete
    assert report.companies == []
    assert client.calls[1][1]["params"]["rejestr"] == "P"
    assert client.calls[2][1]["params"]["rejestr"] == "S"


def test_no_current_extract_uses_history_to_exclude_old_company(monkeypatch):
    monkeypatch.setattr("core.time.sleep", lambda _: None)
    full = {"odpis": {"naglowekP": {"rejestr": "RejP", "numerKRS": "0000123456", "wpis": [
        {"numerWpisu": 2, "dataWpisu": "27.10.2026"},
        {"numerWpisu": 1, "dataWpisu": "11.04.2001"}]}}}
    client = Client([Response(["123456"]), Response(status_code=204), Response(full)])
    report = collect(TARGET, client=client)
    assert report.complete
    assert not report.companies
    assert "OdpisPelny" in client.calls[-1][0][0]


def test_new_company_without_current_pkd_is_not_silently_excluded(monkeypatch):
    monkeypatch.setattr("core.time.sleep", lambda _: None)
    full = {"odpis": {"naglowekP": {"rejestr": "RejP", "numerKRS": "0000123456", "wpis": [
        {"numerWpisu": 1, "dataWpisu": "27.10.2026"}]}}}
    report = collect(TARGET, client=Client([
        Response(["123456"]), Response(status_code=204), Response(full)]))
    assert not report.complete
    assert not report.companies
    assert report.checked == 0
    assert "Nie można potwierdzić" in report.errors[0]


def test_bad_json_is_retried_without_claiming_network_is_blocked(extract, monkeypatch):
    monkeypatch.setattr("core.time.sleep", lambda _: None)
    client = Client([Response(invalid_json=True), Response(extract)])
    assert json_get(client, "https://example.invalid") == extract
    assert len(client.calls) == 2
    client = Client([Response(invalid_json=True)] * 3)
    with pytest.raises(DataError, match="trzykrotnie"):
        json_get(client, "https://example.invalid")


def test_forbidden_response_does_not_fall_back_to_another_register():
    client = Client([Response(status_code=403)])
    with pytest.raises(DataError, match="403"):
        current_extract(client, "0000123456", TARGET)
    assert len(client.calls) == 1


def test_contact_search_failure_does_not_make_registry_results_incomplete(extract, monkeypatch):
    monkeypatch.setattr("core.time.sleep", lambda _: None)
    def fail_contact(*args):
        raise DataError("Search unavailable")
    report = collect(TARGET, prefixes=("38.11.Z",), enrich=fail_contact,
                     client=Client([Response(["123456"]), Response(extract)]))
    assert report.complete
    assert len(report.companies) == 1
    assert len(report.contact_errors) == 1
    assert not report.errors


def test_partial_fetch_is_marked_incomplete(extract, monkeypatch):
    monkeypatch.setattr("core.time.sleep", lambda _: None)
    report = collect(TARGET, client=Client([
        Response(["123456", "123457"]), Response(extract), Response(fail=True)]))
    assert len(report.companies) == 1
    assert report.checked == 1 and report.candidates == 2
    assert not report.complete
    assert len(report.errors) == 1


def test_only_confirmed_pkd_matches_enter_results(extract, monkeypatch):
    from copy import deepcopy
    monkeypatch.setattr("core.time.sleep", lambda _: None)
    other = deepcopy(extract)
    other["odpis"]["naglowekA"]["numerKRS"] = "0000123457"
    business = other["odpis"]["dane"]["dzial3"]["przedmiotDzialalnosci"]
    business["przedmiotPozostalejDzialalnosci"] = [{"kodDzial": "38", "opis": "Cały dział"}]
    report = collect(TARGET, prefixes=("38.11.Z",), client=Client([
        Response(["123456", "123457"]), Response(extract), Response(other)]))
    assert report.complete
    assert report.checked == 2
    assert [company.krs for company in report.companies] == ["0000123456"]


def test_missing_in_both_registers_remains_unresolved(monkeypatch):
    monkeypatch.setattr("core.time.sleep", lambda _: None)
    report = collect(TARGET, client=Client([
        Response(["123456"]), Response(status_code=404), Response(status_code=404)]))
    assert not report.complete
    assert report.checked == 0
    assert not report.companies
    assert len(report.errors) == 1


def test_bulletin_failure_is_not_empty_success():
    with pytest.raises(DataError):
        collect(TARGET, client=Client([Response(fail=True)]))


def test_search_candidates_keep_sources_and_never_become_registry_contacts(extract):
    company = company_from_extract(extract, "0000123456", TARGET)
    content = b'''<rss><channel><item><title>TEST ODPADY SP. Z O.O.</title>
      <description>NIP 1234567890 kontakt: web@example.invalid tel: +48 501 502 503</description>
      <link>https://example.invalid/kontakt</link></item>
      <item><title>Inna firma</title><description>other@example.invalid</description>
      <link>https://example.invalid/inna</link></item></channel></rss>'''
    enrich_contacts(company, Client([Response(content=content)]))
    assert company.email_candidates == ["web@example.invalid"]
    assert company.emails == ["biuro@example.invalid"]
    assert company.phone_candidates == ["+48 501 502 503"]
    assert len(company.sources) == 1
    assert company.sources[0]["match"] == "NIP/KRS"


def test_search_html_error_is_not_no_contacts(extract):
    company = company_from_extract(extract, "0000123456", TARGET)
    with pytest.raises(DataError):
        enrich_contacts(company, Client([Response(content=b"<html>Blocked</html>")]))


def test_excel_preserves_krs_and_formula_like_names():
    report = demo_report(TARGET)
    report.companies[0].name = '=HYPERLINK("https://example.invalid")'
    book = load_workbook(BytesIO(xlsx_bytes(report)), data_only=False)
    assert book["Firmy"]["A2"].data_type == "s"
    assert book["Firmy"]["B2"].value == "0000000000"
    assert book["Informacje"]["B1"].value == "DEMO — dane fikcyjne"
    assert "Źródła kontaktów" in book.sheetnames


def test_pdf_generates_with_polish_text_and_long_sources():
    report = demo_report(TARGET)
    report.companies[0].name = "Żółć Łódź — " * 50
    report.companies[0].krs_source = "https://example.invalid/" + "a" * 1000
    content = pdf_bytes(report)
    assert content.startswith(b"%PDF-")
    assert len(content) > 10000


def test_app_selected_subclasses_and_both_downloads(extract, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from unittest.mock import Mock
    company = company_from_extract(extract, "0000123456", TARGET)
    report = Report(TARGET.isoformat(), "2026-10-28T09:00:00+01:00",
                    ["38.11.Z", "27.20.Z"], False, candidates=1, checked=1, companies=[company])
    fetch = Mock(return_value=report)
    save = Mock()
    monkeypatch.setattr("core.collect", fetch)
    monkeypatch.setattr("core.save_report", save)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    assert not app.exception
    assert not app.sidebar.multiselect
    assert not app.sidebar.expander
    labels = [checkbox.label for checkbox in app.sidebar.checkbox]
    assert "27.20.Z — Produkcja baterii i akumulatorów" in labels
    assert "38.21.Z — Odzysk surowców" in labels
    app.button(key="clear_pkd").click().run()
    app.checkbox(key="pkd_option_38.11.Z").check().run()
    app.checkbox(key="pkd_option_27.20.Z").check().run()
    app.button(key="apply_pkd").click().run()
    app.sidebar.date_input[0].set_value(TARGET)
    app.checkbox(key="search_contacts").uncheck()
    app.button(key="fetch_companies").click().run()
    assert not app.exception
    assert not app.session_state["report"].demo
    fetch.assert_called_once()
    assert fetch.call_args.args == (TARGET, ("27.20.Z", "38.11.Z"))
    assert fetch.call_args.kwargs["main_only"] is False
    assert fetch.call_args.kwargs["enrich"] is None
    save.assert_called_once()
    assert len(app.dataframe) == 1
    downloads = app.get("download_button")
    assert [button.proto.label for button in downloads] == [
        "Eksport do Excela (.xlsx)", "Eksport do PDF"]
    assert all(button.proto.url for button in downloads)
    assert all(not expander.proto.expanded for expander in app.expander)


def test_app_empty_selection_does_not_fetch(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from unittest.mock import Mock
    fetch = Mock()
    monkeypatch.setattr("core.collect", fetch)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    app.button(key="clear_pkd").click().run()
    assert not app.exception
    assert app.button(key="fetch_companies").disabled
    fetch.assert_not_called()


def test_pkd_search_keeps_hidden_selections_and_clear_removes_them():
    from streamlit.testing.v1 import AppTest
    from pkd_catalog import DEFAULT_SELECTED_PKD
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    app.text_input(key="pkd_search").set_value("AKUMULATORY").run()
    assert len([c for c in app.checkbox if c.key.startswith("pkd_option_")]) == 1
    app.checkbox(key="pkd_option_27.20.Z").check().run()
    assert set(app.session_state["draft_pkd"]) == {*DEFAULT_SELECTED_PKD, "27.20.Z"}
    assert set(app.session_state["selected_pkd"]) == set(DEFAULT_SELECTED_PKD)
    app.button(key="apply_pkd").click().run()
    assert set(app.session_state["selected_pkd"]) == {*DEFAULT_SELECTED_PKD, "27.20.Z"}
    summary = app.get("popover")[0].proto.popover.label
    assert "27.20.Z" in summary
    assert "akumulator" not in summary.lower()
    app.text_input(key="pkd_search").set_value("nieistniejąca fraza").run()
    assert set(app.session_state["selected_pkd"]) == {*DEFAULT_SELECTED_PKD, "27.20.Z"}
    app.button(key="clear_pkd").click().run()
    assert app.session_state["selected_pkd"] == []
    app.text_input(key="pkd_search").set_value("").run()
    assert not any(c.value for c in app.checkbox if c.key.startswith("pkd_option_"))
    assert app.get("popover")[0].proto.popover.label == "Wybierz kody PKD"
    assert not app.exception


def test_demo_query_parameter_does_not_generate_fictional_results():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["demo"] = "1"
    app.run()
    assert not app.exception
    assert not app.dataframe
    assert "report" not in app.session_state


def test_changed_pkd_or_date_hides_previous_report(extract):
    from streamlit.testing.v1 import AppTest
    from core import yesterday
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.session_state["selected_pkd"] = ["38.11.Z"]
    report = Report(yesterday().isoformat(), "2026-10-29", ["38.11.Z"], False,
                    candidates=1, checked=1,
                    companies=[company_from_extract(extract, "0000123456", TARGET)])
    app.session_state["report"] = report
    app.run()
    assert len(app.dataframe) == 1
    app.checkbox(key="pkd_option_27.20.Z").check().run()
    assert len(app.dataframe) == 1  # Editing the draft must not change the active report.
    app.button(key="apply_pkd").click().run()
    assert not app.dataframe
    assert not app.get("download_button")
    assert "report" not in app.session_state
    app.checkbox(key="pkd_option_27.20.Z").uncheck().run()
    app.button(key="apply_pkd").click().run()
    app.session_state["report"] = report
    app.run()
    assert len(app.dataframe) == 1
    app.sidebar.date_input[0].set_value(TARGET).run()
    assert not app.dataframe
    assert "report" not in app.session_state


def test_unverified_numbers_are_not_displayed_as_a_company_list():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.session_state["selected_pkd"] = ["38.11.Z"]
    app.session_state["report"] = Report(
        yesterday().isoformat(), "2026-10-29", ["38.11.Z"], False, candidates=1,
        errors=["KRS 0000002664: technical detail"])
    app.run()
    assert not app.exception
    assert not app.dataframe
    assert not app.get("download_button")
    assert not any("0000002664" in text.value for text in app.markdown)
    assert any("część danych jest" in warning.value for warning in app.warning)
    assert all(not expander.proto.expanded for expander in app.expander)


def test_complete_official_pkd_catalog_is_available():
    import re
    from pkd_catalog import PKD_OPTIONS
    # The statutory PKD 2025 structure lists 728 subclasses, including sectors
    # deliberately absent from the previous waste-only catalogue.
    assert len(PKD_OPTIONS) == 728
    assert all(re.fullmatch(r"\d{2}\.\d{2}\.[A-Z]", code) for code in PKD_OPTIONS)
    assert PKD_OPTIONS["01.12.Z"] == "Uprawa ryżu"
    assert PKD_OPTIONS["62.10.B"] == "Pozostała działalność w zakresie programowania"
    assert PKD_OPTIONS["99.00.Z"] == "Organizacje i zespoły eksterytorialne"


def test_user_can_search_and_fetch_an_industry_outside_waste(extract, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from unittest.mock import Mock
    business = extract["odpis"]["dane"]["dzial3"]["przedmiotDzialalnosci"]
    business["przedmiotPrzewazajacejDzialalnosci"] = [
        {"kodDzial": "62", "kodKlasa": "10", "kodPodklasa": "B", "opis": "Programowanie"}]
    business["przedmiotPozostalejDzialalnosci"] = []
    company = company_from_extract(extract, "0000123456", TARGET, ("62.10.B",))
    report = Report(TARGET.isoformat(), "2026-10-29", ["62.10.B"], False,
                    candidates=1, checked=1, companies=[company])
    fetch = Mock(return_value=report)
    monkeypatch.setattr("core.collect", fetch)
    monkeypatch.setattr("core.save_report", Mock())
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    app.button(key="clear_pkd").click().run()
    app.text_input(key="pkd_search").set_value("62.10").run()
    app.checkbox(key="pkd_option_62.10.B").check().run()
    app.button(key="apply_pkd").click().run()
    assert app.get("popover")[0].proto.popover.label == "62.10.B"
    app.sidebar.date_input[0].set_value(TARGET)
    app.checkbox(key="search_contacts").uncheck()
    app.button(key="fetch_companies").click().run()
    assert not app.exception
    assert fetch.call_args.args == (TARGET, ("62.10.B",))
    assert len(app.dataframe) == 1


def test_select_all_covers_hidden_codes_and_waits_for_confirmation():
    from streamlit.testing.v1 import AppTest
    from pkd_catalog import PKD_OPTIONS, DEFAULT_SELECTED_PKD
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    app.text_input(key="pkd_search").set_value("62.10").run()
    checkboxes = [checkbox.key for checkbox in app.checkbox]
    assert checkboxes[0] == "pkd_select_all"
    app.checkbox(key="pkd_select_all").check().run()
    assert set(app.session_state["draft_pkd"]) == set(PKD_OPTIONS)
    assert set(app.session_state["selected_pkd"]) == set(DEFAULT_SELECTED_PKD)
    app.text_input(key="pkd_search").set_value("99.00").run()
    assert app.checkbox(key="pkd_option_99.00.Z").value
    app.checkbox(key="pkd_option_99.00.Z").uncheck().run()
    assert not app.checkbox(key="pkd_select_all").value
    assert len(app.session_state["draft_pkd"]) == 727
    app.checkbox(key="pkd_select_all").check().run()
    app.button(key="apply_pkd").click().run()
    assert set(app.session_state["selected_pkd"]) == set(PKD_OPTIONS)
    assert not app.get("popover")[0].proto.popover.open
    assert len(app.get("popover")[0].proto.popover.label) < 100
    app.checkbox(key="pkd_select_all").uncheck().run()
    assert app.session_state["draft_pkd"] == []
    assert len(app.session_state["selected_pkd"]) == 728
    app.button(key="apply_pkd").click().run()
    assert app.session_state["selected_pkd"] == []
    assert app.button(key="fetch_companies").disabled
    assert not app.exception
