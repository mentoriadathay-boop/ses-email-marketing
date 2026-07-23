# Implantação no Railway com Firecrawl

Guia completo para configurar a integração Firecrawl no seu projeto Railway.

## 1. Configurar Variáveis de Ambiente no Railway

### Passo 1: Acessar o Dashboard Railway
1. Visite https://railway.app
2. Faça login em sua conta
3. Selecione seu projeto `ses-email-marketing`

### Passo 2: Adicionar FIRECRAWL_API_KEY

1. Vá para a aba **Variables**
2. Clique em **New Variable**
3. Configure:
   - **KEY**: `FIRECRAWL_API_KEY`
   - **VALUE**: `sua_chave_firecrawl_aqui` (obtenha em https://www.firecrawl.dev/)
4. Clique em **Add**

### Variáveis Existentes (Verifique se estão configuradas)

Certifique-se de que as seguintes variáveis já existem:

```
DATABASE_URL=postgresql://...          # Fornecida pelo Railway PostgreSQL
BREVO_API_KEY=sk-xxxx...               # Para envio de emails
ANTHROPIC_API_KEY=sk-ant-xxxx...       # Para enriquecimento com Claude
APP_URL=https://tfaemailmkt.up.railway.app
```

## 2. Deploy Automático

Após adicionar a variável:

1. O Railway detectará mudanças de código
2. A build ocorrerá automaticamente
3. A aplicação será reimplantada em ~2-5 minutos

### Verificar Progresso do Deploy

- Vá para a aba **Deployments**
- Procure pelo deploy mais recente
- Aguarde o status mudar para ✓ **Success**

## 3. Testar a Integração

Após o deploy:

1. Acesse https://tfaemailmkt.up.railway.app/prospeccao
2. Você verá um badge verde **Firecrawl ativo** se configurado corretamente
3. Insira uma URL para teste
4. Clique em "Iniciar Extração"

### Testar Especificamente

```bash
# Via curl (teste API de info)
curl https://tfaemailmkt.up.railway.app/prospeccao/info

# Resposta esperada:
# {"firecrawl_enabled": true, "firecrawl_ok": true, "anthropic_ok": true}
```

## 4. Verificar Logs

Se algo não funcionar:

1. Vá para a aba **Logs** no Railway
2. Procure por erro relacionado a Firecrawl
3. Mensagens comuns:
   - "FIRECRAWL_API_KEY não configurada" → Adicione a variável
   - "FirecrawlApp import failed" → Reinstale requirements.txt
   - "API Error" → Verifique se a chave é válida

### Comandos Úteis

```bash
# Verificar se Firecrawl está instalado
python -c "from firecrawl import FirecrawlApp; print('OK')"

# Ver todas as variáveis (não mostra valores por segurança)
env | grep -E "(FIRECRAWL|DATABASE|BREVO|ANTHROPIC)"
```

## 5. Solução de Problemas

### Firecrawl não aparece como "ativo"

**Problema**: Badge verde não aparece após configurar API Key

**Solução**:
1. Aguarde 5 minutos após adicionar a variável
2. Limpe cache do navegador (Ctrl+F5)
3. Recarregue https://tfaemailmkt.up.railway.app/prospeccao

### Extração com HTTP mas sem Firecrawl

**Problema**: Extração está lenta ou não encontra contatos

**Solução**:
1. Verifique se FIRECRAWL_API_KEY está adicionada
2. Teste em `/prospeccao/info` se firecrawl_enabled é `true`
3. Consulte logs de erro

### Erro "Invalid API Key"

**Problema**: API Key está no formato errado ou expirada

**Solução**:
1. Visite https://www.firecrawl.dev/
2. Regenere sua API Key
3. Atualize em Railway Variables

## 6. Cotas e Limites

Firecrawl oferece diferentes planos:

- **Gratuito**: Algumas requisições por mês
- **Pro**: $49/mês com limite maior
- **Enterprise**: Custom

Para verificar seu uso:
1. Acesse https://www.firecrawl.dev/dashboard
2. Vá para **Usage**
3. Veja requisições utilizadas vs. limite

## 7. Otimizações

### Cachear Resultados

Adicione cache para evitar múltiplas extrações da mesma URL:

```python
# (Não implementado ainda, mas é uma melhoria futura)
```

### Usar Firecrawl Markdown

Para melhor performance com Claude, use modo Markdown:

```python
# No arquivo app.py já está implementado:
params={'formats': ['markdown'], 'onlyMainContent': True}
```

## 8. Monitoramento Contínuo

Configure alertas no Railway:

1. Vá para **Settings** → **Notifications**
2. Ative notificações para:
   - Deploy failures
   - High CPU usage
   - Database errors

## Referências

- **Documentação Firecrawl**: https://docs.firecrawl.dev/
- **Railway Docs**: https://docs.railway.app/
- **GitHub Issues**: Se encontrar bugs, relate aqui

## Checklist de Implantação

- [ ] Firecrawl API Key obtida em https://www.firecrawl.dev/
- [ ] Variável `FIRECRAWL_API_KEY` adicionada no Railway
- [ ] Outras variáveis verificadas (DATABASE_URL, BREVO_API_KEY, etc.)
- [ ] Deploy completado com sucesso (status ✓)
- [ ] Badge "Firecrawl ativo" aparece na página
- [ ] Teste de extração realizado com sucesso
- [ ] Logs verificados sem erros
- [ ] API de info retorna `firecrawl_enabled: true`

---

**Suporte**: Em caso de dúvidas, consulte:
1. FIRECRAWL.md neste repositório
2. Documentação oficial do Firecrawl
3. Logs do Railway para mensagens de erro
