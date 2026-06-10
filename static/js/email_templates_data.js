// Dados compartilhados dos 12 templates visuais - usados pela galeria standalone
// e pelo modal de templates dentro de Nova Campanha / Nova Cadencia.
const _TEMPLATES = [
  {
    id: 'carta-pessoal', name: 'Carta Pessoal', cat: 'Texto Corrido',
    desc: 'Tom íntimo, direto e personalizado. Ideal para relacionamento.',
    cor: '#2c3e50', icone: '✉️',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f5f5f5;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1);">
<tr><td style="background:#2c3e50;padding:32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;font-weight:normal;letter-spacing:1px;">Empresa</h1>
</td></tr>
<tr><td style="padding:36px 40px;color:#333;line-height:1.7;">
  <p style="font-size:16px;">Olá, <strong>{nome}</strong>,</p>
  <p>Escrevo esta mensagem com muita satisfação porque tenho algo importante para compartilhar com você.</p>
  <p>Nos últimos meses, tenho visto como [contexto/situação] impacta diretamente o resultado de pessoas como você. E foi pensando nisso que decidi entrar em contato.</p>
  <p>Gostaria de te convidar para [ação/proposta]. Tenho certeza de que vai fazer diferença.</p>
  <p style="margin-top:28px;">Com carinho,<br><strong>Maria Silva</strong><br><span style="color:#888;font-size:14px;">Diretora de Marketing</span></p>
</td></tr>
<tr><td style="background:#f8f9fa;padding:20px 40px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'newsletter', name: 'Newsletter Simples', cat: 'Texto Corrido',
    desc: 'Layout limpo com múltiplas seções. Ideal para conteúdo recorrente.',
    cor: '#1a3a6b', icone: '📰',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f0f2f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#1a3a6b;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:20px;">Newsletter — Edição #01</h1>
  <p style="color:#aac4ff;margin:6px 0 0;font-size:13px;">Empresa · Mês 2025</p>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Olá, <strong>{nome}</strong>!</p>
  <h3 style="color:#1a3a6b;border-bottom:2px solid #e8f0fe;padding-bottom:8px;">📌 Destaque da Semana</h3>
  <p>Texto do destaque principal da newsletter. Escreva aqui o conteúdo mais importante desta edição.</p>
  <h3 style="color:#1a3a6b;border-bottom:2px solid #e8f0fe;padding-bottom:8px;">💡 Dica Rápida</h3>
  <p>Uma dica prática que seus leitores podem aplicar hoje mesmo.</p>
  <div style="text-align:center;margin:24px 0;">
    <a href="#LINK_CTA" style="background:#1a3a6b;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:bold;">Ler mais →</a>
  </div>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'produto-destaque', name: 'Produto Destaque', cat: 'Vendas',
    desc: 'Apresenta um produto ou serviço com CTA forte.',
    cor: '#e63946', icone: '🛍️',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f5f5f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#e63946;padding:32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:24px;">🛍️ Conheça Nossa Solução</h1>
  <p style="color:#ffd6d9;margin:8px 0 0;">Feito para quem quer resultados reais</p>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p>Olá, <strong>{nome}</strong>!</p>
  <div style="background:#fff5f5;border-radius:8px;padding:20px;margin:16px 0;border-left:4px solid #e63946;">
    <h2 style="color:#e63946;margin:0 0 8px;">Nome do Produto</h2>
    <p style="margin:0;font-size:15px;">Descrição breve e impactante do produto ou serviço. O que ele resolve? Por que é único?</p>
  </div>
  <ul style="text-align:left;padding-left:20px;color:#555;line-height:2;">
    <li>✅ Benefício principal número 1</li>
    <li>✅ Benefício principal número 2</li>
    <li>✅ Benefício principal número 3</li>
  </ul>
  <a href="#LINK_CTA" style="display:inline-block;background:#e63946;color:#fff;padding:14px 36px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;margin:20px 0;">Quero Saber Mais →</a>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'oferta-especial', name: 'Oferta Especial', cat: 'Vendas',
    desc: 'Urgência e desconto em destaque. Converte leads em compradores.',
    cor: '#f77f00', icone: '🔥',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#fff8f0;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:linear-gradient(135deg,#f77f00,#d62828);padding:32px;text-align:center;">
  <p style="color:#ffe0b2;margin:0;font-size:13px;letter-spacing:2px;text-transform:uppercase;">Oferta por tempo limitado</p>
  <h1 style="color:#fff;margin:8px 0;font-size:32px;">🔥 50% OFF</h1>
  <p style="color:#ffe0b2;margin:0;">Somente até [DATA]</p>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p>Oi, <strong>{nome}</strong>!</p>
  <p style="font-size:16px;">Essa é uma <strong>oportunidade única</strong>. Por tempo limitado, você tem acesso ao <strong>[Produto/Serviço]</strong> com desconto especial.</p>
  <div style="border:2px dashed #f77f00;border-radius:8px;padding:16px;margin:20px 0;background:#fff8f0;">
    <p style="margin:0;font-size:14px;color:#888;">de <s>R$ 997</s> por apenas</p>
    <p style="margin:4px 0;font-size:36px;font-weight:bold;color:#d62828;">R$ 497</p>
    <p style="margin:0;font-size:13px;color:#888;">ou 12x de R$ 47</p>
  </div>
  <a href="#LINK_CTA" style="display:inline-block;background:#d62828;color:#fff;padding:16px 40px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:18px;">Garantir Minha Vaga →</a>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'comparativo', name: 'Comparativo de Planos', cat: 'Vendas',
    desc: 'Tabela com 3 planos lado a lado. Facilita a decisão de compra.',
    cor: '#3a0ca3', icone: '📊',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f5f5f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#3a0ca3;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">Escolha o Plano Ideal para Você</h1>
</td></tr>
<tr><td style="padding:24px 32px;">
  <p>Olá, <strong>{nome}</strong>!</p>
  <table width="100%" cellpadding="10" cellspacing="0">
    <tr>
      <td style="background:#f8f9fa;border-radius:8px 0 0 8px;text-align:center;padding:20px;border:1px solid #eee;">
        <p style="font-weight:bold;font-size:16px;color:#555;margin:0 0 8px;">Básico</p>
        <p style="font-size:24px;font-weight:bold;color:#3a0ca3;margin:0 0 12px;">R$ 97<span style="font-size:14px;color:#888;">/mês</span></p>
        <p style="font-size:13px;color:#666;margin:0 0 16px;">Para quem está começando</p>
        <a href="#LINK_CTA" style="display:block;background:#e8e0ff;color:#3a0ca3;padding:10px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:13px;">Escolher</a>
      </td>
      <td style="background:#3a0ca3;border-radius:0;text-align:center;padding:20px;">
        <p style="font-size:11px;color:#c8b8ff;margin:0 0 4px;letter-spacing:1px;">MAIS POPULAR</p>
        <p style="font-weight:bold;font-size:16px;color:#fff;margin:0 0 8px;">Profissional</p>
        <p style="font-size:24px;font-weight:bold;color:#D4AF37;margin:0 0 12px;">R$ 197<span style="font-size:14px;color:#c8b8ff;">/mês</span></p>
        <p style="font-size:13px;color:#c8b8ff;margin:0 0 16px;">Para crescer mais rápido</p>
        <a href="#LINK_CTA" style="display:block;background:#D4AF37;color:#000;padding:10px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:13px;">Escolher</a>
      </td>
      <td style="background:#f8f9fa;border-radius:0 8px 8px 0;text-align:center;padding:20px;border:1px solid #eee;">
        <p style="font-weight:bold;font-size:16px;color:#555;margin:0 0 8px;">Premium</p>
        <p style="font-size:24px;font-weight:bold;color:#3a0ca3;margin:0 0 12px;">R$ 397<span style="font-size:14px;color:#888;">/mês</span></p>
        <p style="font-size:13px;color:#666;margin:0 0 16px;">Escala sem limites</p>
        <a href="#LINK_CTA" style="display:block;background:#e8e0ff;color:#3a0ca3;padding:10px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:13px;">Escolher</a>
      </td>
    </tr>
  </table>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'tres-dicas', name: '3 Dicas', cat: 'Educacional',
    desc: 'Três dicas numeradas com ícones. Fácil de ler e muito compartilhável.',
    cor: '#06d6a0', icone: '💡',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f0faf8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#06d6a0;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">💡 3 Dicas para Transformar seus Resultados</h1>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Oi, <strong>{nome}</strong>! Separei 3 dicas que vão fazer diferença imediata no seu negócio.</p>
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="padding:12px 0;border-bottom:1px solid #f0f0f0;">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        <td width="44" valign="top">
          <div style="width:36px;height:36px;background:#06d6a0;border-radius:50%;text-align:center;line-height:36px;color:#fff;font-weight:bold;font-size:16px;">1</div>
        </td>
        <td style="padding-left:12px;">
          <strong style="color:#06886b;">Título da Dica 1</strong>
          <p style="margin:4px 0 0;color:#555;font-size:14px;line-height:1.6;">Explicação prática da primeira dica. O que fazer, por que funciona e como aplicar hoje mesmo.</p>
        </td>
      </tr></table>
    </td></tr>
    <tr><td style="padding:12px 0;border-bottom:1px solid #f0f0f0;">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        <td width="44" valign="top">
          <div style="width:36px;height:36px;background:#06d6a0;border-radius:50%;text-align:center;line-height:36px;color:#fff;font-weight:bold;font-size:16px;">2</div>
        </td>
        <td style="padding-left:12px;">
          <strong style="color:#06886b;">Título da Dica 2</strong>
          <p style="margin:4px 0 0;color:#555;font-size:14px;line-height:1.6;">Explicação prática da segunda dica. Seja específico e use exemplos concretos para ilustrar.</p>
        </td>
      </tr></table>
    </td></tr>
    <tr><td style="padding:12px 0;border-bottom:1px solid #f0f0f0;">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        <td width="44" valign="top">
          <div style="width:36px;height:36px;background:#06d6a0;border-radius:50%;text-align:center;line-height:36px;color:#fff;font-weight:bold;font-size:16px;">3</div>
        </td>
        <td style="padding-left:12px;">
          <strong style="color:#06886b;">Título da Dica 3</strong>
          <p style="margin:4px 0 0;color:#555;font-size:14px;line-height:1.6;">Explicação prática da terceira dica. Termine com uma ação clara que o leitor pode tomar agora.</p>
        </td>
      </tr></table>
    </td></tr>
  </table>
  <div style="text-align:center;margin:24px 0 0;">
    <a href="#LINK_CTA" style="background:#06d6a0;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:bold;">Quero Aprender Mais →</a>
  </div>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'case-sucesso', name: 'Case de Sucesso', cat: 'Educacional',
    desc: 'Resultado real de um cliente com dados e depoimento.',
    cor: '#4361ee', icone: '🏆',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f5f8ff;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#4361ee;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">🏆 Como [Cliente] Conseguiu [Resultado]</h1>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Oi, <strong>{nome}</strong>!</p>
  <p>Deixa eu te contar a história de <strong>[Nome do cliente]</strong>, que estava exatamente na mesma situação que você...</p>
  <div style="background:#f8f9ff;border-radius:8px;padding:20px;margin:16px 0;border-left:4px solid #4361ee;">
    <p style="font-style:italic;color:#555;margin:0 0 8px;">"[Depoimento real do cliente em suas próprias palavras. Quanto mais específico, mais convincente.]"</p>
    <p style="margin:0;font-size:13px;color:#888;font-weight:bold;">— [Nome], [Cargo/Empresa]</p>
  </div>
  <table width="100%" cellpadding="12" cellspacing="8">
    <tr>
      <td style="background:#e8efff;border-radius:8px;text-align:center;"><strong style="font-size:24px;color:#4361ee;">+127%</strong><br><span style="font-size:13px;color:#666;">no resultado X</span></td>
      <td style="background:#e8efff;border-radius:8px;text-align:center;"><strong style="font-size:24px;color:#4361ee;">3x</strong><br><span style="font-size:13px;color:#666;">mais conversões</span></td>
      <td style="background:#e8efff;border-radius:8px;text-align:center;"><strong style="font-size:24px;color:#4361ee;">60 dias</strong><br><span style="font-size:13px;color:#666;">para o resultado</span></td>
    </tr>
  </table>
  <div style="text-align:center;margin-top:24px;">
    <a href="#LINK_CTA" style="background:#4361ee;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:bold;">Quero o Mesmo Resultado →</a>
  </div>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'checklist', name: 'Checklist', cat: 'Educacional',
    desc: 'Lista de itens a fazer ou verificar. Alta taxa de leitura.',
    cor: '#7209b7', icone: '✅',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f9f5ff;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#7209b7;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">✅ Checklist: [Título do Checklist]</h1>
  <p style="color:#e0b3ff;margin:6px 0 0;font-size:14px;">Tudo que você precisa fazer para [objetivo]</p>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Oi, <strong>{nome}</strong>! Criei este checklist para facilitar sua vida.</p>
  <table width="100%" cellpadding="8" cellspacing="4">
    <tr><td style="background:#f9f5ff;border-radius:6px;padding:10px 14px;">
      <span style="display:inline-block;width:20px;height:20px;background:#7209b7;border-radius:4px;text-align:center;line-height:20px;color:#fff;font-size:12px;margin-right:10px;">✓</span>
      <span style="font-size:15px;">Item do checklist número 1</span>
    </td></tr>
    <tr><td style="background:#f9f5ff;border-radius:6px;padding:10px 14px;">
      <span style="display:inline-block;width:20px;height:20px;background:#7209b7;border-radius:4px;text-align:center;line-height:20px;color:#fff;font-size:12px;margin-right:10px;">✓</span>
      <span style="font-size:15px;">Item do checklist número 2</span>
    </td></tr>
    <tr><td style="background:#f9f5ff;border-radius:6px;padding:10px 14px;">
      <span style="display:inline-block;width:20px;height:20px;background:#7209b7;border-radius:4px;text-align:center;line-height:20px;color:#fff;font-size:12px;margin-right:10px;">✓</span>
      <span style="font-size:15px;">Item do checklist número 3</span>
    </td></tr>
    <tr><td style="background:#f9f5ff;border-radius:6px;padding:10px 14px;">
      <span style="display:inline-block;width:20px;height:20px;background:#7209b7;border-radius:4px;text-align:center;line-height:20px;color:#fff;font-size:12px;margin-right:10px;">✓</span>
      <span style="font-size:15px;">Item do checklist número 4</span>
    </td></tr>
    <tr><td style="background:#f9f5ff;border-radius:6px;padding:10px 14px;">
      <span style="display:inline-block;width:20px;height:20px;background:#7209b7;border-radius:4px;text-align:center;line-height:20px;color:#fff;font-size:12px;margin-right:10px;">✓</span>
      <span style="font-size:15px;">Item do checklist número 5</span>
    </td></tr>
    <tr><td style="background:#f9f5ff;border-radius:6px;padding:10px 14px;">
      <span style="display:inline-block;width:20px;height:20px;background:#7209b7;border-radius:4px;text-align:center;line-height:20px;color:#fff;font-size:12px;margin-right:10px;">✓</span>
      <span style="font-size:15px;">Item do checklist número 6</span>
    </td></tr>
  </table>
  <div style="text-align:center;margin-top:24px;">
    <a href="#LINK_CTA" style="background:#7209b7;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:bold;">Baixar Checklist Completo →</a>
  </div>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'convite', name: 'Convite para Evento', cat: 'Eventos',
    desc: 'Convite elegante com data, local e CTA de confirmação.',
    cor: '#d4af37', icone: '📅',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#fffdf0;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;border:1px solid #f0e6c0;">
<tr><td style="background:linear-gradient(135deg,#1a3a6b,#2d5a8e);padding:36px 32px;text-align:center;">
  <p style="color:#D4AF37;margin:0 0 8px;font-size:13px;letter-spacing:3px;text-transform:uppercase;">Você está convidado</p>
  <h1 style="color:#fff;margin:0;font-size:28px;font-weight:normal;">[Nome do Evento]</h1>
  <p style="color:#aac4ff;margin:8px 0 0;font-size:14px;">[Subtítulo ou tema do evento]</p>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p>Prezado(a), <strong>{nome}</strong>,</p>
  <p>É com grande prazer que convidamos você para participar de um evento especial.</p>
  <table width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;">
    <tr>
      <td style="text-align:center;padding:12px;border-right:1px solid #f0f0f0;">
        <div style="font-size:28px;">📅</div>
        <p style="font-weight:bold;margin:4px 0;color:#1a3a6b;">[Data]</p>
        <p style="margin:0;font-size:13px;color:#888;">[Horário]</p>
      </td>
      <td style="text-align:center;padding:12px;border-right:1px solid #f0f0f0;">
        <div style="font-size:28px;">📍</div>
        <p style="font-weight:bold;margin:4px 0;color:#1a3a6b;">[Local]</p>
        <p style="margin:0;font-size:13px;color:#888;">[Endereço]</p>
      </td>
      <td style="text-align:center;padding:12px;">
        <div style="font-size:28px;">🎫</div>
        <p style="font-weight:bold;margin:4px 0;color:#1a3a6b;">Entrada</p>
        <p style="margin:0;font-size:13px;color:#888;">Gratuita</p>
      </td>
    </tr>
  </table>
  <a href="#LINK_CTA" style="background:#D4AF37;color:#1a3a6b;padding:14px 36px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;display:inline-block;">Confirmar Presença →</a>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'webinar', name: 'Webinar / Aula Online', cat: 'Eventos',
    desc: 'Inscrição para webinar com tópicos e palestrante.',
    cor: '#480ca8', icone: '🎥',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f0f0ff;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:linear-gradient(135deg,#480ca8,#7209b7);padding:32px;text-align:center;">
  <p style="color:#c8b8ff;margin:0 0 6px;font-size:13px;letter-spacing:2px;">AULA GRATUITA AO VIVO</p>
  <h1 style="color:#fff;margin:0;font-size:24px;">[Título do Webinar]</h1>
  <p style="color:#e0b3ff;margin:8px 0 0;">[Data] · [Horário] · Via Zoom</p>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Oi, <strong>{nome}</strong>!</p>
  <p>Você foi selecionado(a) para participar de uma aula exclusiva onde vou revelar:</p>
  <ul style="padding-left:20px;line-height:2.2;color:#555;">
    <li>🎯 Tópico de alto valor número 1</li>
    <li>🎯 Tópico de alto valor número 2</li>
    <li>🎯 Tópico de alto valor número 3</li>
    <li>🎯 Estratégia bônus revelada ao vivo</li>
  </ul>
  <div style="background:#f0f0ff;border-radius:8px;padding:16px;margin:16px 0;display:flex;gap:12px;">
    <div style="flex:1;text-align:center;">
      <strong style="font-size:13px;color:#480ca8;">Apresentado por</strong><br>
      <p style="margin:4px 0 0;font-size:15px;font-weight:bold;">[Nome do Palestrante]</p>
    </div>
  </div>
  <div style="text-align:center;margin-top:20px;">
    <a href="#LINK_CTA" style="background:#7209b7;color:#fff;padding:14px 36px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;display:inline-block;">Garantir Minha Vaga Grátis →</a>
    <p style="font-size:12px;color:#888;margin-top:8px;">Vagas limitadas · 100% gratuito</p>
  </div>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'sentimos-falta', name: 'Sentimos Sua Falta', cat: 'Reengajamento',
    desc: 'Reativa leads e clientes inativos com emoção e oferta.',
    cor: '#ef476f', icone: '💔',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#fff5f7;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#ef476f;padding:32px;text-align:center;">
  <div style="font-size:48px;">💔</div>
  <h1 style="color:#fff;margin:8px 0 0;font-size:22px;">Sentimos sua falta, {nome}!</h1>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p style="font-size:16px;">Já faz um tempo que não nos falamos e queríamos saber como você está.</p>
  <p>A gente sabe que a vida é corrida, mas estamos aqui quando precisar.</p>
  <div style="background:#fff5f7;border-radius:8px;padding:20px;margin:20px 0;border:1px dashed #ef476f;">
    <p style="font-weight:bold;color:#ef476f;margin:0 0 8px;">🎁 Presente especial para você voltar</p>
    <p style="margin:0;font-size:15px;">Use o cupom <strong style="font-size:20px;color:#ef476f;">VOLTEI30</strong> e ganhe 30% de desconto</p>
  </div>
  <a href="#LINK_CTA" style="background:#ef476f;color:#fff;padding:14px 36px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;display:inline-block;">Quero Voltar →</a>
  <p style="font-size:12px;color:#aaa;margin-top:16px;">Oferta válida por 7 dias</p>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'pesquisa-rapida', name: 'Pesquisa Rápida', cat: 'Reengajamento',
    desc: 'Pesquisa de satisfação simples com 3 opções clicáveis.',
    cor: '#118ab2', icone: '📊',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f0f8ff;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#118ab2;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">📊 Uma pergunta rápida para você</h1>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p>Oi, <strong>{nome}</strong>!</p>
  <p style="font-size:16px;">Leva menos de 10 segundos e vai nos ajudar muito.</p>
  <p style="font-size:18px;font-weight:bold;margin:24px 0 16px;">[Qual a sua maior dificuldade hoje com X?]</p>
  <table width="100%" cellpadding="8" cellspacing="8">
    <tr>
      <td><a href="#LINK_CTA" style="display:block;background:#e8f4ff;border:2px solid #118ab2;border-radius:8px;padding:14px;text-decoration:none;color:#118ab2;font-weight:bold;font-size:14px;">😕 Opção A: [Resposta 1]</a></td>
    </tr>
    <tr>
      <td><a href="#LINK_CTA" style="display:block;background:#e8f4ff;border:2px solid #118ab2;border-radius:8px;padding:14px;text-decoration:none;color:#118ab2;font-weight:bold;font-size:14px;">😐 Opção B: [Resposta 2]</a></td>
    </tr>
    <tr>
      <td><a href="#LINK_CTA" style="display:block;background:#e8f4ff;border:2px solid #118ab2;border-radius:8px;padding:14px;text-decoration:none;color:#118ab2;font-weight:bold;font-size:14px;">😊 Opção C: [Resposta 3]</a></td>
    </tr>
  </table>
  <p style="font-size:12px;color:#aaa;margin-top:20px;">Sua opinião é muito importante para nós.</p>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
];
