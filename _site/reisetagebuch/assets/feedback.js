/* Floating "Rückmeldung / Vorschlag" button for the work-in-progress
   Reisetagebuch preview. Lets any reader (e.g. Renate on her iPad) send a
   suggestion by e-mail, pre-addressed with the current page title and URL.
   Shared by every preview page via <script src="assets/feedback.js"></script>. */
(function () {
  if (document.getElementById('fb-btn')) return;
  var a = document.createElement('a');
  a.id = 'fb-btn';
  a.textContent = '✎ Rückmeldung';
  a.style.cssText = [
    'position:fixed', 'right:14px', 'bottom:14px', 'z-index:99999',
    'background:#7A3A1C', 'color:#fff', 'font-family:Georgia,\'Crimson Text\',serif',
    'font-size:15px', 'text-decoration:none', 'padding:10px 17px',
    'border-radius:24px', 'box-shadow:0 3px 12px rgba(0,0,0,.28)'
  ].join(';');
  a.onmouseover = function () { a.style.background = '#9A4520'; };
  a.onmouseout = function () { a.style.background = '#7A3A1C'; };
  var subject = 'Reisetagebuch – Vorschlag: ' + document.title;
  var body = 'Liebe Grüße!\n\nMein Vorschlag / meine Anmerkung zu dieser Seite:\n\n\n\n'
           + '(Seite: ' + location.href + ')';
  a.href = 'mailto:kirscjo@gmail.com'
         + '?subject=' + encodeURIComponent(subject)
         + '&body=' + encodeURIComponent(body);
  document.body.appendChild(a);
})();
