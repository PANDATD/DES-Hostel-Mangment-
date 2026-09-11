(() => {
  const toggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (!toggle || !sidebar) return;

  const closeNav = () => {
    document.body.classList.remove('nav-open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Open navigation');
  };

  const openNav = () => {
    document.body.classList.add('nav-open');
    toggle.setAttribute('aria-expanded', 'true');
    toggle.setAttribute('aria-label', 'Close navigation');
  };

  toggle.addEventListener('click', () => {
    document.body.classList.contains('nav-open') ? closeNav() : openNav();
  });

  document.querySelectorAll('[data-close-nav], .primary-nav a').forEach((item) => {
    item.addEventListener('click', closeNav);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeNav();
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth >= 900) closeNav();
  });
})();
