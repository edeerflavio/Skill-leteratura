# Skill: revisao-literatura-medica

Skill de **revisão de literatura médica baseada em evidências e anti-alucinação**,
criada para apoiar a **curadoria de conteúdo de um app médico de referência
clínica** — um **guia
médico amplo**, de qualquer tema e cenário (atenção primária/UBS, ambulatório/
consultório, urgência/emergência, terapia intensiva e as diversas especialidades;
POCUS é só um dos assuntos). Público-alvo: médicos/profissionais.

Princípio central: **só afirma o que recuperou de uma fonte real nesta sessão.**
Sem fonte buscada → sem afirmação. Sem achado → diz que não achou. Antes de
publicar, **verifica** que cada citação (PMID/DOI) existe de verdade.

## O que tem aqui
```
revisao-literatura-medica/
├── SKILL.md                     # instruções que o assistente segue (o "cérebro")
├── references/
│   ├── evidence-grading.md      # GRADE, níveis, métricas de acurácia (POCUS)
│   ├── trusted-sources.md       # lista branca de fontes (inclui POCUS/Brasil)
│   ├── guideline-structure.md   # estrutura de saída p/ diretrizes
│   ├── study-structure.md       # estrutura de saída p/ estudos
│   ├── terminology-rules.md     # PT-BR vs siglas em inglês
│   ├── mermaid-examples.md      # fluxogramas/mapas mentais
│   └── telegram-groups.example.md  # modelo (o real é privado/gitignored)
├── scripts/
│   ├── pubmed_search.py         # PubMed/MEDLINE (grátis) — busca + --trend
│   ├── europepmc_search.py      # Europe PMC (grátis)
│   ├── openalex_search.py       # OpenAlex (grátis): citações + acesso aberto
│   ├── verify_citations.py      # confere se PMID/DOI existem (anti-alucinação)
│   ├── unpaywall_resolve.py     # DOI -> PDF de acesso aberto (+ download)
│   ├── telegram_books.py        # acervo de livros no seu Telegram (Telethon)
│   ├── read_document.py         # ler/buscar em PDF/EPUB (TOC-first + OCR)
│   ├── requirements.txt
│   └── README_TELEGRAM.md       # como configurar o Telegram
└── .claude/skills/run-revisao-literatura-medica/   # "run skill" + driver de testes
```

## Como instalar (Claude Code)

1. Copie a pasta para uma `skills/` que a Claude Code carregue:
   - **Pessoal:** `~/.claude/skills/revisao-literatura-medica`
     (Windows: `C:\Users\<você>\.claude\skills\revisao-literatura-medica`)
   - **Só no projeto do app:** `<projeto>/.claude/skills/revisao-literatura-medica`
2. Instale as dependências:
   ```bash
   pip install -r scripts/requirements.txt
   ```
3. Invoque pedindo naturalmente ("revise a evidência sobre US pulmonar para
   pneumotórax") ou com `/revisao-literatura-medica`.

## Configuração (variáveis de ambiente)

| Variável | Para quê | Obrigatória? |
|---|---|---|
| `NCBI_EMAIL`, `NCBI_API_KEY` | cota maior no PubMed | não |
| `OPENALEX_EMAIL` | "polite pool" do OpenAlex | não (recomendado) |
| `UNPAYWALL_EMAIL` | exigida pela API Unpaywall | sim, p/ usar Unpaywall |
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | acesso ao Telegram (my.telegram.org) | só p/ Telegram |
| `TELEGRAM_BOOKS_CHAT` | grupo padrão de livros | só p/ Telegram |

Telegram precisa de login interativo na 1ª vez — veja `scripts/README_TELEGRAM.md`.

## Verificar que tudo funciona (smoke test)

O "run skill" traz um driver que exercita cada ferramenta com dados reais:

```bash
python .claude/skills/run-revisao-literatura-medica/driver.py smoke
# saída esperada termina em:  == TODOS OS CHECKS PASSARAM ==
```

Sem rede? `... driver.py smoke --offline` (roda só os checks locais).

## Exemplos de uso direto dos scripts
```bash
# Busca em 3 fontes grátis (corroboração cruzada)
python scripts/pubmed_search.py "lung ultrasound pneumothorax diagnostic accuracy" --max 20 --years 5 --json
python scripts/europepmc_search.py "RUSH protocol shock" --max 15 --sort cited --json
python scripts/openalex_search.py "point of care lung ultrasound" --since 2021 --json

# Tendência de publicações por ano (tema quente vs estável)
python scripts/pubmed_search.py "point of care lung ultrasound" --trend --trend-years 12

# Anti-alucinação: confere se as citações existem (exit != 0 se alguma falhar)
python scripts/verify_citations.py --pmid 39375782 --doi 10.1186/s13054-024-05102-y --json

# Texto completo de acesso aberto (resolve + baixa) e leitura TOC-first
python scripts/unpaywall_resolve.py --doi 10.1186/s13054-024-05102-y --download --out downloads --json
python scripts/read_document.py toc downloads/10.1186_s13054-024-05102-y.pdf --json
python scripts/read_document.py search downloads/livro.pdf "B-lines" --pages 103-123 --json
python scripts/read_document.py text downloads/livro.pdf --pages 10-15 --ocr   # OCR só se escaneado

# Acervo de livros no Telegram (após configurar — ver README_TELEGRAM.md)
python scripts/telegram_books.py search "echocardiography" --json
```

## ⚠️ Segurança e privacidade (NÃO versionar)

O `.gitignore` já bloqueia, mas confira antes de qualquer commit:
- **`scripts/*.session`** — sessão do Telegram = acesso à sua conta. Segredo.
- **`references/telegram-groups.md`** — IDs/nomes dos seus grupos privados.
  Versione apenas o `.example.md`.
- **`downloads/`** — livros baixados (direitos autorais). Não redistribua.
- Credenciais (`*_API_*`, e-mails) ficam em **variáveis de ambiente**, nunca em
  arquivos do repositório.

## OCR opcional (só para PDFs escaneados)
```bash
pip install rapidocr-onnxruntime pillow   # sem binário de sistema (Windows-friendly)
```
PDFs com camada de texto (a maioria dos artigos/e-books) **não** precisam de OCR.
