(() => {
  const body = document.body;
  const savedTheme = localStorage.getItem('hna-theme');
  if (savedTheme === 'dark') body.classList.add('dark-theme');
  const toggle = document.querySelector('.theme-toggle');
  const syncLabel = () => { if (toggle) toggle.textContent = body.classList.contains('dark-theme') ? '☀ Light' : '☾ Dark'; };
  syncLabel();
  toggle?.addEventListener('click', () => {
    body.classList.toggle('dark-theme');
    localStorage.setItem('hna-theme', body.classList.contains('dark-theme') ? 'dark' : 'light');
    syncLabel();
  });
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav-links');
  menu?.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
  document.querySelectorAll('.flash-close').forEach(button => button.addEventListener('click', () => button.parentElement.remove()));
})();
