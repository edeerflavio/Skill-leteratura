#!/usr/bin/env python3
"""
Funde e DEDUPLICA resultados de pubmed_search.py, europepmc_search.py e
openalex_search.py. As três bases retornam o mesmo artigo com identificadores
diferentes; este script normaliza DOI/PMID/PMCID/título, junta as duplicatas em
um registro único e marca em quais fontes apareceu.

Entrada: um ou mais arquivos JSON gerados com `--json` (envelope
{"source": ..., "records": [...]}), ou uma lista crua de registros, ou via stdin.

Uso:
  python pubmed_search.py "lung ultrasound pneumothorax" --max 20 --json > pm.json
  python europepmc_search.py "lung ultrasound pneumothorax" --max 20 --json > ep.json
  python openalex_search.py "lung ultrasound pneumothorax" --since 2021 --json > oa.json
  python merge_results.py pm.json ep.json oa.json --json
  python merge_results.py pm.json ep.json oa.json            # tabela markdown
  cat *.json | python merge_results.py --stdin --json

Saída por registro: title, year, journal, doi, pmid, pmcid, sources (lista),
is_oa, oa_url, cited_by_count, study_type, url, priority. Só repassa o que as
buscas trouxeram — não inventa identificadores nem metadados.
"""
import argparse
import json
import re
import sys

# ── normalização de identificadores ──────────────────────────────────────────

def norm_doi(doi):
    if not doi:
        return ""
    d = str(doi).strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = d.replace("doi:", "").strip()
    return d


def norm_pmid(pmid):
    if not pmid:
        return ""
    m = re.search(r"\d+", str(pmid))
    return m.group(0) if m else ""


def norm_pmcid(pmcid):
    if not pmcid:
        return ""
    m = re.search(r"\d+", str(pmcid))
    return ("PMC" + m.group(0)) if m else ""


def norm_title(title):
    if not title:
        return ""
    t = str(title).lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)  # remove pontuação/acentuação ascii
    return re.sub(r"\s+", " ", t).strip()


# ── normalização de registro (campos variam por fonte) ───────────────────────

def normalize(rec, source):
    """Converte um registro de qualquer fonte ao esquema unificado."""
    is_oa = rec.get("is_oa")
    if is_oa is None:
        is_oa = rec.get("isOpenAccess")  # europepmc
    cited = rec.get("cited_by_count")
    if cited is None:
        cited = rec.get("citedByCount", 0)  # europepmc
    study_type = rec.get("type") or ""
    if not study_type and rec.get("pubtypes"):  # europepmc
        study_type = ", ".join(rec.get("pubtypes") or [])
    return {
        "title": (rec.get("title") or "").strip(),
        "year": rec.get("year") or "",
        "journal": rec.get("journal") or "",
        "doi": norm_doi(rec.get("doi")),
        "pmid": norm_pmid(rec.get("pmid")),
        "pmcid": norm_pmcid(rec.get("pmcid")),
        "sources": [source] if source else [],
        "is_oa": bool(is_oa),
        "oa_url": rec.get("oa_url") or "",
        "cited_by_count": int(cited or 0),
        "study_type": study_type,
        "url": rec.get("url") or "",
    }


def _dispatch(data, fallback_source):
    """Resolve um valor JSON em pares (source, records). Aceita envelope
    {source, records}, lista de envelopes, lista de registros, ou dict único."""
    if isinstance(data, dict) and "records" in data:
        yield data.get("source", fallback_source), data["records"]
    elif isinstance(data, list):
        # lista de envelopes ({...,"records":[...]}) vs lista crua de registros
        if data and all(isinstance(x, dict) and "records" in x for x in data):
            for env in data:
                yield env.get("source", fallback_source), env["records"]
        else:
            yield fallback_source, data
    elif isinstance(data, dict):
        yield data.get("source", fallback_source), [data]


def load_payload(text, fallback_source):
    """Lê um ou mais valores JSON concatenados (ex.: `cat *.json`) e devolve
    uma lista de pares (source, records)."""
    dec = json.JSONDecoder()
    pairs = []
    idx, n = 0, len(text)
    while idx < n:
        while idx < n and text[idx].isspace():
            idx += 1
        if idx >= n:
            break
        data, end = dec.raw_decode(text, idx)
        pairs.extend(_dispatch(data, fallback_source))
        idx = end
    return pairs


# ── dedup ────────────────────────────────────────────────────────────────────

def dedup_key(r):
    """Chave de identidade: DOI > PMID > PMCID > título normalizado."""
    return r["doi"] or r["pmid"] or r["pmcid"] or norm_title(r["title"])


def merge_into(dst, src):
    """Funde src em dst, preferindo preencher campos vazios e unir fontes."""
    for s in src["sources"]:
        if s not in dst["sources"]:
            dst["sources"].append(s)
    for fld in ("doi", "pmid", "pmcid", "year", "journal", "oa_url",
                "study_type", "url", "title"):
        if not dst[fld] and src[fld]:
            dst[fld] = src[fld]
    dst["is_oa"] = dst["is_oa"] or src["is_oa"]
    dst["cited_by_count"] = max(dst["cited_by_count"], src["cited_by_count"])


def priority(r):
    """Score heurístico p/ ordenar a 2ª passada. Documentado, não definitivo.

    Pesa: corroboração entre bases > tipo de estudo (síntese/RCT/diretriz) >
    acesso aberto (lê-se o texto completo) > recência > citações.
    """
    score = 0.0
    score += 3.0 * len(r["sources"])  # aparece em mais bases = mais confiável
    st = (r["study_type"] or "").lower()
    if any(k in st for k in ("systematic", "meta-analysis", "review", "guideline",
                             "revisão", "diretriz", "consensus")):
        score += 4.0
    elif any(k in st for k in ("randomized", "rct", "trial")):
        score += 3.0
    if r["is_oa"]:
        score += 2.0  # dá pra ler e citar a página
    try:
        yr = int(str(r["year"])[:4])
        score += max(0.0, (yr - 2018) * 0.5)  # leve bônus de recência
    except (ValueError, TypeError):
        pass
    cited = r["cited_by_count"]
    if cited > 0:
        import math
        score += min(3.0, math.log10(cited + 1))
    return round(score, 2)


def merge(files, stdin):
    by_key = {}
    order = []
    inputs = []
    if stdin:
        inputs.append(("stdin", sys.stdin.read()))
    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            inputs.append((path, fh.read()))

    raw_total = 0
    for label, text in inputs:
        text = text.strip()
        if not text:
            continue
        for src, records in load_payload(text, label):
            for rec in records:
                n = normalize(rec, src)
                raw_total += 1
                key = dedup_key(n)
                if not key:
                    key = f"_noid_{len(order)}"  # sem nenhum id: não funde
                if key in by_key:
                    merge_into(by_key[key], n)
                else:
                    by_key[key] = n
                    order.append(key)

    merged = [by_key[k] for k in order]
    for r in merged:
        r["priority"] = priority(r)
    merged.sort(key=lambda r: r["priority"], reverse=True)
    return merged, raw_total


# ── saída ─────────────────────────────────────────────────────────────────────

def as_markdown(merged, raw_total, dups):
    extra = (raw_total - dups) - len(merged)  # removidos por filtro (ex.: --min-year)
    note = f", {extra} filtrados" if extra > 0 else ""
    lines = [
        f"**{len(merged)} únicos** de {raw_total} registros "
        f"({dups} duplicatas fundidas{note})",
        "",
        "| # | Prior. | Ano | Título | Fontes | OA | PMID | DOI | Cit. |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(merged, 1):
        title = r["title"][:70] + ("..." if len(r["title"]) > 70 else "")
        title = title.replace("|", "\\|")
        oa = "OA" if r["is_oa"] else ""
        lines.append(
            f"| {i} | {r['priority']} | {r['year']} | {title} | "
            f"{'+'.join(r['sources'])} | {oa} | {r['pmid']} | {r['doi']} | "
            f"{r['cited_by_count']} |"
        )
    return "\n".join(lines)


def main():
    # Console Windows (cp1252) quebra com acentos/JSON na saida; forca UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(
        description="Funde e deduplica resultados de PubMed/Europe PMC/OpenAlex.")
    ap.add_argument("files", nargs="*", help="JSONs gerados com --json")
    ap.add_argument("--stdin", action="store_true",
                    help="lê também um JSON colado/pipe pela entrada padrão")
    ap.add_argument("--min-year", type=int,
                    help="descarta registros anteriores a este ano")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    args = ap.parse_args()

    if not args.files and not args.stdin:
        ap.error("informe ao menos um arquivo JSON ou use --stdin")

    try:
        merged, raw_total = merge(args.files, args.stdin)
    except (OSError, json.JSONDecodeError) as e:
        err = {"error": str(e)}
        print(json.dumps(err, ensure_ascii=False) if args.json
              else f"ERRO ao ler entrada: {e}")
        sys.exit(1)

    dups = raw_total - len(merged)  # antes de qualquer filtro

    if args.min_year:
        kept = []
        for r in merged:
            try:
                if int(str(r["year"])[:4]) >= args.min_year:
                    kept.append(r)
            except (ValueError, TypeError):
                kept.append(r)  # sem ano legível: mantém (não esconde evidência)
        merged = kept

    if args.json:
        print(json.dumps({
            "raw_total": raw_total,
            "unique": len(merged),
            "duplicates_merged": raw_total - len(merged),
            "records": merged,
        }, ensure_ascii=False, indent=2))
    else:
        print(as_markdown(merged, raw_total, dups))


if __name__ == "__main__":
    main()
