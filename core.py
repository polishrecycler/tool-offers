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


class KrsResponseError(DataError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def yesterday(now: datetime | None = None) -> date:
    return (now or datetime.now(WARSAW)).astimezone(WARSAW).date() - timedelta(days=1)


def session() -> requests.Session:
    result = requests.Session()
    result.headers["User-Agent"] = "ToolOffers/0.1 (public KRS research)"
    result.headers["Accept"] = "application/json"
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"], respect_retry_after_header=True, raise_on_status=False)
    result.mount("https://", HTTPAdapter(max_retries=retry))
    return result


def json_get(client, url: str, params=None):
    # The server sometimes returns an empty response or a non-JSON error page.
    # HTTP failures are retried by the session adapter; malformed bodies need
    # their own bounded retry. A 204 is a valid "no current extract" response.
    for attempt in range(3):
        try:
            response = client.get(url, params=params, timeout=(10, 45))
            status_code = getattr(response, "status_code", 200)
            if status_code == 204:
                raise KrsResponseError(204, "Rejestr nie udostępnia aktualnego odpisu (kod odpowiedzi 204).")
            if status_code == 404:
                raise KrsResponseError(404, "Brak odpisu w wybranej części rejestru (kod odpowiedzi 404).")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, (dict, list)):
                raise ValueError("Unexpected response body")
            return payload
        except requests.HTTPError as exc:
            code = getattr(response, "status_code", None)
            raise DataError(f"Serwer rejestru odrzucił pobranie odpisu (kod odpowiedzi {code or 'nieznany'}). "
                            "Nie oznacza to braku firmy ani niezgodności jej działalności.") from exc
        except requests.Timeout as exc:
            raise DataError("Przekroczono czas oczekiwania na odpowiedź rejestru. Spróbuj ponownie.") from exc
        except requests.RequestException as exc:
            # JSONDecodeError also inherits RequestException in requests.
            if not isinstance(exc, ValueError):
                raise DataError("Nie udało się połączyć z rejestrem podczas pobierania odpisu.") from exc
            if attempt == 2:
                raise DataError("Serwer rejestru trzykrotnie zwrócił pustą lub nieczytelną odpowiedź.") from exc
        except ValueError as exc:
            if attempt == 2:
                raise DataError("Serwer rejestru trzykrotnie zwrócił pustą lub nieczytelną odpowiedź.") from exc
        time.sleep(0.5 * (attempt + 1))


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


def extract_registry(header: dict, number: str) -> str:
    if krs_number(header["numerKRS"]) != number:
        raise DataError("Numer KRS odpisu nie odpowiada żądanemu numerowi.")
    registry = {"P": "P", "RejP": "P", "S": "S", "RejS": "S"}.get(header.get("rejestr"))
    if registry is None:
        raise DataError("Nieznane oznaczenie części rejestru w odpisie.")
    return registry


def _check_full_extract(client, number: str, registry: str, target: date):
    """Use history only to exclude old/non-business entities, never as current PKD."""
    payload = json_get(client, f"{API}/OdpisPelny/{number}", {"rejestr": registry, "format": "json"})
    try:
        header = payload["odpis"]["naglowekP"]
        if extract_registry(header, number) != "P":
            return None
        first = [entry for entry in header["wpis"] if str(entry.get("numerWpisu")) == "1"]
        if len(first) != 1:
            raise DataError("Nie można jednoznacznie ustalić pierwszej rejestracji z odpisu pełnego.")
        if parse_date(first[0]["dataWpisu"]) != target:
            return None
    except (KeyError, TypeError, AttributeError) as exc:
        raise DataError("Nie można ustalić pierwszej rejestracji z odpisu pełnego.") from exc
    raise DataError("Firma została zarejestrowana w wybranym dniu, ale nie ma aktualnego odpisu. "
                    "Nie można potwierdzić jej obecnych kodów działalności.")


def current_extract(client, number: str, target: date):
    try:
        return json_get(client, f"{API}/OdpisAktualny/{number}", {"rejestr": "P", "format": "json"})
    except KrsResponseError as exc:
        if exc.status_code == 204:
            return _check_full_extract(client, number, "P", target)
        if exc.status_code != 404:
            raise
    # Daily bulletins include associations as well as entrepreneurs.
    try:
        return json_get(client, f"{API}/OdpisAktualny/{number}", {"rejestr": "S", "format": "json"})
    except KrsResponseError as exc:
        if exc.status_code == 204:
            return _check_full_extract(client, number, "S", target)
        raise DataError("Nie odnaleziono aktualnego odpisu pozwalającego zweryfikować firmę. "
                        "Wynik pozostaje niepełny.") from exc


def entry_pkd_code(entry: dict) -> str:
    # KRS accepts a division, group, class or a full subclass. A broad
    # entry must not break unrelated exact matches, nor prove a narrower code.
    if not re.fullmatch(r"\d{2}", str(entry.get("kodDzial", ""))):
        raise DataError("Brak poprawnego działu klasyfikacji w odpisie.")
    parts = [str(entry[k]) for k in ("kodDzial", "kodKlasa", "kodPodklasa")
             if entry.get(k) is not None]
    code = ".".join(parts)
    if not re.fullmatch(r"\d{2}(?:\.\d|\.\d{2}(?:\.[A-Z])?)?", code):
        raise DataError("Nieznany format kodu działalności w odpisie.")
    return code


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
        if extract_registry(header, number) != "P":
            return None
        registered = parse_date(header["dataRejestracjiWKRS"])
        if registered != target:
            return None  # Date of registration, NEVER date of the latest entry.
        data = extract["dane"]
        business = data["dzial3"]["przedmiotDzialalnosci"]
        entries = list(business.get("przedmiotPrzewazajacejDzialalnosci", []))
        if not main_only:
            entries += business.get("przedmiotPozostalejDzialalnosci", [])
        matches = []
        filter_codes = tuple(normalize_pkd(prefix) for prefix in prefixes)
        for entry in entries:
            code = entry_pkd_code(entry)
            if normalize_pkd(code).startswith(filter_codes):
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
    contact_errors: list[str] = field(default_factory=list)

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
    payload = json_get(client, f"{API}/Biuletyn/{target.isoformat()}")
    numbers = bulletin_numbers(payload)
    report.candidates = len(numbers)
    for index, number in enumerate(sorted(numbers), 1):
        try:
            payload = current_extract(client, number, target)
            company = company_from_extract(payload, number, target, prefixes, main_only) if payload is not None else None
            report.checked += 1
            if company:
                if enrich:
                    try:
                        enrich(company, client)
                    except Exception:
                        company.contact_status = "Błąd wyszukiwania — sprawdź ręcznie"
                        report.contact_errors.append(f"KRS {number}: nie udało się wyszukać kontaktów.")
                report.companies.append(company)
        except DataError as exc:
            report.errors.append(f"KRS {number}: {exc}")
        if progress:
            progress(index, report.candidates,
                     f"Sprawdzanie rejestru — potwierdzone firmy zgodne z kodami: {len(report.companies)}")
        time.sleep(0.2)
    return report


def save_report(report: Report, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(WARSAW).strftime("%Y%m%dT%H%M%S%f")
    path = directory / f"{'DEMO-' if report.demo else ''}krs-{report.target_date}-{stamp}.json"
    path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
