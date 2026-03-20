function applyTheme(t) {
    document.documentElement.setAttribute('data-bs-theme', t);
    localStorage.setItem('theme', t);
    
    const isDark = (t === 'dark');
    const themeIcon = document.getElementById('theme-icon');

    if (themeIcon) {
        themeIcon.className = isDark ? 'bi bi-sun fs-5' : 'bi bi-moon-stars fs-5';
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-bs-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        applyTheme(savedTheme);
    } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        applyTheme(prefersDark ? 'dark' : 'light');
    }
}

// Listen for system theme changes only if the user hasn't set a manual override
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (!localStorage.getItem('theme')) {
        applyTheme(e.matches ? 'dark' : 'light');
    }
});

initTheme();