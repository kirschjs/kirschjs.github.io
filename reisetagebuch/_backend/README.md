# Leserkommentare – Backend

Statische GitHub-Pages-Seiten können nichts speichern. Die Kommentare liegen
deshalb in einem **Cloudflare Worker** mit einem **KV-Namespace**. Beides ist im
Free Plan enthalten und für diese Seite bei weitem ausreichend (100 000 Lese-
und 1 000 Schreibzugriffe pro Tag; ein Kommentar = ein Schreibzugriff).

Leser brauchen **kein Konto** und geben **keine E-Mail-Adresse** an – gespeichert
werden nur Name, Text und Zeitpunkt.

## Einmalige Einrichtung (ca. 10 Minuten)

Wrangler muss nicht installiert werden – `npx` holt es bei Bedarf.

```bash
cd ~/Documents/kirschjs.github.io/reisetagebuch/_backend

# 1) einmalig anmelden (öffnet den Browser; kostenloses Cloudflare-Konto genügt)
npx wrangler login

# 2) KV-Namespace anlegen – gibt eine id aus
npx wrangler kv namespace create KOMMENTARE

# 3) diese id in wrangler.toml bei `id = "HIER_DIE_KV_ID_EINTRAGEN"` eintragen

# 4) Moderations-Passwort setzen (frei wählbar, gut aufheben)
npx wrangler secret put ADMIN_TOKEN

# 5) hochladen
npx wrangler deploy
```

`wrangler deploy` gibt am Ende eine URL aus, etwa

```
https://reisetagebuch-kommentare.<dein-name>.workers.dev
```

Für diese Seite ist das seit 30.08.2026:
`https://reisetagebuch-kommentare.kommentarr.workers.dev`
(KV-Namespace `KOMMENTARE`, id `24e3ac07ef964ad78f64753b65f15e9f`).

Diese URL in **`reisetagebuch/assets/comments.js`** ganz oben eintragen:

```js
var API = 'https://reisetagebuch-kommentare.<dein-name>.workers.dev';
```

Committen, pushen – fertig. Bis dahin läuft die Seite im **Vorschau-Modus**:
die bereits übernommenen 172 Kommentare aus WordPress werden angezeigt, ein neu
geschriebener Kommentar bleibt nur im Browser des Schreibenden sichtbar.

## Moderieren

`reisetagebuch/kommentare-admin.html` im Browser öffnen, das oben gesetzte
`ADMIN_TOKEN` eintragen (es bleibt lokal im Browser gespeichert). Dort lassen
sich neue Zuschriften **freigeben**, **löschen** und direkt **beantworten** –
Renates Antworten erscheinen sofort und farblich abgesetzt.

## Datenschutz

* keine Cookies, kein Tracking, keine Drittanbieter-Skripte;
* nur Name + Text + Zeitstempel werden gespeichert, keine E-Mail, keine IP
  (die IP dient ausschließlich einer 60-Sekunden-Sperre gegen Spam und wird
  nicht dauerhaft abgelegt);
* KV liegt verteilt in Cloudflares Edge-Netz; eine EU-Beschränkung lässt sich über
  `wrangler kv namespace create` **nicht** setzen (der Free Plan bietet sie nicht an).
  Gespeichert werden ohnehin nur Name, Text und Zeitstempel – nichts, was über das
  hinausgeht, was ohnehin öffentlich auf der Seite steht.

## Bestandsdaten

`reisetagebuch/assets/comments-seed.json` enthält die 172 Kommentare, die am
30. August 2026 über die öffentliche WordPress-API von
jewishgermanculturecooking.com exportiert wurden. Diese Datei ist statisch und
wird nie überschrieben; alles Neue liegt im Worker. Neu erzeugt wird sie mit
`_build/import_wp_comments.py` (im Projektordner `MamisHP/designs/_build`).
