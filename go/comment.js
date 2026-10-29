// Copy-and-open page for comments on existing GitHub issues (GitHub cannot pre-fill those).
// Text comes from go/comments.json, keyed by the folder name, or from ?t= (text) and ?u= (issue URL).
(function () {
  var q = new URLSearchParams(location.search);
  var key = q.get('id') || location.pathname.replace(/\/(index\.html)?$/, '').split('/').pop();
  var box = document.getElementById('text'), btn = document.getElementById('go'),
      label = document.getElementById('label'), hint = document.getElementById('hint');
  var target = '';

  function show(entry) {
    if (!entry || !entry.text || !/^https:\/\/github\.com\//.test(entry.url || '')) {
      label.textContent = 'No comment text found for this link.';
      btn.disabled = true;
      return;
    }
    label.textContent = entry.label || 'Comment';
    box.value = entry.text;
    target = entry.url;
    btn.disabled = false;
  }

  function fallback() {
    box.focus(); box.select();
    try { document.execCommand('copy'); } catch (e) {}
  }

  btn.addEventListener('click', function () {
    var win = window.open(target, '_blank');
    if (win) win.opener = null;
    var done = function () { hint.textContent = 'Copied. In the comment box on GitHub, paste with Ctrl+V and press Comment.'; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(box.value).then(done, function () { fallback(); done(); });
    } else { fallback(); done(); }
    if (!win) location.href = target;
  });

  if (q.get('t')) show({ text: q.get('t'), url: q.get('u'), label: q.get('l') });
  else fetch('../comments.json', { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (all) { show(all[key]); })
    .catch(function () { show(null); });
})();
