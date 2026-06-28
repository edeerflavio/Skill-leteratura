# Grupos de Telegram (MODELO — copie para telegram-groups.md e preencha)

> O arquivo real `telegram-groups.md` é **ignorado pelo git** (privacidade —
> contém IDs/nomes dos seus grupos). Este `.example.md` é só o modelo.

Descubra seus grupos rodando:

```
python scripts/telegram_books.py chats --json
```

Copie os IDs/nome relevantes para `references/telegram-groups.md` no formato:

## Mais relevantes para POCUS
| Grupo | id | Conteúdo observado |
|---|---|---|
| <nome do grupo POCUS> | `-100xxxxxxxxxx` | artigos/livros de POCUS |
| <nome do grupo de eco> | `-100xxxxxxxxxx` | ecocardiografia |

## Acervo amplo de livros
| Grupo | id | Conteúdo |
|---|---|---|
| <grupo de livros> (PADRÃO) | `-100xxxxxxxxxx` | livros-texto (PDF/EPUB) |

## Uso
- `search`/`list`/`download` aceitam `--chat <id>`; sem `--chat`, usam o padrão
  definido em `TELEGRAM_BOOKS_CHAT`.
- Direitos autorais: acervo é para **consulta/curadoria**; não redistribua
  conteúdo protegido.
