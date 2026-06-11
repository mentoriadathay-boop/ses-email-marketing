// image_editor.js — edição de múltiplas imagens nos templates visuais
// Adiciona, sobre o iframe de Preview de um e-mail HTML completo (template/IA),
// botões "📷 Trocar imagem" em cada <img> e "+ Adicionar imagem aqui" entre as
// seções do template, permitindo upload do computador ou busca no Unsplash.

// ─────────────────────────────────────────────
// Modal genérico de escolha de imagem (Upload / Unsplash)
// ─────────────────────────────────────────────
let _imgPickCallback = null;
let _imgPickUrl = '';

function _abrirImagePicker(callback) {
  _imgPickCallback = callback;
  _imgPickUrl = '';
  document.getElementById('imgPickBtnConfirmar').disabled = true;
  document.getElementById('imgPickUploadPreview').innerHTML = '';
  document.getElementById('imgPickUnsplashResults').innerHTML = '';
  document.getElementById('imgPickUnsplashQuery').value = '';
  const firstTab = document.querySelector('#imgPickTabs .nav-link');
  if (firstTab) imgPickSwitchTab('upload', firstTab);
  new bootstrap.Modal(document.getElementById('modalEscolherImagem')).show();
}

function imgPickSwitchTab(tab, btn) {
  document.getElementById('imgPickTabUpload').classList.toggle('d-none', tab !== 'upload');
  document.getElementById('imgPickTabUnsplash').classList.toggle('d-none', tab !== 'unsplash');
  document.querySelectorAll('#imgPickTabs .nav-link').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

async function imgPickUpload(input) {
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
      _imgPickUrl = data.url;
      document.getElementById('imgPickUploadPreview').innerHTML =
        `<img src="${data.url}" style="max-height:120px;border-radius:8px;margin-top:8px;border:1px solid #ddd;">`;
      document.getElementById('imgPickBtnConfirmar').disabled = false;
    } else {
      alert('Erro no upload: ' + (data.erro || 'desconhecido'));
    }
  } catch (e) {
    alert('Erro ao fazer upload da imagem.');
  }
}

async function imgPickBuscarUnsplash() {
  const q = document.getElementById('imgPickUnsplashQuery').value.trim();
  if (!q) return;
  const div = document.getElementById('imgPickUnsplashResults');
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
             onclick="imgPickSelecionarUnsplash('${img.full}',this)">
      </div>
    `).join('');
  } catch (e) {
    div.innerHTML = '<div class="col-12 text-danger small">Erro de conexão com o Unsplash.</div>';
  }
}

function imgPickSelecionarUnsplash(url, imgEl) {
  document.querySelectorAll('#imgPickUnsplashResults img').forEach(i => i.style.borderColor = 'transparent');
  imgEl.style.borderColor = '#4361ee';
  _imgPickUrl = url;
  document.getElementById('imgPickBtnConfirmar').disabled = false;
}

function imgPickConfirmar() {
  if (!_imgPickUrl || !_imgPickCallback) return;
  const cb = _imgPickCallback;
  const url = _imgPickUrl;
  _imgPickCallback = null;
  bootstrap.Modal.getInstance(document.getElementById('modalEscolherImagem'))?.hide();
  cb(url);
}

// ─────────────────────────────────────────────
// Overlay de edição sobre o iframe de Preview
// ─────────────────────────────────────────────
function setupImageEditingOverlay(containerId, textareaId) {
  const previewWrap = document.getElementById('preview-' + containerId);
  if (!previewWrap) return;
  const iframe = previewWrap.querySelector('iframe');
  if (!iframe || !iframe.contentDocument) return;
  const doc = iframe.contentDocument;
  const body = doc.body;
  if (!body) return;

  // remove overlays de uma renderização anterior
  doc.querySelectorAll('._img-edit-overlay').forEach(el => el.remove());

  if (!doc.getElementById('_img-edit-style')) {
    const style = doc.createElement('style');
    style.id = '_img-edit-style';
    style.textContent = `
      ._img-edit-overlay { position:absolute; z-index:9999; font-family:Arial,sans-serif; }
      ._img-btn-trocar { position:absolute; top:6px; right:6px; background:rgba(0,0,0,.65); color:#fff; border:none;
        padding:4px 10px; border-radius:6px; font-size:12px; cursor:pointer; pointer-events:auto; }
      ._img-btn-trocar:hover { background:#4361ee; }
      ._img-add-bar { left:0; right:0; height:0; display:flex; align-items:center; justify-content:center; pointer-events:none; }
      ._img-add-bar button { background:#eef0ff; color:#4361ee; border:1px dashed #4361ee; border-radius:6px;
        font-size:12px; padding:3px 10px; cursor:pointer; transform:translateY(-50%); pointer-events:auto; }
      ._img-add-bar button:hover { background:#4361ee; color:#fff; }
    `;
    doc.head.appendChild(style);
  }
  if (getComputedStyle(body).position === 'static') body.style.position = 'relative';

  const bodyRect = body.getBoundingClientRect();

  // Botão "Trocar imagem" sobre cada <img>
  const imgs = Array.from(body.querySelectorAll('img'));
  imgs.forEach((img, idx) => {
    const rect = img.getBoundingClientRect();
    if (rect.width < 20 || rect.height < 20) return; // ignora pixels de rastreamento

    const overlay = doc.createElement('div');
    overlay.className = '_img-edit-overlay';
    overlay.style.left = (rect.left - bodyRect.left) + 'px';
    overlay.style.top = (rect.top - bodyRect.top) + 'px';
    overlay.style.width = rect.width + 'px';
    overlay.style.height = rect.height + 'px';
    overlay.style.pointerEvents = 'none';

    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.className = '_img-btn-trocar';
    btn.textContent = '📷 Trocar imagem';
    btn.addEventListener('click', () => {
      _abrirImagePicker((url) => {
        _trocarImagemEmHtml(textareaId, idx, url);
        editorTab('preview', containerId, textareaId);
      });
    });
    overlay.appendChild(btn);
    body.appendChild(overlay);
  });

  // Barras "+ Adicionar imagem aqui" entre as seções (linhas) da tabela principal
  const mainTable = _findMainTable(doc);
  if (mainTable) {
    const tbody = Array.from(mainTable.children).find(c => c.tagName === 'TBODY') || mainTable;
    const rows = Array.from(tbody.children).filter(c => c.tagName === 'TR');

    if (rows.length) {
      const positions = [];
      const firstRect = rows[0].getBoundingClientRect();
      positions.push({ y: firstRect.top - bodyRect.top, rowIdx: 0 });
      rows.forEach((r, i) => {
        const rRect = r.getBoundingClientRect();
        positions.push({ y: rRect.bottom - bodyRect.top, rowIdx: i + 1 });
      });

      positions.forEach(pos => {
        const bar = doc.createElement('div');
        bar.className = '_img-edit-overlay _img-add-bar';
        bar.style.top = pos.y + 'px';

        const btn = doc.createElement('button');
        btn.type = 'button';
        btn.textContent = '+ Adicionar imagem aqui';
        btn.addEventListener('click', () => {
          _abrirImagePicker((url) => {
            _inserirBlocoImagemEmHtml(textareaId, pos.rowIdx, url);
            editorTab('preview', containerId, textareaId);
          });
        });
        bar.appendChild(btn);
        body.appendChild(bar);
      });
    }
  }
}

// Encontra a tabela "principal" do template: a que tem mais linhas (<tr>) diretas,
// presumindo que ela representa as seções do e-mail (cabeçalho, corpo, rodapé...).
function _findMainTable(doc) {
  const tables = Array.from(doc.querySelectorAll('table'));
  let best = null, bestCount = 0;
  tables.forEach(t => {
    const tbody = Array.from(t.children).find(c => c.tagName === 'TBODY');
    const rows = Array.from((tbody || t).children).filter(c => c.tagName === 'TR');
    if (rows.length > bestCount) { bestCount = rows.length; best = t; }
  });
  return bestCount > 1 ? best : null;
}

function _serializeDoc(doc, originalHtml) {
  if (/^<!DOCTYPE/i.test(originalHtml)) {
    return '<!DOCTYPE html>\n' + doc.documentElement.outerHTML;
  } else if (/^<html/i.test(originalHtml)) {
    return doc.documentElement.outerHTML;
  }
  return doc.body.innerHTML;
}

// Troca o src da imagem de índice imgIdx (na ordem de document order) pelo novo URL.
function _trocarImagemEmHtml(textareaId, imgIdx, novaUrl) {
  const textarea = document.getElementById(textareaId);
  const html = textarea.value || '';
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const imgs = doc.querySelectorAll('img');
  if (imgs[imgIdx]) imgs[imgIdx].setAttribute('src', novaUrl);
  textarea.value = _serializeDoc(doc, html);
}

// Insere um novo bloco (linha da tabela principal) com uma imagem na posição rowIdx.
function _inserirBlocoImagemEmHtml(textareaId, rowIdx, novaUrl) {
  const textarea = document.getElementById(textareaId);
  const html = textarea.value || '';
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const mainTable = _findMainTable(doc);
  if (!mainTable) return;

  const tbody = Array.from(mainTable.children).find(c => c.tagName === 'TBODY') || mainTable;
  const rows = Array.from(tbody.children).filter(c => c.tagName === 'TR');

  // descobre o número de colunas da linha de referência para usar colspan correto
  const refRow = rows[Math.min(rowIdx, rows.length - 1)];
  let cols = 1;
  if (refRow) {
    cols = Array.from(refRow.children).reduce(
      (sum, td) => sum + (parseInt(td.getAttribute('colspan') || '1', 10)), 0
    ) || 1;
  }

  const tr = doc.createElement('tr');
  const td = doc.createElement('td');
  if (cols > 1) td.setAttribute('colspan', String(cols));
  td.setAttribute('align', 'center');
  td.setAttribute('style', 'padding:16px 32px;');
  const img = doc.createElement('img');
  img.setAttribute('src', novaUrl);
  img.setAttribute('alt', '');
  img.setAttribute('style', 'max-width:100%;border-radius:8px;display:block;margin:0 auto;');
  td.appendChild(img);
  tr.appendChild(td);

  if (rowIdx >= rows.length || !rows.length) {
    tbody.appendChild(tr);
  } else {
    tbody.insertBefore(tr, rows[rowIdx]);
  }

  textarea.value = _serializeDoc(doc, html);
}
