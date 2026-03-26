"""
Nexus - Interactions Module
==============================
File   : backend/routes/interaction_routes.py
Member : 4 — Likes & Comments + Notifications
"""

from flask import Blueprint, request, jsonify, session
from backend.models.db import db, User, Post, Like, Comment, Notification

interact_bp = Blueprint('interact', __name__)


def get_session_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None


def create_notification(user_id, actor_id, notif_type, post_id=None):
    if user_id == actor_id:
        return
    notif = Notification(user_id=user_id, actor_id=actor_id,
                         type=notif_type, post_id=post_id)
    db.session.add(notif)


@interact_bp.route('/like/<int:post_id>', methods=['POST'])
def toggle_like(post_id):
    current_user = get_session_user()
    if not current_user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    post = Post.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(
        user_id=current_user.id, post_id=post_id
    ).first()

    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        new_like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(new_like)
        # Notify post owner
        create_notification(post.user_id, current_user.id, 'like', post_id)
        db.session.commit()
        liked = True

    new_count = Like.query.filter_by(post_id=post_id).count()
    return jsonify({'success': True, 'liked': liked,
                    'like_count': new_count, 'post_id': post_id}), 200


@interact_bp.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    current_user = get_session_user()
    if not current_user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    post = Post.query.get_or_404(post_id)
    data = request.get_json() if request.is_json else request.form
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'success': False, 'message': 'Comment cannot be empty.'}), 400
    if len(content) > 500:
        return jsonify({'success': False, 'message': 'Comment too long.'}), 400

    new_comment = Comment(user_id=current_user.id, post_id=post_id, content=content)
    db.session.add(new_comment)
    # Notify post owner
    create_notification(post.user_id, current_user.id, 'comment', post_id)
    db.session.commit()

    comment_count = Comment.query.filter_by(post_id=post_id).count()
    return jsonify({
        'success':       True,
        'comment':       new_comment.to_dict(),
        'username':      current_user.username,
        'comment_count': comment_count
    }), 201


@interact_bp.route('/comments/<int:post_id>', methods=['GET'])
def get_comments(post_id):
    post = Post.query.get_or_404(post_id)
    comments_data = []
    for comment in post.comments:
        c = comment.to_dict()
        c['username'] = comment.user.username if comment.user else 'Unknown'
        comments_data.append(c)
    return jsonify({'success': True, 'post_id': post_id, 'comments': comments_data}), 200


@interact_bp.route('/comment/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    current_user = get_session_user()
    if not current_user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Comment deleted'}), 200