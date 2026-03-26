"""
Nexus - Posts & Feed Module
=============================
File   : backend/routes/post_routes.py
Member : 3 — Post Creation & Feed
Handles: Create Post (with image + hashtags), View Feed,
         Delete Post, Repost/Share, Filter by hashtag

API Endpoints:
  GET  /posts/feed              → Main feed (all posts)
  GET  /posts/feed?tag=python   → Feed filtered by hashtag
  POST /posts/create            → Create post (image + hashtags)
  POST /posts/delete/<id>       → Delete own post
  POST /posts/repost/<id>       → Repost someone's post
  GET  /posts/api/feed          → REST: Feed JSON
  GET  /posts/api/<id>          → REST: Single post JSON
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash, current_app
from backend.models.db import db, User, Post, Profile, Like, Comment
from flask_jwt_extended import jwt_required, get_jwt_identity
import os, re, uuid
from werkzeug.utils import secure_filename

post_bp = Blueprint('post', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_session_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_hashtags(text):
    """Extract hashtags from post content e.g. #python #flask"""
    return list(set(tag.lower() for tag in re.findall(r'#(\w+)', text)))

def save_image(file):
    """Save uploaded image and return relative URL"""
    upload_folder = os.path.join(current_app.static_folder, 'images', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    ext      = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(upload_folder, filename))
    return f'/static/images/uploads/{filename}'


# ── FEED ──────────────────────────────────────────────────────────────────────

@post_bp.route('/feed', methods=['GET'])
def feed():
    """
    Member 3 - Main Feed with hashtag filtering
    ?tag=python  → filter by hashtag
    """
    current_user = get_session_user()
    if not current_user:
        flash('Please log in to view the feed.', 'warning')
        return redirect(url_for('auth.login_page'))

    tag_filter = request.args.get('tag', '').strip().lower()

    query = db.session.query(Post, User, Profile)\
              .join(User,    Post.user_id == User.id)\
              .outerjoin(Profile, Profile.user_id == User.id)

    # Filter by hashtag if provided
    if tag_filter:
        query = query.filter(Post.content.ilike(f'%#{tag_filter}%'))

    posts = query.order_by(Post.created_at.desc()).limit(50).all()

    liked_post_ids = set(
        like.post_id for like in Like.query.filter_by(user_id=current_user.id).all()
    )

    # Get trending hashtags from recent posts
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(100).all()
    all_tags = []
    for p in recent_posts:
        all_tags.extend(extract_hashtags(p.content))
    from collections import Counter
    trending_tags = [tag for tag, count in Counter(all_tags).most_common(8)]

    return render_template(
        'feed.html',
        posts=posts,
        current_user=current_user,
        liked_post_ids=liked_post_ids,
        trending_tags=trending_tags,
        active_tag=tag_filter
    )


# ── CREATE POST ───────────────────────────────────────────────────────────────

@post_bp.route('/create', methods=['POST'])
def create_post():
    """
    Member 3 - Create Post
    Accepts: content (text), image (file upload), category
    Auto-extracts hashtags from content
    """
    current_user = get_session_user()
    if not current_user:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        return redirect(url_for('auth.login_page'))

    content  = request.form.get('content', '').strip()
    category = request.form.get('category', '').strip()
    image_url = None

    if not content:
        flash('Post content cannot be empty.', 'error')
        return redirect(url_for('post.feed'))

    if len(content) > 1000:
        flash('Post cannot exceed 1000 characters.', 'error')
        return redirect(url_for('post.feed'))

    # Handle image upload
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            if size > MAX_FILE_SIZE:
                flash('Image too large. Max size is 2MB.', 'error')
                return redirect(url_for('post.feed'))
            try:
                image_url = save_image(file)
            except Exception as e:
                flash('Image upload failed. Post created without image.', 'warning')

    # Append category as hashtag if provided
    if category and f'#{category.lower()}' not in content.lower():
        content = f"{content} #{category.lower()}"

    new_post = Post(
        user_id=current_user.id,
        content=content,
        image_url=image_url
    )
    db.session.add(new_post)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'post': new_post.to_dict()}), 201

    flash('Post published!', 'success')
    return redirect(url_for('post.feed'))


# ── DELETE POST ───────────────────────────────────────────────────────────────

@post_bp.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    """Member 3 - Delete own post"""
    current_user = get_session_user()
    if not current_user:
        return redirect(url_for('auth.login_page'))

    post = Post.query.get_or_404(post_id)

    if post.user_id != current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        flash('You can only delete your own posts.', 'error')
        return redirect(url_for('post.feed'))

    # Delete image file if exists
    if post.image_url:
        try:
            img_path = os.path.join(current_app.static_folder,
                                    post.image_url.lstrip('/static/'))
            if os.path.exists(img_path):
                os.remove(img_path)
        except:
            pass

    db.session.delete(post)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'message': 'Post deleted'}), 200

    flash('Post deleted.', 'info')
    return redirect(url_for('post.feed'))


# ── REPOST ────────────────────────────────────────────────────────────────────

@post_bp.route('/repost/<int:post_id>', methods=['POST'])
def repost(post_id):
    """
    Member 3 - Repost / Share
    Creates a new post quoting the original post content.
    """
    current_user = get_session_user()
    if not current_user:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        return redirect(url_for('auth.login_page'))

    original = Post.query.get_or_404(post_id)
    original_author = User.query.get(original.user_id)

    # Optional added comment from user
    data    = request.get_json() if request.is_json else request.form
    comment = data.get('comment', '').strip()

    # Build repost content
    repost_content = f'🔁 Reposted from @{original_author.username}:\n\n"{original.content}"'
    if comment:
        repost_content = f'{comment}\n\n{repost_content}'

    new_post = Post(
        user_id=current_user.id,
        content=repost_content,
        image_url=original.image_url,
        is_repost=True,
        original_post_id=original.id
    )
    db.session.add(new_post)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'post': new_post.to_dict()}), 201

    flash('Post shared to your feed!', 'success')
    return redirect(url_for('post.feed'))


# ── REST ──────────────────────────────────────────────────────────────────────

@post_bp.route('/api/feed', methods=['GET'])
def feed_api():
    page  = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    posts = Post.query.order_by(Post.created_at.desc())\
                      .paginate(page=page, per_page=limit, error_out=False)
    return jsonify({
        'success': True,
        'posts':   [p.to_dict() for p in posts.items],
        'total':   posts.total,
        'pages':   posts.pages,
        'current_page': posts.page
    }), 200

@post_bp.route('/api/<int:post_id>', methods=['GET'])
def get_post_api(post_id):
    post = Post.query.get_or_404(post_id)
    data = post.to_dict()
    data['comments'] = [c.to_dict() for c in post.comments]
    return jsonify({'success': True, 'post': data}), 200