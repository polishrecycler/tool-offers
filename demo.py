from datetime import datetime
from core import Company, Report, WARSAW


def demo_report(target):
    company = Company(krs="0000000000", name="PRZYKŁAD — Fikcyjna firma recyklingowa sp. z o.o.",
                      registration_date=target.isoformat(), address="Przykładowa 1, Warszawa",
                      pkd=["38.11.Z — Zbieranie odpadów innych niż niebezpieczne"],
                      emails=["kontakt@example.invalid"], websites=["https://example.invalid"],
                      contact_status="DEMO — dane fikcyjne")
    return Report(target.isoformat(), datetime.now(WARSAW).isoformat(), ["37", "38", "39"],
                  False, candidates=1, checked=1, companies=[company], demo=True)
