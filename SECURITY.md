# Segurança e LGPD — ConvertMail

Este documento resume o que foi auditado, corrigido e implementado neste repositório, e o que ficou como risco residual conhecido. Mantenha atualizado a cada nova auditoria — documentar o que ficou pendente evita redescobrir do zero.

## Auditoria de segurança — 26-27/08/2026

Cobertura: ~151 rotas, 4 frentes (auth/IDOR, SQLi/injeção, upload/SSRF/webhooks, cripto/sessão/CSRF). Corrigido e deployado em produção (commits `0550bde`, `22e2072`, `0003241`).

- **IDOR multi-tenant**: várias rotas faziam `SELECT/DELETE ... WHERE id=%s` sem checar dono. Corrigido com o helper `_check_owner(table, id, conn)` (`app.py`).
- **Bug crítico correlato**: `_get_email_account()` pegava a primeira conta ativa do banco inteiro — todos os usuários compartilhavam a mesma caixa de email conectada. Corrigido para filtrar por `user_id`.
- **Senha de admin**: fallback hardcoded era reaplicado a cada restart se `ADMIN_PASSWORD` não estivesse setada. Corrigido: senha aleatória forte gerada só na criação, nunca sobrescrita, nunca logada.
- **Sessão não revalidava assinatura**: cancelamento/reembolso via webhook Hotmart não derrubava sessões já abertas. Corrigido: revalidação de `status`/`role` a cada 60s (`before_request`, `app.py`).
- **SSRF autenticado**: em `/prospeccao/extrair` e teste de conta IMAP/SMTP. Corrigido com `_host_e_privado_ou_interno()` (bloqueia IP privado/loopback/link-local antes de conectar).
- **CSRF**: `CSRFProtect` nunca estava ativo apesar de `flask-wtf` instalado. Ativado globalmente, com retrofit automático via `base.html` (injeta token em todo `fetch()`/`<form method=post>`) e exceção (`@csrf.exempt`) só nas rotas genuinamente públicas (webhook Hotmart, tracking de pixel, captura de formulário embutível, chat da landing, descadastro).
- **`ENCRYPTION_KEY` ausente em produção**: rotacionada; senhas de email conectadas antes da rotação precisaram ser reconectadas (efeito colateral esperado).
- **Tabela `signature` era global** entre tenants (sem uso de `user_id` apesar da coluna existir). Corrigido nos 5 pontos que liam/gravavam.

**Decisão consciente de não mexer**: `api_nichos` aceita `mailing_ids` de qualquer tenant para estatísticas agregadas (baixo risco, não expõe lista de contatos).

## LGPD — implementado em 27/08/2026

Antes desta rodada não havia política de privacidade, termos de uso, registro de consentimento, nem exclusão/anonimização real de dados. Implementado:

- **Consentimento**: tabela `user_consents` (documento, versão, data, IP). Gate em `before_request` (`app.py`) força aceite em `/aceitar-termos` antes de liberar qualquer rota autenticada — cobre tanto contas novas quanto sessões já abertas antes da feature existir (consentimento retroativo). Suba a constante `TERMS_VERSION` para reabrir o aceite quando o texto mudar.
- **Páginas públicas** `/termos` e `/privacidade`, com identificação legal completa e lista de subprocessadores (Railway, Brevo, Anthropic, Hotmart).
- **Exportação de dados da conta**: `/conta/exportar-dados` (perfil, consentimentos, contas de email conectadas — sem segredos, kits de marca).
- **Exclusão de conta (self-service)**: `/conta/excluir-agora` (imediata) ou `/conta/agendar-exclusao` (agendada em 30 dias, cancelável em `/conta/cancelar-exclusao`). Job diário `processar_exclusoes_agendadas` processa o que passou do prazo. Ambos os caminhos chamam `_excluir_dados_usuario`, que também substitui a exclusão manual de admin (`/admin/usuarios/<id>/deletar`) — corrige o bug pré-existente de deixar contatos/campanhas órfãos.
- **Fila de revisão de remoção de lead**: quando a IA classifica uma resposta como `pedido_remocao` (`/ia/classificar-resposta`), o contato entra em `data_removal_requests` (`/leads/solicitar-remocao`) para revisão manual em `/leads/remocoes-pendentes` — nada é apagado automaticamente. Ao aprovar, os dados pessoais do contato são apagados (mantendo `email`/`user_id`) e o email vai para a `blacklist` (já existente, global) para impedir reimportação futura.
- **Blacklist preservada por decisão de produto**: descadastros e remoções aprovadas permanecem documentados na blacklist indefinidamente — é a forma de garantir que um contato que pediu para não ser mais contatado não seja recontatado numa reimportação futura, mesmo depois de exclusão de conta (a blacklist não é apagada na exclusão de conta, propositalmente).

## Riscos residuais conhecidos (documentados, não corrigidos nesta rodada)

1. **Tabelas de engajamento sem `user_id`**: `contact_activities`, `contact_scores`, `contact_purchases`, `send_analytics`, `email_opens`, `email_clicks` são chaveadas só por `contact_email`, diferente de `contacts` (que já tem `UNIQUE(user_id, email)` desde a auditoria de 08/2026). Se dois assinantes diferentes importarem o mesmo email de lead, os dados de engajamento desses dois contatos colidem no banco hoje. A exclusão de conta (`_excluir_dados_usuario`) já lida com isso com segurança (só apaga se nenhum outro tenant ainda referenciar o email), mas o problema de origem — dois tenants podendo ver/influenciar o score um do outro para um email compartilhado — não foi corrigido.
2. **Rotas de IA sem rate limit por usuário** (`/ia/gerar-email`, `/ia/melhorar-texto`, `/ia/chat-assistente`, `/ia/classificar-resposta` etc.): qualquer conta ativa pode gerar quantidade ilimitada de chamadas à API Anthropic. Não é risco de segurança de dados, é risco de custo.
3. **Blacklist é global entre tenants** (comportamento intencional, não um bug): um descadastro/remoção feito por um assinante impede que QUALQUER outro assinante envie para aquele email no futuro. É a base do requisito de produto "impedir reimportação futura", mas vale deixar registrado como comportamento não óbvio.
4. **Notificações internas (tabela `notifications`)**: feed global (não tem `user_id`), usado internamente para avisos de campanha/tarefa. Contém `contact_email` incidentalmente. Não foi incluída na exclusão de conta por não ser seguramente atribuível a um tenant — exposição de PII aqui é mínima e indireta.
5. **Planos**: o produto é vendido como plano único (`users.plan` existe na tabela mas nunca é lido em nenhuma rota) — não há lógica de limites/gating por plano para auditar. Se um plano com tiers for introduzido no futuro, revisar esta seção.

## Como testar as rotas de LGPD localmente

Ver gotchas gerais (venv do projeto fica em `venv/`, use `venv/Scripts/python.exe`; carregar `.env` manualmente com `load_dotenv()`; rodar com `use_reloader=False, debug=False`; boot local demora 30-90s pelas migrações DDL). Sempre testar contra uma conta descartável (nunca a conta real) e limpar os dados de teste ao final.
