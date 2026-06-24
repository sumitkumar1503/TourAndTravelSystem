/**
 * TravelBot — global UI helpers (dark mode, etc.)
 */
(function () {
    // ---------- Dark mode ----------
    const KEY = 'tg-theme';
    const root = document.documentElement;

    function apply(theme) {
        root.setAttribute('data-theme', theme);
        document.body.classList.toggle('tg-dark', theme === 'dark');
    }

    function init() {
        const stored = localStorage.getItem(KEY);
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        apply(stored || (prefersDark ? 'dark' : 'light'));

        const btn = document.getElementById('darkModeToggle');
        if (btn) {
            const updateIcon = () => {
                const cur = root.getAttribute('data-theme') || 'light';
                btn.innerHTML = cur === 'dark'
                    ? '<i class="bi bi-sun-fill"></i>'
                    : '<i class="bi bi-moon-stars-fill"></i>';
            };
            updateIcon();
            btn.addEventListener('click', () => {
                const cur = root.getAttribute('data-theme') || 'light';
                const next = cur === 'dark' ? 'light' : 'dark';
                apply(next);
                localStorage.setItem(KEY, next);
                updateIcon();
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
