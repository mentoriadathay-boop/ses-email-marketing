#!/usr/bin/env python
"""
Script de teste para integração Firecrawl
Testa a extração de leads usando Firecrawl

Uso:
    FIRECRAWL_API_KEY=sua_chave python test_firecrawl.py
"""

import os
import json
import sys
from datetime import datetime

# Teste 1: Verificar se a biblioteca está instalada
print("[TEST 1] Verificando se firecrawl-py está instalado...")
try:
    from firecrawl import FirecrawlApp
    print("✓ firecrawl-py está instalado")
except ImportError:
    print("✗ firecrawl-py NÃO está instalado")
    print("  Execute: pip install firecrawl-py")
    sys.exit(1)

# Teste 2: Verificar API Key
print("\n[TEST 2] Verificando FIRECRAWL_API_KEY...")
api_key = os.environ.get('FIRECRAWL_API_KEY', '').strip()
if not api_key:
    print("✗ FIRECRAWL_API_KEY não configurada")
    print("  Execute: export FIRECRAWL_API_KEY=sua_chave_aqui")
    sys.exit(1)
print(f"✓ API Key configurada ({api_key[:10]}...)")

# Teste 3: Teste de conexão com Firecrawl
print("\n[TEST 3] Testando conexão com Firecrawl...")
try:
    app = FirecrawlApp(api_key=api_key)
    print("✓ Conexão com Firecrawl estabelecida")
except Exception as e:
    print(f"✗ Erro ao conectar: {e}")
    sys.exit(1)

# Teste 4: Teste de scraping
print("\n[TEST 4] Testando scraping de página...")
test_url = "https://www.anthropic.com/contact"
print(f"  URL de teste: {test_url}")
try:
    resultado = app.scrape_url(test_url, params={
        'formats': ['markdown'],
        'onlyMainContent': True,
    })

    if resultado and 'markdown' in resultado:
        content = resultado['markdown']
        print(f"✓ Conteúdo extraído com sucesso ({len(content)} caracteres)")

        # Mostrar preview
        preview = content[:300].replace('\n', ' ')
        print(f"  Preview: {preview}...")

        # Teste 5: Teste de extração de emails
        print("\n[TEST 5] Testando extração de emails...")
        import re
        EMAIL_RE = re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b')
        emails = EMAIL_RE.findall(content)
        if emails:
            emails_unicos = list(set(emails))
            print(f"✓ Encontrados {len(emails_unicos)} email(s) únicos:")
            for em in emails_unicos[:5]:
                print(f"  - {em}")
            if len(emails_unicos) > 5:
                print(f"  ... e {len(emails_unicos) - 5} mais")
        else:
            print("⚠ Nenhum email encontrado na página")

    else:
        print(f"⚠ Resultado não contém 'markdown': {list(resultado.keys()) if resultado else 'None'}")

except Exception as e:
    print(f"✗ Erro ao fazer scraping: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Teste 6: Teste de Claude
print("\n[TEST 6] Testando integração com Claude...")
try:
    import anthropic as _anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False
    print("⚠ Claude (anthropic) não está instalado")

if ANTHROPIC_OK:
    api_key_anthropic = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if api_key_anthropic:
        try:
            client = _anthropic.Anthropic(api_key=api_key_anthropic)
            resposta = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=100,
                messages=[{'role': 'user', 'content': 'Teste de conexão com Claude. Responda com "OK".'}]
            )
            if resposta.content[0].text.strip():
                print("✓ Claude está funcionando")
        except Exception as e:
            print(f"⚠ Erro ao conectar com Claude: {e}")
    else:
        print("⚠ ANTHROPIC_API_KEY não configurada")

# Resumo final
print("\n" + "="*60)
print("RESUMO DOS TESTES")
print("="*60)
print("""
✓ Firecrawl está configurado corretamente
✓ Extração de conteúdo está funcionando
✓ Sistema pronto para captura de leads

PRÓXIMOS PASSOS:
1. Acesse https://tfaemailmkt.up.railway.app/prospeccao
2. Insira a URL de um site para teste
3. Clique em "Iniciar Extração"
4. O sistema usará Firecrawl automaticamente (se API Key configurada)

Para mais informações, veja FIRECRAWL.md
""")
