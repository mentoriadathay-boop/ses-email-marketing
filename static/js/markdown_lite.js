// Conversor leve de markdown -> HTML para as respostas da IA nos chats
// (assistente in-app, widget flutuante, chat da landing). Sempre escapa HTML
// antes de aplicar qualquer formatação, então é seguro usar com innerHTML
// mesmo que o texto da IA contenha algo parecido com uma tag.
function mdToHtml(text) {
  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function inline(s) {
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
    return s;
  }
  var parts = String(text == null ? '' : text).split('```');
  var html = '';
  for (var i = 0; i < parts.length; i++) {
    if (i % 2 === 1) {
      html += '<pre class="md-code">' + escapeHtml(parts[i].trim()) + '</pre>';
      continue;
    }
    var lines = escapeHtml(parts[i]).split('\n');
    var inList = false;
    for (var j = 0; j < lines.length; j++) {
      var line = lines[j];
      var m = line.match(/^[-•]\s+(.*)/);
      if (m) {
        if (!inList) { html += '<ul class="md-list">'; inList = true; }
        html += '<li>' + inline(m[1]) + '</li>';
        continue;
      }
      if (inList) { html += '</ul>'; inList = false; }
      if (line.trim() === '') { html += '<br>'; continue; }
      html += inline(line) + '<br>';
    }
    if (inList) html += '</ul>';
  }
  return html;
}
