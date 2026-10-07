(() => {
  const themeToggle = document.querySelector('[data-theme-toggle]');

  const applyTheme = (theme) => {
    const dark = theme === 'dark';
    document.documentElement.classList.toggle('dark', dark);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    document.documentElement.classList.toggle('scheme-dark', dark);
    document.documentElement.classList.toggle('scheme-light', !dark);
    localStorage.setItem('hostelos-theme', theme);
    if (themeToggle) {
      themeToggle.setAttribute('aria-label', dark ? 'Switch to day theme' : 'Switch to night theme');
      themeToggle.setAttribute('title', dark ? 'Switch to day theme' : 'Switch to night theme');
    }
  };

  themeToggle?.addEventListener('click', () => {
    applyTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark');
  });

  const toggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (!toggle || !sidebar) return;

  let lastFocusedElement = null;

  const closeNav = () => {
    document.body.classList.remove('nav-open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Open navigation');
    if (lastFocusedElement) {
      lastFocusedElement.focus();
      lastFocusedElement = null;
    }
  };

  const openNav = () => {
    lastFocusedElement = document.activeElement;
    document.body.classList.add('nav-open');
    toggle.setAttribute('aria-expanded', 'true');
    toggle.setAttribute('aria-label', 'Close navigation');
    sidebar.querySelector('a, button')?.focus();
  };

  toggle.addEventListener('click', () => {
    document.body.classList.contains('nav-open') ? closeNav() : openNav();
  });

  document.querySelectorAll('[data-close-nav], .primary-nav a').forEach((item) => {
    item.addEventListener('click', closeNav);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && document.body.classList.contains('nav-open')) closeNav();
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth >= 900 && document.body.classList.contains('nav-open')) closeNav();
  });

  sidebar.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab' || !document.body.classList.contains('nav-open')) return;

    const focusable = sidebar.querySelectorAll('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (!focusable.length) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
})();
