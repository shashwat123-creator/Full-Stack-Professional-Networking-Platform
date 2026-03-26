/**
 * Nexus — main.js
 * Shared utilities used across all pages.
 */

// Auto-dismiss flash messages after 4 seconds
document.addEventListener('DOMContentLoaded', () => {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(f => {
        setTimeout(() => {
            f.style.transition = 'opacity 0.4s ease';
            f.style.opacity = '0';
            setTimeout(() => f.remove(), 400);
        }, 4000);
    });
});