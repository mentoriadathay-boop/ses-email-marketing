// editor.js — Editor visual Quill para ConvertMail

const _quillMap = new Map();   // containerId -> quill instance
let _tplTarget = null;         // { quill, subjectId } — editor alvo do modal de templates
let _tplCache = null;          // cache dos templates da API
const _rawHtmlContainers = new Set(); // containers cujo textarea contém um HTML completo (template/IA) — não sincronizar a partir do Quill

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
  // Documentos HTML completos (gerados por IA ou templates) não devem ser
  // colados no Quill — ele sanitiza/perde o layout. Mantemos o textarea
  // intacto e mostramos via showHtmlInEditor (aba Preview/HTML).
  const isFullHtmlDoc = /^<!DOCTYPE|^<html/i.test(inicial);
  if (isFullHtmlDoc) {
    showHtmlInEditor(cfg.containerId, cfg.textareaId, inicial);
  } else if (inicial) {
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

  // Indo para a aba "Texto" enquanto o conteúdo é um HTML completo (template/IA):
  // editar visualmente no Quill iria mangling o HTML e perder layout/imagens. Avisa antes.
  if (tab === 'visual' && _rawHtmlContainers.has(containerId)) {
    const ok = confirm('Editar na aba "Texto" vai converter este e-mail para um formato simples e pode perder a formatação original (imagens, layout, cores). Deseja continuar?');
    if (!ok) return;
    _rawHtmlContainers.delete(containerId);
  }

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
// Insere HTML completo (gerado por IA ou template) direto no editor,
// sem passar pelo Quill (que sanitiza/mangla documentos HTML completos),
// e mostra a aba Preview já renderizada.
// ─────────────────────────────────────────────
function showHtmlInEditor(containerId, textareaId, html, subjectId, subjectValue) {
  const textarea = document.getElementById(textareaId);
  if (!textarea) return;
  textarea.value = html;
  _rawHtmlContainers.add(containerId);

  if (subjectId && subjectValue) {
    const subjectEl = document.getElementById(subjectId);
    if (subjectEl && !subjectEl.value.trim()) subjectEl.value = subjectValue;
  }

  const visualWrap = document.getElementById('visual-' + containerId);
  const htmlWrap = document.getElementById('html-' + containerId);
  const previewWrap = document.getElementById('preview-' + containerId);
  const btnVisual = document.getElementById('tab-btn-visual-' + containerId);
  const btnHtml = document.getElementById('tab-btn-html-' + containerId);
  const btnPreview = document.getElementById('tab-btn-preview-' + containerId);

  [visualWrap, htmlWrap].forEach(el => el && el.classList.add('d-none'));
  [btnVisual, btnHtml].forEach(el => el && el.classList.remove('active'));

  if (previewWrap) {
    previewWrap.classList.remove('d-none');
    btnPreview && btnPreview.classList.add('active');
    const iframe = previewWrap.querySelector('iframe');
    if (iframe) {
      const base = `<base href="${window.location.origin}/">`;
      const out = html.includes('<base') ? html : base + html;
      iframe.removeAttribute('srcdoc');
      iframe.contentDocument.open();
      iframe.contentDocument.write(out);
      iframe.contentDocument.close();
      setTimeout(() => {
        try {
          const h = iframe.contentDocument.body?.scrollHeight || 0;
          if (h > 0) iframe.style.height = (h + 24) + 'px';
        } catch (e) {}
      }, 150);
    }
  }
}

// ─────────────────────────────────────────────
// Editar Textos de um HTML completo (template/IA)
// ─────────────────────────────────────────────
let _editTextsTarget = null;

const _NAO_EDITAVEIS = ['SCRIPT', 'STYLE', 'BR', 'IMG', 'HR', 'INPUT', 'SELECT', 'OPTION', 'HEAD', 'TITLE', 'META', 'LINK'];

function _getEditableTextEls(doc) {
  return Array.from(doc.body.querySelectorAll('*')).filter(el => {
    if (_NAO_EDITAVEIS.includes(el.tagName)) return false;
    const hasElementChild = Array.from(el.childNodes).some(n => n.nodeType === 1);
    if (hasElementChild) return false;
    const text = (el.textContent || '').trim();
    return text.length > 0;
  });
}

function editTextsModal(containerId, textareaId) {
  const textarea = document.getElementById(textareaId);
  const html = (textarea && textarea.value) || '';
  if (!html.trim()) { alert('Não há conteúdo no e-mail ainda.'); return; }

  const doc = new DOMParser().parseFromString(html, 'text/html');
  const els = _getEditableTextEls(doc);
  if (!els.length) {
    alert('Nenhum texto editável encontrado neste e-mail.');
    return;
  }

  const list = document.getElementById('editTextsList');
  list.innerHTML = els.map((el, i) => {
    const tag = el.tagName.toLowerCase();
    const text = el.textContent.trim();
    const rows = text.length > 100 ? 4 : (text.length > 40 ? 2 : 1);
    return `
      <div class="mb-2">
        <label class="form-label small text-muted mb-1">&lt;${tag}&gt;</label>
        <textarea class="form-control form-control-sm edit-text-value" data-idx="${i}" rows="${rows}">${_escapeHtml(text)}</textarea>
      </div>`;
  }).join('');

  _editTextsTarget = { containerId, textareaId };
  new bootstrap.Modal(document.getElementById('modalEditTexts')).show();
}

function applyEditTexts() {
  if (!_editTextsTarget) return;
  const textarea = document.getElementById(_editTextsTarget.textareaId);
  const html = (textarea && textarea.value) || '';
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const els = _getEditableTextEls(doc);

  document.querySelectorAll('#editTextsList .edit-text-value').forEach(ta => {
    const idx = parseInt(ta.dataset.idx, 10);
    if (els[idx]) els[idx].textContent = ta.value;
  });

  let newHtml;
  if (/^<!DOCTYPE/i.test(html)) {
    newHtml = '<!DOCTYPE html>\n' + doc.documentElement.outerHTML;
  } else if (/^<html/i.test(html)) {
    newHtml = doc.documentElement.outerHTML;
  } else {
    newHtml = doc.body.innerHTML;
  }

  textarea.value = newHtml;
  _rawHtmlContainers.add(_editTextsTarget.containerId);

  bootstrap.Modal.getInstance(document.getElementById('modalEditTexts')).hide();

  const previewWrap = document.getElementById('preview-' + _editTextsTarget.containerId);
  if (previewWrap && !previewWrap.classList.contains('d-none')) {
    editorTab('preview', _editTextsTarget.containerId, _editTextsTarget.textareaId);
  }
}

// ─────────────────────────────────────────────
// Editar Links e Botões (CTAs) de um HTML completo (template/IA)
// ─────────────────────────────────────────────
let _editLinksTarget = null;

function _escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

function editLinksModal(containerId, textareaId) {
  const textarea = document.getElementById(textareaId);
  const html = (textarea && textarea.value) || '';
  if (!html.trim()) { alert('Não há conteúdo no e-mail ainda.'); return; }

  const doc = new DOMParser().parseFromString(html, 'text/html');
  const links = Array.from(doc.querySelectorAll('a[href]'));
  if (!links.length) {
    alert('Nenhum link/botão encontrado neste e-mail.');
    return;
  }

  const list = document.getElementById('editLinksList');
  list.innerHTML = links.map((a, i) => {
    const label = (a.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60) || '(sem texto)';
    const href = a.getAttribute('href') || '';
    return `
      <div class="mb-2 p-2 border rounded">
        <label class="form-label small text-muted mb-1">Botão/link: <strong>${_escapeHtml(label)}</strong></label>
        <input type="text" class="form-control form-control-sm edit-link-href" data-idx="${i}"
               value="${_escapeHtml(href)}" placeholder="https://...">
      </div>`;
  }).join('');

  _editLinksTarget = { containerId, textareaId };
  new bootstrap.Modal(document.getElementById('modalEditLinks')).show();
}

function applyEditLinks() {
  if (!_editLinksTarget) return;
  const textarea = document.getElementById(_editLinksTarget.textareaId);
  const html = (textarea && textarea.value) || '';
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const links = Array.from(doc.querySelectorAll('a[href]'));

  document.querySelectorAll('#editLinksList .edit-link-href').forEach(inp => {
    const idx = parseInt(inp.dataset.idx, 10);
    const val = inp.value.trim();
    if (links[idx] && val) links[idx].setAttribute('href', val);
  });

  let newHtml;
  if (/^<!DOCTYPE/i.test(html)) {
    newHtml = '<!DOCTYPE html>\n' + doc.documentElement.outerHTML;
  } else if (/^<html/i.test(html)) {
    newHtml = doc.documentElement.outerHTML;
  } else {
    newHtml = doc.body.innerHTML;
  }

  textarea.value = newHtml;
  _rawHtmlContainers.add(_editLinksTarget.containerId);

  bootstrap.Modal.getInstance(document.getElementById('modalEditLinks')).hide();

  // Atualiza a aba Preview se ela existir, sem trocar a aba atual à força
  const previewWrap = document.getElementById('preview-' + _editLinksTarget.containerId);
  if (previewWrap && !previewWrap.classList.contains('d-none')) {
    editorTab('preview', _editLinksTarget.containerId, _editLinksTarget.textareaId);
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
  stepDiv.querySelector('.btn-ai-email')?.setAttribute(
    'onclick', `openAIModal('${containerId}','${textareaId}','${subjectId}')`
  );
  stepDiv.querySelector('.btn-templates-visuais')?.setAttribute(
    'onclick', `openTemplatesModal('${containerId}','${textareaId}','${subjectId}')`
  );
  stepDiv.querySelector('.btn-edit-links')?.setAttribute(
    'onclick', `editLinksModal('${containerId}','${textareaId}')`
  );
  stepDiv.querySelector('.btn-edit-texts')?.setAttribute(
    'onclick', `editTextsModal('${containerId}','${textareaId}')`
  );

  initEditor({ containerId, textareaId, subjectId, autoSignature: false });
}

// Sincroniza todos os editores antes do submit (garante textareas atualizados)
function syncAllEditors() {
  _quillMap.forEach((quill, containerId) => {
    if (_rawHtmlContainers.has(containerId)) return; // mantém HTML completo (template/IA) intacto
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
