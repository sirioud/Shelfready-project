"""Command line: python -m shelfready audit FILE.csv [--html PATH]"""

import argparse
import sys
from pathlib import Path

from .loader import LoaderError, load_products
from .models import Product
from .report import terminal_report, write_html_report
from .scoring import ProductScore, score_catalog
from .sector import SECTOR


def build_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="shelfready",
        description="Score product listings for AI readability.",
    )
    sub = parser.add_subparsers(dest="command", required=True) # sub-commands, so export/history can be added later

    audit: argparse.ArgumentParser = sub.add_parser("audit", help="Score a product CSV file")
    audit.add_argument("csv_file")
    audit.add_argument("--html", metavar="PATH", help="also write an HTML report to PATH")
    return parser


def run_audit(args: argparse.Namespace) -> None:
    products: list[Product]
    errors: list[str]
    products, errors = load_products(args.csv_file)

    scores: list[ProductScore]
    catalog_score: float
    scores, catalog_score = score_catalog(products)

    print(terminal_report(scores, catalog_score, errors))

    if args.html:
        source_name: str = Path(args.csv_file).name
        path: Path = write_html_report(args.html, scores, catalog_score, errors, source_name=source_name, sector=SECTOR)
        print(f"\nHTML report written to {path}")


def main(argv: list[str] | None = None) -> int:
    # argv lets the tests pass a fake command line. returns 0 if ok, 1 on error
    args: argparse.Namespace = build_parser().parse_args(argv)
    try:
        if args.command == "audit":
            run_audit(args)
    except LoaderError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
