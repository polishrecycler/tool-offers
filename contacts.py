"""Public web search; snippets remain candidates, never verified contacts."""
import re
import unicodedata
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
import requests

from core import Company, DataError

EMAIL = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
PHONE = re.compile(r"(?:tel(?:efon)?\.?|phone)\s*[:.]?\s*(\+?\d[\d ()\-]{7,20}\d)", re.I)


def plain(text: str) -> str:
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def folded(text):
    return re.sub(r"\W+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def search_url(company: Company) -> str:
    identifier = company.nip or company.krs
    return "https://www.bing.com/search?" + urlencode({"q": f'"{company.name}" "{identifier}" kontakt'})


def enrich_contacts(company: Company, client):
    url = search_url(company)
    try:
        response = client.get(url + "&format=rss", timeout=(10, 30))
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise DataError("Zbyt duża odpowiedź wyszukiwarki.")
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError) as exc:
        raise DataError("Wyszukiwarka jest niedostępna lub nie zwróciła RSS.") from exc
    if root.tag != "rss" or root.find("channel") is None:
        raise DataError("Nieznany format wyników wyszukiwarki.")
    found = False
    for item in root.findall("./channel/item")[:10]:
        title = plain(item.findtext("title", ""))
        snippet = plain(item.findtext("description", ""))
        link = item.findtext("link", "")
        if urlsplit(link).scheme not in ("http", "https"):
            continue
        text = title + " " + snippet
        # Record why a result was associated with this entity; names alone can collide.
        id_match = any(re.search(rf"(?<!\d){re.escape(value)}(?!\d)", text)
                       for value in (company.nip, company.krs) if value)
        name_match = len(folded(company.name)) >= 8 and folded(company.name) in folded(text)
        if not (id_match or name_match):
            continue
        emails = sorted(set(EMAIL.findall(text)))
        phones = []
        for phone in PHONE.findall(text):
            digits = re.sub(r"\D", "", phone)
            if len(digits) in (9, 11) and digits not in (company.nip, company.krs, company.regon):
                phones.append(phone.strip())
        company.sources.append({"title": title, "url": link, "snippet": snippet,
                                "match": "NIP/KRS" if id_match else "nazwa — wymaga potwierdzenia",
                                "emails": emails, "phones": phones})
        company.email_candidates.extend(emails)
        company.phone_candidates.extend(phones)
        found = True
    company.email_candidates = sorted(set(company.email_candidates) - set(company.emails))
    company.phone_candidates = sorted(set(company.phone_candidates))
    company.contact_status = ("Znaleziono wyniki — kontakty wymagają potwierdzenia" if found
                              else "Brak pasujących wyników; sprawdź ręcznie")
