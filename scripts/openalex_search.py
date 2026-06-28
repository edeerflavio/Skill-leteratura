#!/usr/bin/env python3
"""
Busca no OpenAlex (https://openalex.org) — 3ª fonte grátis, sem chave.
Útil para CORROBORAÇÃO CRUZADA (achado que aparece em PubMed + Europe PMC +
OpenAlex tem confiança maior), contagem de citações e link de ACESSO ABERTO
(oa_url) — que dá para baixar e ler com read_document.py (TOC-first).

Boa prática: defina OPENALEX_EMAIL para entrar no "polite pool" (mais estável).

Uso:
  python openalex_search.py "point of care lung ultrasound" --max 15 --json
  python openalex_search.py "RUSH protocol shock" --since 2021 --oa-only --json
  python openalex_search.py "FAST exam trauma" --sort cited --json

Saída por registro: title, doi, year, journal, cited_by_count, is_oa, oa_url,
authors, type, url. Só repassa o que a API retornou.
"""
import argparse
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("Falta 'requests'. Rode: pip install -r requirements.txt")

BASE = "https://api.openalex.org/works"
EMAIL = os.environ.get("OPENALEX_EMAIL") or os.environ.get("NCBI_EMAIL") or ""


def _get(params, retries=3):
    if EMAIL:
        params["mailto"] = EMAIL
    for attempt in range(retries):
        try:
            r = requests.get(BASE, params=params, timeout=30)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(1.3 * (attempt + 1))
    raise RuntimeError("unreachable")


def search(query, max_results, since_year, oa_only, sort):
    filters = []
    if since_year:
        filters.append(f"from_publication_date:{since_year}-01-01")
    if oa_only:
        filters.append("is_oa:true")
    params = {
        "search": query,
        "per_page": str(min(max_results, 200)),
    }
    if filters:
        params["filter"] = ",".join(filters)
    if sort == "cited":
        params["sort"] = "cited_by_count:desc"
    elif sort == "date":
        params["sort"] = "publication_date:desc"
    # default: relevance_score (quando há 'search')

    data = _get(params).json()
    total = data.get("meta", {}).get("count", 0)
    out = []
    for w in data.get("results", [])[:max_results]:
        authors = [a.get("author", {}).get("display_name", "")
                   for a in w.get("authorships", [])]
        oa = w.get("open_access", {}) or {}
        loc = w.get("primary_location", {}) or {}
        src = (loc.get("source") or {})
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        out.append({
            "title": (w.get("title") or "").rstrip("."),
            "doi": doi,
            "year": w.get("publication_year", ""),
            "journal": src.get("display_name", ""),
            "type": w.get("type", ""),
            "cited_by_count": w.get("cited_by_count", 0),
            "is_oa": oa.get("is_oa", False),
            "oa_url": oa.get("oa_url", "") or "",
            "authors": authors[:6] + (["et al."] if len(authors) > 6 else []),
            "url": (f"https://doi.org/{doi}" if doi
                    else w.get("id", "")),
        })
    return out, total, params


def main():
    # Console Windows (cp1252) quebra com acentos/JSON na saida; forca UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Busca OpenAlex (grátis).")
    ap.add_argument("query")
    ap.add_argument("--max", type=int, default=15, dest="max_results")
    ap.add_argument("--since", type=int, default=0, help="ano mínimo (ex.: 2021)")
    ap.add_argument("--oa-only", action="store_true", help="só acesso aberto")
    ap.add_argument("--sort", choices=["relevance", "cited", "date"],
                    default="relevance")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        records, total, used = search(args.query, args.max_results, args.since,
                                      args.oa_only, args.sort)
    except Exception as e:
        err = {"error": str(e), "source": "openalex"}
        print(json.dumps(err, ensure_ascii=False) if args.json else f"ERRO OpenAlex: {e}")
        sys.exit(1)

    if args.json:
        print(json.dumps({"source": "openalex", "filter": used.get("filter", ""),
                          "total_found": total, "returned": len(records),
                          "records": records}, ensure_ascii=False, indent=2))
        return

    print(f"OpenAlex — {total} encontrados, mostrando {len(records)}\n")
    for i, r in enumerate(records, 1):
        oa = f" [OA: {r['oa_url']}]" if r["is_oa"] and r["oa_url"] else (
            " [OA]" if r["is_oa"] else "")
        print(f"{i}. {r['title']} ({r['year']}){oa}")
        print(f"   {r['journal']} | {r['type']} | citações: {r['cited_by_count']}")
        print(f"   {('DOI ' + r['doi']) if r['doi'] else r['url']}\n")


if __name__ == "__main__":
    main()
