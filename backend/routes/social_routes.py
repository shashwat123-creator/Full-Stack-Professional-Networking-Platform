"""
Nexus - Social Features Module
================================
File   : backend/routes/social_routes.py
Feature: Follow System + Notifications + Search
Handles: Follow/Unfollow, Get Followers/Following,
         Get Notifications, Mark Read, Search Users/Posts

API Endpoints:
  POST /social/follow/<user_id>       → Follow/Unfollow toggle
  GET  /social/followers/<user_id>    → Get followers list
  GET  /social/following/<user_id>    → Get following list
  GET  /social/notifications          → Get notifications page
  POST /social/notifications/read     → Mark all as read
  GET  /social/search                 → Search users & posts
  GET  /social/api/notifications      → REST: notifications JSON
  GET  /social/api/unread-count       → REST: unread count
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
from backend.models.db import db, User, Post, Profile, Follow, Notification, Like, Comment
import re

social_bp = Blueprint('social', __name__)


def get_session_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None


def create_notification(user_id, actor_id, notif_type, post_id=None):
    """Helper to create a notification — skip if notifying yourself"""
    if user_id == actor_id:
        return
    notif = Notification(
        user_id=user_id,
        actor_id=actor_id,
        type=notif_type,
        post_id=post_id
    )
    db.session.add(notif)


# ── FOLLOW / UNFOLLOW ─────────────────────────────────────────────────────────

@social_bp.route('/follow/<int:user_id>', methods=['POST'])
def toggle_follow(user_id):
    """Toggle follow/unfollow a user"""
    current_user = get_session_user()
    if not current_user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    if current_user.id == user_id:
        return jsonify({'success': False, 'message': 'Cannot follow yourself'}), 400

    target = User.query.get_or_404(user_id)

    existing = Follow.query.filter_by(
        follower_id=current_user.id,
        followed_id=user_id
    ).first()

    if existing:
        # Unfollow
        db.session.delete(existing)
        db.session.commit()
        following = False
    else:
        # Follow
        new_follow = Follow(follower_id=current_user.id, followed_id=user_id)
        db.session.add(new_follow)
        # Create notification
        create_notification(user_id, current_user.id, 'follow')
        db.session.commit()
        following = True

    followers_count = Follow.query.filter_by(followed_id=user_id).count()

    return jsonify({
        'success':         True,
        'following':       following,
        'followers_count': followers_count
    }), 200


# ── NOTIFICATIONS PAGE ────────────────────────────────────────────────────────

@social_bp.route('/notifications', methods=['GET'])
def notifications_page():
    current_user = get_session_user()
    if not current_user:
        return redirect(url_for('auth.login_page'))

    notifications = Notification.query\
        .filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(50).all()

    # Mark all as read
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()

    return render_template('notifications.html',
                           current_user=current_user,
                           notifications=notifications)


# ── MARK NOTIFICATIONS READ ───────────────────────────────────────────────────

@social_bp.route('/notifications/read', methods=['POST'])
def mark_read():
    current_user = get_session_user()
    if not current_user:
        return jsonify({'success': False}), 401
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True}), 200


# ── SEARCH ────────────────────────────────────────────────────────────────────

@social_bp.route('/search', methods=['GET'])
def search():
    current_user = get_session_user()
    if not current_user:
        return redirect(url_for('auth.login_page'))

    query = request.args.get('q', '').strip()
    user_results  = []
    post_results  = []

    if query:
        # Search users by username or full name
        user_results = db.session.query(User, Profile)\
            .outerjoin(Profile, Profile.user_id == User.id)\
            .filter(
                db.or_(
                    User.username.ilike(f'%{query}%'),
                    Profile.full_name.ilike(f'%{query}%'),
                    Profile.headline.ilike(f'%{query}%')
                )
            ).limit(10).all()

        # Search posts by content or hashtag
        post_results = db.session.query(Post, User, Profile)\
            .join(User, Post.user_id == User.id)\
            .outerjoin(Profile, Profile.user_id == User.id)\
            .filter(Post.content.ilike(f'%{query}%'))\
            .order_by(Post.created_at.desc())\
            .limit(20).all()

    return render_template('search.html',
                           current_user=current_user,
                           query=query,
                           user_results=user_results,
                           post_results=post_results)


# ── REST: Unread Count ────────────────────────────────────────────────────────

@social_bp.route('/api/unread-count', methods=['GET'])
def unread_count():
    current_user = get_session_user()
    if not current_user:
        return jsonify({'count': 0}), 200
    count = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).count()
    return jsonify({'count': count}), 200


# ── REST: Notifications JSON ──────────────────────────────────────────────────

@social_bp.route('/api/notifications', methods=['GET'])
def notifications_api():
    current_user = get_session_user()
    if not current_user:
        return jsonify({'success': False}), 401
    notifications = Notification.query\
        .filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(20).all()
    return jsonify({
        'success': True,
        'notifications': [n.to_dict() for n in notifications]
    }), 200


# ── REST: Follow Status ───────────────────────────────────────────────────────

@social_bp.route('/api/follow-status/<int:user_id>', methods=['GET'])
def follow_status(user_id):
    current_user = get_session_user()
    if not current_user:
        return jsonify({'following': False}), 200
    existing = Follow.query.filter_by(
        follower_id=current_user.id, followed_id=user_id
    ).first()
    followers_count = Follow.query.filter_by(followed_id=user_id).count()
    following_count = Follow.query.filter_by(follower_id=user_id).count()
    return jsonify({
        'following':       existing is not None,
        'followers_count': followers_count,
        'following_count': following_count
    }), 200