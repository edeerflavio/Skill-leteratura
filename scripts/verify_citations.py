#!/usr/bin/env python3
"""
Verificador de citações (anti-alucinação). Confirma que cada PMID/DOI que a
skill pretende citar EXISTE de verdade em fontes autoritativas, e compara o
título informado com o título real (pega PMID/DOI "trocado" ou inventado).

Fontes (grátis, sem chave):
- DOI  -> CrossRef  (https://api.crossref.org/works/{doi})
- PMID -> NCBI eSummary (PubMed)

Uso:
  # itens individuais
  python verify_citations.py --pmid 39375782 --doi 10.1186/s13054-024-05102-y
  python verify_citations.py --pmid 99999999 --title "Foo bar" --json

  # lote: pipe de um JSON [{ "pmid": "...", "doi": "...", "title": "..." }, ...]
  echo '[{"pmid":"39375782","title":"Nuts and bolts of lung ultrasound"}]' | \
      python verify_citations.py --stdin --json

Saída por item: exists (bool), source, found_title, title_match (true/false/null),
status e (para títulos) title_check / title_overlap / shared_anchors.

Status possíveis:
  ok                   -> existe e título bate (ou nenhum título informado).
  nao_encontrado       -> ID não existe (citação fabricada/trocada). BLOQUEIA.
  titulo_divergente    -> ID existe mas o título informado CONFLITA com o real
                          (mesma língua, vocabulário comparável). BLOQUEIA.
  titulo_nao_conferido -> ID existe; título não pôde ser comparado (idioma
                          diferente/paráfrase, ex.: alegação em PT-BR vs título
                          em inglês). NÃO bloqueia — é aviso "confira manualmente"
                          (veja shared_anchors p/ siglas em comum como BLUE/VCI).
  erro                 -> falha de rede/HTTP.

Exit code != 0 quando há item BLOQUEANTE (nao_encontrado/titulo_divergente/erro).
'needs_review' no JSON conta os títulos a conferir manualmente.
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

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CROSSREF = "https://api.crossref.org/works"
MAILTO = os.environ.get("NCBI_EMAIL") or os.environ.get("OPENALEX_EMAIL") or ""
UA = f"medlit-review (mailto:{MAILTO})" if MAILTO else "medlit-review"
NCBI_KEY = os.environ.get("NCBI_API_KEY", "")


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower())


_STOP = {"the", "a", "an", "of", "for", "and", "or", "in", "on", "to", "with",
         "versus", "vs", "by", "from", "de", "da", "do", "e", "para", "em",
         "um", "uma", "que", "no", "na", "dos", "das"}


def _anchors(s):
    """Tokens 'salientes' que sobrevivem a paráfrase/tradução: SIGLAS em caixa
    alta (BLUE, FAST, VCI, RUSH, POCUS) e números/anos. Servem de âncora para
    distinguir 'título correto em outro idioma' de 'ID trocado'."""
    out = set()
    for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]*", s or ""):
        if re.fullmatch(r"\d[\d.\-]*", t):
            out.add(t.lower())
        elif len(t) >= 2 and t.isupper():
            out.add(t.lower())
    return out


def _title_relation(given, found):
    """Compara o título informado com o título real e classifica em 3 estados:

    - 'match'        : sobreposição alta (containment >= 0.7) -> status ok.
    - 'divergent'    : títulos CLARAMENTE comparáveis (mesma língua, vocabulário
                       em comum suficiente) mas que CONFLITAM -> ID provavelmente
                       trocado. Bloqueia.
    - 'unverifiable' : pouca/nenhuma sobreposição de palavras. Quase sempre é
                       título em outro idioma ou parafraseado (o curador escreve
                       a alegação em PT-BR) — NÃO é prova de ID trocado. Vira
                       aviso 'confira manualmente', não bloqueio.

    Retorna dict com rel, containment, termos e âncoras em comum.
    """
    base = {"rel": "no_title", "containment": None, "shared": [], "anchors": []}
    if not given or not found:
        return base
    a = set(_norm(given).split()) - _STOP
    b = set(_norm(found).split()) - _STOP
    if not a or not b:
        return base
    inter = sorted(a & b)
    containment = len(inter) / min(len(a), len(b))
    anchors = sorted(_anchors(given) & _anchors(found))
    if containment >= 0.7:
        rel = "match"
    else:
        union = a | b
        jaccard = len(inter) / len(union) if union else 0.0
        # Só afirmamos DIVERGÊNCIA quando há vocabulário em comum suficiente para
        # garantir que os títulos são comparáveis (mesma língua) e ainda assim
        # discordam. Caso contrário, é incomparável -> aviso, não bloqueio.
        if len(inter) >= 3 and jaccard >= 0.30:
            rel = "divergent"
        else:
            rel = "unverifiable"
    return {"rel": rel, "containment": round(containment, 2),
            "shared": inter, "anchors": anchors}


# rel -> (status, title_match)
_REL_STATUS = {
    "match": ("ok", True),
    "divergent": ("titulo_divergente", False),
    "unverifiable": ("titulo_nao_conferido", None),
    "no_title": ("ok", None),
}

# Statuses que TRAVAM publicação (exit != 0). 'titulo_nao_conferido' é aviso.
BLOCKING = {"nao_encontrado", "titulo_divergente", "erro"}


def _get(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=30)
            return r
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError("unreachable")


def verify_doi(doi, given_title):
    doi = doi.strip().replace("https://doi.org/", "").lstrip("/")
    r = _get(f"{CROSSREF}/{doi}")
    if r.status_code == 404:
        return {"type": "doi", "id": doi, "exists": False, "source": "crossref",
                "status": "nao_encontrado"}
    if r.status_code != 200:
        return {"type": "doi", "id": doi, "exists": None, "source": "crossref",
                "status": "erro", "http": r.status_code}
    msg = r.json().get("message", {})
    found = (msg.get("title") or [""])[0]
    year = ""
    issued = msg.get("issued", {}).get("date-parts", [[None]])
    if issued and issued[0] and issued[0][0]:
        year = str(issued[0][0])
    rel = _title_relation(given_title, found)
    status, tmatch = _REL_STATUS[rel["rel"]]
    return {"type": "doi", "id": doi, "exists": True, "source": "crossref",
            "found_title": found, "year": year,
            "journal": (msg.get("container-title") or [""])[0],
            "title_match": tmatch, "title_check": rel["rel"],
            "title_overlap": rel["containment"], "shared_terms": rel["shared"],
            "shared_anchors": rel["anchors"], "status": status}


def verify_pmid(pmid, given_title):
    pmid = str(pmid).strip()
    params = {"db": "pubmed", "id": pmid, "retmode": "json", "tool": "medlit-review"}
    if MAILTO:
        params["email"] = MAILTO
    if NCBI_KEY:
        params["api_key"] = NCBI_KEY
    r = _get(f"{EUTILS}/esummary.fcgi", params)
    if r.status_code != 200:
        return {"type": "pmid", "id": pmid, "exists": None, "source": "pubmed",
                "status": "erro", "http": r.status_code}
    result = r.json().get("result", {})
    rec = result.get(pmid)
    # PMID inexistente costuma vir com 'error' ou sem entrada útil
    if not rec or rec.get("error") or (not rec.get("title") and not rec.get("uids")):
        return {"type": "pmid", "id": pmid, "exists": False, "source": "pubmed",
                "status": "nao_encontrado"}
    found = (rec.get("title") or "").rstrip(".")
    rel = _title_relation(given_title, found)
    status, tmatch = _REL_STATUS[rel["rel"]]
    return {"type": "pmid", "id": pmid, "exists": True, "source": "pubmed",
            "found_title": found, "year": (rec.get("pubdate", "") or "").split(" ")[0],
            "journal": rec.get("fulljournalname", "") or rec.get("source", ""),
            "title_match": tmatch, "title_check": rel["rel"],
            "title_overlap": rel["containment"], "shared_terms": rel["shared"],
            "shared_anchors": rel["anchors"], "status": status}


def verify_item(item):
    out = []
    if item.get("doi"):
        out.append(verify_doi(item["doi"], item.get("title", "")))
        time.sleep(0.2)
    if item.get("pmid"):
        out.append(verify_pmid(item["pmid"], item.get("title", "")))
        time.sleep(0.34)
    if not out:
        out.append({"type": "?", "id": None, "exists": None,
                    "status": "erro", "note": "sem pmid nem doi"})
    return out


def main():
    # Console Windows (cp1252) quebra com ✓ e acentos no modo texto; força UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Verifica se PMIDs/DOIs citados existem.")
    ap.add_argument("--pmid", action="append", default=[])
    ap.add_argument("--doi", action="append", default=[])
    ap.add_argument("--title", default="", help="título esperado (1 item)")
    ap.add_argument("--stdin", action="store_true", help="lê lista JSON do stdin")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    items = []
    if args.stdin:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            sys.exit(f"stdin não é JSON válido: {e}")
        items = data if isinstance(data, list) else [data]
    else:
        # combina pmids e dois soltos; --title aplica ao 1º item
        for i, p in enumerate(args.pmid):
            items.append({"pmid": p, "title": args.title if i == 0 else ""})
        for i, d in enumerate(args.doi):
            if i < len(items):
                items[i]["doi"] = d
            else:
                items.append({"doi": d, "title": args.title if not items else ""})
    if not items:
        sys.exit("Nada para verificar. Use --pmid/--doi ou --stdin.")

    results = []
    blocking = False
    needs_review = 0
    for item in items:
        checks = verify_item(item)
        for c in checks:
            st = c.get("status")
            if st in BLOCKING:
                blocking = True
            elif st == "titulo_nao_conferido":
                needs_review += 1
        results.append({"input": item, "checks": checks})

    all_ok = not blocking
    if args.json:
        print(json.dumps({"all_verified": all_ok, "needs_review": needs_review,
                          "results": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            for c in r["checks"]:
                icon = {"ok": "OK ", "nao_encontrado": "FALSO",
                        "titulo_divergente": "DIVERG", "titulo_nao_conferido": "REVISAR",
                        "erro": "ERRO"}.get(c.get("status"), "?")
                line = f"[{icon}] {c['type'].upper()} {c.get('id')}"
                if c.get("found_title"):
                    line += f" — {c['found_title'][:70]}"
                if c.get("status") == "titulo_divergente":
                    line += "  (título informado NÃO bate!)"
                elif c.get("status") == "titulo_nao_conferido":
                    anc = c.get("shared_anchors") or []
                    line += ("  (título não conferível automaticamente"
                             + (f"; âncoras em comum: {', '.join(anc)}" if anc else "")
                             + " — confira manualmente)")
                print(line)
        tail = "TODAS VERIFICADAS ✓" if all_ok else "ATENÇÃO: há citações não confirmadas ✗"
        if needs_review:
            tail += f"  [{needs_review} título(s) p/ conferência manual]"
        print("\n" + tail)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
