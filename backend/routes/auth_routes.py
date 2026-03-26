"""
Nexus - Authentication Module
================================
File   : backend/routes/auth_routes.py
Member : 1 — Authentication & Authorization
Handles: Register, Login, Logout, JWT, Remember Me,
         Forgot Password (real email), Reset Password,
         Change Password, Password Strength
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash, current_app
from backend.models.db import db, User, Profile
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import re

auth_bp = Blueprint('auth', __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def password_strength(pw):
    score = 0
    if len(pw) >= 6:  score += 1
    if len(pw) >= 10: score += 1
    if re.search(r'[A-Z]', pw): score += 1
    if re.search(r'[0-9]', pw): score += 1
    if re.search(r'[^A-Za-z0-9]', pw): score += 1
    return score

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def send_reset_email(user_email, reset_url):
    """Send password reset email via Flask-Mail"""
    try:
        mail = Mail(current_app)
        msg = Message(
            subject='Reset Your Nexus Password',
            recipients=[user_email]
        )
        msg.html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:2rem;background:#1a1a1c;color:#f0ede8;border-radius:12px;">
            <h2 style="color:#c9a84c;font-size:1.5rem;margin-bottom:1rem;">Reset your password</h2>
            <p style="color:#a09b94;margin-bottom:1.5rem;">
                You requested a password reset for your Nexus account.
                Click the button below to set a new password.
            </p>
            <a href="{reset_url}"
               style="display:inline-block;background:#c9a84c;color:#0e0e0f;padding:.75rem 1.5rem;
                      border-radius:8px;font-weight:600;text-decoration:none;margin-bottom:1.5rem;">
                Reset Password
            </a>
            <p style="color:#6b6560;font-size:.85rem;">
                This link expires in 30 minutes. If you did not request this, ignore this email.
            </p>
            <p style="color:#6b6560;font-size:.85rem;margin-top:.5rem;">
                Or copy this link: <br>{reset_url}
            </p>
        </div>
        """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


# ── REGISTER ─────────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() if request.is_json else request.form
    username         = data.get('username', '').strip()
    email            = data.get('email', '').strip()
    password         = data.get('password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    if not username or not email or not password:
        msg = 'All fields are required.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error'); return redirect(url_for('auth.register_page'))

    if not is_valid_email(email):
        msg = 'Invalid email format.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error'); return redirect(url_for('auth.register_page'))

    if len(password) < 6:
        msg = 'Password must be at least 6 characters.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error'); return redirect(url_for('auth.register_page'))

    if confirm_password and password != confirm_password:
        msg = 'Passwords do not match.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error'); return redirect(url_for('auth.register_page'))

    if User.query.filter_by(username=username).first():
        msg = f'Username "{username}" is already taken.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 409
        flash(msg, 'error'); return redirect(url_for('auth.register_page'))

    if User.query.filter_by(email=email).first():
        msg = 'An account with this email already exists.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 409
        flash(msg, 'error'); return redirect(url_for('auth.register_page'))

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.flush()

    new_profile = Profile(user_id=new_user.id, full_name=username)
    db.session.add(new_profile)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'message': 'Registration successful!', 'user_id': new_user.id}), 201

    flash('Account created! Please sign in.', 'success')
    return redirect(url_for('auth.login_page'))


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    data        = request.get_json() if request.is_json else request.form
    email       = data.get('email', '').strip()
    password    = data.get('password', '').strip()
    remember_me = data.get('remember_me', False)

    if not email or not password:
        msg = 'Email and password are required.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error'); return redirect(url_for('auth.login_page'))

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        msg = 'Invalid email or password.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 401
        flash(msg, 'error'); return redirect(url_for('auth.login_page'))

    access_token = create_access_token(identity=str(user.id))
    session['user_id']  = user.id
    session['username'] = user.username

    if remember_me:
        session.permanent = True
        from datetime import timedelta
        current_app.permanent_session_lifetime = timedelta(days=30)

    if request.is_json:
        return jsonify({'success': True, 'access_token': access_token, 'user': user.to_dict()}), 200

    flash(f'Welcome back, {user.username}!', 'success')
    return redirect(url_for('post.feed'))


# ── LOGOUT ────────────────────────────────────────────────────────────────────

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('You have been signed out.', 'info')
    return redirect(url_for('auth.login_page'))


# ── FORGOT PASSWORD ──────────────────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    return render_template('forgot_password.html')

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Member 1 - Forgot Password
    Generates a secure token and sends reset link via email.
    """
    data  = request.get_json() if request.is_json else request.form
    email = data.get('email', '').strip()

    if not email:
        msg = 'Email is required.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error'); return redirect(url_for('auth.forgot_password_page'))

    user = User.query.filter_by(email=email).first()

    if user:
        # Generate secure timed token
        s = get_serializer()
        token = s.dumps(email, salt='password-reset-salt')
        reset_url = url_for('auth.reset_password_page', token=token, _external=True)

        # Send email
        sent = send_reset_email(email, reset_url)
        if not sent:
            # Email failed — show token in flash for demo purposes
            flash(f'Email not configured. Use this link to reset: /auth/reset-password/{token}', 'warning')
            return redirect(url_for('auth.login_page'))

    # Always show success to prevent email enumeration
    flash('If that email exists, a reset link has been sent. Check your inbox.', 'success')
    if request.is_json:
        return jsonify({'success': True, 'message': 'Reset link sent if email exists.'}), 200
    return redirect(url_for('auth.login_page'))


# ── RESET PASSWORD PAGE ───────────────────────────────────────────────────────

@auth_bp.route('/reset-password/<token>', methods=['GET'])
def reset_password_page(token):
    """Member 1 - Reset Password Page (from email link)"""
    try:
        s     = get_serializer()
        email = s.loads(token, salt='password-reset-salt', max_age=1800)  # 30 min
    except SignatureExpired:
        flash('Reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password_page'))
    except BadSignature:
        flash('Invalid reset link.', 'error')
        return redirect(url_for('auth.forgot_password_page'))

    return render_template('reset_password.html', token=token, email=email)


@auth_bp.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Member 1 - Save new password from reset link"""
    try:
        s     = get_serializer()
        email = s.loads(token, salt='password-reset-salt', max_age=1800)
    except (SignatureExpired, BadSignature):
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('auth.forgot_password_page'))

    data       = request.get_json() if request.is_json else request.form
    new_pw     = data.get('new_password', '').strip()
    confirm_pw = data.get('confirm_password', '').strip()

    if not new_pw or len(new_pw) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return redirect(url_for('auth.reset_password_page', token=token))

    if new_pw != confirm_pw:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('auth.reset_password_page', token=token))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login_page'))

    user.set_password(new_pw)
    db.session.commit()

    flash('Password reset successfully! Please sign in.', 'success')
    return redirect(url_for('auth.login_page'))


# ── CHANGE PASSWORD ──────────────────────────────────────────────────────────

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    uid = session.get('user_id')
    if not uid:
        if request.is_json: return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        return redirect(url_for('auth.login_page'))

    user = User.query.get(uid)
    data = request.get_json() if request.is_json else request.form

    current_pw     = data.get('current_password', '').strip()
    new_pw         = data.get('new_password', '').strip()
    confirm_new_pw = data.get('confirm_new_password', '').strip()

    if not current_pw or not new_pw or not confirm_new_pw:
        msg = 'All password fields are required.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error'); return redirect(url_for('profile.edit_profile_page'))

    if not user.check_password(current_pw):
        msg = 'Current password is incorrect.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 401
        flash(msg, 'error'); return redirect(url_for('profile.edit_profile_page'))

    if new_pw != confirm_new_pw:
        msg = 'New passwords do not match.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error'); return redirect(url_for('profile.edit_profile_page'))

    if len(new_pw) < 6:
        msg = 'New password must be at least 6 characters.'
        if request.is_json: return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error'); return redirect(url_for('profile.edit_profile_page'))

    user.set_password(new_pw)
    db.session.commit()

    if request.is_json: return jsonify({'success': True, 'message': 'Password changed!'}), 200
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile.edit_profile_page'))


# ── REST ──────────────────────────────────────────────────────────────────────

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    uid  = get_jwt_identity()
    user = User.query.get(uid)
    if not user: return jsonify({'success': False, 'message': 'User not found'}), 404
    return jsonify({'success': True, 'user': user.to_dict()}), 200