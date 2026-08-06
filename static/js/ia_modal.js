// ia_modal.js — Modal "Criar com IA" e Modal "Galeria de Templates"
// Usados dentro de Nova Campanha / Nova Cadência para inserir HTML
// gerado por IA ou template visual diretamente no editor (via showHtmlInEditor).

// Alvo atual: para onde o HTML gerado/escolhido deve ser inserido
let _aiTarget = null; // { containerId, textareaId, subjectId }

// ─────────────────────────────────────────────
// Modal Criar com IA
// ─────────────────────────────────────────────
let _iamStep = 1;
const _iamTotalSteps = 6;
let _iamHtmlGerado = '';
let _iamModo = null; // 'novo' | 'melhorar'

const _iamStepLabels = [
  '', 'Passo 1 de 6 — Sobre o público',
  'Passo 2 de 6 — Objetivo do email',
  'Passo 3 de 6 — Tema e contexto',
  'Passo 4 de 6 — Formato do email',
  'Passo 5 de 6 — Kit de Marca',
  'Passo 6 de 6 — Imagem',
];

function openAIModal(containerId, textareaId, subjectId) {
  _aiTarget = { containerId, textareaId, subjectId };
  iamReset();
  _iamCarregarKits();
  new bootstrap.Modal(document.getElementById('modalCriarIA')).show();
}

function openAIModalComTema(containerId, textareaId, subjectId, tema) {
  openAIModal(containerId, textareaId, subjectId);
  iamEscolherModo('novo');
  document.getElementById('iamTema').value = tema || '';
  while (_iamStep < 3) iamMudarStep(1);
}

// ─────────────────────────────────────────────
// Passo 0 — escolha do modo (criar novo x melhorar conteúdo existente)
// ─────────────────────────────────────────────
function iamEscolherModo(modo) {
  _iamModo = modo;
  document.getElementById('iamStep0').classList.add('d-none');
  document.getElementById('iamStepMelhorar').classList.toggle('d-none', modo !== 'melhorar');
  document.getElementById('iamWizardCriar').classList.toggle('d-none', modo !== 'novo');
}

function iamVoltarStep0() {
  _iamModo = null;
  document.getElementById('iamStepMelhorar').classList.add('d-none');
  document.getElementById('iamWizardCriar').classList.add('d-none');
  document.getElementById('iamStep0').classList.remove('d-none');
  document.getElementById('iamPlaceholder').classList.remove('d-none');
  document.getElementById('iamResultado').classList.add('d-none');
  document.getElementById('iamBtnInserir').classList.add('d-none');
}

// ─────────────────────────────────────────────
// "Melhorar meu conteúdo" — mantém o conteúdo íntegro, só formata
// ─────────────────────────────────────────────
async function iamFormatarConteudo() {
  const conteudo = document.getElementById('iamConteudoOriginal').value.trim();
  if (!conteudo) { alert('Cole o conteúdo do seu email antes de continuar.'); return; }

  document.getElementById('iamPlaceholder').classList.add('d-none');
  document.getElementById('iamResultado').classList.add('d-none');
  document.getElementById('iamBtnInserir').classList.add('d-none');
  document.getElementById('iamLoading').classList.remove('d-none');

  const msgs = [
    'Lendo seu conteúdo...',
    'Organizando títulos e seções...',
    'Aplicando formatação visual...',
    'Finalizando...',
  ];
  let mi = 0;
  const timer = setInterval(() => {
    document.getElementById('iamMsgGerando').textContent = msgs[mi % msgs.length];
    mi++;
  }, 1500);

  try {
    const res = await fetch('/ia/formatar-conteudo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conteudo })
    });
    const texto = await res.text();
    let data;
    try { data = JSON.parse(texto); } catch (pe) {
      clearInterval(timer);
      document.getElementById('iamLoading').classList.add('d-none');
      document.getElementById('iamPlaceholder').classList.remove('d-none');
      console.error('Resposta nao-JSON:', res.status, texto.substring(0, 200));
      alert('Erro do servidor (status ' + res.status + '). Tente novamente.');
      return;
    }
    clearInterval(timer);
    document.getElementById('iamLoading').classList.add('d-none');
    if (data.erro) {
      document.getElementById('iamPlaceholder').classList.remove('d-none');
      alert('Erro ao formatar conteúdo: ' + data.erro);
      return;
    }
    _iamHtmlGerado = data.html;
    document.getElementById('iamHtmlOutput').value = _iamHtmlGerado;
    const iframe = document.getElementById('iamPreviewFrame');
    iframe.contentDocument.open();
    iframe.contentDocument.write(_iamHtmlGerado);
    iframe.contentDocument.close();
    document.getElementById('iamResultado').classList.remove('d-none');
    document.getElementById('iamBtnInserir').classList.remove('d-none');
    iamSwitchResultTab('preview');
  } catch (e) {
    clearInterval(timer);
    document.getElementById('iamLoading').classList.add('d-none');
    document.getElementById('iamPlaceholder').classList.remove('d-none');
    alert('Erro de conexão: ' + e);
  }
}

function iamReset() {
  _iamStep = 1;
  _iamModo = null;
  _iamHtmlGerado = '';
  document.getElementById('iamStep0').classList.remove('d-none');
  document.getElementById('iamStepMelhorar').classList.add('d-none');
  document.getElementById('iamWizardCriar').classList.add('d-none');
  document.getElementById('iamConteudoOriginal').value = '';
  document.getElementById('iamPublico').value = '';
  document.getElementById('iamFaixaEtaria').value = 'Todas as idades';
  document.querySelectorAll('input[name="iam_nivel"]').forEach(r => {
    r.checked = false;
    const wrap = r.closest('[onclick]');
    if (wrap) { wrap.style.background = ''; wrap.style.borderColor = ''; }
  });
  document.querySelectorAll('.iam-obj-chk').forEach(c => {
    c.checked = false;
    const wrap = c.closest('[onclick]');
    if (wrap) { wrap.style.background = ''; wrap.style.borderColor = ''; }
  });
  document.getElementById('iamObjetivoCustom').value = '';
  document.getElementById('iamTema').value = '';
  document.getElementById('iamContexto').value = '';
  document.getElementById('iamResultado').value = '';
  document.querySelectorAll('input[name="iam_formato"]').forEach(r => {
    r.checked = false;
    const wrap = r.closest('[onclick]');
    if (wrap) { wrap.style.background = ''; wrap.style.borderColor = ''; }
  });
  document.getElementById('iamKitId').value = '';
  document.getElementById('iamToggleImagem').checked = false;
  document.getElementById('iamImagemSection').classList.add('d-none');
  document.getElementById('iamImagemUrl').value = '';
  document.getElementById('iamUploadPreview').innerHTML = '';
  document.getElementById('iamUnsplashResults').innerHTML = '';

  for (let i = 1; i <= _iamTotalSteps; i++) {
    document.getElementById('iamStep' + i).classList.toggle('d-none', i !== 1);
    document.getElementById('iamDot' + i).style.background = i === 1 ? '#4361ee' : '#e0e0e0';
  }
  document.getElementById('iamStepLabel').textContent = _iamStepLabels[1];
  document.getElementById('iamBtnAnterior').style.display = 'none';
  document.getElementById('iamBtnProximo').classList.remove('d-none');
  document.getElementById('iamBtnGerar').classList.add('d-none');
  document.getElementById('iamBtnInserir').classList.add('d-none');

  document.getElementById('iamPlaceholder').classList.remove('d-none');
  document.getElementById('iamLoading').classList.add('d-none');
  document.getElementById('iamResultado').classList.add('d-none');
}

async function _iamCarregarKits() {
  const sel = document.getElementById('iamKitId');
  const semKits = document.getElementById('iamSemKits');
  sel.innerHTML = '<option value="">Sem kit de marca (cores padrão)</option>';
  try {
    const res = await fetch('/api/brand-kits');
    const kits = await res.json();
    if (kits.length) {
      semKits.classList.add('d-none');
      kits.forEach(k => {
        const opt = document.createElement('option');
        opt.value = k.id;
        opt.textContent = k.name;
        sel.appendChild(opt);
      });
    } else {
      semKits.classList.remove('d-none');
    }
  } catch (e) { /* ignora — segue sem kits */ }
}

function iamMudarStep(dir) {
  const proximo = _iamStep + dir;
  if (proximo < 1 || proximo > _iamTotalSteps) return;
  document.getElementById('iamStep' + _iamStep).classList.add('d-none');
  _iamStep = proximo;
  document.getElementById('iamStep' + _iamStep).classList.remove('d-none');
  document.getElementById('iamStepLabel').textContent = _iamStepLabels[_iamStep];
  for (let i = 1; i <= _iamTotalSteps; i++) {
    document.getElementById('iamDot' + i).style.background = i <= _iamStep ? '#4361ee' : '#e0e0e0';
  }
  document.getElementById('iamBtnAnterior').style.display = _iamStep > 1 ? '' : 'none';
  const isLast = _iamStep === _iamTotalSteps;
  document.getElementById('iamBtnProximo').classList.toggle('d-none', isLast);
  document.getElementById('iamBtnGerar').classList.toggle('d-none', !isLast);
}

function iamSelectRadio(name, value, el) {
  document.querySelectorAll(`input[name="${name}"]`).forEach(r => {
    r.checked = r.value === value;
    const wrap = r.closest('[onclick]');
    if (wrap) {
      wrap.style.background = r.value === value ? '#f0f4ff' : '';
      wrap.style.borderColor = r.value === value ? '#4361ee' : '';
    }
  });
}

function iamToggleObjetivo(value, el) {
  const chk = el.querySelector('input');
  chk.checked = !chk.checked;
  el.style.background = chk.checked ? '#f0f4ff' : '';
  el.style.borderColor = chk.checked ? '#4361ee' : '';
}

function iamToggleImagemSection() {
  const show = document.getElementById('iamToggleImagem').checked;
  document.getElementById('iamImagemSection').classList.toggle('d-none', !show);
}

function iamSwitchImgTab(tab, btn) {
  document.getElementById('iamTabUpload').classList.toggle('d-none', tab !== 'upload');
  document.getElementById('iamTabUnsplash').classList.toggle('d-none', tab !== 'unsplash');
  document.querySelectorAll('#iamImgTabs .nav-link').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

async function iamUploadImagem(input) {
  const file = input.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('imagem', file);
  try {
    const res = await fetch('/upload/imagem', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.url) {
      document.getElementById('iamImagemUrl').value = data.url;
      document.getElementById('iamUploadPreview').innerHTML =
        `<img src="${data.url}" style="max-height:120px;border-radius:8px;margin-top:8px;border:1px solid #ddd;">
         <div class="small text-success mt-1"><i class="bi bi-check-circle me-1"></i>Imagem pronta para usar</div>`;
    } else {
      alert('Erro no upload: ' + (data.erro || 'desconhecido'));
    }
  } catch (e) {
    alert('Erro ao fazer upload da imagem.');
  }
}

async function iamBuscarUnsplash() {
  const q = document.getElementById('iamUnsplashQuery').value.trim();
  if (!q) return;
  const div = document.getElementById('iamUnsplashResults');
  div.innerHTML = '<div class="col-12 text-center py-2"><span class="spinner-border spinner-border-sm"></span></div>';
  try {
    const res = await fetch('/ia/buscar-imagem', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q })
    });
    const data = await res.json();
    if (data.erro) {
      div.innerHTML = `<div class="col-12 text-danger small">${data.erro}</div>`;
      return;
    }
    div.innerHTML = (data.imagens || []).map(img => `
      <div class="col-4">
        <img src="${img.thumb}" alt="${img.desc}" title="${img.desc} — ${img.autor}"
             style="width:100%;height:70px;object-fit:cover;border-radius:6px;cursor:pointer;border:2px solid transparent;"
             onclick="iamSelecionarUnsplash('${img.full}',this)">
      </div>
    `).join('');
  } catch (e) {
    div.innerHTML = '<div class="col-12 text-danger small">Erro de conexão com o Unsplash.</div>';
  }
}

function iamSelecionarUnsplash(url, imgEl) {
  document.querySelectorAll('#iamUnsplashResults img').forEach(i => i.style.borderColor = 'transparent');
  imgEl.style.borderColor = '#4361ee';
  document.getElementById('iamImagemUrl').value = url;
}

function iamColetarDados() {
  const objetivoChks = [...document.querySelectorAll('.iam-obj-chk:checked')].map(c => c.value);
  const customObj = document.getElementById('iamObjetivoCustom').value.trim();
  if (customObj) objetivoChks.push(customObj);
  const nivelEl = document.querySelector('input[name="iam_nivel"]:checked');
  const formatoEl = document.querySelector('input[name="iam_formato"]:checked');
  return {
    publico: document.getElementById('iamPublico').value.trim(),
    faixa_etaria: document.getElementById('iamFaixaEtaria').value,
    nivel: nivelEl ? nivelEl.value : 'Intermediário',
    objetivo: objetivoChks.join(', '),
    tema: document.getElementById('iamTema').value.trim(),
    contexto: document.getElementById('iamContexto').value.trim(),
    resultado: document.getElementById('iamResultado').value.trim(),
    formato: formatoEl ? formatoEl.value : 'Texto corrido',
    kit_id: document.getElementById('iamKitId').value || null,
    imagem_url: document.getElementById('iamImagemUrl').value.trim(),
  };
}

async function iamGerarEmail() {
  const dados = iamColetarDados();
  if (!dados.tema) { alert('Informe o tema do email no Passo 3.'); return; }

  document.getElementById('iamPlaceholder').classList.add('d-none');
  document.getElementById('iamResultado').classList.add('d-none');
  document.getElementById('iamBtnInserir').classList.add('d-none');
  document.getElementById('iamLoading').classList.remove('d-none');

  const msgs = [
    'Analisando o público-alvo...',
    'Definindo estrutura do email...',
    'Escrevendo o conteúdo...',
    'Aplicando formatação HTML...',
  ];
  let mi = 0;
  const timer = setInterval(() => {
    document.getElementById('iamMsgGerando').textContent = msgs[mi % msgs.length];
    mi++;
  }, 1800);

  try {
    const res = await fetch('/ia/gerar-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dados)
    });
    const texto = await res.text();
    let data;
    try { data = JSON.parse(texto); } catch (pe) {
      clearInterval(timer);
      document.getElementById('iamLoading').classList.add('d-none');
      document.getElementById('iamPlaceholder').classList.remove('d-none');
      console.error('Resposta nao-JSON:', res.status, texto.substring(0, 200));
      alert('Erro do servidor (status ' + res.status + '). Tente novamente.');
      return;
    }
    clearInterval(timer);
    document.getElementById('iamLoading').classList.add('d-none');
    if (data.erro) {
      document.getElementById('iamPlaceholder').classList.remove('d-none');
      alert('Erro ao gerar email: ' + data.erro);
      return;
    }
    _iamHtmlGerado = data.html;
    document.getElementById('iamHtmlOutput').value = _iamHtmlGerado;
    const iframe = document.getElementById('iamPreviewFrame');
    iframe.contentDocument.open();
    iframe.contentDocument.write(_iamHtmlGerado);
    iframe.contentDocument.close();
    document.getElementById('iamResultado').classList.remove('d-none');
    document.getElementById('iamBtnInserir').classList.remove('d-none');
    iamSwitchResultTab('preview');
  } catch (e) {
    clearInterval(timer);
    document.getElementById('iamLoading').classList.add('d-none');
    document.getElementById('iamPlaceholder').classList.remove('d-none');
    alert('Erro de conexão: ' + e);
  }
}

function iamSwitchResultTab(tab) {
  const isPreview = tab === 'preview';
  document.getElementById('iamTabPreview').classList.toggle('d-none', !isPreview);
  document.getElementById('iamTabHtml').classList.toggle('d-none', isPreview);
  document.getElementById('iamBtnTabPreview').classList.toggle('active', isPreview);
  document.getElementById('iamBtnTabHtml').classList.toggle('active', !isPreview);
  if (isPreview) {
    const editado = document.getElementById('iamHtmlOutput').value;
    if (editado !== _iamHtmlGerado) {
      _iamHtmlGerado = editado;
      const iframe = document.getElementById('iamPreviewFrame');
      iframe.contentDocument.open();
      iframe.contentDocument.write(_iamHtmlGerado);
      iframe.contentDocument.close();
    }
  }
}

function iamInserirNoEditor() {
  if (!_iamHtmlGerado || !_aiTarget) return;
  const html = document.getElementById('iamHtmlOutput').value || _iamHtmlGerado;
  const tema = document.getElementById('iamTema').value.trim();
  showHtmlInEditor(_aiTarget.containerId, _aiTarget.textareaId, html, _aiTarget.subjectId, tema);
  bootstrap.Modal.getInstance(document.getElementById('modalCriarIA')).hide();
}

// ─────────────────────────────────────────────
// Modal Galeria de Templates
// ─────────────────────────────────────────────
let _gtmTemplateAtivo = null;

function openTemplatesModal(containerId, textareaId, subjectId) {
  _aiTarget = { containerId, textareaId, subjectId };
  const primeiroBtn = document.querySelector('#modalGaleriaTemplates .gtm-cat-btn');
  gtmFiltrarCat('todos', primeiroBtn);
  new bootstrap.Modal(document.getElementById('modalGaleriaTemplates')).show();
}

function gtmFiltrarCat(cat, btn) {
  document.querySelectorAll('#modalGaleriaTemplates .gtm-cat-btn').forEach(b => {
    b.className = b === btn ? 'btn btn-sm btn-primary gtm-cat-btn' : 'btn btn-sm btn-outline-secondary gtm-cat-btn';
  });
  const grade = document.getElementById('gtmGrade');
  grade.innerHTML = '';
  const lista = cat === 'todos' ? _TEMPLATES : _TEMPLATES.filter(t => t.cat === cat);
  lista.forEach(t => {
    const col = document.createElement('div');
    col.className = 'col-md-4 col-sm-6';
    col.innerHTML = `
      <div class="card h-100" style="cursor:pointer;transition:transform .15s,box-shadow .15s;"
           onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 8px 24px rgba(0,0,0,.12)'"
           onmouseout="this.style.transform='';this.style.boxShadow=''">
        <div style="height:120px;background:${t.cor};border-radius:12px 12px 0 0;display:flex;align-items:center;justify-content:center;font-size:42px;">
          ${t.icone}
        </div>
        <div class="card-body p-3">
          <span class="badge mb-2" style="background:${t.cor}22;color:${t.cor};font-size:.7rem;">${t.cat}</span>
          <h6 class="fw-bold mb-1">${t.name}</h6>
          <p class="text-muted small mb-3">${t.desc}</p>
          <div class="d-flex gap-2">
            <button type="button" class="btn btn-sm btn-primary flex-fill" onclick="gtmAbrirPrevia('${t.id}')">
              <i class="bi bi-eye me-1"></i>Prévia
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="gtmUsarDireto('${t.id}')" title="Usar este template">
              <i class="bi bi-check-lg"></i>
            </button>
          </div>
        </div>
      </div>`;
    grade.appendChild(col);
  });
}

async function gtmAbrirPrevia(id) {
  _gtmTemplateAtivo = _TEMPLATES.find(t => t.id === id);
  if (!_gtmTemplateAtivo) return;
  document.getElementById('gtmModalTitulo').textContent = _gtmTemplateAtivo.name;
  const iframe = document.getElementById('gtmPreviaFrame');
  iframe.contentDocument.open();
  iframe.contentDocument.write(_gtmTemplateAtivo.html);
  iframe.contentDocument.close();

  // Popula dropdown de kits
  const sel = document.getElementById('gtmKitAplicar');
  sel.innerHTML = '<option value="">Sem kit</option>';
  try {
    const res = await fetch('/api/brand-kits');
    const kits = await res.json();
    kits.forEach(k => {
      const opt = document.createElement('option');
      opt.value = k.id;
      opt.textContent = k.name;
      sel.appendChild(opt);
    });
  } catch (e) {}

  bootstrap.Modal.getInstance(document.getElementById('modalGaleriaTemplates'))?.hide();
  new bootstrap.Modal(document.getElementById('modalGtmPrevia')).show();
}

async function gtmAplicarKit() {
  if (!_gtmTemplateAtivo) return;
  const kitId = document.getElementById('gtmKitAplicar').value;
  if (!kitId) { alert('Selecione um kit de marca.'); return; }
  const res = await fetch('/api/brand-kits');
  const kits = await res.json();
  const kit = kits.find(k => String(k.id) === String(kitId));
  if (!kit) return;
  let html = _gtmTemplateAtivo.html;
  html = html.replace(/#1a3a6b/g, kit.primary_color || '#1a3a6b');
  html = html.replace(/#D4AF37/g, kit.secondary_color || '#D4AF37');
  html = html.replace(/#4361ee/g, kit.accent_color || '#4361ee');
  html = html.replace(/#333333|color:#333(?![a-f0-9])/g, kit.text_color || '#333333');
  html = html.replace(/Arial,sans-serif/g, (kit.font_primary || 'Arial') + ',sans-serif');
  _gtmTemplateAtivo = { ..._gtmTemplateAtivo, html };
  const iframe = document.getElementById('gtmPreviaFrame');
  iframe.contentDocument.open();
  iframe.contentDocument.write(html);
  iframe.contentDocument.close();
}

function gtmPersonalizarComIA() {
  if (!_gtmTemplateAtivo || !_aiTarget) return;
  bootstrap.Modal.getInstance(document.getElementById('modalGtmPrevia'))?.hide();
  const tema = _gtmTemplateAtivo.name + ' — ' + _gtmTemplateAtivo.cat;
  openAIModalComTema(_aiTarget.containerId, _aiTarget.textareaId, _aiTarget.subjectId, tema);
}

function gtmUsarTemplate() {
  if (!_gtmTemplateAtivo || !_aiTarget) return;
  _gtmAplicarTemplateAoConteudo(_gtmTemplateAtivo.html, _gtmTemplateAtivo.name, _gtmTemplateAtivo.wrapOnly);
  bootstrap.Modal.getInstance(document.getElementById('modalGtmPrevia'))?.hide();
}

function gtmUsarDireto(id) {
  const tpl = _TEMPLATES.find(t => t.id === id);
  if (!tpl || !_aiTarget) return;
  _gtmAplicarTemplateAoConteudo(tpl.html, tpl.name, tpl.wrapOnly);
  bootstrap.Modal.getInstance(document.getElementById('modalGaleriaTemplates'))?.hide();
}

// Se o editor de destino já tem conteúdo (texto/imagens/links do usuário),
// pergunta o que fazer com esse conteúdo em relação ao template escolhido.
// Caso contrário, apenas insere o template.
let _gtmPendingTemplate = null; // { html, nome, wrapOnly }

async function _gtmAplicarTemplateAoConteudo(templateHtml, nome, wrapOnly) {
  const conteudoAtual = getEditorContent(_aiTarget.containerId, _aiTarget.textareaId);

  if (!conteudoAtual.trim()) {
    showHtmlInEditor(_aiTarget.containerId, _aiTarget.textareaId, templateHtml, _aiTarget.subjectId, nome);
    return;
  }

  if (wrapOnly) {
    const wrapped = _wrapContentInTemplate(conteudoAtual, templateHtml);
    showHtmlInEditor(_aiTarget.containerId, _aiTarget.textareaId, wrapped, _aiTarget.subjectId, nome);
    showToast('Layout aplicado ao seu conteúdo (texto mantido na íntegra).', 'success');
    return;
  }

  _gtmPendingTemplate = { html: templateHtml, nome };
  new bootstrap.Modal(document.getElementById('modalEscolhaTemplate')).show();
}

function _wrapContentInTemplate(content, templateHtml) {
  const marker = '<!-- CONTEUDO_USUARIO -->';
  const endMarker = '<!-- /CONTEUDO_USUARIO -->';
  const startIdx = templateHtml.indexOf(marker);
  const endIdx = templateHtml.indexOf(endMarker);
  if (startIdx !== -1 && endIdx !== -1) {
    return templateHtml.substring(0, startIdx + marker.length) + '\n' + content + '\n' + templateHtml.substring(endIdx);
  }
  const parser = new DOMParser();
  const doc = parser.parseFromString(templateHtml, 'text/html');
  const tds = doc.querySelectorAll('td');
  let mainTd = null;
  let maxLen = 0;
  tds.forEach(td => {
    const style = td.getAttribute('style') || '';
    if (style.includes('padding') && !style.includes('background:#f8f9fa') && !style.includes('text-align:center')) {
      const textLen = td.textContent.length;
      if (textLen > maxLen) { maxLen = textLen; mainTd = td; }
    }
  });
  if (mainTd) {
    mainTd.innerHTML = content;
    return '<!DOCTYPE html>' + doc.documentElement.outerHTML;
  }
  return templateHtml.replace(/<td style="padding:3[0-9]px[^"]*"[^>]*>[\s\S]*?<\/td>(\s*<\/tr>\s*<tr><td style="background:#f8f9fa)/,
    `<td style="padding:32px;color:#333;font-size:15px;line-height:1.7;">\n${content}\n</td>$1`);
}

async function gtmEscolherOpcao(opcao) {
  bootstrap.Modal.getInstance(document.getElementById('modalEscolhaTemplate'))?.hide();
  if (!_gtmPendingTemplate) return;
  const { html: templateHtml, nome } = _gtmPendingTemplate;
  _gtmPendingTemplate = null;

  if (opcao === 'substituir') {
    showHtmlInEditor(_aiTarget.containerId, _aiTarget.textareaId, templateHtml, _aiTarget.subjectId, nome);
    return;
  }

  if (opcao === 'encaixar') {
    const conteudoAtual = getEditorContent(_aiTarget.containerId, _aiTarget.textareaId);
    const wrapped = _wrapContentInTemplate(conteudoAtual, templateHtml);
    showHtmlInEditor(_aiTarget.containerId, _aiTarget.textareaId, wrapped, _aiTarget.subjectId, nome);
    showToast('Layout aplicado (texto mantido na íntegra).', 'success');
    return;
  }

  const conteudoAtual = getEditorContent(_aiTarget.containerId, _aiTarget.textareaId);
  const endpoint = opcao === 'visual' ? '/ia/ajustar-visual' : '/ia/aplicar-template';

  showToast('Aplicando com IA, aguarde...', 'info');
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conteudo_html: conteudoAtual, template_html: templateHtml })
    });
    const texto = await res.text();
    let data;
    try { data = JSON.parse(texto); } catch (parseErr) {
      console.error('Resposta não-JSON de ' + endpoint + ':', res.status, texto);
      alert('Erro ao aplicar template com IA (resposta inválida do servidor, status ' + res.status + '). Veja o console para detalhes.');
      return;
    }
    if (!res.ok || data.erro) {
      alert('Erro ao aplicar template com IA: ' + (data.erro || ('status ' + res.status)));
      return;
    }
    showHtmlInEditor(_aiTarget.containerId, _aiTarget.textareaId, data.html, _aiTarget.subjectId, nome);
    showToast('Template aplicado ao seu conteúdo!', 'success');
  } catch (e) {
    console.error('Erro de rede em ' + endpoint + ':', e);
    alert('Erro ao aplicar template com IA: ' + e.message);
  }
}
