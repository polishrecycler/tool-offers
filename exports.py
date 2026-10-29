from io import BytesIO
from pathlib import Path
import re
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from core import Report


def rows(report: Report) -> list[dict]:
    return [{"Nazwa": c.name, "KRS": c.krs, "NIP": c.nip, "REGON": c.regon,
             "Rejestracja w KRS": c.registration_date, "Adres": c.address,
             "PKD": "\n".join(c.pkd), "E-mail z KRS": "; ".join(c.emails),
             "WWW z KRS": "; ".join(c.websites),
             "E-mail z internetu (do potwierdzenia)": "; ".join(c.email_candidates),
             "Telefon z internetu (do potwierdzenia)": "; ".join(c.phone_candidates),
             "Status kontaktu": c.contact_status, "Źródło KRS": c.krs_source,
             "Źródła internetowe": "\n".join(s["url"] for s in c.sources)} for c in report.companies]


def status(report):
    if report.demo:
        return "DEMO — dane fikcyjne"
    return ("Sprawdzono wszystkie numery z biuletynu" if report.complete else
            "Raport niepełny — nie wszystkie firmy udało się zweryfikować")


def metadata(report):
    return [("Status", status(report)), ("Dzień rejestracji", report.target_date),
            ("Wygenerowano", report.generated_at), ("Strefa czasowa", "Europe/Warsaw"),
            ("PKD", ", ".join(report.filters)),
            ("Zakres PKD", "Tylko przeważające" if report.main_only else "Wszystkie ujawnione"),
            ("Numery z biuletynu", report.candidates), ("Rozpatrzone numery firm", report.checked),
            ("Firmy pasujące", len(report.companies)),
            ("Pierwsze rejestracje przed filtrem kodów", report.qualification.get("new_registrations", len(report.companies))),
            ("Inna data pierwszej rejestracji", report.qualification.get("other_registration_date", 0)),
            ("Podmioty z rejestru stowarzyszeń", report.qualification.get("outside_business_registry", 0)),
            ("Nowe firmy z innymi kodami", report.qualification.get("other_pkd", 0)),
            ("Problemy z wyszukiwaniem kontaktów", len(report.contact_errors)),
            ("Uwaga", "Data pierwszej rejestracji w KRS. PKD i kontakty KRS pochodzą z odpisu aktualnego. "
             "Pierwszy wpis nie oznacza daty zawarcia umowy spółki. Wyniki internetu wymagają potwierdzenia. "
             "Brak wyniku nie dowodzi braku danych kontaktowych.")]


def literal(value):
    # Force all external strings to be spreadsheet text, including formula prefixes.
    text = str(value) if value is not None else ""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)[:32767]


def xlsx_bytes(report: Report) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Firmy"
    records = rows(report)
    headers = list(records[0]) if records else ["Nazwa", "KRS", "NIP", "Rejestracja w KRS", "PKD"]
    sheet.append(headers)
    for record in records:
        sheet.append([literal(record[h]) for h in headers])
    meta = book.create_sheet("Informacje")
    for key, value in metadata(report):
        meta.append([key, literal(value)])
    errors = book.create_sheet("Błędy")
    errors.append(["Problemy do ponownego sprawdzenia"])
    for error in report.errors + report.contact_errors:
        errors.append([literal(error)])
    sources = book.create_sheet("Źródła kontaktów")
    sources.append(["KRS", "Nazwa firmy", "URL", "Tytuł", "Fragment wyniku", "Dopasowanie", "E-mail", "Telefon"])
    for company in report.companies:
        for source in company.sources:
            sources.append([literal(value) for value in
                            [company.krs, company.name, source["url"], source["title"], source["snippet"],
                             source["match"], "; ".join(source["emails"]), "; ".join(source["phones"])]])
    for ws in book:
        for row in ws:
            for cell in row:
                if isinstance(cell.value, str):
                    # XML-invalid characters are removed, all text stays literal.
                    cell.value = literal(cell.value)
                    cell.data_type = "s"
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="176B53")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for column in ws.columns:
            ws.column_dimensions[column[0].column_letter].width = 28
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def pdf_bytes(report: Report) -> bytes:
    font_path = Path(__file__).parent / "assets" / "DejaVuSans.ttf"
    if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVu", str(font_path)))
    style = ParagraphStyle("body", fontName="DejaVu", fontSize=8, leading=11, alignment=TA_LEFT,
                           splitLongWords=True)
    title = ParagraphStyle("title", parent=style, fontSize=16, leading=21)
    def p(value):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)
    story = [Paragraph("Nowe firmy: środowisko i odpady", title), p(status(report)), Spacer(1, 12)]
    for key, value in metadata(report):
        story.append(p(f"{key}: {value}"))
    story.append(Spacer(1, 14))
    if not report.companies:
        story.append(p("Brak firm w raporcie. Sprawdź status i ewentualne błędy."))
    for company in report.companies:
        story += [p(company.name), p(f"KRS: {company.krs} | NIP: {company.nip} | REGON: {company.regon}"),
                  p(f"Rejestracja: {company.registration_date} | {company.address}"),
                  p("PKD: " + "; ".join(company.pkd)),
                  p("E-mail z KRS: " + "; ".join(company.emails)),
                  p("WWW z KRS: " + "; ".join(company.websites)),
                  p("E-mail z internetu (do potwierdzenia): " + "; ".join(company.email_candidates)),
                  p("Telefon z internetu (do potwierdzenia): " + "; ".join(company.phone_candidates)),
                  p(company.contact_status), p("Źródło KRS: " + company.krs_source)]
        for source in company.sources:
            story += [p("Źródło internetowe: " + source["url"]),
                      p("Dopasowanie: " + source["match"]), p(source["snippet"])]
        story.append(Spacer(1, 16))
    if report.errors:
        story.append(p("Błędy — raport wymaga ponownego sprawdzenia:"))
        story.extend(p(error) for error in report.errors)
    if report.contact_errors:
        story.append(p("Nie udało się uzupełnić kontaktów (dopasowanie firm pozostaje potwierdzone):"))
        story.extend(p(error) for error in report.contact_errors)
    out = BytesIO()
    def footer(canvas, doc):
        canvas.setFont("DejaVu", 8)
        canvas.drawString(30, 20, f"Tool Offers | {report.target_date} | {status(report)} | strona {doc.page}")
    SimpleDocTemplate(out, pagesize=A4, rightMargin=30, leftMargin=30,
                      topMargin=30, bottomMargin=40).build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
