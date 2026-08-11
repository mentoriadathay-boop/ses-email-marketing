// editor.js — Editor visual Quill para ConvertMail

const _quillMap = new Map();   // containerId -> quill instance
window._quillMap = _quillMap;  // exposto para consumidores externos (nova_campanha.html)
let _tplTarget = null;         // { quill, subjectId } — editor alvo do modal de templates
let _tplCache = null;          // cache dos templates da API
const _rawHtmlContainers = new Set(); // containers cujo textarea contém um HTML completo (template/IA) — não sincronizar a partir do Quill

// ─────────────────────────────────────────────
// Registro de formatos extras do Quill (fonte, tamanho, espaçamento entre linhas, undo/redo)
// ─────────────────────────────────────────────
const _FONT_WHITELIST = ['arial', 'georgia', 'verdana', 'trebuchet', 'times-new-roman', 'courier', 'roboto', 'open-sans', 'montserrat'];
const _FONT_LABELS = {
  arial: 'Arial', georgia: 'Georgia', verdana: 'Verdana', trebuchet: 'Trebuchet MS',
  'times-new-roman': 'Times New Roman', courier: 'Courier New',
  roboto: 'Roboto', 'open-sans': 'Open Sans', montserrat: 'Montserrat'
};
const _FONT_FAMILIES = {
  arial: 'Arial, sans-serif', georgia: 'Georgia, serif', verdana: 'Verdana, sans-serif',
  trebuchet: "'Trebuchet MS', sans-serif", 'times-new-roman': "'Times New Roman', serif",
  courier: "'Courier New', monospace", roboto: "'Roboto', sans-serif",
  'open-sans': "'Open Sans', sans-serif", montserrat: "'Montserrat', sans-serif"
};
const _SIZE_WHITELIST = ['8px', '10px', '12px', '14px', '16px', '18px', '20px', '24px', '28px', '32px', '36px', '40px', '48px', '56px', '64px', '72px'];
const _LINEHEIGHT_WHITELIST = ['1', '1.5', '2'];

// CSS injetado no preview de conteúdo "fragmento" (não é um documento HTML completo)
// para que ele renderize com a mesma fonte, tamanho e espaçamento do editor Quill.
const _PREVIEW_FRAGMENT_CSS = `<style>
  body { font-family: Arial, Helvetica, sans-serif; font-size: 16px; line-height: 1.6; color: #333; margin: 0; padding: 16px; }
  p, ul, ol, blockquote { margin: 0 0 1em 0; padding: 0; }
  li { margin-bottom: .25em; }
  img { max-width: 100%; }
</style>`;

(function _registerQuillFormats() {
  if (typeof Quill === 'undefined' || window._quillFormatsRegistered) return;
  window._quillFormatsRegistered = true;

  const FontClass = Quill.import('formats/font');
  FontClass.whitelist = _FONT_WHITELIST;
  Quill.register(FontClass, true);

  const SizeStyle = Quill.import('attributors/style/size');
  SizeStyle.whitelist = _SIZE_WHITELIST;
  Quill.register(SizeStyle, true);

  const Parchment = Quill.import('parchment');
  const LineHeightStyle = new Parchment.Attributor.Style('lineheight', 'line-height', {
    scope: Parchment.Scope.BLOCK,
    whitelist: _LINEHEIGHT_WHITELIST
  });
  Quill.register(LineHeightStyle, true);

  const icons = Quill.import('ui/icons');
  icons['undo'] = '<i class="bi bi-arrow-counterclockwise"></i>';
  icons['redo'] = '<i class="bi bi-arrow-clockwise"></i>';

  // CSS dos pickers de fonte/tamanho/espaçamento
  let css = `
.ql-snow .ql-picker.ql-size .ql-picker-item[data-value]::before,
.ql-snow .ql-picker.ql-size .ql-picker-label[data-value]::before { content: attr(data-value); }
.ql-snow .ql-picker.ql-lineheight .ql-picker-item::before,
.ql-snow .ql-picker.ql-lineheight .ql-picker-label::before { content: 'Espaçamento'; }
.ql-snow .ql-picker.ql-lineheight .ql-picker-item[data-value]::before,
.ql-snow .ql-picker.ql-lineheight .ql-picker-label[data-value]::before { content: attr(data-value); }
.ql-snow .ql-picker.ql-lineheight { width: 90px; }
.ql-snow .ql-picker.ql-font { width: 150px; }
.ql-snow .ql-picker.ql-size { width: 70px; }
`;
  _FONT_WHITELIST.forEach(f => {
    css += `.ql-font-${f} { font-family: ${_FONT_FAMILIES[f]}; }
.ql-snow .ql-picker.ql-font .ql-picker-item[data-value="${f}"]::before,
.ql-snow .ql-picker.ql-font .ql-picker-label[data-value="${f}"]::before { content: '${_FONT_LABELS[f]}'; font-family: ${_FONT_FAMILIES[f]}; }
`;
  });
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
})();

// ─────────────────────────────────────────────
// Inicializar editor (Visual + HTML em abas)
// ─────────────────────────────────────────────
function initEditor(cfg) {
  // cfg: { containerId, textareaId, subjectId, autoSignature }
  const textarea = document.getElementById(cfg.textareaId);
  const visualDiv = document.getElementById(cfg.containerId);

  const toolbarCfg = [
    [{ font: _FONT_WHITELIST }, { size: _SIZE_WHITELIST }],
    ['bold', 'italic', 'underline', 'strike'],
    [{ color: [] }, { background: [] }],
    [{ align: [] }],
    [{ list: 'ordered' }, { list: 'bullet' }],
    [{ indent: '-1' }, { indent: '+1' }],
    [{ lineheight: _LINEHEIGHT_WHITELIST }],
    ['link', 'image'],
    ['undo', 'redo'],
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
          image: function () { _uploadImage(quill); },
          undo: function () { quill.history.undo(); },
          redo: function () { quill.history.redo(); }
        }
      },
      history: { delay: 1000, maxStack: 100, userOnly: true }
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

function insertImageToHtmlByEl(btn) {
  var ta = btn.closest('.html-wrap').querySelector('textarea');
  if (!ta) return;
  _abrirImagePicker(function(url) {
    if (!url) return;
    var imgTag = '<img src="' + url + '" alt="imagem" style="max-width:100%;height:auto;display:block;margin:12px auto;border-radius:8px;">';
    var pos = ta.selectionStart || ta.value.length;
    ta.value = ta.value.slice(0, pos) + imgTag + ta.value.slice(pos);
    ta.focus();
  });
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
        const isFullDoc = /^\s*(<!DOCTYPE|<html)/i.test(conteudo);
        let html;
        if (!conteudo) {
          html = base + _PREVIEW_FRAGMENT_CSS + vazio;
        } else if (isFullDoc || conteudo.includes('<base')) {
          html = isFullDoc && !conteudo.includes('<base') ? base + conteudo : conteudo;
        } else {
          html = base + _PREVIEW_FRAGMENT_CSS + conteudo;
        }
        iframe.removeAttribute('srcdoc');
        iframe.contentDocument.open();
        iframe.contentDocument.write(html);
        iframe.contentDocument.close();
        setTimeout(() => {
          try {
            const h = iframe.contentDocument.body?.scrollHeight || 0;
            if (h > 0) iframe.style.height = (h + 24) + 'px';
          } catch (e) {}
          if (_rawHtmlContainers.has(containerId) && typeof setupImageEditingOverlay === 'function') {
            setupImageEditingOverlay(containerId, textareaId);
          }
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
        if (typeof setupImageEditingOverlay === 'function') {
          setupImageEditingOverlay(containerId, textareaId);
        }
      }, 150);
    }
  }
}

// ─────────────────────────────────────────────
// Toast simples (usado em vários lugares)
// ─────────────────────────────────────────────
function showToast(msg, type) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const div = document.createElement('div');
  div.className = `alert alert-${type || 'info'} alert-dismissible shadow`;
  div.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  container.appendChild(div);
  setTimeout(() => div.remove(), 6000);
}

// ─────────────────────────────────────────────
// Lê o conteúdo atual de um editor, seja ele um HTML completo
// (raw mode) ou um conteúdo editado visualmente no Quill
// ─────────────────────────────────────────────
function getEditorContent(containerId, textareaId) {
  const textarea = document.getElementById(textareaId);
  if (_rawHtmlContainers.has(containerId)) {
    return (textarea && textarea.value) || '';
  }
  const quill = _quillMap.get(containerId);
  if (quill) {
    const h = quill.root.innerHTML;
    return h === '<p><br></p>' ? '' : h;
  }
  return (textarea && textarea.value) || '';
}

// ─────────────────────────────────────────────
// Melhorar texto do e-mail com IA (sem abrir modal extra)
// ─────────────────────────────────────────────
async function melhorarTextoIA(containerId, textareaId, btnEl) {
  const html = getEditorContent(containerId, textareaId);
  if (!html.trim()) {
    alert('Escreva (ou gere) o conteúdo do e-mail antes de melhorar com IA.');
    return;
  }
  const original = btnEl ? btnEl.innerHTML : null;
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Melhorando...';
  }
  try {
    const res = await fetch('/ia/melhorar-texto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html })
    });
    const texto = await res.text();
    let data;
    try { data = JSON.parse(texto); } catch (pe) {
      console.error('Resposta nao-JSON de melhorar-texto:', res.status, texto);
      const titleMatch = texto.match(/<title>(.*?)<\/title>/i);
      let msg = 'Erro do servidor (status ' + res.status + ').';
      if (titleMatch) msg += '\n\nTítulo: ' + titleMatch[1];
      const bodySnip = (texto || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().substring(0, 300);
      if (bodySnip) msg += '\n\nDetalhe: ' + bodySnip;
      alert(msg);
      return;
    }
    if (data.erro) { alert('Erro ao melhorar texto: ' + data.erro); return; }
    showHtmlInEditor(containerId, textareaId, data.html);
    showToast('Texto melhorado com IA!', 'success');
  } catch (e) {
    alert('Erro de conexão ao melhorar texto: ' + (e.message || e));
  } finally {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.innerHTML = original;
    }
  }
}

// ─────────────────────────────────────────────
// Editar Textos de um HTML completo (template/IA)
// ─────────────────────────────────────────────
let _editTextsTarget = null;

const _INLINE_TAGS = new Set([
  'SPAN','STRONG','EM','B','I','U','A','BR','SUB','SUP','SMALL','MARK','CODE','S','ABBR','CITE','TIME','FONT'
]);

const _TAG_LABELS = {
  'P':'Parágrafo', 'H1':'Título', 'H2':'Subtítulo', 'H3':'Subtítulo',
  'H4':'Subtítulo', 'H5':'Subtítulo', 'H6':'Subtítulo',
  'LI':'Item da lista', 'A':'Link / Botão', 'DIV':'Bloco de info'
};

function _getEditableTextEls(doc) {
  const els = [];
  const seen = new Set();
  doc.body.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, a[href]').forEach(el => {
    if (seen.has(el)) return;
    const text = (el.textContent || '').trim();
    if (text.length < 2) return;
    const hasBlockChild = Array.from(el.querySelectorAll('*')).some(c => !_INLINE_TAGS.has(c.tagName));
    if (hasBlockChild) return;
    if (el.tagName === 'A') {
      let p = el.parentElement;
      while (p && p !== doc.body) { if (seen.has(p)) return; p = p.parentElement; }
    }
    els.push(el);
    seen.add(el);
    el.querySelectorAll('*').forEach(c => seen.add(c));
  });
  return els;
}

function _getBlockText(el) {
  let text = (el.innerText || el.textContent || '').trim();
  if (el.tagName === 'LI') text = text.replace(/^[✓✔☑✅]\s*/, '');
  return text;
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
    const label = _TAG_LABELS[el.tagName] || el.tagName.toLowerCase();
    const text = _getBlockText(el);
    const rows = text.length > 200 ? 5 : (text.length > 80 ? 3 : (text.length > 30 ? 2 : 1));
    return `
      <div class="mb-3 p-2 border rounded">
        <label class="form-label small fw-semibold text-primary mb-1">${label}</label>
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
    if (!els[idx]) return;
    const el = els[idx];
    const newText = ta.value;

    if (el.tagName === 'LI') {
      const decorSpan = el.querySelector('span');
      if (decorSpan && decorSpan.textContent.trim().length <= 2) {
        const spanHtml = decorSpan.outerHTML;
        el.innerHTML = spanHtml + _escapeHtml(newText);
      } else {
        el.textContent = newText;
      }
    } else if (el.querySelector('br')) {
      el.innerHTML = _escapeHtml(newText).replace(/\n/g, '<br>');
    } else {
      el.textContent = newText;
    }
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
  stepDiv.querySelector('.btn-melhorar-ia')?.setAttribute(
    'onclick', `melhorarTextoIA('${containerId}','${textareaId}', this)`
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
