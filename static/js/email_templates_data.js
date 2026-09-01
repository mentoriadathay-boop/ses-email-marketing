// Dados compartilhados dos 12 templates visuais - usados pela galeria standalone
// e pelo modal de templates dentro de Nova Campanha / Nova Cadencia.
const _TEMPLATES = [
  {
    id: 'carta-pessoal', name: 'Carta Pessoal', cat: 'Texto Corrido',
    desc: 'Tom íntimo, direto e personalizado. Ideal para relacionamento.',
    cor: '#2c3e50', icone: '✉️',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f5f5f5;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1);">
<tr><td style="background:#2c3e50;padding:32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;font-weight:normal;letter-spacing:1px;">Empresa</h1>
</td></tr>
<tr><td style="padding:36px 40px;color:#333;line-height:1.7;">
  <p style="font-size:16px;">Olá, <strong>{nome}</strong>,</p>
  <p>Escrevo esta mensagem com muita satisfação porque tenho algo importante para compartilhar com você.</p>
  <p>Nos últimos meses, tenho visto como [contexto/situação] impacta diretamente o resultado de pessoas como você. Conversei com dezenas de pessoas na mesma posição e percebi um padrão: [observação/insight relevante]. E foi pensando nisso que decidi entrar em contato.</p>
  <p>Pensando nisso, preparei [solução/proposta] especialmente para quem está vivendo essa fase. Não é uma solução genérica — é algo que desenhei a partir do que realmente funciona na prática, com base em [experiência/dado que sustenta a proposta].</p>
  <p>Gostaria de te convidar para [ação/proposta]. São apenas alguns minutos do seu tempo, e tenho certeza de que vai fazer diferença real na forma como você lida com [tema/situação].</p>
  <div style="text-align:center;margin:28px 0;">
    <a href="#LINK_CTA" style="background:#2c3e50;color:#fff;padding:13px 32px;border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block;">[Texto do botão] →</a>
  </div>
  <p>Se tiver qualquer dúvida, é só responder este e-mail — leio e respondo pessoalmente.</p>
  <p style="margin-top:28px;">Com carinho,<br><strong>Maria Silva</strong><br><span style="color:#888;font-size:14px;">Diretora de Marketing</span></p>
  <p style="font-size:13px;color:#999;border-top:1px solid #f0f0f0;padding-top:12px;margin-top:20px;">P.S.: [Reforço final — um motivo extra para agir agora ou um detalhe que cria proximidade.]</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#1a3a6b;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:20px;">Newsletter — Edição #01</h1>
  <p style="color:#aac4ff;margin:6px 0 0;font-size:13px;">Empresa · Mês 2025</p>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Olá, <strong>{nome}</strong>! Nesta edição você vai encontrar o destaque da semana, uma dica prática para aplicar hoje mesmo e uma recomendação especial. Vamos lá?</p>
  <h3 style="color:#1a3a6b;border-bottom:2px solid #e8f0fe;padding-bottom:8px;">📌 Destaque da Semana</h3>
  <p>Texto do destaque principal da newsletter. Explique o contexto (o que aconteceu ou o que você descobriu), por que isso importa para o leitor e qual o próximo passo prático que ele pode dar a partir dessa informação.</p>
  <h3 style="color:#1a3a6b;border-bottom:2px solid #e8f0fe;padding-bottom:8px;">💡 Dica Rápida</h3>
  <p>Uma dica prática que seus leitores podem aplicar hoje mesmo. Descreva o passo a passo em 2-3 frases: o que fazer primeiro, o que fazer em seguida e o resultado esperado.</p>
  <h3 style="color:#1a3a6b;border-bottom:2px solid #e8f0fe;padding-bottom:8px;">🎯 Recomendado para Você</h3>
  <p>Com base no seu interesse em [tema], separamos [conteúdo/recurso/oferta]. Vale a pena conferir porque [motivo específico].</p>
  <div style="text-align:center;margin:24px 0;">
    <a href="#LINK_CTA" style="background:#1a3a6b;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:bold;">Ler mais →</a>
  </div>
  <p style="font-size:13px;color:#999;border-top:1px solid #f0f0f0;padding-top:12px;">Até a próxima edição! Se tiver sugestões de temas, é só responder este e-mail.</p>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'newsletter-rica', name: 'Newsletter Rica (Premium)', cat: 'Texto Corrido',
    desc: 'Layout editorial: capa hero, subtítulo, chapéu de edição, texto serifado, blocos coloridos e assinatura destacada.',
    cor: '#5B2A6E', icone: '📚',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f5f2e9;font-family:Georgia,'Times New Roman',serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f2e9;"><tr><td align="center" style="padding:24px 12px;">
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:#ffffff;">

<!-- Chapéu de edição (topo minimalista com barras douradas) -->
<tr><td style="background:#fefaf1;border-top:6px solid #c9a86a;border-bottom:1px solid #eee5d0;padding:14px 40px;">
  <table width="100%"><tr>
    <td style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#8a6d3b;font-weight:bold;">Edição #01</td>
    <td align="right" style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:1px;color:#8a6d3b;">Julho · 2026</td>
  </tr></table>
</td></tr>

<!-- Capa editorial (título hero + subtítulo + linha decorativa) -->
<tr><td style="padding:52px 40px 20px;background:#fff;text-align:center;">
  <p style="margin:0 0 18px;font-family:Arial,sans-serif;font-size:12px;letter-spacing:4px;text-transform:uppercase;color:#c9a86a;font-weight:bold;">Boletim Semanal</p>
  <h1 style="margin:0;font-family:Georgia,serif;font-size:38px;line-height:1.15;color:#1a1a1a;font-weight:normal;">
    O <em style="color:#5B2A6E;">tema principal</em> desta edição
  </h1>
  <p style="margin:16px auto 0;max-width:440px;font-family:Georgia,serif;font-size:17px;line-height:1.55;color:#666;font-style:italic;">
    Uma linha de subtítulo que resume o que a pessoa vai aprender ou levar dessa edição
  </p>
  <div style="width:60px;height:3px;background:#c9a86a;margin:32px auto 0;"></div>
</td></tr>

<!-- Imagem hero (grande, sem padding lateral) -->
<tr><td style="padding:0;background:#fff;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"><tr>
    <td align="center" valign="middle" height="320" style="background:#f5f2e9;color:#5B2A6E;font-family:Georgia,serif;font-size:20px;">
      Imagem de capa (600x320)
    </td>
  </tr></table>
</td></tr>

<!-- Corpo com drop cap (letra capitular) -->
<tr><td style="padding:32px 40px 8px;background:#fff;">
  <p style="margin:0;font-family:Georgia,serif;font-size:18px;line-height:1.7;color:#2a2a2a;">
    <span style="float:left;font-size:64px;line-height:0.85;color:#5B2A6E;padding:6px 10px 0 0;font-weight:bold;">O</span>lá, <strong>{nome}</strong>. Nesta edição você vai encontrar três leituras cuidadas — uma análise, uma prática e uma recomendação. Comece por qual quiser.
  </p>
</td></tr>

<!-- Seção 1: título numerado editorial -->
<tr><td style="padding:36px 40px 8px;background:#fff;">
  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;letter-spacing:3px;color:#c9a86a;text-transform:uppercase;font-weight:bold;">
    01 · Análise
  </p>
  <h2 style="margin:8px 0 0;font-family:Georgia,serif;font-size:26px;line-height:1.25;color:#1a1a1a;font-weight:normal;">
    Título forte da primeira seção
  </h2>
</td></tr>
<tr><td style="padding:12px 40px 20px;background:#fff;">
  <p style="margin:0;font-family:Georgia,serif;font-size:17px;line-height:1.7;color:#333;">
    Explique o contexto: o que aconteceu, o que você descobriu, por que isso importa para quem lê. Use frases mais longas e ritmadas aqui — é o parágrafo âncora do texto.
  </p>
</td></tr>

<!-- Citação em destaque (blockquote editorial) -->
<tr><td style="padding:8px 40px;background:#fff;">
  <table cellpadding="0" cellspacing="0" style="width:100%;">
    <tr>
      <td style="padding:24px 28px;background:#fefaf1;border-left:4px solid #c9a86a;">
        <p style="margin:0;font-family:Georgia,serif;font-size:20px;line-height:1.5;color:#5B2A6E;font-style:italic;">
          &ldquo;Uma frase de destaque que o leitor vai lembrar depois de terminar a leitura.&rdquo;
        </p>
        <p style="margin:12px 0 0;font-family:Arial,sans-serif;font-size:12px;color:#8a6d3b;letter-spacing:1px;text-transform:uppercase;">— Autor ou fonte</p>
      </td>
    </tr>
  </table>
</td></tr>

<!-- Divisor ornamental -->
<tr><td style="padding:24px 40px;background:#fff;text-align:center;">
  <span style="font-family:Georgia,serif;font-size:24px;color:#c9a86a;letter-spacing:16px;">◆ ◆ ◆</span>
</td></tr>

<!-- Seção 2: prática -->
<tr><td style="padding:12px 40px 8px;background:#fff;">
  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;letter-spacing:3px;color:#c9a86a;text-transform:uppercase;font-weight:bold;">
    02 · Na Prática
  </p>
  <h2 style="margin:8px 0 16px;font-family:Georgia,serif;font-size:26px;line-height:1.25;color:#1a1a1a;font-weight:normal;">
    Passo a passo para aplicar hoje
  </h2>
  <table cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td width="44" valign="top" style="padding:0 12px 0 0;">
        <div style="width:32px;height:32px;background:#5B2A6E;color:#fff;border-radius:50%;text-align:center;line-height:32px;font-family:Georgia,serif;font-size:16px;font-weight:bold;">1</div>
      </td>
      <td valign="top" style="padding-bottom:16px;">
        <h3 style="margin:0;font-family:Georgia,serif;font-size:18px;color:#1a1a1a;font-weight:bold;">Primeiro passo</h3>
        <p style="margin:4px 0 0;font-family:Georgia,serif;font-size:16px;line-height:1.6;color:#444;">Descreva o que fazer primeiro e por quê.</p>
      </td>
    </tr>
    <tr>
      <td valign="top" style="padding:0 12px 0 0;">
        <div style="width:32px;height:32px;background:#5B2A6E;color:#fff;border-radius:50%;text-align:center;line-height:32px;font-family:Georgia,serif;font-size:16px;font-weight:bold;">2</div>
      </td>
      <td valign="top" style="padding-bottom:16px;">
        <h3 style="margin:0;font-family:Georgia,serif;font-size:18px;color:#1a1a1a;font-weight:bold;">Segundo passo</h3>
        <p style="margin:4px 0 0;font-family:Georgia,serif;font-size:16px;line-height:1.6;color:#444;">Detalhe a próxima ação e o que esperar.</p>
      </td>
    </tr>
    <tr>
      <td valign="top" style="padding:0 12px 0 0;">
        <div style="width:32px;height:32px;background:#5B2A6E;color:#fff;border-radius:50%;text-align:center;line-height:32px;font-family:Georgia,serif;font-size:16px;font-weight:bold;">3</div>
      </td>
      <td valign="top">
        <h3 style="margin:0;font-family:Georgia,serif;font-size:18px;color:#1a1a1a;font-weight:bold;">Terceiro passo</h3>
        <p style="margin:4px 0 0;font-family:Georgia,serif;font-size:16px;line-height:1.6;color:#444;">Descreva o resultado esperado e como medir.</p>
      </td>
    </tr>
  </table>
</td></tr>

<!-- Divisor ornamental -->
<tr><td style="padding:32px 40px 16px;background:#fff;text-align:center;">
  <span style="font-family:Georgia,serif;font-size:24px;color:#c9a86a;letter-spacing:16px;">◆ ◆ ◆</span>
</td></tr>

<!-- Seção 3: recomendação com card premium -->
<tr><td style="padding:8px 40px 32px;background:#fff;">
  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;letter-spacing:3px;color:#c9a86a;text-transform:uppercase;font-weight:bold;">
    03 · Recomendação
  </p>
  <h2 style="margin:8px 0 16px;font-family:Georgia,serif;font-size:26px;line-height:1.25;color:#1a1a1a;font-weight:normal;">
    O que separamos para você
  </h2>
  <table cellpadding="0" cellspacing="0" width="100%" style="border:1px solid #eee5d0;border-radius:6px;">
    <tr>
      <td style="padding:24px 28px;background:#fefaf1;">
        <p style="margin:0;font-family:Georgia,serif;font-size:17px;line-height:1.6;color:#333;">
          Com base no seu interesse em <em>[tema]</em>, separamos <em>[conteúdo/recurso/oferta]</em>. Vale porque <em>[motivo específico]</em>.
        </p>
        <div style="margin-top:20px;">
          <a href="#LINK_CTA" style="display:inline-block;background:#5B2A6E;color:#fff;padding:14px 32px;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;letter-spacing:1px;text-transform:uppercase;text-decoration:none;border-radius:2px;">
            Ler agora
          </a>
        </div>
      </td>
    </tr>
  </table>
</td></tr>

<!-- P.S. -->
<tr><td style="padding:0 40px 32px;background:#fff;">
  <p style="margin:0;font-family:Georgia,serif;font-size:16px;line-height:1.7;color:#666;font-style:italic;border-top:1px dashed #ddd;padding-top:20px;">
    <strong style="color:#5B2A6E;font-style:normal;">P.S.:</strong> se tiver sugestões de tema para as próximas edições, é só responder este email — leio todas.
  </p>
</td></tr>

<!-- Assinatura pessoal -->
<tr><td style="padding:0 40px 40px;background:#fff;">
  <p style="margin:0;font-family:Georgia,serif;font-size:16px;color:#333;">Com carinho,</p>
  <p style="margin:6px 0 0;font-family:Georgia,serif;font-size:22px;color:#5B2A6E;font-style:italic;">[Seu nome]</p>
  <p style="margin:2px 0 0;font-family:Arial,sans-serif;font-size:12px;color:#888;letter-spacing:1px;text-transform:uppercase;">[Seu cargo · Empresa]</p>
</td></tr>

<!-- Rodapé escuro premium -->
<tr><td style="background:#1a1a1a;padding:32px 40px;text-align:center;">
  <p style="margin:0;font-family:Georgia,serif;font-size:16px;color:#c9a86a;letter-spacing:2px;">[NOME DA EMPRESA]</p>
  <p style="margin:6px 0 20px;font-family:Arial,sans-serif;font-size:11px;color:#888;letter-spacing:2px;text-transform:uppercase;">Boletim de assinantes</p>
  <p style="margin:0;font-size:20px;">
    <a href="#" style="color:#c9a86a;text-decoration:none;margin:0 8px;">📷</a>
    <a href="#" style="color:#c9a86a;text-decoration:none;margin:0 8px;">💼</a>
    <a href="#" style="color:#c9a86a;text-decoration:none;margin:0 8px;">📺</a>
    <a href="#" style="color:#c9a86a;text-decoration:none;margin:0 8px;">📱</a>
  </p>
  <p style="margin:20px 0 0;font-family:Arial,sans-serif;font-size:11px;color:#666;">
    © 2026 · <a href="#" style="color:#c9a86a;text-decoration:underline;">Cancelar inscrição</a>
  </p>
</td></tr>

</table></td></tr></table></body></html>`
  },
  {
    id: 'produto-destaque', name: 'Produto Destaque', cat: 'Vendas',
    desc: 'Apresenta um produto ou serviço com CTA forte.',
    cor: '#e63946', icone: '🛍️',
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f5f5f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#e63946;padding:32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:24px;">🛍️ Conheça Nossa Solução</h1>
  <p style="color:#ffd6d9;margin:8px 0 0;">Feito para quem quer resultados reais</p>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p>Olá, <strong>{nome}</strong>!</p>
  <p style="text-align:left;">Se você já passou por [problema/situação comum do público], sabe como isso pode [consequência negativa]. Foi pensando em resolver exatamente isso que criamos a solução abaixo.</p>
  <div style="background:#fff5f5;border-radius:8px;padding:20px;margin:16px 0;border-left:4px solid #e63946;text-align:left;">
    <h2 style="color:#e63946;margin:0 0 8px;">Nome do Produto</h2>
    <p style="margin:0;font-size:15px;">Descrição breve e impactante do produto ou serviço. O que ele resolve? Por que é único? Em poucas palavras, explique a transformação que a pessoa vai sentir ao usar.</p>
  </div>
  <p style="text-align:left;font-weight:bold;color:#333;margin:16px 0 8px;">O que você recebe:</p>
  <ul style="text-align:left;padding-left:20px;color:#555;line-height:2;">
    <li>✅ Benefício principal número 1 — explique o resultado prático</li>
    <li>✅ Benefício principal número 2 — explique o resultado prático</li>
    <li>✅ Benefício principal número 3 — explique o resultado prático</li>
    <li>✅ Bônus exclusivo incluso na oferta</li>
  </ul>
  <div style="background:#f8f9fa;border-radius:8px;padding:16px;margin:16px 0;text-align:left;border-left:4px solid #ddd;">
    <p style="font-style:italic;color:#555;margin:0;font-size:14px;">"[Depoimento curto de um cliente satisfeito, citando um resultado específico.]" — [Nome, cargo/empresa]</p>
  </div>
  <a href="#LINK_CTA" style="display:inline-block;background:#e63946;color:#fff;padding:14px 36px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;margin:20px 0;">Quero Saber Mais →</a>
  <p style="font-size:12px;color:#aaa;">Dúvidas? Responda este e-mail, vamos te ajudar com prazer.</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:linear-gradient(135deg,#f77f00,#d62828);padding:32px;text-align:center;">
  <p style="color:#ffe0b2;margin:0;font-size:13px;letter-spacing:2px;text-transform:uppercase;">Oferta por tempo limitado</p>
  <h1 style="color:#fff;margin:8px 0;font-size:32px;">🔥 50% OFF</h1>
  <p style="color:#ffe0b2;margin:0;">Somente até [DATA]</p>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p>Oi, <strong>{nome}</strong>!</p>
  <p style="font-size:16px;">Essa é uma <strong>oportunidade única</strong>. Por tempo limitado, você tem acesso ao <strong>[Produto/Serviço]</strong> com desconto especial — e eu queria que você fosse uma das primeiras pessoas a saber.</p>
  <p>Se você já estava de olho nisso, ou já considerou resolver [problema/situação], esse é o momento certo: o investimento agora é menor, e o resultado é o mesmo de sempre.</p>
  <div style="border:2px dashed #f77f00;border-radius:8px;padding:16px;margin:20px 0;background:#fff8f0;">
    <p style="margin:0;font-size:14px;color:#888;">de <s>R$ 997</s> por apenas</p>
    <p style="margin:4px 0;font-size:36px;font-weight:bold;color:#d62828;">R$ 497</p>
    <p style="margin:0;font-size:13px;color:#888;">ou 12x de R$ 47</p>
  </div>
  <p style="text-align:left;font-weight:bold;color:#333;margin:16px 0 8px;">O que está incluso nessa oferta:</p>
  <ul style="text-align:left;padding-left:20px;color:#555;line-height:1.9;">
    <li>🎁 [Item 1 incluso na oferta]</li>
    <li>🎁 [Item 2 incluso na oferta]</li>
    <li>🎁 Bônus extra por tempo limitado</li>
  </ul>
  <a href="#LINK_CTA" style="display:inline-block;background:#d62828;color:#fff;padding:16px 40px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:18px;">Garantir Minha Vaga →</a>
  <p style="font-size:13px;color:#888;margin-top:16px;">⚠️ Após [DATA] o valor volta ao normal e os bônus saem do ar. Garanta o seu agora.</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#3a0ca3;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">Escolha o Plano Ideal para Você</h1>
</td></tr>
<tr><td style="padding:24px 32px;">
  <p>Olá, <strong>{nome}</strong>!</p>
  <p>Sabemos que escolher o plano certo pode ser difícil — por isso preparamos um comparativo simples para te ajudar a decidir com confiança. Todos os planos incluem [benefício comum a todos], e a diferença está em [o que muda entre eles].</p>
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
  <p style="font-size:13px;color:#888;margin-top:16px;">💬 Ainda com dúvidas sobre qual plano escolher? Responda este e-mail contando seu objetivo principal e te ajudamos a decidir. E lembre-se: você pode mudar de plano a qualquer momento, sem multa.</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#06d6a0;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">💡 3 Dicas para Transformar seus Resultados</h1>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Oi, <strong>{nome}</strong>! Toda semana vejo pessoas cometendo os mesmos erros em [tema/área], e a boa notícia é que são fáceis de corrigir. Separei 3 dicas práticas que vão fazer diferença imediata no seu negócio — pode aplicar a primeira ainda hoje.</p>
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
  <p style="margin-top:16px;color:#555;font-size:14px;line-height:1.6;">Sozinhas, cada uma dessas dicas já ajuda. Mas quando você aplica as três juntas, o efeito é multiplicado — é exatamente isso que ensinamos, com exemplos práticos do dia a dia, em [recurso/produto].</p>
  <div style="text-align:center;margin:24px 0 0;">
    <a href="#LINK_CTA" style="background:#06d6a0;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:bold;">Quero Aprender Mais →</a>
  </div>
  <p style="font-size:12px;color:#aaa;text-align:center;margin-top:12px;">Já aplicou alguma dessas dicas? Responda este e-mail e me conta o resultado!</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#4361ee;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">🏆 Como [Cliente] Conseguiu [Resultado]</h1>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Oi, <strong>{nome}</strong>!</p>
  <p>Deixa eu te contar a história de <strong>[Nome do cliente]</strong>, que estava exatamente na mesma situação que você: [descreva o cenário inicial — a dor, a frustração, o que já tinha tentado e não funcionou].</p>
  <p>Quando começamos a trabalhar juntos, o primeiro passo foi [ação/mudança 1]. Depois, ajustamos [ação/mudança 2]. Em poucas semanas, os primeiros resultados já apareceram — e [Nome do cliente] percebeu que finalmente estava no caminho certo.</p>
  <div style="background:#f8f9ff;border-radius:8px;padding:20px;margin:16px 0;border-left:4px solid #4361ee;">
    <p style="font-style:italic;color:#555;margin:0 0 8px;">"[Depoimento real do cliente em suas próprias palavras. Quanto mais específico, mais convincente.]"</p>
    <p style="margin:0;font-size:13px;color:#888;font-weight:bold;">— [Nome], [Cargo/Empresa]</p>
  </div>
  <p style="font-weight:bold;color:#333;">Os números falam por si:</p>
  <table width="100%" cellpadding="12" cellspacing="8">
    <tr>
      <td style="background:#e8efff;border-radius:8px;text-align:center;"><strong style="font-size:24px;color:#4361ee;">+127%</strong><br><span style="font-size:13px;color:#666;">no resultado X</span></td>
      <td style="background:#e8efff;border-radius:8px;text-align:center;"><strong style="font-size:24px;color:#4361ee;">3x</strong><br><span style="font-size:13px;color:#666;">mais conversões</span></td>
      <td style="background:#e8efff;border-radius:8px;text-align:center;"><strong style="font-size:24px;color:#4361ee;">60 dias</strong><br><span style="font-size:13px;color:#666;">para o resultado</span></td>
    </tr>
  </table>
  <p style="margin-top:16px;color:#555;font-size:14px;line-height:1.6;">O que diferencia esse processo não é sorte — é um método replicável, que já ajudou [número] pessoas/empresas a saírem do mesmo ponto de partida e chegarem a resultados parecidos.</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#7209b7;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">✅ Checklist: [Título do Checklist]</h1>
  <p style="color:#e0b3ff;margin:6px 0 0;font-size:14px;">Tudo que você precisa fazer para [objetivo]</p>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Oi, <strong>{nome}</strong>! Criei este checklist porque percebi que muita gente tenta resolver [objetivo] sem seguir uma ordem clara — e acaba perdendo tempo ou esquecendo etapas importantes.</p>
  <p>Siga os itens abaixo na ordem. Cada um deles resolve uma parte específica do processo, e ao final você terá [resultado esperado].</p>
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
  <p style="margin-top:16px;color:#555;font-size:14px;line-height:1.6;">Quer a versão completa, com explicações detalhadas de cada item e exemplos práticos? Preparamos um material gratuito com tudo isso — é só clicar no botão abaixo.</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #f0e6c0;">
<tr><td style="background:linear-gradient(135deg,#1a3a6b,#2d5a8e);padding:36px 32px;text-align:center;">
  <p style="color:#D4AF37;margin:0 0 8px;font-size:13px;letter-spacing:3px;text-transform:uppercase;">Você está convidado</p>
  <h1 style="color:#fff;margin:0;font-size:28px;font-weight:normal;">[Nome do Evento]</h1>
  <p style="color:#aac4ff;margin:8px 0 0;font-size:14px;">[Subtítulo ou tema do evento]</p>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p>Prezado(a), <strong>{nome}</strong>,</p>
  <p>É com grande prazer que convidamos você para participar de um evento especial, pensado para [público-alvo] que querem [objetivo do evento].</p>
  <p style="text-align:left;">Durante o evento, você vai: conhecer [tema/conteúdo 1], entender como [tema/conteúdo 2] e ter a oportunidade de [networking/interação/brinde]. Tudo isso em um ambiente [descrição do ambiente/clima do evento].</p>
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
  <p style="font-size:13px;color:#888;">As vagas são limitadas para garantir a qualidade do evento — confirme sua presença o quanto antes.</p>
  <a href="#LINK_CTA" style="background:#D4AF37;color:#1a3a6b;padding:14px 36px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;display:inline-block;">Confirmar Presença →</a>
  <p style="font-size:12px;color:#aaa;margin-top:16px;">Dúvidas sobre o evento? Responda este e-mail, será um prazer ajudar.</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:linear-gradient(135deg,#480ca8,#7209b7);padding:32px;text-align:center;">
  <p style="color:#c8b8ff;margin:0 0 6px;font-size:13px;letter-spacing:2px;">AULA GRATUITA AO VIVO</p>
  <h1 style="color:#fff;margin:0;font-size:24px;">[Título do Webinar]</h1>
  <p style="color:#e0b3ff;margin:8px 0 0;">[Data] · [Horário] · Via Zoom</p>
</td></tr>
<tr><td style="padding:28px 32px;color:#333;">
  <p>Oi, <strong>{nome}</strong>!</p>
  <p>Se você sente que [dor/dificuldade comum do público] está te travando, essa aula foi feita para você. Você foi selecionado(a) para participar de uma aula exclusiva e 100% gratuita, onde vou revelar:</p>
  <ul style="padding-left:20px;line-height:2.2;color:#555;">
    <li>🎯 Tópico de alto valor número 1 — explique o que será mostrado</li>
    <li>🎯 Tópico de alto valor número 2 — explique o que será mostrado</li>
    <li>🎯 Tópico de alto valor número 3 — explique o que será mostrado</li>
    <li>🎯 Estratégia bônus revelada ao vivo</li>
  </ul>
  <p style="text-align:left;font-size:14px;color:#555;">Essa aula é ideal para [perfil 1] e [perfil 2] que querem [resultado desejado] sem [obstáculo comum].</p>
  <div style="background:#f0f0ff;border-radius:8px;padding:16px;margin:16px 0;">
    <div style="text-align:center;">
      <strong style="font-size:13px;color:#480ca8;">Apresentado por</strong><br>
      <p style="margin:4px 0 0;font-size:15px;font-weight:bold;">[Nome do Palestrante]</p>
      <p style="margin:4px 0 0;font-size:13px;color:#666;">[Breve credencial/experiência do palestrante que gera autoridade]</p>
    </div>
  </div>
  <p style="font-size:13px;color:#888;">🎁 Bônus exclusivo: quem assistir ao vivo até o final ganha [bônus extra].</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#ef476f;padding:32px;text-align:center;">
  <div style="font-size:48px;">💔</div>
  <h1 style="color:#fff;margin:8px 0 0;font-size:22px;">Sentimos sua falta, {nome}!</h1>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p style="font-size:16px;">Já faz um tempo que não nos falamos e queríamos saber como você está.</p>
  <p>A gente sabe que a vida é corrida, mas muita coisa mudou desde a última vez: [novidade 1], [novidade 2] e [melhoria recente]. Tudo isso pensando em te entregar uma experiência ainda melhor.</p>
  <p>E porque sentimos mesmo sua falta, separamos algo especial:</p>
  <div style="background:#fff5f7;border-radius:8px;padding:20px;margin:20px 0;border:1px dashed #ef476f;">
    <p style="font-weight:bold;color:#ef476f;margin:0 0 8px;">🎁 Presente especial para você voltar</p>
    <p style="margin:0;font-size:15px;">Use o cupom <strong style="font-size:20px;color:#ef476f;">VOLTEI30</strong> e ganhe 30% de desconto</p>
  </div>
  <a href="#LINK_CTA" style="background:#ef476f;color:#fff;padding:14px 36px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;display:inline-block;">Quero Voltar →</a>
  <p style="font-size:12px;color:#aaa;margin-top:16px;">Oferta válida por 7 dias</p>
  <p style="font-size:13px;color:#999;border-top:1px solid #f8e0e6;padding-top:12px;margin-top:16px;">Se preferir não receber mais nossos e-mails, sem problemas — você pode se descadastrar a qualquer momento no link abaixo.</p>
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
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#118ab2;padding:28px 32px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;">📊 Uma pergunta rápida para você</h1>
</td></tr>
<tr><td style="padding:32px;color:#333;text-align:center;">
  <p>Oi, <strong>{nome}</strong>!</p>
  <p style="font-size:16px;">Estamos sempre buscando melhorar [produto/serviço/conteúdo], e sua opinião é fundamental para isso. Leva menos de 10 segundos e vai nos ajudar muito a direcionar nossos próximos passos.</p>
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
  <p style="font-size:13px;color:#888;margin-top:20px;">Ao responder, você nos ajuda a criar conteúdos e soluções cada vez mais alinhados com o que você realmente precisa.</p>
  <p style="font-size:12px;color:#aaa;">Sua opinião é muito importante para nós. Obrigado pelo seu tempo!</p>
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#888;">
  © 2025 Empresa · <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
  {
    id: 'texto-limpo', name: 'Texto Limpo (Sem Alterar)', cat: 'Texto Corrido',
    desc: 'Encaixa seu texto em um layout responsivo sem alterar nenhuma palavra. Ideal para manter controle total.',
    cor: '#6b7280', icone: '📝',
    wrapOnly: true,
    html: `<!DOCTYPE html><html><body style="margin:0;padding:20px;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
<tr><td style="padding:24px 32px 20px;text-align:center;border-bottom:1px solid #f0f0f0;">
  <img src="" alt="" style="max-height:60px;max-width:200px;" onerror="this.style.display='none'">
</td></tr>
<tr><td style="padding:32px;color:#333333;font-size:15px;line-height:1.7;">
  <!-- CONTEUDO_USUARIO -->
  <p>Olá, <strong>{nome}</strong>,</p>
  <p>Seu texto aparecerá aqui exatamente como você escreveu, sem nenhuma alteração. O template apenas adiciona um container visual ao redor do seu conteúdo.</p>
  <!-- /CONTEUDO_USUARIO -->
</td></tr>
<tr><td style="background:#f8f9fa;padding:16px 32px;text-align:center;font-size:12px;color:#999;">
  © 2025 · <a href="#" style="color:#999;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>`
  },
];
