# Controle Financeiro - versão para Vercel

Esta versão remove o Streamlit e usa FastAPI + HTML/CSS + Jinja2 para rodar na Vercel.

## Rodar local

```bash
pip install -r requirements.txt
set DATABASE_URL=sua_url_do_supabase
set SECRET_KEY=uma_chave_qualquer
python app.py
```

Acesse: http://localhost:8000

## Variáveis na Vercel

Em Project Settings > Environment Variables:

```txt
DATABASE_URL=sua_url_do_supabase
SECRET_KEY=uma_chave_grande_aleatoria
```

## Deploy

1. Suba estes arquivos para o GitHub.
2. Na Vercel, clique em Add New > Project.
3. Importe o repositório.
4. Configure as variáveis de ambiente.
5. Clique em Deploy.
