"""Generate an SVG dashboard and Markdown report from CAN test results."""

import csv
from collections import Counter
from pathlib import Path


RESULTS_FILE = Path("can_test_results.csv")
SVG_FILE = Path("can_test_summary.svg")
REPORT_FILE = Path("CAN_VALIDATION_REPORT.md")


def load_results():
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(
            "can_test_results.csv not found. Run: python3 test_can_system.py"
        )

    with RESULTS_FILE.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("The results file contains no test data")

    return rows


def create_svg(passed, failed, errors, total):
    pass_rate = (passed / total * 100) if total else 0
    progress_width = 680 * pass_rate / 100

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
width="900" height="440" viewBox="0 0 900 440">
  <rect width="900" height="440" rx="24" fill="#0d1117"/>

  <text x="50" y="65" fill="#f0f6fc"
        font-family="Arial, sans-serif" font-size="30" font-weight="bold">
    Virtual CAN Bus and ECU Validation
  </text>

  <text x="50" y="100" fill="#8b949e"
        font-family="Arial, sans-serif" font-size="17">
    Automated communication, diagnostics and fault-injection tests
  </text>

  <rect x="50" y="140" width="240" height="150" rx="16"
        fill="#161b22" stroke="#238636" stroke-width="3"/>
  <text x="170" y="190" text-anchor="middle" fill="#8b949e"
        font-family="Arial, sans-serif" font-size="19">PASSED</text>
  <text x="170" y="260" text-anchor="middle" fill="#3fb950"
        font-family="Arial, sans-serif" font-size="58" font-weight="bold">
    {passed}
  </text>

  <rect x="330" y="140" width="240" height="150" rx="16"
        fill="#161b22" stroke="#da3633" stroke-width="3"/>
  <text x="450" y="190" text-anchor="middle" fill="#8b949e"
        font-family="Arial, sans-serif" font-size="19">FAILED</text>
  <text x="450" y="260" text-anchor="middle" fill="#f85149"
        font-family="Arial, sans-serif" font-size="58" font-weight="bold">
    {failed}
  </text>

  <rect x="610" y="140" width="240" height="150" rx="16"
        fill="#161b22" stroke="#d29922" stroke-width="3"/>
  <text x="730" y="190" text-anchor="middle" fill="#8b949e"
        font-family="Arial, sans-serif" font-size="19">ERRORS</text>
  <text x="730" y="260" text-anchor="middle" fill="#e3b341"
        font-family="Arial, sans-serif" font-size="58" font-weight="bold">
    {errors}
  </text>

  <text x="50" y="350" fill="#f0f6fc"
        font-family="Arial, sans-serif" font-size="20">Pass rate</text>
  <rect x="170" y="330" width="680" height="28" rx="14" fill="#30363d"/>
  <rect x="170" y="330" width="{progress_width:.1f}" height="28"
        rx="14" fill="#238636"/>
  <text x="850" y="405" text-anchor="end" fill="#3fb950"
        font-family="Arial, sans-serif" font-size="24" font-weight="bold">
    {pass_rate:.1f}%
  </text>
</svg>
"""

    SVG_FILE.write_text(svg, encoding="utf-8")
    return pass_rate


def safe(value):
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def create_report(rows, passed, failed, errors, total, pass_rate):
    table_rows = []

    for row in rows:
        table_rows.append(
            f"| {safe(row['test_id'])} | {safe(row['test_name'])} | "
            f"{safe(row['status'])} | {safe(row['details'])} |"
        )

    report = f"""# CAN and ECU Validation Report

![CAN validation summary](can_test_summary.svg)

## Summary

- **Total tests:** {total}
- **Passed:** {passed}
- **Failed:** {failed}
- **Errors:** {errors}
- **Pass rate:** {pass_rate:.1f}%

## Detailed Results

| Test ID | Test name | Status | Details |
|---|---|---|---|
{chr(10).join(table_rows)}

## Validation Scope

The automated suite validates standard CAN-message construction, arbitration-ID
and payload limits, ECU signal encoding, engine RPM, vehicle speed, coolant
temperature, diagnostic trouble-code behavior, message-drop injection, data
corruption and communication recovery.

## Important Note

This is a software-only CAN and ECU simulation. It demonstrates validation
methods without claiming experience with a physical CAN interface or vehicle.
"""

    REPORT_FILE.write_text(report, encoding="utf-8")


def main():
    rows = load_results()
    counts = Counter(row["status"].strip().upper() for row in rows)

    passed = counts.get("PASS", 0)
    failed = counts.get("FAIL", 0)
    errors = counts.get("ERROR", 0)
    total = len(rows)

    pass_rate = create_svg(passed, failed, errors, total)
    create_report(rows, passed, failed, errors, total, pass_rate)

    print("CAN VALIDATION REPORT GENERATED")
    print("=" * 45)
    print(f"Passed:    {passed}")
    print(f"Failed:    {failed}")
    print(f"Errors:    {errors}")
    print(f"Total:     {total}")
    print(f"Pass rate: {pass_rate:.1f}%")
    print(f"Created:   {SVG_FILE}")
    print(f"Created:   {REPORT_FILE}")


if __name__ == "__main__":
    main()
