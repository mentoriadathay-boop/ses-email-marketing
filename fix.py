content = open('app.py', 'r', encoding='utf-8').read()
content = content.replace('# --- Banco de dados ---', '# --- Banco de dados ---\nos.makedirs(os.path.dirname(DB_PATH), exist_ok=True)')
open('app.py', 'w', encoding='utf-8').write(content)
print('Feito!')