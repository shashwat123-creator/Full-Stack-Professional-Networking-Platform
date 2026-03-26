/**
 * Nexus — feed.js
 * Member 4 — Frontend for Likes & Comments interactions.
 * Communicates with /interact/* API endpoints.
 */

// ── Character Counter ──────────────────────────────────────────────────────
const postContent = document.getElementById('post-content');
const charCount   = document.getElementById('char-count');
if (postContent && charCount) {
    postContent.addEventListener('input', () => {
        const len = postContent.value.length;
        charCount.textContent = `${len} / 1000`;
        charCount.style.color = len > 900 ? '#f85149' : '#8b949e';
    });
}


// ── Toggle Like (Member 4) ──────────────────────────────────────────────────
async function toggleLike(postId, btn) {
    try {
        const resp = await fetch(`/interact/like/${postId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await resp.json();
        if (data.success) {
            const countEl = document.getElementById(`like-count-${postId}`);
            if (countEl) countEl.textContent = data.like_count;

            btn.classList.toggle('liked', data.liked);

            // Animate heart
            btn.querySelector('.like-icon').style.transform = 'scale(1.5)';
            setTimeout(() => {
                btn.querySelector('.like-icon').style.transform = 'scale(1)';
            }, 200);
        } else {
            showToast(data.message || 'Error', 'error');
        }
    } catch (err) {
        showToast('Network error. Please try again.', 'error');
    }
}


// ── Toggle Comment Section (Member 4) ────────────────────────────────────────
function toggleComments(postId) {
    const section = document.getElementById(`comments-${postId}`);
    if (!section) return;

    if (section.style.display === 'none' || !section.style.display) {
        section.style.display = 'block';
        loadComments(postId);
    } else {
        section.style.display = 'none';
    }
}


// ── Load Comments (Member 4) ──────────────────────────────────────────────────
async function loadComments(postId) {
    const listEl = document.getElementById(`comments-list-${postId}`);
    if (!listEl) return;

    listEl.innerHTML = '<div style="color:#8b949e;font-size:.85rem;padding:.5rem">Loading...</div>';

    try {
        const resp = await fetch(`/interact/comments/${postId}`);
        const data = await resp.json();

        if (data.success && data.comments.length > 0) {
            listEl.innerHTML = data.comments.map(c => `
                <div class="comment-item">
                    <span class="comment-author">${escapeHtml(c.username)}</span>
                    <span class="comment-text">${escapeHtml(c.content)}</span>
                    <span class="comment-time">${c.created_at}</span>
                </div>
            `).join('');
        } else {
            listEl.innerHTML = '<div style="color:#8b949e;font-size:.85rem;padding:.25rem">No comments yet. Be the first!</div>';
        }
    } catch (err) {
        listEl.innerHTML = '<div style="color:#f85149;font-size:.85rem">Failed to load comments.</div>';
    }
}


// ── Add Comment (Member 4) ────────────────────────────────────────────────────
async function addComment(postId) {
    const input = document.getElementById(`comment-input-${postId}`);
    if (!input) return;

    const content = input.value.trim();
    if (!content) { showToast('Comment cannot be empty', 'warning'); return; }

    try {
        const resp = await fetch(`/interact/comment/${postId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });
        const data = await resp.json();

        if (data.success) {
            input.value = '';
            // Update count
            const countEl = document.getElementById(`comment-count-${postId}`);
            if (countEl) countEl.textContent = data.comment_count;
            // Append new comment to list
            const listEl = document.getElementById(`comments-list-${postId}`);
            if (listEl) {
                const div = document.createElement('div');
                div.className = 'comment-item';
                div.innerHTML = `
                    <span class="comment-author">${escapeHtml(data.username)}</span>
                    <span class="comment-text">${escapeHtml(data.comment.content)}</span>
                    <span class="comment-time">just now</span>
                `;
                listEl.appendChild(div);
                div.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        } else {
            showToast(data.message || 'Error posting comment', 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}

// Allow Enter key in comment input
document.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.classList.contains('comment-input')) {
        const postId = e.target.id.replace('comment-input-', '');
        addComment(parseInt(postId));
    }
});


// ── Utility: Escape HTML ─────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}


// ── Utility: Toast Notification ──────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.querySelector('.flash-container') || (() => {
        const c = document.createElement('div');
        c.className = 'flash-container';
        document.body.appendChild(c);
        return c;
    })();

    const toast = document.createElement('div');
    toast.className = `flash flash--${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity .3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}