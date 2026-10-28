"""Manual or scheduled report generation: python cli.py [--date YYYY-MM-DD]."""
import argparse
from datetime import date
from pathlib import Path

from contacts import enrich_contacts
from core import DataError, collect, pkd_filters, save_report, yesterday
from demo import demo_report
from exports import pdf_bytes, status, xlsx_bytes


def main():
    parser = argparse.ArgumentParser(description="Nowe firmy KRS — raport Excel i PDF")
    parser.add_argument("--date", type=date.fromisoformat, default=None)
    parser.add_argument("--pkd", default="37,38,39")
    parser.add_argument("--main-only", action="store_true")
    parser.add_argument("--no-web", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "reports")
    args = parser.parse_args()
    target = args.date or yesterday()
    try:
        report = demo_report(target) if args.demo else collect(
            target, pkd_filters(args.pkd), args.main_only, None if args.no_web else enrich_contacts)
        path = save_report(report, args.output)
        path.with_suffix(".xlsx").write_bytes(xlsx_bytes(report))
        path.with_suffix(".pdf").write_bytes(pdf_bytes(report))
    except (DataError, OSError) as exc:
        print(f"BŁĄD: {exc}")
        return 1
    print(f"{status(report)}. Firmy: {len(report.companies)}. Pliki: {path.with_suffix('')}")
    return 0 if report.complete or report.demo else 2


if __name__ == "__main__":
    raise SystemExit(main())
