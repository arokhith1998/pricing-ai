# data/

| Folder | Contents | Git |
|---|---|---|
| `synthetic/` | Generated demo data (`python -m pricing.generate`). Safe to share. | **committed** |
| `private/` | Real customer/partner CSVs delivered under NDA. | **gitignored** (only `.gitkeep` is tracked) |

## Running the diagnostic on a real CSV

A partner's export goes in `data/private/` and never leaves it for git. The
diagnostic and dashboard take any path:

```powershell
$env:PYTHONPATH = "."
python -m pricing.diagnostic data/private/<partner>-deals.csv
streamlit run app/dashboard.py   # then set the path in the sidebar
```

The CSV must satisfy the required columns in `pricing/schema.py` (see
`gtm/data-request.md` for the prospect-facing version). `ingest.validate()`
raises a clear error listing any missing required columns, so a partial or
mis-mapped export fails loudly rather than silently. Handle this data under the
NDA at `docs/legal/one-page-mutual-nda-data-addendum.md`.
