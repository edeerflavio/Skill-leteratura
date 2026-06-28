#!/usr/bin/env python3
"""
Busca no PubMed/MEDLINE via NCBI E-utilities (esearch + esummary).
Sem chave funciona; defina NCBI_API_KEY no ambiente para cota maior.

Uso:
  python pubmed_search.py "point of care ultrasound sepsis" --max 20 --json
  python pubmed_search.py "lung ultrasound pneumothorax" --years 5 --json

Saída JSON: lista de registros com pmid, doi, title, journal, year, authors,
pubtypes (desenho do estudo) e url. NUNCA inventa dados — só repassa o que a
API retornou. Se a API não retornar um campo, ele vem vazio/null.
"""
import argparse
import datetime
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("Falta 'requests'. Rode: pip install -r requirements.txt")

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "medlit-review"
EMAIL = os.environ.get("NCBI_EMAIL", "")
API_KEY = os.environ.get("NCBI_API_KEY", "")


def _params(extra):
    p = {"tool": TOOL}
    if EMAIL:
        p["email"] = EMAIL
    if API_KEY:
        p["api_key"] = API_KEY
    p.update(extra)
    return p


def _get(path, params, retries=3):
    url = f"{EUTILS}/{path}"
    for attempt in range(retries):
        try:
            r = requests.get(url, params=_params(params), timeout=30)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def search(query, max_results, years, lang):
    term = query
    if years:
        term += f' AND ("last {years} years"[PDat])'
    if lang:
        term += f" AND {lang}[Language]"

    es = _get("esearch.fcgi", {
        "db": "pubmed",
        "term": term,
        "retmax": str(max_results),
        "retmode": "json",
        "sort": "relevance",
    }).json()

    idlist = es.get("esearchresult", {}).get("idlist", [])
    total = es.get("esearchresult", {}).get("count", "0")
    if not idlist:
        return [], total, term

    # esummary em lote
    time.sleep(0.34)  # respeita rate limit sem api_key
    su = _get("esummary.fcgi", {
        "db": "pubmed",
        "id": ",".join(idlist),
        "retmode": "json",
    }).json()

    result = su.get("result", {})
    out = []
    for pmid in idlist:
        rec = result.get(pmid)
        if not rec:
            continue
        doi = ""
        for aid in rec.get("articleids", []):
            if aid.get("idtype") == "doi":
                doi = aid.get("value", "")
                break
        authors = [a.get("name", "") for a in rec.get("authors", [])]
        year = ""
        pubdate = rec.get("pubdate", "")
        if pubdate:
            year = pubdate.split(" ")[0]
        out.append({
            "pmid": pmid,
            "doi": doi,
            "title": rec.get("title", "").rstrip("."),
            "journal": rec.get("fulljournalname", "") or rec.get("source", ""),
            "year": year,
            "authors": authors[:6] + (["et al."] if len(authors) > 6 else []),
            "pubtypes": rec.get("pubtype", []),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return out, total, term


def trend(query, n_years):
    """Contagem de publicações por ano (últimos n_years) para o tema.
    Sinaliza se é um tema 'quente' (crescente) ou estável. Conta via esearch
    com retmax=0 por ano — não baixa registros."""
    this_year = datetime.date.today().year
    start = this_year - n_years + 1
    series = []
    for yr in range(start, this_year + 1):
        es = _get("esearch.fcgi", {
            "db": "pubmed",
            "term": f"({query}) AND {yr}[PDat]",
            "retmax": "0",
            "retmode": "json",
        }).json()
        count = int(es.get("esearchresult", {}).get("count", "0"))
        series.append({"year": yr, "count": count})
        time.sleep(0.34)  # rate limit sem api_key
    return series


def main():
    # Console Windows (cp1252) quebra com acentos/JSON na saida; forca UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Busca PubMed/MEDLINE (E-utilities).")
    ap.add_argument("query", help="termos de busca (pode usar sintaxe MeSH/PubMed)")
    ap.add_argument("--max", type=int, default=20, dest="max_results")
    ap.add_argument("--years", type=int, default=0, help="restringe aos últimos N anos")
    ap.add_argument("--lang", default="", help="ex.: english, portuguese")
    ap.add_argument("--trend", action="store_true",
                    help="mostra publicações por ano (volume do tema)")
    ap.add_argument("--trend-years", type=int, default=12, dest="trend_years")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    args = ap.parse_args()

    if args.trend:
        try:
            series = trend(args.query, args.trend_years)
        except Exception as e:
            err = {"error": str(e), "source": "pubmed", "mode": "trend"}
            print(json.dumps(err, ensure_ascii=False) if args.json else f"ERRO PubMed: {e}")
            sys.exit(1)
        if args.json:
            print(json.dumps({"source": "pubmed", "mode": "trend",
                              "query": args.query, "trend": series},
                             ensure_ascii=False, indent=2))
            return
        peak = max((s["count"] for s in series), default=0) or 1
        print(f"PubMed — publicações/ano para: {args.query}\n")
        for s in series:
            bar = "█" * round(40 * s["count"] / peak)
            print(f"  {s['year']}  {s['count']:>6}  {bar}")
        total_all = sum(s["count"] for s in series)
        print(f"\n  total no período: {total_all}")
        return

    try:
        records, total, term = search(args.query, args.max_results, args.years, args.lang)
    except Exception as e:
        err = {"error": str(e), "source": "pubmed"}
        print(json.dumps(err, ensure_ascii=False) if args.json else f"ERRO PubMed: {e}")
        sys.exit(1)

    if args.json:
        print(json.dumps({
            "source": "pubmed",
            "query_used": term,
            "total_found": total,
            "returned": len(records),
            "records": records,
        }, ensure_ascii=False, indent=2))
        return

    print(f"PubMed — {total} encontrados, mostrando {len(records)} (query: {term})\n")
    for i, r in enumerate(records, 1):
        ids = f"PMID {r['pmid']}" + (f" | DOI {r['doi']}" if r['doi'] else "")
        print(f"{i}. {r['title']} ({r['year']})")
        print(f"   {r['journal']} | {', '.join(r['pubtypes']) or '—'}")
        print(f"   {ids}\n   {r['url']}\n")


if __name__ == "__main__":
    main()
