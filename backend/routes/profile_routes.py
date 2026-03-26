"""
Nexus - Profile Module
========================
File   : backend/routes/profile_routes.py
Member : 2 — User Profile Management
Handles: View Profile, Edit Profile

API Endpoints:
  GET  /profile/view/<user_id>   → View any user's profile
  GET  /profile/edit             → Edit current user's profile (page)
  POST /profile/edit             → Save profile updates
  GET  /profile/api/<user_id>    → REST: Get profile as JSON
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
from backend.models.db import db, User, Profile, Post
from flask_jwt_extended import jwt_required, get_jwt_identity

profile_bp = Blueprint('profile', __name__)


def get_session_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None


@profile_bp.route('/view/<int:user_id>', methods=['GET'])
def view_profile(user_id):
    current_user = get_session_user()
    if not current_user:
        flash('Please log in to view profiles.', 'warning')
        return redirect(url_for('auth.login_page'))

    user = User.query.get_or_404(user_id)

    if not user.profile:
        p = Profile(user_id=user.id, full_name=user.username)
        db.session.add(p)
        db.session.commit()

    # Fresh query to get latest profile data
    db.session.expire_all()
    user = User.query.get(user_id)

    user_posts = Post.query.filter_by(user_id=user_id)\
                           .order_by(Post.created_at.desc())\
                           .limit(10).all()

    return render_template(
        'profile.html',
        profile_user=user,
        profile=user.profile,
        posts=user_posts,
        current_user=current_user,
        is_own_profile=(current_user.id == user_id)
    )


@profile_bp.route('/edit', methods=['GET'])
def edit_profile_page():
    current_user = get_session_user()
    if not current_user:
        return redirect(url_for('auth.login_page'))

    # Expire cache and get fresh data
    db.session.expire_all()
    current_user = User.query.get(session.get('user_id'))

    if not current_user.profile:
        p = Profile(user_id=current_user.id, full_name=current_user.username)
        db.session.add(p)
        db.session.commit()

    return render_template('edit_profile.html',
                           user=current_user,
                           profile=current_user.profile)


@profile_bp.route('/edit', methods=['POST'])
def edit_profile():
    current_user = get_session_user()
    if not current_user:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        return redirect(url_for('auth.login_page'))

    data = request.get_json() if request.is_json else request.form

    profile = current_user.profile
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.session.add(profile)

    # Update all fields — empty string clears the field
    profile.full_name = data.get('full_name', '').strip()
    profile.headline  = data.get('headline',  '').strip()
    profile.bio       = data.get('bio',       '').strip()
    profile.location  = data.get('location',  '').strip()

    db.session.commit()
    db.session.expire_all()

    if request.is_json:
        db.session.refresh(profile)
        return jsonify({'success': True, 'profile': profile.to_dict()}), 200

    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile.view_profile', user_id=current_user.id))


@profile_bp.route('/api/<int:user_id>', methods=['GET'])
def get_profile_api(user_id):
    user = User.query.get_or_404(user_id)
    if not user.profile:
        return jsonify({'success': False, 'message': 'Profile not found'}), 404
    return jsonify({
        'success': True,
        'user':    user.to_dict(),
        'profile': user.profile.to_dict()
    }), 200