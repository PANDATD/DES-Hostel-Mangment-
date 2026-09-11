# UI / UX Update

This update changes only the presentation layer. Application routes, database models, CRUD behavior, CSRF protection, attendance logic, and existing data are unchanged.

## Improvements

- Responsive desktop sidebar with clear active navigation state.
- Mobile top bar with accessible slide-out navigation and backdrop.
- Improved spacing, typography, visual hierarchy, cards, buttons, and status badges.
- Touch-friendly 44px form controls and buttons.
- Responsive one-column forms on phones.
- Safer horizontal scrolling for data-heavy tables with sticky headers.
- Improved dashboard metric cards.
- Better authentication screen layout and browser autocomplete behavior.
- Improved focus states, keyboard navigation, skip link, reduced-motion support, and contrast.
- Added lightweight `app/static/app.js` only for mobile navigation behavior.

## Modified / added files

- `app/templates/base.html`
- `app/templates/auth/login.html`
- `app/templates/admin/complaints.html`
- `app/templates/admin/fees.html`
- `app/templates/student/complaints.html`
- `app/templates/student/fees.html`
- `app/static/app.css`
- `app/static/app.js` (new)

## Validation

All Jinja templates were parsed successfully after the update. Full Flask tests could not be executed in the artifact environment because the required Python 3.12/Flask environment was not locally available and external dependency downloads were unavailable.
