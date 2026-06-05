// editor.js — Editor visual Quill para ConvertMail

const _quillMap = new Map();   // containerId -> quill instance
let _tplTarget = null;         // { quill, subjectId } — editor alvo do modal de templates
let _tplCache = null;          // cache dos templates da API

// ─────────────────────────────────────────────
// Inicializar editor (Visual + HTML em abas)
// ─────────────────────────────────────────────
function initEditor(cfg) {
  // cfg: { containerId, textareaId, subjectId, autoSignature }
  const textarea = document.getElementById(cfg.textareaId);
  const visualDiv = document.getElementById(cfg.containerId);

  const toolbarCfg = [
    ['bold', 'italic', 'underline', 'strike'],
    [{ color: [] }, { background: [] }],
    [{ size: ['small', false, 'large', 'huge'] }],
    [{ align: [] }],
    [{ list: 'ordered' }, { list: 'bullet' }],
    ['link', 'image'],
    ['clean']
  ];

  // Cria instância Quill com closure para capturar referência
  let quill;
  quill = new Quill('#' + cfg.containerId, {
    theme: 'snow',
    placeholder: 'Escreva o corpo do email aqui...',
    modules: {
      toolbar: {
        container: toolbarCfg,
        handlers: {
          image: function () { _uploadImage(quill); }
        }
      }
    }
  });

  // Carrega conteúdo inicial
  const inicial = textarea.value.trim();
  if (inicial) {
    quill.clipboard.dangerouslyPasteHTML(inicial);
  } else if (cfg.autoSignature) {
    // carrega assinatura apenas se o campo está vazio
    _fetchSignature(quill);
  }

  // Sincroniza Quill → textarea em tempo real
  quill.on('text-change', function () {
    textarea.value = quill.root.innerHTML === '<p><br></p>' ? '' : quill.root.innerHTML;
  });

  _quillMap.set(cfg.containerId, quill);
  return quill;
}

// ─────────────────────────────────────────────
// Upload de imagem
// ─────────────────────────────────────────────
function _uploadImage(quill) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/jpeg,image/png,image/gif,image/webp';
  input.click();
  input.onchange = async function () {
    const file = input.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      alert('Imagem muito grande. Máximo 5MB.');
      return;
    }
    const fd = new FormData();
    fd.append('imagem', file);
    try {
      const res = await fetch('/upload/imagem', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.url) {
        const range = quill.getSelection(true);
        quill.insertEmbed(range ? range.index : quill.getLength() - 1, 'image', data.url);
      } else {
        alert('Erro no upload: ' + (data.erro || 'desconhecido'));
      }
    } catch (e) {
      alert('Erro ao fazer upload da imagem.');
    }
  };
}

function uploadImageToEditor(containerId) {
  const quill = _quillMap.get(containerId);
  if (quill) _uploadImage(quill);
}

// ─────────────────────────────────────────────
// Inserir {nome} no cursor
// ─────────────────────────────────────────────
function insertNome(containerId) {
  const quill = _quillMap.get(containerId);
  if (!quill) return;
  const range = quill.getSelection(true);
  quill.insertText(range ? range.index : quill.getLength() - 1, '{nome}', 'user');
  quill.focus();
}

// ─────────────────────────────────────────────
// Alternar aba Texto / HTML / Preview
// ─────────────────────────────────────────────
function editorTab(tab, containerId, textareaId) {
  const quill = _quillMap.get(containerId);
  const textarea = document.getElementById(textareaId);
  const visualWrap = document.getElementById('visual-' + containerId);
  const htmlWrap = document.getElementById('html-' + containerId);
  const previewWrap = document.getElementById('preview-' + containerId);
  const btnVisual = document.getElementById('tab-btn-visual-' + containerId);
  const btnHtml = document.getElementById('tab-btn-html-' + containerId);
  const btnPreview = document.getElementById('tab-btn-preview-' + containerId);

  // Captura qual aba estava ativa ANTES de ocultar tudo
  const fromVisual = visualWrap && !visualWrap.classList.contains('d-none');

  [visualWrap, htmlWrap, previewWrap].forEach(el => el && el.classList.add('d-none'));
  [btnVisual, btnHtml, btnPreview].forEach(el => el && el.classList.remove('active'));

  if (tab === 'html') {
    // Só sincroniza Quill→textarea se vinha da aba Texto
    if (fromVisual && quill) {
      textarea.value = quill.root.innerHTML === '<p><br></p>' ? '' : quill.root.innerHTML;
    }
    htmlWrap.classList.remove('d-none');
    btnHtml.classList.add('active');
  } else if (tab === 'preview') {
    // Se vinha da aba Texto, sincroniza Quill→textarea primeiro
    if (fromVisual && quill) {
      textarea.value = quill.root.innerHTML === '<p><br></p>' ? '' : quill.root.innerHTML;
    }
    // Lê direto do textarea pelo ID — funciona vindo da aba HTML ou Texto
    const conteudo = document.getElementById(textareaId)?.value || '';
    if (previewWrap) {
      previewWrap.classList.remove('d-none');
      const iframe = previewWrap.querySelector('iframe');
      if (iframe) {
        const vazio = '<p style="color:#999;font-style:italic;padding:16px">Nenhum conteúdo para visualizar.</p>';
        // Injeta <base> para resolver URLs relativas (imagens, CSS local)
        const base = `<base href="${window.location.origin}/">`;
        const html = conteudo
          ? (conteudo.includes('<base') ? conteudo : base + conteudo)
          : vazio;
        iframe.removeAttribute('srcdoc');
        iframe.contentDocument.open();
        iframe.contentDocument.write(html);
        iframe.contentDocument.close();
        setTimeout(() => {
          try {
            const h = iframe.contentDocument.body?.scrollHeight || 0;
            if (h > 0) iframe.style.height = (h + 24) + 'px';
          } catch (e) {}
        }, 150);
      }
    }
    btnPreview && btnPreview.classList.add('active');
  } else {
    // Voltando para aba Texto: carrega textarea no Quill
    if (quill) quill.clipboard.dangerouslyPasteHTML(textarea.value || '');
    visualWrap.classList.remove('d-none');
    btnVisual.classList.add('active');
  }
}

// ─────────────────────────────────────────────
// Assinatura
// ─────────────────────────────────────────────
async function _fetchSignature(quill) {
  try {
    const res = await fetch('/api/assinatura');
    const data = await res.json();
    if (data.body_html) {
      const len = quill.getLength();
      quill.clipboard.dangerouslyPasteHTML(len > 1 ? len - 1 : 0, '\n' + data.body_html);
    }
  } catch (e) { /* sem assinatura configurada */ }
}

function reinserirAssinatura(containerId) {
  const quill = _quillMap.get(containerId);
  if (quill) _fetchSignature(quill);
}

// ─────────────────────────────────────────────
// Modal de templates
// ─────────────────────────────────────────────
function openTemplateModal(containerId, subjectId) {
  _tplTarget = { containerId, subjectId };
  _renderTemplates();
  new bootstrap.Modal(document.getElementById('modalTemplates')).show();
}

async function _renderTemplates() {
  const container = document.getElementById('template-cards-container');
  if (!container) return;

  if (!_tplCache) {
    container.innerHTML = '<div class="text-muted text-center py-3">Carregando...</div>';
    const res = await fetch('/api/templates');
    _tplCache = await res.json();
  }

  // Agrupa por categoria
  const cats = {};
  _tplCache.forEach(t => {
    const c = t.category || 'Geral';
    if (!cats[c]) cats[c] = [];
    cats[c].push(t);
  });

  let html = '';
  for (const [cat, tpls] of Object.entries(cats)) {
    html += `<div class="mb-3"><h6 class="text-muted small fw-bold mb-2">${cat.toUpperCase()}</h6><div class="row g-2">`;
    tpls.forEach(t => {
      html += `<div class="col-md-6">
        <div class="card card-body py-2 px-3 h-100" style="cursor:pointer;border:1px solid #e0e0e0"
             onmouseover="this.style.borderColor='#4361ee'" onmouseout="this.style.borderColor='#e0e0e0'"
             onclick="applyTemplate(${t.id})">
          <div class="fw-semibold small">${t.name}</div>
          <div class="text-muted" style="font-size:.75rem">${t.subject || ''}</div>
        </div>
      </div>`;
    });
    html += '</div></div>';
  }
  container.innerHTML = html;
}

function applyTemplate(tplId) {
  if (!_tplTarget || !_tplCache) return;
  const tpl = _tplCache.find(t => t.id === tplId);
  if (!tpl) return;

  const quill = _quillMap.get(_tplTarget.containerId);
  if (quill) quill.clipboard.dangerouslyPasteHTML(tpl.body_html || '');

  if (_tplTarget.subjectId) {
    const inp = document.getElementById(_tplTarget.subjectId);
    if (inp && tpl.subject) inp.value = tpl.subject;
  }

  bootstrap.Modal.getInstance(document.getElementById('modalTemplates')).hide();
}

function filterTemplates(q) {
  if (!_tplCache) return;
  const term = q.toLowerCase();
  const filtered = term ? _tplCache.filter(t =>
    t.name.toLowerCase().includes(term) || (t.subject || '').toLowerCase().includes(term)
  ) : null;

  if (!term) { _renderTemplates(); return; }

  const container = document.getElementById('template-cards-container');
  let html = '<div class="row g-2">';
  (filtered || []).forEach(t => {
    html += `<div class="col-md-6">
      <div class="card card-body py-2 px-3 h-100" style="cursor:pointer;border:1px solid #e0e0e0"
           onmouseover="this.style.borderColor='#4361ee'" onmouseout="this.style.borderColor='#e0e0e0'"
           onclick="applyTemplate(${t.id})">
        <div class="fw-semibold small">${t.name}</div>
        <div class="text-muted" style="font-size:.75rem">${t.subject || ''}</div>
      </div>
    </div>`;
  });
  html += '</div>';
  container.innerHTML = html;
}

// ─────────────────────────────────────────────
// Helpers para nova_cadencia (múltiplos editores por passo)
// ─────────────────────────────────────────────
let _stepCount = 0;

function initStepEditor(stepDiv) {
  const idx = _stepCount++;
  const containerId = 'quill-step-' + idx;
  const textareaId = 'textarea-step-' + idx;

  const editorDiv = stepDiv.querySelector('.step-quill-container');
  const textarea = stepDiv.querySelector('.step-body-textarea');
  if (!editorDiv || !textarea) return;

  editorDiv.id = containerId;
  textarea.id = textareaId;

  // Botões extras do passo
  stepDiv.querySelector('.btn-insert-nome')?.setAttribute('onclick', `insertNome('${containerId}')`);
  stepDiv.querySelector('.btn-upload-imagem')?.setAttribute('onclick', `uploadImageToEditor('${containerId}')`);
  stepDiv.querySelector('.btn-tab-visual')?.setAttribute('id', `tab-btn-visual-${containerId}`);
  stepDiv.querySelector('.btn-tab-visual')?.setAttribute('onclick', `editorTab('visual','${containerId}','${textareaId}')`);
  stepDiv.querySelector('.btn-tab-html')?.setAttribute('id', `tab-btn-html-${containerId}`);
  stepDiv.querySelector('.btn-tab-html')?.setAttribute('onclick', `editorTab('html','${containerId}','${textareaId}')`);
  stepDiv.querySelector('.btn-tab-preview')?.setAttribute('id', `tab-btn-preview-${containerId}`);
  stepDiv.querySelector('.btn-tab-preview')?.setAttribute('onclick', `editorTab('preview','${containerId}','${textareaId}')`);
  stepDiv.querySelector('.visual-wrap')?.setAttribute('id', `visual-${containerId}`);
  stepDiv.querySelector('.html-wrap')?.setAttribute('id', `html-${containerId}`);
  stepDiv.querySelector('.preview-wrap')?.setAttribute('id', `preview-${containerId}`);

  // Atualiza subjectId para o modal de template deste passo
  const subjectInput = stepDiv.querySelector('input[name="step_subject[]"]');
  const subjectId = 'subject-step-' + idx;
  if (subjectInput) subjectInput.id = subjectId;

  stepDiv.querySelector('.btn-template')?.setAttribute(
    'onclick', `openTemplateModal('${containerId}','${subjectId}')`
  );
  stepDiv.querySelector('.btn-assinatura')?.setAttribute(
    'onclick', `reinserirAssinatura('${containerId}')`
  );

  initEditor({ containerId, textareaId, subjectId, autoSignature: false });
}

// Sincroniza todos os editores antes do submit (garante textareas atualizados)
function syncAllEditors() {
  _quillMap.forEach((quill, containerId) => {
    const editorEl = document.getElementById(containerId);
    if (!editorEl) return;
    // O evento text-change já sincroniza continuamente, mas forçamos aqui
    const formEl = editorEl.closest('form');
    if (!formEl) return;
    const textareaId = containerId.replace('quill-', 'textarea-').replace('quill', 'textarea');
    const ta = document.getElementById(textareaId);
    if (ta) ta.value = quill.root.innerHTML === '<p><br></p>' ? '' : quill.root.innerHTML;
  });
  return true;
}
