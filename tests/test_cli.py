import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from shelfready.__main__ import main

SAMPLE = Path(__file__).parent.parent / "shelfready" / "data" / "sample_products.csv"


class CliTests(unittest.TestCase):
    def test_audit_sample_file(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["audit", str(SAMPLE)])
        self.assertEqual(code, 0)
        self.assertIn("AI readability score: 85.3 / 100", output.getvalue())
        self.assertIn("Products likely to be recommended: 5 of 10", output.getvalue())

    def test_audit_writes_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "reports" / "report.html"
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["audit", str(SAMPLE), "--html", str(target)])
            self.assertEqual(code, 0)
            self.assertTrue(target.exists())
            self.assertIn("ShelfReady report", target.read_text(encoding="utf-8"))
            self.assertIn("HTML report written to", output.getvalue())

    def test_audit_writes_ai_ready_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "feed.tsv"
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["audit", str(SAMPLE), "--feed", str(target)])
            self.assertEqual(code, 0)
            lines: list[str] = target.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "id\tproduct_highlight\tquestion_and_answer")
            self.assertTrue(lines[1].startswith("P001\t"))
            self.assertIn("AI-ready feed written to", output.getvalue())

    def test_missing_file(self):
        errors = io.StringIO()
        with redirect_stderr(errors):
            code = main(["audit", "missing.csv"])
        self.assertEqual(code, 1)
        self.assertIn("File not found", errors.getvalue())

    def test_folder_gives_clean_error(self):
        errors = io.StringIO()
        with redirect_stderr(errors):
            code = main(["audit", str(SAMPLE.parent)])
        self.assertEqual(code, 1)
        self.assertIn("Not a file", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
