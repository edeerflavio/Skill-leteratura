#!/usr/bin/env python3
"""
Acessa o acervo de livros médicos em um grupo/canal do Telegram (via Telethon).
Permite buscar, listar e baixar documentos (PDF/EPUB/etc.) para servir de
referência de livro-texto na revisão.

Pré-requisitos (uma vez):
  1) pip install -r requirements.txt
  2) Pegue API_ID e API_HASH em https://my.telegram.org  -> "API development tools"
  3) Exporte:
       export TELEGRAM_API_ID=123456
       export TELEGRAM_API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
       export TELEGRAM_BOOKS_CHAT="@meu_grupo_de_livros"   # ou id numérico, ou t.me/...
  4) Na 1ª execução, o Telethon pede seu telefone + código (login interativo).
     A sessão fica salva em scripts/.tg_books.session (NÃO versionar / não compartilhar).

Comandos:
  python telegram_books.py login
  python telegram_books.py search "echocardiography" --max 20 --json
  python telegram_books.py list --max 30 --json
  python telegram_books.py download --id 12345 --out ./downloads --json
  python telegram_books.py chats --json        # ajuda a descobrir o id/nome do grupo

Segurança: este script usa SUA conta de usuário. Use só em grupos que você
participa legitimamente. Respeite direitos autorais ao redistribuir conteúdo.
"""
import argparse
import json
import os
import sys

# Console do Windows costuma ser cp1252 e quebra ao imprimir emoji/acentos
# (nomes de grupos e arquivos de livros têm 🩺, ✅, acentos, etc.). Força UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

try:
    from telethon.sync import TelegramClient
    from telethon.tl.types import (
        InputMessagesFilterDocument,
        DocumentAttributeFilename,
    )
except ImportError:
    sys.exit("Falta 'telethon'. Rode: pip install -r requirements.txt")

SESSION = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tg_books")
API_ID = os.environ.get("TELEGRAM_API_ID", "")
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
DEFAULT_CHAT = os.environ.get("TELEGRAM_BOOKS_CHAT", "")


def _need_creds():
    if not API_ID or not API_HASH:
        sys.exit("Defina TELEGRAM_API_ID e TELEGRAM_API_HASH (veja my.telegram.org).")
    try:
        return int(API_ID)
    except ValueError:
        sys.exit("TELEGRAM_API_ID deve ser numérico.")


def _client():
    api_id = _need_creds()
    return TelegramClient(SESSION, api_id, API_HASH)


def _filename(msg):
    doc = getattr(msg, "document", None)
    if not doc:
        return None
    for attr in doc.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            return attr.file_name
    return f"doc_{msg.id}"


def _chat(arg_chat):
    chat = arg_chat or DEFAULT_CHAT
    if not chat:
        sys.exit("Informe o grupo: --chat ou env TELEGRAM_BOOKS_CHAT.")
    # tenta interpretar id numérico
    try:
        return int(chat)
    except (ValueError, TypeError):
        return chat


def cmd_login(args):
    with _client() as client:
        me = client.get_me()
        out = {"ok": True, "user": getattr(me, "username", None) or me.first_name}
        _emit(out, args.json, f"Login ok como {out['user']}. Sessão salva.")


def cmd_chats(args):
    with _client() as client:
        dialogs = []
        for d in client.iter_dialogs(limit=args.max_results):
            if d.is_group or d.is_channel:
                dialogs.append({
                    "id": d.id,
                    "name": d.name,
                    "type": "group" if d.is_group else "channel",
                })
        _emit({"chats": dialogs}, args.json,
              "\n".join(f"{c['id']}\t{c['type']}\t{c['name']}" for c in dialogs))


def cmd_search(args):
    chat = _chat(args.chat)
    with _client() as client:
        results = []
        for msg in client.iter_messages(
            chat,
            search=args.query,
            filter=InputMessagesFilterDocument,
            limit=args.max_results,
        ):
            fn = _filename(msg)
            results.append({
                "id": msg.id,
                "filename": fn,
                "size_bytes": getattr(msg.document, "size", None),
                "date": msg.date.isoformat() if msg.date else None,
                "caption": (msg.message or "")[:200],
            })
        _emit({"chat": str(chat), "query": args.query, "results": results},
              args.json, _fmt_files(results))


def cmd_list(args):
    chat = _chat(args.chat)
    with _client() as client:
        results = []
        for msg in client.iter_messages(
            chat, filter=InputMessagesFilterDocument, limit=args.max_results
        ):
            results.append({
                "id": msg.id,
                "filename": _filename(msg),
                "size_bytes": getattr(msg.document, "size", None),
                "date": msg.date.isoformat() if msg.date else None,
            })
        _emit({"chat": str(chat), "results": results}, args.json, _fmt_files(results))


def cmd_download(args):
    chat = _chat(args.chat)
    os.makedirs(args.out, exist_ok=True)
    with _client() as client:
        msg = client.get_messages(chat, ids=args.id)
        if not msg or not getattr(msg, "document", None):
            _emit({"error": "mensagem sem documento", "id": args.id}, args.json,
                  f"ERRO: mensagem {args.id} não tem documento.")
            sys.exit(1)
        path = client.download_media(msg, file=args.out)
        out = {"id": args.id, "filename": _filename(msg), "path": path}
        _emit(out, args.json, f"Baixado: {path}")


def _fmt_files(results):
    if not results:
        return "(nenhum arquivo)"
    lines = []
    for r in results:
        mb = f"{r['size_bytes']/1e6:.1f} MB" if r.get("size_bytes") else "?"
        lines.append(f"[id {r['id']}] {r.get('filename')}  ({mb})")
    return "\n".join(lines)


def _emit(obj, as_json, text):
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))
    else:
        print(text)


def main():
    # Parsers "pai" para que --json e --chat funcionem DEPOIS do subcomando
    # (uso natural: `telegram_books.py search "x" --json`).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true")
    chat_opt = argparse.ArgumentParser(add_help=False)
    chat_opt.add_argument("--chat", default="", help="grupo/canal (id, @nome ou link)")

    ap = argparse.ArgumentParser(description="Acervo de livros médicos no Telegram.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login", parents=[common])

    p_chats = sub.add_parser("chats", help="lista seus grupos/canais", parents=[common])
    p_chats.add_argument("--max", type=int, default=100, dest="max_results")

    p_search = sub.add_parser("search", help="busca documentos por palavra",
                              parents=[common, chat_opt])
    p_search.add_argument("query")
    p_search.add_argument("--max", type=int, default=20, dest="max_results")

    p_list = sub.add_parser("list", help="lista documentos recentes",
                            parents=[common, chat_opt])
    p_list.add_argument("--max", type=int, default=30, dest="max_results")

    p_dl = sub.add_parser("download", help="baixa um documento por id de mensagem",
                          parents=[common, chat_opt])
    p_dl.add_argument("--id", type=int, required=True)
    p_dl.add_argument("--out", default="./downloads")

    args = ap.parse_args()
    if not hasattr(args, "chat"):
        args.chat = ""
    dispatch = {
        "login": cmd_login, "chats": cmd_chats, "search": cmd_search,
        "list": cmd_list, "download": cmd_download,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
