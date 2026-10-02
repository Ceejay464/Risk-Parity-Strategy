# Validation record

Verification date: October 2, 2026. Executable calculations are preserved; reader-facing source text is translated. Exact original files are archived.
The checks below do not establish independent reproduction of previously reported historical performance.

## Completed checks

- SHA-256 integrity of exact original archives and unchanged market data; executable source structure compared after excluding reader text.
- Executable structure of 67 original notebook code cells compared; displayed prose is translated and execution counts retained.
- Approved teaser copied byte for byte; risk parity uses the final corrected version.
- Python syntax, notebook JSON structure, and local documentation links checked.
- All five base local entry points completed, with data kind and engine identified in the report.
- `python -m unittest discover -s tests -v`: 8 checks passed.

## Lightweight demonstration

The original strategy class completed 640 synthetic daily slices and 1238 fills.
Additional checks cover fill-callback position/cash updates, balanced actual risk contributions, and the 300-bar initialization gate.

Native vn.py was not installed. Native entry-point syntax, help, and missing-dependency messages were checked, but complete native backtesting remains unverified. No adapter/native matching equivalence is claimed.

## Environment and limits

Python 3.13.1, NumPy 2.4.4, pandas 3.0.2, and openpyxl 3.1.5.

Data-vendor provenance, adjustment conventions, exchange calendars, option executability, and original reported returns were not independently validated. Original notebooks requiring absent modules were not reexecuted. HTML structure and links were checked without browser screenshot validation. New reports are table-only.

## English-edition checks

36 original Python sources and 67 notebook code cells passed executable-structure comparisons. All 15 custom-engine baseline cases matched original equity and trades exactly. Both portfolio daily-adapter comparisons matched equity, trades, saved strategy states, and pending orders exactly. This verifies translation behavior on the supplied inputs and demos; it does not establish historical performance or native vn.py equivalence.
