#!/usr/bin/env python3
"""
Resolve um DOI para o melhor PDF de ACESSO ABERTO via Unpaywall (grátis).
Serve para ler o TEXTO COMPLETO de artigos que vêm do PubMed/Europe PMC sem
link OA — e, com --download, já baixa o PDF para ler com read_document.py
(TOC-first), citando a página.

Unpaywall exige um e-mail de contato (polite pool). Defina:
  export UNPAYWALL_EMAIL="voce@exemplo.com"   # ou OPENALEX_EMAIL / NCBI_EMAIL

Uso:
  python unpaywall_resolve.py --doi 10.1186/s13054-024-05102-y --json
  python unpaywall_resolve.py --doi 10.1186/s13054-024-05102-y --download --out ../downloads
  echo '["10.1186/s13054-024-05102-y","10.1002/jum.16088"]' | \
      python unpaywall_resolve.py --stdin --json

Saída por DOI: is_oa, oa_status (gold/green/hybrid/bronze/closed), pdf_url, url,
host_type, version. Só repassa o que a API retornou.
"""
import argparse
import json
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("Falta 'requests'. Rode: pip install -r requirements.txt")

BASE = "https://api.unpaywall.org/v2"
EMAIL = (os.environ.get("UNPAYWALL_EMAIL") or os.environ.get("OPENALEX_EMAIL")
         or os.environ.get("NCBI_EMAIL") or "")


def _clean_doi(doi):
    return doi.strip().replace("https://doi.org/", "").replace("doi:", "").lstrip("/")


def _get(url, params=None, retries=3, stream=False):
    for attempt in range(retries):
        try:
            return requests.get(url, params=params, timeout=40, stream=stream)
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(1.3 * (attempt + 1))
    raise RuntimeError("unreachable")


def resolve(doi):
    doi = _clean_doi(doi)
    r = _get(f"{BASE}/{doi}", params={"email": EMAIL})
    if r.status_code == 404:
        return {"doi": doi, "is_oa": False, "status": "nao_encontrado"}
    if r.status_code != 200:
        return {"doi": doi, "is_oa": None, "status": "erro", "http": r.status_code}
    d = r.json()
    best = d.get("best_oa_location") or {}
    return {
        "doi": doi,
        "is_oa": d.get("is_oa", False),
        "oa_status": d.get("oa_status", ""),
        "title": d.get("title", ""),
        "year": d.get("year", ""),
        "journal": d.get("journal_name", ""),
        "pdf_url": best.get("url_for_pdf") or "",
        "url": best.get("url") or "",
        "host_type": best.get("host_type", ""),
        "version": best.get("version", ""),
        "status": "ok" if d.get("is_oa") else "fechado",
    }


def download(pdf_url, doi, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", doi)
    path = os.path.join(out_dir, f"{safe}.pdf")
    r = _get(pdf_url, stream=True)
    ctype = r.headers.get("Content-Type", "")
    if r.status_code != 200:
        return {"downloaded": False, "http": r.status_code}
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
    size = os.path.getsize(path)
    looks_pdf = ("pdf" in ctype.lower()) or _is_pdf(path)
    return {"downloaded": True, "path": path, "size_bytes": size,
            "content_type": ctype, "looks_like_pdf": looks_pdf}


def _is_pdf(path):
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser(description="Resolve DOI -> PDF de acesso aberto (Unpaywall).")
    ap.add_argument("--doi", action="append", default=[])
    ap.add_argument("--stdin", action="store_true", help="lê lista JSON de DOIs do stdin")
    ap.add_argument("--download", action="store_true", help="baixa o PDF OA")
    ap.add_argument("--out", default="../downloads")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not EMAIL:
        sys.exit("Defina UNPAYWALL_EMAIL (ou OPENALEX_EMAIL/NCBI_EMAIL) — "
                 "a API do Unpaywall exige um e-mail de contato.")

    dois = list(args.doi)
    if args.stdin:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            sys.exit(f"stdin não é JSON válido: {e}")
        dois += data if isinstance(data, list) else [data]
    if not dois:
        sys.exit("Nada para resolver. Use --doi ou --stdin.")

    results = []
    for doi in dois:
        rec = resolve(doi)
        if args.download and rec.get("pdf_url"):
            rec["download"] = download(rec["pdf_url"], rec["doi"], args.out)
            time.sleep(0.3)
        results.append(rec)
        time.sleep(0.2)

    if args.json:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            tag = "OA" if r.get("is_oa") else "fechado"
            print(f"[{tag}] {r['doi']} ({r.get('oa_status') or '-'})")
            if r.get("pdf_url"):
                print(f"   PDF: {r['pdf_url']}")
            if r.get("download", {}).get("downloaded"):
                d = r["download"]
                print(f"   baixado: {d['path']} ({d['size_bytes']/1e6:.1f} MB, "
                      f"pdf={d['looks_like_pdf']})")


if __name__ == "__main__":
    main()
