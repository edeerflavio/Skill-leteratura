---
name: run-revisao-literatura-medica
description: >
  Build, run, smoke-test, and drive the `revisao-literatura-medica` skill — the
  evidence-based / anti-hallucination medical literature tools for curating a
  broad, general medical reference app (primary care to ICU). Use when asked to run, launch, build, test, smoke-test, verify, or
  exercise these tools (pubmed_search, europepmc_search, telegram_books) from a
  clean machine. It is a set of Python CLI tools (no GUI/server); the driver
  runs each against real APIs and checks output.
---

# Run: revisao-literatura-medica

This "unit" is **not** a GUI or server — it's three Python **CLI tools** plus a
SKILL.md of instructions. "Driving the app" therefore means **invoking each tool
with representative args and checking exit code + JSON shape**. The driver
`.claude/skills/run-revisao-literatura-medica/driver.py` does exactly that.

> Paths below are relative to the unit root `revisao-literatura-medica/`.

The tools:
- `scripts/pubmed_search.py` — PubMed/MEDLINE via NCBI E-utilities (free, no key)
- `scripts/europepmc_search.py` — Europe PMC via REST (free, no key)
- `scripts/openalex_search.py` — OpenAlex (free, no key): cross-corroboration,
  citation counts, open-access PDF URLs
- `scripts/verify_citations.py` — checks that cited PMIDs/DOIs actually exist
  (CrossRef + NCBI), flags fabricated/mismatched references; exit≠0 if any fail
- `scripts/unpaywall_resolve.py` — DOI → open-access PDF (resolve + `--download`);
  needs `UNPAYWALL_EMAIL`
- `scripts/pubmed_search.py --trend` — publication counts per year (topic volume)
- `scripts/telegram_books.py` — user's Telegram medical-book archive (Telethon)
- `scripts/read_document.py` — read/search inside downloaded PDF/EPUB books
  (PyMuPDF text extraction; TOC-first; RapidOCR fallback for scanned pages)

## Prerequisites

Python 3.10+ and the two runtime deps. From the unit root:

```bash
python -m pip install -r scripts/requirements.txt
```

That installs `requests` (PubMed/Europe PMC), `telethon` (Telegram), and
`pymupdf` (read_document). No OS packages, no GPU, no display — headless CLI
tools. Optional OCR (scanned PDFs only): `pip install rapidocr-onnxruntime pillow`.

## Build

None. Pure Python, nothing to compile. Setup = the `pip install` above.

## Run (agent path) — the driver

Run the smoke test. It makes **real** calls to the free PubMed and Europe PMC
APIs and confirms the Telegram tool fails cleanly without credentials:

```bash
python .claude/skills/run-revisao-literatura-medica/driver.py smoke
```

Expected tail on success (exit code 0):

```
== TODOS OS CHECKS PASSARAM ==
```

Driver subcommands (all verified):

```bash
python .claude/skills/run-revisao-literatura-medica/driver.py smoke           # all tools
python .claude/skills/run-revisao-literatura-medica/driver.py smoke --offline # skip network (PubMed/EuropePMC)
python .claude/skills/run-revisao-literatura-medica/driver.py pubmed          # PubMed only
python .claude/skills/run-revisao-literatura-medica/driver.py europepmc       # Europe PMC only
python .claude/skills/run-revisao-literatura-medica/driver.py openalex        # OpenAlex only
python .claude/skills/run-revisao-literatura-medica/driver.py verify          # citation verifier only
python .claude/skills/run-revisao-literatura-medica/driver.py reader          # read_document only (offline)
python .claude/skills/run-revisao-literatura-medica/driver.py telegram        # Telegram robustness only
```

Use `--offline` when the container has no network — it runs only the Telegram
robustness check (which needs no network) and still exits 0.

## Run the tools directly

Same invocations the driver makes, if you want raw output. Run from the unit root:

```bash
python scripts/pubmed_search.py "lung ultrasound pneumothorax diagnostic accuracy" --max 3 --years 5 --json
python scripts/europepmc_search.py "RUSH protocol shock ultrasound" --max 3 --json
python scripts/openalex_search.py "point of care lung ultrasound" --max 3 --json
python scripts/verify_citations.py --pmid 39375782 --json   # exit 0 (real) / exit 1 (fabricado)
python scripts/telegram_books.py --help
python scripts/read_document.py info <arquivo.pdf>
python scripts/read_document.py toc <arquivo.pdf> --json
python scripts/read_document.py search <arquivo.pdf> "pneumothorax" --pages 103-123 --json
```

Telegram needs setup before any real command — see
`scripts/README_TELEGRAM.md` (env vars `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`,
`TELEGRAM_BOOKS_CHAT`, then a one-time interactive `login`).

## Test

There is no separate unit-test suite; the driver **is** the test. `smoke`
returns exit 0 when every tool works.

## Gotchas

- **Europe PMC + `sort=RELEVANCE` = empty results.** The EBI API silently
  returns a body with only `{"version": ...}` (no `hitCount`, no results) when
  given the invalid value `sort=RELEVANCE`. Relevance is already the default —
  so `europepmc_search.py` sends **no** `sort` param unless you pass
  `--sort cited`/`--sort date`. The driver asserts `total_found > 0` to catch
  this regression. If you "improve" the script, do not re-add a relevance sort.
- **`--sort cited` on a broad query returns off-topic megahits.** Sorting purely
  by citation count drops relevance ranking, so a vague query surfaces famous
  unrelated papers (UK Biobank, etc.). Use `--sort cited` only with a *specific*
  query; default (relevance) is right for most curation work.
- **PubMed has no API key here.** It works, but is rate-limited to ~3 req/s. The
  script already sleeps `0.34s` between esearch and esummary. Set `NCBI_API_KEY`
  to raise the cap; not required for the smoke.
- **Windows console (cp1252) crashes on emoji/accents.** Telegram group names and
  book filenames contain emoji (🩺, ⚡️) and accents. Printing them on the default
  Windows code page raises `UnicodeEncodeError: 'charmap' codec can't encode`.
  `telegram_books.py` now forces `sys.stdout/stderr.reconfigure(encoding="utf-8")`
  at import. If you pipe its JSON into **another** Python on Windows, also export
  `PYTHONIOENCODING=utf-8` for that consumer, or it crashes on print.
- **Global flags must work after the subcommand.** `--json`/`--chat` are attached
  to each subparser (via `parents=`), so `telegram_books.py search "x" --json`
  works. Argparse does **not** let a top-level-only flag appear after the
  subcommand — an earlier version failed with "unrecognized arguments: --json".
- **git-bash `/tmp` ≠ Windows-Python path.** Redirecting to `/tmp/x.json` in
  git-bash then opening `'/tmp/x.json'` from Windows `python` fails
  (`FileNotFoundError`). Use a relative file in the cwd for both ends.
- **Telegram cannot be fully driven headless.** It uses *your* user account and a
  one-time interactive phone-code login. The driver only verifies the tool is
  importable (`--help`) and **fails cleanly** without creds — it never attempts a
  real login. Don't expect the smoke to list or download books.
- **`.tg_books.session` is a secret.** A successful login writes it under
  `scripts/`; it grants access to the user's Telegram account. It's gitignored —
  keep it that way.
- **`verify_citations.py` exits non-zero by design.** Exit 1 means "at least one
  citation not confirmed" — that's the success signal for catching a fabricated
  reference, not a crash. Statuses: `ok`, `nao_encontrado` (fabricated),
  `titulo_divergente` (real ID, wrong title). Run it before publishing anything.
- **OpenAlex: don't send `sort=relevance` literally.** Like Europe PMC, relevance
  is the implicit default when `search=` is present; the script only sets `sort`
  for `--sort cited`/`--sort date`. Broad query + `--sort cited` surfaces famous
  off-topic megahits — use a specific query.
- **Read books TOC-first, never blind.** `read_document.py toc` pulls the PDF's
  embedded outline (verified on a real 954-page textbook: full chapter list with
  page numbers). Pick the relevant chapter's page range, then
  `search "<term>" --pages <a-b>` searches only there. Falls back to detecting a
  "Contents/Sumário" page when there's no embedded outline; `source: none` means
  neither exists — only then search the whole document.
- **Blank pages are not scanned pages.** `_page_is_scanned` flags a page only
  when it has little/no text **and** an embedded image. A truly empty page
  (no text, no image) is *not* flagged for OCR — an earlier version wrongly set
  `needs_ocr: True` for blank pages.
- **Most medical PDFs are text-native — don't OCR them.** Journal articles and
  modern ebooks have a real text layer; `read_document.py` extracts it directly
  (faithful, no OCR errors). OCR only kicks in for scanned/image-only pages,
  which `info` flags as `needs_ocr: True`. A scanned page with no `--ocr` returns
  the literal marker `[PÁGINA ESCANEADA — não legível sem OCR]` — by design, so
  the agent never fabricates unread content.
- **OCR engine is RapidOCR (pip-only).** `pip install rapidocr-onnxruntime pillow`
  — no system binary. First `--ocr` call downloads ~10MB of ONNX models. The
  reader auto-detects RapidOCR, else Tesseract (`pytesseract`), else reports the
  page unreadable. Verified: a scanned test page OCR'd back to its exact text.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Falta 'requests'` / `Falta 'telethon'` | `python -m pip install -r scripts/requirements.txt` |
| Europe PMC check shows `total=0` | An invalid `sort` was sent — see first Gotcha; remove it. |
| PubMed/Europe PMC test fails with a network error | No outbound network. Run with `--offline` (covers Telegram only). |
| Telegram `--help` fails with `Falta 'telethon'` | telethon not installed — run the `pip install` above. |
| `telegram_books.py login` says "Defina TELEGRAM_API_ID…" | Expected without creds. For real use, set the env vars per `scripts/README_TELEGRAM.md`. |
