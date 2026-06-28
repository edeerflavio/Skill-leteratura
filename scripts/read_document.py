#!/usr/bin/env python3
"""
Leitura e busca DENTRO de livros/artigos (PDF e EPUB) do acervo.

Filosofia anti-alucinação:
- Caminho principal é EXTRAÇÃO da camada de texto (fiel, sem erro de OCR).
- Páginas escaneadas (só imagem, sem texto) são marcadas como
  "[PÁGINA ESCANEADA — não legível sem OCR]". A ferramenta NUNCA inventa o
  conteúdo de uma página que não conseguiu ler.
- OCR é fallback opcional (--ocr), só nessas páginas. Veja a seção OCR abaixo.

Comandos (FLUXO TOC-FIRST recomendado: info -> toc -> search --pages -> text):
  python read_document.py info  <arquivo>
  python read_document.py toc   <arquivo> [--json]          # sumário/índice
  python read_document.py search <arquivo> "termo" [--pages 103-123] [--context 240] [--max 20] [--json]
  python read_document.py text  <arquivo> [--pages 10-25] [--ocr] [--json]

Por que TOC-first: veja o sumário (toc), ache o capítulo do tema e a faixa de
páginas, e busque SÓ ali (--pages). Mais preciso, mais barato, e a citação sai
com a página certa — em vez de varrer um livro de 900 páginas às cegas.

Suporta: .pdf (PyMuPDF) e .epub (zip + XHTML). Use com arquivos baixados via
telegram_books.py download.

OCR (opcional): requer um motor instalado. Detecção automática:
  - RapidOCR  (pip install rapidocr-onnxruntime)  -> sem binário de sistema
  - Tesseract (pip install pytesseract + binário tesseract-ocr no PATH)
Sem motor, --ocr apenas avisa quais páginas ficaram ilegíveis.
"""
import argparse
import html
import json
import os
import re
import sys
import zipfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SCAN_TEXT_THRESHOLD = 80  # < isso de chars "úteis" numa página => suspeita de scan


# ----------------------------- PDF (PyMuPDF) --------------------------------
def _open_pdf(path):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        sys.exit("Falta PyMuPDF. Rode: pip install pymupdf")
    return fitz.open(path)


def _parse_pages(spec, n):
    """'10-25' / '5' / '' -> lista de índices 0-based."""
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            a = int(a) if a else 1
            b = int(b) if b else n
            out.extend(range(a - 1, min(b, n)))
        else:
            out.append(int(part) - 1)
    return [i for i in out if 0 <= i < n]


def _page_is_scanned(page, text):
    """Escaneada = pouco/nenhum texto E há imagem cobrindo a página.
    Página em branco (sem texto e sem imagem) NÃO é escaneada — nada a OCR."""
    if len(text.strip()) >= SCAN_TEXT_THRESHOLD:
        return False
    try:
        return bool(page.get_images())
    except Exception:
        return False


def pdf_pages_text(path, page_spec, use_ocr):
    doc = _open_pdf(path)
    n = doc.page_count
    idxs = _parse_pages(page_spec, n)
    result = []
    ocr = _load_ocr() if use_ocr else None
    for i in idxs:
        page = doc[i]
        text = page.get_text()
        scanned = _page_is_scanned(page, text)
        if scanned:
            if ocr:
                text = _ocr_pdf_page(page, ocr)
                tag = "ocr"
            else:
                text = "[PÁGINA ESCANEADA — não legível sem OCR]"
                tag = "scanned-no-ocr"
        else:
            tag = "text"
        result.append({"page": i + 1, "mode": tag, "text": text})
    return {"file": os.path.basename(path), "pages_total": n,
            "pages_returned": [r["page"] for r in result], "content": result}


def pdf_info(path):
    doc = _open_pdf(path)
    n = doc.page_count
    scanned = 0
    sample = min(n, 60)  # amostra para não varrer livro inteiro
    for i in range(sample):
        page = doc[i]
        if _page_is_scanned(page, page.get_text()):
            scanned += 1
    meta = doc.metadata or {}
    return {
        "file": os.path.basename(path), "type": "pdf", "pages": n,
        "title": meta.get("title", ""), "author": meta.get("author", ""),
        "scanned_pages_in_sample": scanned, "sample_size": sample,
        "needs_ocr": scanned > 0,
    }


def pdf_search(path, term, context, max_hits, page_spec=""):
    doc = _open_pdf(path)
    hits = []
    pat = re.compile(re.escape(term), re.IGNORECASE)
    idxs = _parse_pages(page_spec, doc.page_count)  # vazio => todas
    for i in idxs:
        text = doc[i].get_text()
        for m in pat.finditer(text):
            a = max(0, m.start() - context // 2)
            b = min(len(text), m.end() + context // 2)
            snippet = re.sub(r"\s+", " ", text[a:b]).strip()
            hits.append({"page": i + 1, "snippet": snippet})
            if len(hits) >= max_hits:
                return _search_result(path, term, hits)
    return _search_result(path, term, hits)


# Palavras que marcam uma página de sumário/índice (PT/EN/ES)
_TOC_WORDS = ("sumário", "sumario", "índice", "indice", "conteúdo", "conteudo",
              "contents", "table of contents", "índice analítico")


def pdf_toc(path, max_scan=25):
    """Sumário do livro. 1º tenta a TOC embutida (outline); se vazia,
    procura uma PÁGINA de sumário nas primeiras páginas (heurística)."""
    doc = _open_pdf(path)
    n = doc.page_count
    toc = doc.get_toc(simple=True)  # [[nível, título, página], ...]
    if toc:
        entries = [{"level": lvl, "title": (title or "").strip(), "page": pg}
                   for lvl, title, pg in toc if (title or "").strip()]
        return {"file": os.path.basename(path), "pages_total": n,
                "source": "outline", "entries": entries}

    # Fallback: achar página cujo texto pareça um sumário
    best = None
    for i in range(min(max_scan, n)):
        text = doc[i].get_text()
        low = text.lower()
        if not any(w in low for w in _TOC_WORDS):
            continue
        # linhas terminando em número de página são forte sinal de sumário
        dotted = len(re.findall(r"\.{2,}\s*\d{1,4}\s*$", text, re.MULTILINE))
        trailing = len(re.findall(r"\S.*\s\d{1,4}\s*$", text, re.MULTILINE))
        score = dotted * 3 + trailing
        if best is None or score > best[1]:
            best = (i, score, text)
    if best and best[1] >= 5:
        i, _, text = best
        lines = [re.sub(r"\s+", " ", ln).strip()
                 for ln in text.splitlines() if ln.strip()]
        return {"file": os.path.basename(path), "pages_total": n,
                "source": f"contents-page-{i+1}", "entries": [],
                "contents_page": i + 1, "contents_text": "\n".join(lines)}

    return {"file": os.path.basename(path), "pages_total": n,
            "source": "none", "entries": [],
            "note": "Sem sumário embutido nem página de índice detectável; "
                    "use 'search' direto ou 'text --pages' por amostragem."}


# ------------------------------- EPUB ---------------------------------------
def _epub_chapters(path):
    out = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist()
                 if n.lower().endswith((".xhtml", ".html", ".htm"))]
        for name in sorted(names):
            raw = z.read(name).decode("utf-8", errors="replace")
            text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
            text = re.sub(r"(?s)<[^>]+>", " ", text)
            text = html.unescape(re.sub(r"\s+", " ", text)).strip()
            if text:
                out.append((name, text))
    return out


def epub_info(path):
    ch = _epub_chapters(path)
    chars = sum(len(t) for _, t in ch)
    return {"file": os.path.basename(path), "type": "epub",
            "chapters": len(ch), "chars": chars, "needs_ocr": False}


def epub_toc(path):
    """Sumário do EPUB: tenta toc.ncx/nav; senão, deriva título de cada capítulo."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        # 1) toc.ncx (EPUB2)
        ncx = next((n for n in names if n.lower().endswith(".ncx")), None)
        if ncx:
            raw = z.read(ncx).decode("utf-8", errors="replace")
            titles = re.findall(r"(?is)<navlabel>\s*<text>(.*?)</text>", raw)
            entries = [{"level": 1, "title": html.unescape(t).strip(), "page": None}
                       for t in titles if t.strip()]
            if entries:
                return {"file": os.path.basename(path), "source": "ncx",
                        "entries": entries}
    # 2) fallback: 1ª linha de cada capítulo
    ch = _epub_chapters(path)
    entries = []
    for i, (name, text) in enumerate(ch):
        title = (text[:80].strip() or name)
        entries.append({"level": 1, "title": title, "page": i + 1, "section": name})
    return {"file": os.path.basename(path), "source": "chapters", "entries": entries}


def epub_text(path, page_spec):
    ch = _epub_chapters(path)
    idxs = _parse_pages(page_spec, len(ch))
    content = [{"page": i + 1, "mode": "text", "section": ch[i][0],
                "text": ch[i][1]} for i in idxs]
    return {"file": os.path.basename(path), "pages_total": len(ch),
            "pages_returned": [c["page"] for c in content], "content": content}


def epub_search(path, term, context, max_hits, page_spec=""):
    ch = _epub_chapters(path)
    hits = []
    pat = re.compile(re.escape(term), re.IGNORECASE)
    allow = set(_parse_pages(page_spec, len(ch))) if page_spec else None
    for i, (name, text) in enumerate(ch):
        if allow is not None and i not in allow:
            continue
        for m in pat.finditer(text):
            a = max(0, m.start() - context // 2)
            b = min(len(text), m.end() + context // 2)
            hits.append({"page": i + 1, "section": name,
                         "snippet": text[a:b].strip()})
            if len(hits) >= max_hits:
                return _search_result(path, term, hits)
    return _search_result(path, term, hits)


# ------------------------------- OCR ----------------------------------------
def _load_ocr():
    """Retorna um callable(image_bytes_png)->str, ou None se nenhum motor."""
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()

        def _run(png_bytes):
            import numpy as np
            from PIL import Image
            import io
            img = np.array(Image.open(io.BytesIO(png_bytes)).convert("RGB"))
            res, _ = engine(img)
            return "\n".join(line[1] for line in res) if res else ""
        return _run
    except ImportError:
        pass
    try:
        import pytesseract
        from PIL import Image
        import io

        def _run(png_bytes):
            return pytesseract.image_to_string(
                Image.open(io.BytesIO(png_bytes)), lang="por+eng")
        return _run
    except ImportError:
        return None


def _ocr_pdf_page(page, ocr):
    pix = page.get_pixmap(dpi=300)
    return ocr(pix.tobytes("png")) or "[OCR não extraiu texto]"


# ----------------------------- dispatch -------------------------------------
def _search_result(path, term, hits):
    return {"file": os.path.basename(path), "term": term,
            "hit_count": len(hits), "hits": hits}


def _ext(path):
    return os.path.splitext(path)[1].lower()


def main():
    ap = argparse.ArgumentParser(description="Lê/busca em PDF e EPUB (anti-alucinação).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("file")
    common.add_argument("--json", action="store_true")

    sub.add_parser("info", parents=[common])
    sub.add_parser("toc", parents=[common])  # sumário/índice -> capítulos+páginas

    p_text = sub.add_parser("text", parents=[common])
    p_text.add_argument("--pages", default="", help="ex.: 10-25 ou 3 ou 1-5,40-42")
    p_text.add_argument("--ocr", action="store_true", help="OCR em páginas escaneadas")

    p_search = sub.add_parser("search", parents=[common])
    p_search.add_argument("term")
    p_search.add_argument("--context", type=int, default=240)
    p_search.add_argument("--max", type=int, default=20, dest="max_hits")
    p_search.add_argument("--pages", default="",
                          help="restringe a busca a um intervalo (use após ver a TOC)")

    args = ap.parse_args()
    if not os.path.isfile(args.file):
        sys.exit(f"Arquivo não encontrado: {args.file}")
    ext = _ext(args.file)
    if ext not in (".pdf", ".epub"):
        sys.exit(f"Formato não suportado: {ext} (use .pdf ou .epub)")

    if args.cmd == "info":
        out = pdf_info(args.file) if ext == ".pdf" else epub_info(args.file)
    elif args.cmd == "toc":
        out = pdf_toc(args.file) if ext == ".pdf" else epub_toc(args.file)
    elif args.cmd == "text":
        out = (pdf_pages_text(args.file, args.pages, args.ocr) if ext == ".pdf"
               else epub_text(args.file, args.pages))
    elif args.cmd == "search":
        out = (pdf_search(args.file, args.term, args.context, args.max_hits, args.pages)
               if ext == ".pdf"
               else epub_search(args.file, args.term, args.context, args.max_hits, args.pages))

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        _print_human(args.cmd, out)


def _print_human(cmd, out):
    if cmd == "info":
        for k, v in out.items():
            print(f"{k}: {v}")
    elif cmd == "toc":
        print(f"{out['file']} — sumário (fonte: {out['source']})")
        if out.get("note"):
            print(f"  {out['note']}")
        if out.get("contents_text"):
            print("\n--- página de sumário detectada (pág "
                  f"{out.get('contents_page')}) ---\n{out['contents_text']}")
        for e in out.get("entries", []):
            pg = f"  → pág {e['page']}" if e.get("page") else ""
            print(f"{'  ' * (e.get('level', 1) - 1)}• {e['title']}{pg}")
    elif cmd == "search":
        print(f"'{out['term']}' em {out['file']}: {out['hit_count']} ocorrências\n")
        for h in out["hits"]:
            loc = f"pág {h['page']}"
            print(f"[{loc}] …{h['snippet']}…\n")
    else:  # text
        print(f"{out['file']} — páginas {out['pages_returned']}\n")
        for c in out["content"]:
            print(f"===== pág {c['page']} ({c['mode']}) =====")
            print(c["text"])
            print()


if __name__ == "__main__":
    main()
