/* ===================== boot ===================== */
fit();
const startView = (location.hash || '').slice(1);
go(VIEWS[startView] ? startView : 'health', false);
window.addEventListener('hashchange', () => { const v = location.hash.slice(1); if (VIEWS[v] && v !== state.view) go(v, false); });
if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => render());
