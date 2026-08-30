/* ═══════════════════════════════════════════════════════════════════════════
   Kommentar-Backend für das Reisetagebuch – ein einzelner Cloudflare Worker
   mit einem KV-Namespace.  Kostenlos im Free Plan (100 000 Reads/Tag,
   1 000 Writes/Tag) – für diese Seite um Größenordnungen zu viel.

   Datenmodell im KV (Binding: KOMMENTARE)
     t:<entry>   JSON-Array der FREIGEGEBENEN Kommentare eines Beitrags.
                 Genau ein Read pro Seitenaufruf.
     p:<id>      ein einzelner, noch nicht freigegebener Kommentar.
     r:<ip-hash> Sperre gegen Schnellfeuer, TTL 60 s.

   Endpunkte
     GET  /comments?entry=eintrag-japan-4      → { items: [...] }
     POST /comments   {entry,name,text,parent} → { ok, id, pending }
     GET  /admin/pending          (Token)      → { items: [...] }
     POST /admin/approve {id}     (Token)      → { ok }
     POST /admin/reply   {entry,text,parent}   → { ok }   Renates Antwort
     POST /admin/delete  {id|entry+cid}(Token) → { ok }

   Das Admin-Token wird als Secret gesetzt (siehe README) und im Header
   X-Admin-Token mitgeschickt.  Es gibt bewusst keine Login-Seite: wer das
   Token hat, darf moderieren.
   ═══════════════════════════════════════════════════════════════════════════ */

/* Der erste Eintrag ist die Rückfallantwort für unbekannte Herkünfte.
   Die localhost-Einträge dienen nur der lokalen Vorschau
   (python3 -m http.server 8777 im reisetagebuch-Ordner).
   CORS schützt einen öffentlichen Schreib-Endpunkt ohnehin nicht – dafür
   sorgen Honigtopf, Längenprüfung, IP-Sperre und die Freigabepflicht. */
const ORIGINS = [
  'https://kirschjs.github.io',
  'https://jewishgermanculturecooking.com',
  'https://www.jewishgermanculturecooking.com',
  'http://127.0.0.1:8777',
  'http://localhost:8777',
];

const MAXNAME = 60;
const MAXTEXT = 4000;
const OWNER   = 'Renate';

/* ── kleine Helfer ───────────────────────────────────────────────────────── */
const cors = (req) => {
  const o = req.headers.get('Origin') || '';
  const allow = ORIGINS.includes(o) ? o : ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allow,
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,X-Admin-Token',
    'Vary': 'Origin',
  };
};
const json = (req, body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...cors(req) },
  });

/* Entry-Kennung = Dateiname der Seite ohne .html – nichts anderes zulassen,
   damit keine fremden KV-Schlüssel beschrieben werden können. */
const validEntry = (s) => typeof s === 'string' && /^[a-z0-9-]{3,60}$/.test(s);

const clean = (s, max) =>
  String(s == null ? '' : s)
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '')  /* Steuerzeichen */
    .replace(/\r\n?/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
    .slice(0, max);

const newId = () =>
  Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);

const thread = async (env, entry) => {
  const raw = await env.KOMMENTARE.get('t:' + entry);
  return raw ? JSON.parse(raw) : [];
};

const authed = (req, env) =>
  !!env.ADMIN_TOKEN && req.headers.get('X-Admin-Token') === env.ADMIN_TOKEN;

/* ── Worker ──────────────────────────────────────────────────────────────── */
export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';

    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors(req) });

    /* ── öffentlich: freigegebene Kommentare eines Beitrags ────────────── */
    if (req.method === 'GET' && path === '/comments') {
      const entry = url.searchParams.get('entry');
      if (!validEntry(entry)) return json(req, { error: 'bad entry' }, 400);
      return json(req, { items: await thread(env, entry) });
    }

    /* ── öffentlich: neuen Kommentar einreichen (kommt in die Warteschlange) ─ */
    if (req.method === 'POST' && path === '/comments') {
      let b;
      try { b = await req.json(); } catch { return json(req, { error: 'bad json' }, 400); }

      if (b.website) return json(req, { ok: true, id: newId(), pending: true }); /* Honigtopf */
      if (!validEntry(b.entry)) return json(req, { error: 'bad entry' }, 400);

      const text = clean(b.text, MAXTEXT);
      if (text.length < 2) return json(req, { error: 'leer' }, 400);
      const name = clean(b.name, MAXNAME) || 'Gast';

      /* höchstens ein Kommentar pro Minute und IP */
      const ip = req.headers.get('CF-Connecting-IP') || '?';
      const rk = 'r:' + ip;
      if (await env.KOMMENTARE.get(rk)) return json(req, { error: 'zu schnell' }, 429);
      await env.KOMMENTARE.put(rk, '1', { expirationTtl: 60 });

      const c = {
        id: newId(), name, text,
        date: new Date().toISOString(),
        parent: typeof b.parent === 'string' && b.parent.length < 40 ? b.parent : null,
        owner: false,
        entry: b.entry,
      };
      await env.KOMMENTARE.put('p:' + c.id, JSON.stringify(c));
      return json(req, { ok: true, id: c.id, pending: true });
    }

    /* ── ab hier nur mit Token ─────────────────────────────────────────── */
    if (path.startsWith('/admin')) {
      if (!authed(req, env)) return json(req, { error: 'kein Zugang' }, 401);

      if (req.method === 'GET' && path === '/admin/pending') {
        const { keys } = await env.KOMMENTARE.list({ prefix: 'p:' });
        const items = await Promise.all(
          keys.map((k) => env.KOMMENTARE.get(k.name).then((v) => (v ? JSON.parse(v) : null)))
        );
        return json(req, { items: items.filter(Boolean).sort((a, b) => (a.date < b.date ? -1 : 1)) });
      }

      let b = {};
      if (req.method === 'POST') { try { b = await req.json(); } catch { /* egal */ } }

      /* freigeben: aus der Warteschlange in den Beitrags-Thread */
      if (req.method === 'POST' && path === '/admin/approve') {
        const raw = await env.KOMMENTARE.get('p:' + b.id);
        if (!raw) return json(req, { error: 'unbekannt' }, 404);
        const c = JSON.parse(raw);
        const entry = c.entry;
        delete c.entry;
        const list = await thread(env, entry);
        if (!list.some((x) => x.id === c.id)) list.push(c);
        list.sort((a, b2) => (a.date < b2.date ? -1 : 1));
        await env.KOMMENTARE.put('t:' + entry, JSON.stringify(list));
        await env.KOMMENTARE.delete('p:' + b.id);
        return json(req, { ok: true });
      }

      /* Renates eigene Antwort – erscheint sofort, als owner markiert */
      if (req.method === 'POST' && path === '/admin/reply') {
        if (!validEntry(b.entry)) return json(req, { error: 'bad entry' }, 400);
        const text = clean(b.text, MAXTEXT);
        if (text.length < 2) return json(req, { error: 'leer' }, 400);
        const list = await thread(env, b.entry);
        list.push({
          id: newId(), name: OWNER, text,
          date: new Date().toISOString(),
          parent: typeof b.parent === 'string' ? b.parent : null,
          owner: true,
        });
        list.sort((a, b2) => (a.date < b2.date ? -1 : 1));
        await env.KOMMENTARE.put('t:' + b.entry, JSON.stringify(list));
        return json(req, { ok: true });
      }

      /* löschen: entweder aus der Warteschlange (id) oder aus einem Thread */
      if (req.method === 'POST' && path === '/admin/delete') {
        if (b.entry && b.cid) {
          if (!validEntry(b.entry)) return json(req, { error: 'bad entry' }, 400);
          const list = (await thread(env, b.entry)).filter((x) => x.id !== b.cid);
          await env.KOMMENTARE.put('t:' + b.entry, JSON.stringify(list));
          return json(req, { ok: true });
        }
        await env.KOMMENTARE.delete('p:' + b.id);
        return json(req, { ok: true });
      }
    }

    return json(req, { error: 'not found' }, 404);
  },
};
