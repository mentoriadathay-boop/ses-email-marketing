# Integração Firecrawl - Prospecção de Leads

## O que é Firecrawl?

Firecrawl é um serviço de web scraping inteligente que:
- Renderiza JavaScript automaticamente
- Extrai dados estruturados de páginas complexas
- Identifica e normaliza contatos e informações de empresas
- Oferece fallback automático para conteúdo quando JavaScript não é necessário

## Configuração

### 1. Obter API Key

1. Visite https://www.firecrawl.dev/
2. Registre-se na plataforma
3. Gere uma API Key no painel de controle
4. Copie a chave

### 2. Adicionar a Variável de Ambiente

No seu ambiente (Railway, Heroku, ou local):

```bash
export FIRECRAWL_API_KEY="sua_chave_aqui"
```

Ou adicione a um arquivo `.env`:

```
FIRECRAWL_API_KEY=sua_chave_aqui
```

### 3. Instalar Dependência

A biblioteca `firecrawl-py` já foi adicionada ao `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Como Funciona na Aplicação

### Fluxo de Extração

1. **Tentativa Firecrawl**: Quando você inicia uma extração de lead, o sistema tenta usar o Firecrawl
2. **Fallback HTTP**: Se Firecrawl não estiver configurado ou falhar, usa HTTP simples
3. **Enriquecimento Claude**: Independente do método, usa Claude para estruturar os contatos

```
URL → Firecrawl (ou HTTP) → HTML/Texto → Claude → Leads Estruturados
```

### Vantagens do Firecrawl

- ✅ **JavaScript Renderizado**: Funciona com sites dinâmicos
- ✅ **Melhor Extração**: Identifica contatos automaticamente
- ✅ **Retry Automático**: Tenta novamente em caso de falha
- ✅ **Sem Configuração**: Funciona out-of-the-box com a API Key

## Uso na Interface

Na página de Prospecção (/prospeccao):

1. Cole a URL do site
2. Configure o máximo de páginas
3. Clique em "Iniciar Extração"
4. O sistema automaticamente:
   - Tentará usar Firecrawl se a API Key estiver configurada
   - Fará fallback para HTTP se necessário
   - Extrairá e estruturará os contatos com Claude

## Limites e Cotas

Firecrawl oferece:
- **Plano Gratuito**: Algumas requisições por mês
- **Planos Pagos**: Maior volume com preço por requisição

Verifique https://www.firecrawl.dev/pricing para detalhes atualizados.

## Troubleshooting

### API Key não configurada

Se não houver FIRECRAWL_API_KEY, o sistema usa automaticamente HTTP. É seguro deixar em branco.

### Falha ao usar Firecrawl

```python
# O sistema tenta Firecrawl, se falhar:
1. Log de erro é silencioso
2. Fallback automático para HTTP
3. Extração continua normalmente
```

### Testar Configuração

```bash
# No terminal Python:
import os
from firecrawl import FirecrawlApp

api_key = os.environ.get('FIRECRAWL_API_KEY')
if api_key:
    app = FirecrawlApp(api_key=api_key)
    result = app.scrape_url('https://example.com')
    print(result)
else:
    print("FIRECRAWL_API_KEY não configurada")
```

## Próximos Passos

- [ ] Adicionar modo de extração específica (contatos, emails, telefones)
- [ ] Implementar cache de resultados Firecrawl
- [ ] Adicionar análise de sucesso de extração (Firecrawl vs HTTP)
- [ ] Opções avançadas na interface (modo Markdown vs HTML)

## Mais Informações

- Documentação Oficial: https://docs.firecrawl.dev/
- API Reference: https://docs.firecrawl.dev/api-reference/scrape
- Status: https://status.firecrawl.dev/
