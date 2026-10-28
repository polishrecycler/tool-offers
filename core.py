"""KRS report pipeline. No network work happens at import time."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import time
from typing import Callable
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

WARSAW = ZoneInfo("Europe/Warsaw")
API = "https://api-krs.ms.gov.pl/api/krs"
DEFAULT_PKD = ("37", "38", "39")


class DataError(RuntimeError):
    pass


def yesterday(now: datetime | None = None) -> date:
    return (now or datetime.now(WARSAW)).astimezone(WARSAW).date() - timedelta(days=1)


def session() -> requests.Session:
    result = requests.Session()
    result.headers["User-Agent"] = "ToolOffers/0.1 (public KRS research)"
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"], respect_retry_after_header=True)
    result.mount("https://", HTTPAdapter(max_retries=retry))
    return result


def json_get(client, url: str, params=None):
    try:
        response = client.get(url, params=params, timeout=(10, 45))
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise DataError(f"Nie można pobrać danych KRS ({type(exc).__name__}). "
                        "Sprawdź dostęp do api-krs.ms.gov.pl oraz dostępność API.") from exc


def krs_number(value) -> str:
    text = str(value)
    if not re.fullmatch(r"\d{1,10}", text):
        raise DataError("Nieprawidłowy numer KRS w odpowiedzi biuletynu.")
    return text.zfill(10)


def bulletin_numbers(payload) -> list[str]:
    if not isinstance(payload, list):
        raise DataError("Nieznany format biuletynu KRS. Raport został zatrzymany.")
    result = []
    for item in payload:
        if isinstance(item, dict):
            item = item.get("numerKRS", item.get("krs"))
        result.append(krs_number(item))
    return sorted(set(result))


def parse_date(value: str) -> date:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except (ValueError, TypeError):
            continue
    raise DataError("Brak poprawnej daty pierwszej rejestracji w odpisie KRS.")


def normalize_pkd(value: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", value.upper())


def pkd_filters(text: str) -> tuple[str, ...]:
    values = tuple(normalize_pkd(x.strip()) for x in text.split(",") if x.strip())
    if not values or any(not re.fullmatch(r"\d{2}(?:\d{2}[A-Z]?)?", x) for x in values):
        raise DataError("Podaj działy lub kody PKD po przecinku, np. 37, 38, 39 lub 38.11.Z.")
    return values


def contact_values(tree, key: str) -> list[str]:
    values = []
    if isinstance(tree, dict):
        for name, value in tree.items():
            if name == key and isinstance(value, str) and value.strip():
                values.append(value.strip())
            else:
                values.extend(contact_values(value, key))
    elif isinstance(tree, list):
        for item in tree:
            values.extend(contact_values(item, key))
    return sorted(set(values))


@dataclass
class Company:
    krs: str
    name: str
    registration_date: str
    nip: str = ""
    regon: str = ""
    address: str = ""
    pkd: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    websites: list[str] = field(default_factory=list)
    phone_candidates: list[str] = field(default_factory=list)
    email_candidates: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    contact_status: str = "Nie wyszukiwano w internecie"
    krs_source: str = ""


def company_from_extract(payload, number: str, target: date, prefixes=DEFAULT_PKD,
                         main_only: bool = False) -> Company | None:
    try:
        extract = payload["odpis"]
        header = extract["naglowekA"]
        registered = parse_date(header["dataRejestracjiWKRS"])
        if registered != target:
            return None  # Date of registration, NEVER date of the latest entry.
        if krs_number(header["numerKRS"]) != number:
            raise DataError("Numer KRS odpisu nie odpowiada żądanemu numerowi.")
        # Only the entrepreneurs' register; bulletin can contain other entities.
        if header.get("rejestr", "P") != "P":
            return None
        data = extract["dane"]
        business = data["dzial3"]["przedmiotDzialalnosci"]
        entries = list(business.get("przedmiotPrzewazajacejDzialalnosci", []))
        if not main_only:
            entries += business.get("przedmiotPozostalejDzialalnosci", [])
        matches = []
        for entry in entries:
            code = ".".join(str(entry[k]) for k in ("kodDzial", "kodKlasa", "kodPodklasa") if entry.get(k) is not None)
            if not re.fullmatch(r"\d{2}\.\d{2}\.[A-Z]", code):
                raise DataError("Nieznany format kodu PKD w odpisie.")
            if any(normalize_pkd(code).startswith(normalize_pkd(p)) for p in prefixes):
                matches.append(f"{code} — {entry.get('opis', '')}")
        if not matches:
            return None
        first = data["dzial1"]
        entity = first["danePodmiotu"]
        ids = entity.get("identyfikatory", {})
        address = first.get("siedzibaIAdres", {}).get("adres", {})
        address_text = " ".join(str(address.get(k, "")) for k in
                                ("ulica", "nrDomu", "nrLokalu", "kodPocztowy", "miejscowosc")).strip()
        return Company(number, entity["nazwa"], registered.isoformat(),
                       nip=ids.get("nip", ""), regon=ids.get("regon", ""), address=address_text,
                       pkd=sorted(set(matches)), emails=contact_values(first, "adresPocztyElektronicznej"),
                       websites=contact_values(first, "adresStronyInternetowej"),
                       krs_source=f"{API}/OdpisAktualny/{number}?rejestr=P&format=json")
    except (KeyError, TypeError, AttributeError) as exc:
        raise DataError("Niepełny lub nieznany format odpisu KRS; wpis wymaga ponownego sprawdzenia.") from exc


@dataclass
class Report:
    target_date: str
    generated_at: str
    filters: list[str]
    main_only: bool
    candidates: int = 0
    checked: int = 0
    companies: list[Company] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    demo: bool = False

    @property
    def complete(self):
        return self.checked == self.candidates and not self.errors and not self.demo


def collect(target: date, prefixes=DEFAULT_PKD, main_only=False,
            enrich: Callable | None = None, progress: Callable | None = None,
            client=None) -> Report:
    if target >= datetime.now(WARSAW).date():
        raise DataError("Wybierz zakończony dzień — najpóźniej wczoraj.")
    client = client or session()
    report = Report(target.isoformat(), datetime.now(WARSAW).isoformat(), list(prefixes), main_only)
    # Full daily bulletin; repeated changes to the same company are deduplicated.
    if progress:
        progress(0, 0, "Pobieranie dziennego biuletynu KRS")
    payload = json_get(client, f"{API}/Biuletyn/{target.isoformat()}",
                       {"godzinaOd": 0, "godzinaDo": 23})
    numbers = bulletin_numbers(payload)
    report.candidates = len(numbers)
    for index, number in enumerate(sorted(numbers), 1):
        try:
            payload = json_get(client, f"{API}/OdpisAktualny/{number}", {"rejestr": "P", "format": "json"})
            company = company_from_extract(payload, number, target, prefixes, main_only)
            report.checked += 1
            if company:
                if enrich:
                    try:
                        enrich(company, client)
                    except Exception:
                        company.contact_status = "Błąd wyszukiwania — sprawdź ręcznie"
                        report.errors.append(f"KRS {number}: nie udało się wyszukać kontaktów.")
                report.companies.append(company)
        except DataError as exc:
            report.errors.append(f"KRS {number}: {exc}")
        if progress:
            progress(index, report.candidates, f"Sprawdzono {index}/{report.candidates} odpisów")
        time.sleep(0.2)
    return report


def save_report(report: Report, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(WARSAW).strftime("%Y%m%dT%H%M%S%f")
    path = directory / f"{'DEMO-' if report.demo else ''}krs-{report.target_date}-{stamp}.json"
    path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
