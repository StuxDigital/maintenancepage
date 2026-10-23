// Checks assets/js/changelog.js renders "## vYY.MM.DD" and "## vYY.MM.DD-N" headings and
// orders sections Added, Changed, Fixed, Removed, Security, Deprecated. Run: node tests/changelog.js
var fs = require('fs'), vm = require('vm'), path = require('path');
var md = '# Changelog\n\n## v26.10.23-1\n\n### Deprecated\n\n- d\n\n### Fixed\n\n- f\n\n### Added\n\n- a\n\n### Security\n\n- s\n\n## v26.10.23\n\n### Changed\n\n- c\n';
var target = { innerHTML: '', getAttribute: function () { return ''; } };
var ctx = {
    document: { getElementById: function () { return target; } },
    fetch: function () { return Promise.resolve({ ok: true, text: function () { return Promise.resolve(md); } }); }
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'assets', 'js', 'changelog.js'), 'utf8'), ctx);
setTimeout(function () {
    var h = target.innerHTML, fail = 0;
    function ok(c, m) { if (!c) { console.error('FAIL: ' + m); fail = 1; } }
    ok(h.indexOf('v26.10.23-1') > -1 && h.indexOf('v26.10.23<') > -1, 'date version headings render');
    var order = ['cl-label-added', 'cl-label-fixed', 'cl-label-security', 'cl-label-deprecated'].map(function (c) { return h.indexOf(c); });
    ok(order.every(function (v, i) { return v > -1 && (i === 0 || v > order[i - 1]); }), 'sections in fixed order');
    if (fail) process.exit(1);
    console.log('changelog renderer OK');
}, 50);
