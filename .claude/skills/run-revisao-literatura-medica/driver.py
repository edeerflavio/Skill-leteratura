#!/usr/bin/env python3
"""
Driver / smoke test da skill `revisao-literatura-medica`.

Esta skill é um conjunto de ferramentas CLI em Python (sem GUI/servidor).
"Dirigir o app" = executar cada ferramenta com argumentos representativos e
conferir exit code + forma da saída JSON. É assim que um agente futuro valida,
de máquina limpa, que as ferramentas funcionam.

Uso:
  python driver.py smoke           # roda tudo (PubMed + Europe PMC + Telegram)
  python driver.py smoke --offline # pula os testes que precisam de rede
  python driver.py pubmed          # só PubMed
  python driver.py europepmc       # só Europe PMC
  python driver.py merge           # só dedup do merge_results (offline)
  python driver.py telegram        # só checagem do telegram_books (sem credencial)

Códigos de saída: 0 = todos os checks passaram; 1 = algum falhou.
Rede: PubMed e Europe PMC fazem chamadas reais (APIs grátis). Telegram NÃO faz
login — apenas confirma que a ferramenta falha de forma limpa sem credenciais
(ou, se TELEGRAM_* estiver setado, que aceita os comandos).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

# unit root = .../revisao-literatura-medica (3 níveis acima deste arquivo:
# run-.../  -> skills/ -> .claude/ -> <unit>)
UNIT = Path(__file__).resolve().parents[3]
SCRIPTS = UNIT / "scripts"
PY = sys.executable

GREEN, RED, DIM, RST = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def run(args, timeout=60, stdin=None):
    """Executa um script e devolve (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [PY, *args], cwd=str(SCRIPTS),
        capture_output=True, text=True, timeout=timeout, input=stdin,
    )
    return proc.returncode, proc.stdout, proc.stderr


def check(name, ok, detail=""):
    mark = f"{GREEN}PASS{RST}" if ok else f"{RED}FAIL{RST}"
    print(f"  [{mark}] {name}" + (f"  {DIM}{detail}{RST}" if detail else ""))
    return ok


def test_pubmed():
    print("PubMed (chamada real à API NCBI):")
    rc, out, err = run(["pubmed_search.py",
                        "lung ultrasound pneumothorax diagnostic accuracy",
                        "--max", "3", "--years", "5", "--json"])
    if not check("exit code 0", rc == 0, err.strip()[:120]):
        return False
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        return check("saída é JSON válido", False, str(e))
    ok = check("saída é JSON válido", True)
    ok &= check("source == pubmed", data.get("source") == "pubmed")
    recs = data.get("records", [])
    ok &= check("retornou registros", len(recs) > 0, f"{len(recs)} registros")
    if recs:
        r = recs[0]
        ok &= check("registro tem PMID", bool(r.get("pmid")), f"PMID {r.get('pmid')}")
        ok &= check("registro tem título", bool(r.get("title")))
    return ok


def test_europepmc():
    print("Europe PMC (chamada real à API EBI):")
    rc, out, err = run(["europepmc_search.py",
                        "RUSH protocol shock ultrasound",
                        "--max", "3", "--json"])
    if not check("exit code 0", rc == 0, err.strip()[:120]):
        return False
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        return check("saída é JSON válido", False, str(e))
    ok = check("saída é JSON válido", True)
    ok &= check("source == europepmc", data.get("source") == "europepmc")
    # regressão conhecida: sort inválido fazia a API devolver 0 — garantir >0
    total = int(data.get("total_found", 0) or 0)
    ok &= check("total_found > 0 (regressão do sort)", total > 0, f"total={total}")
    ok &= check("retornou registros", len(data.get("records", [])) > 0)
    return ok


def test_openalex():
    print("OpenAlex (chamada real à API):")
    rc, out, err = run(["openalex_search.py", "point of care lung ultrasound",
                        "--max", "3", "--json"])
    if not check("exit code 0", rc == 0, err.strip()[:120]):
        return False
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        return check("saída é JSON válido", False, str(e))
    ok = check("source == openalex", data.get("source") == "openalex")
    ok &= check("total_found > 0", int(data.get("total_found", 0) or 0) > 0,
                f"total={data.get('total_found')}")
    recs = data.get("records", [])
    ok &= check("retornou registros com título", bool(recs and recs[0].get("title")))
    return ok


def test_verify():
    print("verify_citations.py (real + fabricado):")
    # PMID real -> all_verified True
    rc, out, err = run(["verify_citations.py", "--pmid", "39375782", "--json"])
    ok = check("real: exit 0", rc == 0, err.strip()[:120])
    try:
        data = json.loads(out)
        ok &= check("real: all_verified True", data.get("all_verified") is True)
    except json.JSONDecodeError as e:
        ok &= check("real: JSON válido", False, str(e))
    # PMID fabricado -> exit 1, all_verified False
    rc, out, err = run(["verify_citations.py", "--pmid", "99999999", "--json"])
    ok &= check("fabricado: exit != 0 (trava publicação)", rc != 0, f"rc={rc}")
    try:
        data = json.loads(out)
        ok &= check("fabricado: all_verified False", data.get("all_verified") is False)
        c0 = data["results"][0]["checks"][0]
        ok &= check("fabricado: exists False", c0.get("exists") is False)
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        ok &= check("fabricado: JSON esperado", False, str(e))
    return ok


def test_unpaywall():
    print("unpaywall_resolve.py (robustez):")
    rc, out, err = run(["unpaywall_resolve.py", "--help"])
    ok = check("--help funciona", rc == 0, err.strip()[:80] or out.strip()[:50])
    if os.environ.get("UNPAYWALL_EMAIL") or os.environ.get("OPENALEX_EMAIL") \
            or os.environ.get("NCBI_EMAIL"):
        rc, out, err = run(["unpaywall_resolve.py", "--doi",
                            "10.1186/s13054-024-05102-y", "--json"])
        try:
            r = json.loads(out)["results"][0]
            ok &= check("resolve DOI OA conhecido", r.get("is_oa") is True,
                        f"oa_status={r.get('oa_status')}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            ok &= check("resolve retornou JSON", False, str(e))
    else:
        rc, out, err = run(["unpaywall_resolve.py", "--doi", "10.1/x"])
        msg = out + err
        ok &= check("falha limpa sem UNPAYWALL_EMAIL",
                    rc != 0 and "EMAIL" in msg.upper(),
                    "(defina UNPAYWALL_EMAIL p/ testar resolução real)")
    return ok


def test_reader():
    print("read_document.py (PDF nativo gerado na hora):")
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return check("PyMuPDF instalado", False, "pip install pymupdf")
    check("PyMuPDF instalado", True)
    # cria um PDF de 1 página com texto conhecido, em pasta temporária
    import tempfile
    tmp = Path(tempfile.gettempdir()) / "_reader_smoke.pdf"
    doc = fitz.open()
    for _ in range(3):
        doc.new_page()
    doc[0].insert_text((72, 72), "POCUS lung ultrasound B-lines")
    doc[1].insert_text((72, 72), "Chapter on pneumothorax and lung point")
    doc.set_toc([[1, "Intro", 1], [1, "Pneumothorax", 2]])  # sumário embutido
    doc.save(str(tmp))
    doc.close()
    # toc deve extrair o sumário embutido
    rc, out, err = run(["read_document.py", "toc", str(tmp), "--json"])
    ok = check("toc exit 0", rc == 0, err.strip()[:120])
    try:
        t = json.loads(out)
        titles = [e.get("title") for e in t.get("entries", [])]
        ok &= check("toc lê outline embutido", t.get("source") == "outline"
                    and "Pneumothorax" in titles, f"entries={titles}")
    except json.JSONDecodeError:
        ok &= check("toc é JSON válido", False)
    # search restrito ao 'capítulo' (pág 2) deve achar a palavra lá
    rc, out, err = run(["read_document.py", "search", str(tmp),
                        "pneumothorax", "--pages", "2", "--json"])
    ok &= check("search --pages exit 0", rc == 0, err.strip()[:120])
    try:
        data = json.loads(out)
        ok &= check("achou ocorrência no capítulo", data.get("hit_count", 0) > 0)
        hits = data.get("hits", [])
        ok &= check("ocorrência na página certa (2)",
                    bool(hits and hits[0].get("page") == 2),
                    f"pág {hits[0].get('page') if hits else '—'}")
    except json.JSONDecodeError as e:
        ok &= check("saída é JSON válido", False, str(e))
    # info deve reportar PDF nativo (needs_ocr False)
    rc, out, err = run(["read_document.py", "info", str(tmp), "--json"])
    try:
        info = json.loads(out)
        ok &= check("info: PDF nativo (needs_ocr False)", info.get("needs_ocr") is False)
    except json.JSONDecodeError:
        ok &= check("info é JSON válido", False)
    try:
        tmp.unlink()
    except OSError:
        pass
    return ok


def test_merge():
    print("merge_results.py (dedup offline com JSON sintético):")
    # mesmo artigo em 3 fontes, com IDs em formatos diferentes + 1 exclusivo
    payload = json.dumps([
        {"source": "pubmed", "records": [
            {"pmid": "39375782", "doi": "10.1016/j.chest.2024.01.001",
             "title": "Lung ultrasound for pneumothorax.", "year": "2024"},
            {"pmid": "30000001", "title": "FAST exam in trauma", "year": "2019"},
        ]},
        {"source": "europepmc", "records": [
            {"pmid": "39375782", "doi": "https://doi.org/10.1016/J.CHEST.2024.01.001",
             "title": "Lung ultrasound for pneumothorax", "year": "2024",
             "isOpenAccess": True, "citedByCount": 12},
        ]},
        {"source": "openalex", "records": [
            {"doi": "10.1016/j.chest.2024.01.001", "title": "Lung Ultrasound for Pneumothorax",
             "year": "2024", "type": "review", "cited_by_count": 15,
             "is_oa": True, "oa_url": "https://example.org/pdf"},
        ]},
    ])
    rc, out, err = run(["merge_results.py", "--stdin", "--json"], stdin=payload)
    ok = check("exit 0", rc == 0, err.strip()[:120])
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        return ok & check("saída é JSON válido", False, str(e))
    ok &= check("4 registros -> 2 únicos", data.get("unique") == 2,
                f"unique={data.get('unique')}, raw={data.get('raw_total')}")
    ok &= check("2 duplicatas fundidas", data.get("duplicates_merged") == 2)
    recs = data.get("records", [])
    top = recs[0] if recs else {}
    ok &= check("artigo fundido nas 3 fontes",
                set(top.get("sources", [])) == {"pubmed", "europepmc", "openalex"},
                f"sources={top.get('sources')}")
    ok &= check("DOI/PMID normalizados e preenchidos",
                top.get("doi") == "10.1016/j.chest.2024.01.001"
                and top.get("pmid") == "39375782")
    ok &= check("is_oa propagado e citações por máximo",
                top.get("is_oa") is True and top.get("cited_by_count") == 15)
    return ok


def test_telegram():
    print("telegram_books.py (sem login — checagem de robustez):")
    has_creds = bool(os.environ.get("TELEGRAM_API_ID") and
                     os.environ.get("TELEGRAM_API_HASH"))
    # 1) --help sempre deve funcionar (telethon importável)
    rc, out, err = run(["telegram_books.py", "--help"])
    ok = check("--help funciona (telethon instalado)", rc == 0,
               err.strip()[:120] or out.strip()[:60])
    if has_creds:
        print(f"  {DIM}(TELEGRAM_* detectado — pulando teste de falha sem credencial){RST}")
        return ok
    # 2) sem credencial, 'login' deve falhar de forma limpa (rc!=0, msg clara)
    rc, out, err = run(["telegram_books.py", "login"])
    msg = (out + err)
    ok &= check("falha limpa sem credencial", rc != 0 and "TELEGRAM_API_ID" in msg,
                msg.strip().splitlines()[-1][:90] if msg.strip() else "")
    return ok


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    offline = "--offline" in sys.argv

    if not SCRIPTS.is_dir():
        print(f"{RED}ERRO{RST}: pasta de scripts não encontrada em {SCRIPTS}")
        sys.exit(2)

    print(f"{DIM}unit: {UNIT}{RST}\n")
    results = []

    if cmd in ("smoke", "pubmed") and not (offline and cmd == "smoke"):
        results.append(test_pubmed())
    if cmd in ("smoke", "europepmc") and not (offline and cmd == "smoke"):
        results.append(test_europepmc())
    if cmd in ("smoke", "openalex") and not (offline and cmd == "smoke"):
        results.append(test_openalex())
    if cmd in ("smoke", "verify") and not (offline and cmd == "smoke"):
        results.append(test_verify())
    if cmd in ("smoke", "unpaywall"):
        results.append(test_unpaywall())
    if cmd in ("smoke", "reader"):
        results.append(test_reader())
    if cmd in ("smoke", "merge"):
        results.append(test_merge())
    if cmd in ("smoke", "telegram"):
        results.append(test_telegram())

    if not results:
        print("nada a rodar (verifique o comando)")
        sys.exit(2)

    print()
    if all(results):
        print(f"{GREEN}== TODOS OS CHECKS PASSARAM =={RST}")
        sys.exit(0)
    print(f"{RED}== ALGUM CHECK FALHOU =={RST}")
    sys.exit(1)


if __name__ == "__main__":
    main()
