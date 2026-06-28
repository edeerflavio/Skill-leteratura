# Configurar o acesso ao acervo de livros no Telegram

O `telegram_books.py` usa a **sua conta** de Telegram (via Telethon) para buscar
e baixar documentos (PDF/EPUB) do grupo onde os livros médicos são enviados.

## 1. Instalar dependências
```
pip install -r requirements.txt
```

## 2. Obter credenciais de API (uma vez)
1. Acesse https://my.telegram.org e faça login com seu número.
2. Vá em **API development tools**.
3. Crie um app (qualquer nome). Anote o **api_id** e o **api_hash**.

## 3. Definir variáveis de ambiente
PowerShell (Windows):
```powershell
$env:TELEGRAM_API_ID    = "123456"
$env:TELEGRAM_API_HASH  = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:TELEGRAM_BOOKS_CHAT = "@nome_do_grupo"   # ou o id numérico, ou link t.me/...
```
Para deixar permanente, use `setx` ou as Variáveis de Ambiente do Windows.

## 4. Primeiro login (interativo)
```
python telegram_books.py login
```
O Telethon vai pedir seu telefone e o código enviado no app. A sessão fica
salva em `scripts/.tg_books.session`. **Não** versione nem compartilhe esse
arquivo — ele dá acesso à sua conta.

## 5. Descobrir o grupo (se não souber o id/nome)
```
python telegram_books.py chats --json
```
Copie o `id` ou nome do grupo de livros para `TELEGRAM_BOOKS_CHAT`.

## 6. Uso no dia a dia
```
python telegram_books.py search "echocardiography" --max 20 --json
python telegram_books.py list --max 30 --json
python telegram_books.py download --id 12345 --out ./downloads --json
```

## Segurança e ética
- Use apenas grupos dos quais você participa legitimamente.
- Respeite direitos autorais: o acervo serve de **referência de consulta** para a
  curadoria; redistribuir conteúdo protegido pode ser ilegal.
- O `.session` e o `api_hash` são segredos. Trate como senha.

## .gitignore sugerido
```
scripts/.tg_books.session
scripts/.tg_books.session-journal
downloads/
```
