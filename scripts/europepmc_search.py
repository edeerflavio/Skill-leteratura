#!/usr/bin/env python3
"""
Busca no Europe PMC (REST API, grátis, sem chave).
Cobre PubMed + Agricola + preprints + texto completo aberto + contagem de citações.

Uso:
  python europepmc_search.py "cardiac point of care ultrasound" --max 20 --json
  python europepmc_search.py "FAST exam trauma" --open-only --json

Saída JSON: registros com id/source, pmid, doi, title, journal, year, authors,
citedByCount, isOpenAccess, pubtypes e url. Só repassa o que a API retornou.
"""
import argparse
import json
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("Falta 'requests'. Rode: pip install -r requirements.txt")

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _get(params, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(BASE, params=params, timeout=30)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def search(query, max_results, open_only, years, sort):
    q = query
    if open_only:
        q += " AND OPEN_ACCESS:Y"
    if years:
        # Europe PMC aceita filtro por data de publicação
        q += f" AND (FIRST_PDATE:[{_year_floor(years)} TO 3000])"

    params = {
        "query": q,
        "format": "json",
        "pageSize": str(min(max_results, 100)),
        "resultType": "core",
    }
    # IMPORTANTE: o default já é por relevância. NÃO enviar "sort=RELEVANCE"
    # (valor inválido -> a API devolve resposta vazia). Só envie sort válido.
    if sort == "cited":
        params["sort"] = "CITED desc"
    elif sort == "date":
        params["sort"] = "P_PDATE_D desc"

    data = _get(params).json()

    hits = data.get("resultList", {}).get("result", [])
    total = data.get("hitCount", 0)
    out = []
    for h in hits[:max_results]:
        out.append({
            "id": h.get("id", ""),
            "source": h.get("source", ""),
            "pmid": h.get("pmid", ""),
            "doi": h.get("doi", ""),
            "title": (h.get("title", "") or "").rstrip("."),
            "journal": h.get("journalInfo", {}).get("journal", {}).get("title", "")
                       or h.get("bookOrReportDetails", {}).get("publisher", ""),
            "year": h.get("pubYear", ""),
            "authors": h.get("authorString", ""),
            "citedByCount": h.get("citedByCount", 0),
            "isOpenAccess": h.get("isOpenAccess", "N") == "Y",
            "pubtypes": h.get("pubTypeList", {}).get("pubType", []),
            "url": _url(h),
        })
    return out, total, q


def _url(h):
    doi = h.get("doi")
    if doi:
        return f"https://doi.org/{doi}"
    pmid = h.get("pmid")
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    src, hid = h.get("source", ""), h.get("id", "")
    if src and hid:
        return f"https://europepmc.org/article/{src}/{hid}"
    return ""


def _year_floor(years):
    # Aproxima "últimos N anos" sem usar data atual: usa o ano declarado pelo usuário.
    # Aqui usamos um piso simples baseado em offset; o assistente pode refinar a query.
    return f"NOW-{years}YEARS"


def main():
    # Console Windows (cp1252) quebra com acentos/JSON na saida; forca UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Busca Europe PMC (REST).")
    ap.add_argument("query")
    ap.add_argument("--max", type=int, default=20, dest="max_results")
    ap.add_argument("--open-only", action="store_true", help="só acesso aberto")
    ap.add_argument("--years", type=int, default=0, help="últimos N anos (FIRST_PDATE)")
    ap.add_argument("--sort", choices=["relevance", "cited", "date"],
                    default="relevance", help="ordenação (default: relevance)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        records, total, q = search(args.query, args.max_results, args.open_only,
                                    args.years, args.sort)
    except Exception as e:
        err = {"error": str(e), "source": "europepmc"}
        print(json.dumps(err, ensure_ascii=False) if args.json else f"ERRO Europe PMC: {e}")
        sys.exit(1)

    if args.json:
        print(json.dumps({
            "source": "europepmc",
            "query_used": q,
            "total_found": total,
            "returned": len(records),
            "records": records,
        }, ensure_ascii=False, indent=2))
        return

    print(f"Europe PMC — {total} encontrados, mostrando {len(records)} (query: {q})\n")
    for i, r in enumerate(records, 1):
        ids = []
        if r["pmid"]:
            ids.append(f"PMID {r['pmid']}")
        if r["doi"]:
            ids.append(f"DOI {r['doi']}")
        oa = " [OA]" if r["isOpenAccess"] else ""
        print(f"{i}. {r['title']} ({r['year']}){oa}")
        print(f"   {r['journal']} | citações: {r['citedByCount']}")
        print(f"   {' | '.join(ids) or 'sem ID'}\n   {r['url']}\n")


if __name__ == "__main__":
    main()
