/* ═══════════════════════════════════════════════════════════════════════════
   Leserkommentare für das Reisetagebuch.

   Hängt unter die »Kultureller Kommentar«-Notizen der linken Spalte:
     · »Mein Kommentar«     – hervorgehobenes Formular (Name + Text)
     · »Stimmen der Leser«  – bestehende Kommentare, Renates Antworten
                              farblich abgesetzt und eingerückt

   Zwei Quellen, die zusammengeführt werden:
     1. assets/comments-seed.json – die 172 Kommentare, die aus der
        WordPress-Seite übernommen wurden (Stand August 2026, unveränderlich).
     2. der Cloudflare-Worker unter API – alles, was seither geschrieben wurde.

   Neue Kommentare gehen beim Worker in die Warteschlange und erscheinen erst,
   wenn Renate sie in kommentare-admin.html freigibt; bis dahin sieht nur der
   Schreibende selbst seinen Beitrag (localStorage), als »wartet auf Freigabe«
   gekennzeichnet. Wird API geleert, läuft alles im reinen Vorschau-Modus
   weiter – dann bleibt jeder neue Kommentar lokal. Einrichtung des Workers:
   _backend/README.md.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* Adresse des Cloudflare-Workers; leeren, um in den Vorschau-Modus
     zurückzufallen (siehe _backend/README.md).                        ── */
  var API = 'https://reisetagebuch-kommentare.kommentarr.workers.dev';

  var MAXNAME = 60, MAXTEXT = 4000;

  /* Beschriftung der beiden Überschriften je Reise (native Schrift wie bei
     den Notizen darüber; wo es keine gibt, bleibt die Zeile weg). */
  var LABEL = {
    japan:   { mine: 'ひとこと',  voices: 'お便り' },
    israel:  { mine: 'תגובה',    voices: 'תגובות' },
    ecuador: { mine: 'mi comentario', voices: 'comentarios' }
  };

  var MONTHS = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli',
                'August', 'September', 'Oktober', 'November', 'Dezember'];

  var col = document.querySelector('.talmud .col-left');
  if (!col) return;

  var entry = (location.pathname.split('/').pop() || '').replace(/\.html?$/i, '');
  if (!entry) return;
  var land  = document.body.getAttribute('data-land') || '';
  var lab   = LABEL[land] || {};
  var LSKEY = 'rtb-kommentar:' + entry;

  /* ── Hilfsfunktionen ──────────────────────────────────────────────────── */
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function german(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return '';
    return d.getDate() + '. ' + MONTHS[d.getMonth()] + ' ' + d.getFullYear();
  }
  /* Freitext → Absätze; alles escaped, nichts vom Leser wird als HTML gedeutet */
  function paras(text) {
    return String(text).split(/\n\s*\n/).map(function (p) {
      return '<p>' + esc(p.trim()).replace(/\n/g, '<br>') + '</p>';
    }).join('');
  }
  function store(list) {
    try { localStorage.setItem(LSKEY, JSON.stringify(list)); } catch (e) { /* privates Fenster */ }
  }
  function loadLocal() {
    try { return JSON.parse(localStorage.getItem(LSKEY) || '[]'); } catch (e) { return []; }
  }

  /* ── Gerüst aufbauen ──────────────────────────────────────────────────── */
  var sec = el('section', 'comments');
  sec.id = 'kommentare';

  var t1 = el('div', 'side-title mine', 'Mein Kommentar' +
            (lab.mine ? '<small class="native">' + lab.mine + '</small>' : ''));
  sec.appendChild(t1);

  var form = el('form', 'cbox');
  form.setAttribute('novalidate', '');
  form.innerHTML =
    '<div class="replyto" hidden></div>' +
    '<label for="k-name">Ihr Name</label>' +
    '<input id="k-name" name="name" type="text" maxlength="' + MAXNAME + '" autocomplete="name">' +
    '<label for="k-text">Ihr Kommentar</label>' +
    '<textarea id="k-text" name="text" maxlength="' + MAXTEXT + '"></textarea>' +
    '<div class="hp"><label>Bitte frei lassen<input name="website" type="text" tabindex="-1" autocomplete="off"></label></div>' +
    '<button type="submit">abschicken</button>' +
    '<p class="hint">Ihr Kommentar erscheint, sobald Renate ihn freigegeben hat. ' +
    'Es werden nur Name und Text gespeichert – keine E-Mail-Adresse.</p>' +
    '<div class="msg" hidden></div>';
  sec.appendChild(form);

  var t2 = el('div', 'side-title voices', 'Stimmen der Leser' +
            (lab.voices ? '<small class="native">' + lab.voices + '</small>' : '') +
            '<span class="cnt"></span>');
  sec.appendChild(t2);

  var list = el('ul', 'clist');
  sec.appendChild(list);
  col.appendChild(sec);

  var msgBox   = form.querySelector('.msg');
  var replyBox = form.querySelector('.replyto');
  var nameIn   = form.querySelector('[name=name]');
  var textIn   = form.querySelector('[name=text]');
  var button   = form.querySelector('button');
  var cntSpan  = t2.querySelector('.cnt');
  var replyTo  = null;

  function say(text, bad) {
    msgBox.textContent = text;
    msgBox.className = 'msg' + (bad ? ' bad' : '');
    msgBox.hidden = false;
  }

  /* ── Anzeige ──────────────────────────────────────────────────────────── */
  function card(c) {
    var li = el('li', 'cmt' + (c.owner ? ' owner' : '') +
                      (c.parent ? ' reply' : '') + (c.pending ? ' pending' : ''));
    li.appendChild(el('div', 'who',
      '<span>' + esc(c.name) + '</span><span class="when">' + german(c.date) + '</span>'));
    li.appendChild(el('div', 'body', c.html != null ? c.html : paras(c.text || '')));
    if (!c.parent && !c.pending) {
      var b = el('button', 're', '↩ antworten');
      b.type = 'button';
      b.onclick = function () { setReply(c); };
      li.appendChild(b);
    }
    return li;
  }

  function setReply(c) {
    replyTo = c;
    replyBox.innerHTML = 'Antwort an <b>' + esc(c.name) + '</b> · <a>abbrechen</a>';
    replyBox.hidden = false;
    replyBox.querySelector('a').onclick = function () {
      replyTo = null; replyBox.hidden = true;
    };
    textIn.focus();
    t1.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  /* Kommentare chronologisch, jede Antwort direkt unter ihrem Bezug. */
  function render(items) {
    var top = items.filter(function (c) { return !c.parent; });
    var kids = {};
    items.forEach(function (c) {
      if (c.parent) (kids[c.parent] = kids[c.parent] || []).push(c);
    });
    list.innerHTML = '';
    top.forEach(function (c) {
      list.appendChild(card(c));
      (kids[c.id] || []).forEach(function (k) { list.appendChild(card(k)); });
    });
    /* Antworten, deren Bezugskommentar fehlt (z. B. gelöscht), nicht verlieren */
    var seen = {};
    top.forEach(function (c) { seen[c.id] = 1; });
    items.forEach(function (c) {
      if (c.parent && !seen[c.parent]) list.appendChild(card(c));
    });
    cntSpan.textContent = items.length === 0 ? 'noch keine' :
                          items.length === 1 ? '1 Zuschrift' : items.length + ' Zuschriften';
  }

  var merged = [];
  function refresh() {
    var pending = loadLocal();
    render(merged.concat(pending).sort(function (a, b) {
      return (a.date < b.date) ? -1 : (a.date > b.date) ? 1 : 0;
    }));
  }

  /* ── Laden ────────────────────────────────────────────────────────────── */
  function get(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    });
  }

  var sources = [
    get('assets/comments-seed.json').then(function (all) { return all[entry] || []; })
                                    .catch(function () { return []; })
  ];
  if (API) {
    sources.push(
      get(API + '/comments?entry=' + encodeURIComponent(entry))
        .then(function (d) { return d.items || []; })
        .catch(function () { return []; })
    );
  }
  Promise.all(sources).then(function (parts) {
    merged = [].concat.apply([], parts);
    /* was inzwischen freigegeben wurde, muss lokal nicht mehr »wartend« stehen */
    var live = {};
    merged.forEach(function (c) { live[c.id] = 1; });
    var rest = loadLocal().filter(function (c) { return !live[c.id]; });
    store(rest);
    refresh();
  });

  /* ── Absenden ─────────────────────────────────────────────────────────── */
  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (form.website.value) return;                    /* Honigtopf: nur Bots füllen das */

    var name = nameIn.value.trim().slice(0, MAXNAME);
    var text = textIn.value.trim().slice(0, MAXTEXT);
    if (text.length < 2) { say('Bitte schreiben Sie noch ein paar Worte.', true); return; }
    if (!name) name = 'Gast';

    var local = {
      id: 'local-' + Date.now(),
      name: name, text: text, date: new Date().toISOString(),
      parent: replyTo ? replyTo.id : null, owner: false, pending: true
    };

    function done(note) {
      store(loadLocal().concat([local]));
      refresh();
      nameIn.value = ''; textIn.value = '';
      replyTo = null; replyBox.hidden = true;
      say(note);
      button.disabled = false;
    }

    button.disabled = true;
    if (!API) {                                        /* Vorschau-Modus */
      done('Danke! In dieser Vorschau bleibt Ihr Kommentar vorerst nur auf ' +
           'diesem Gerät sichtbar.');
      return;
    }
    fetch(API + '/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry: entry, name: name, text: text,
                             parent: local.parent })
    }).then(function (r) { return r.json().then(function (d) {
        if (!r.ok || !d.ok) throw new Error(d.error || r.status);
        if (d.id) local.id = d.id;
        done('Vielen Dank! Ihr Kommentar wartet nun auf die Freigabe durch Renate.');
      }); })
      .catch(function () {
        button.disabled = false;
        say('Das Abschicken hat leider nicht geklappt. Bitte später noch einmal ' +
            'versuchen – Ihr Text bleibt so lange stehen.', true);
      });
  });
})();
