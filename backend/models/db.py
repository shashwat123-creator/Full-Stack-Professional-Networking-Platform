"""
database module
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()


# ── MEMBER 1: User ────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username      = db.Column(db.String(50),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    profile       = db.relationship('Profile',      backref='user', uselist=False, cascade='all, delete-orphan')
    posts         = db.relationship('Post',         backref='author', lazy=True,   cascade='all, delete-orphan')
    likes         = db.relationship('Like',         backref='user',   lazy=True,   cascade='all, delete-orphan')
    comments      = db.relationship('Comment',      backref='user',   lazy=True,   cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user',   lazy=True,   cascade='all, delete-orphan', foreign_keys='Notification.user_id')

    # Follow relationships
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy=True, cascade='all, delete-orphan')
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy=True, cascade='all, delete-orphan')

    def set_password(self, raw_password):
        self.password_hash = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, raw_password):
        return bcrypt.checkpw(raw_password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self):
        return {'id': self.id, 'username': self.username, 'email': self.email,
                'created_at': self.created_at.strftime('%Y-%m-%d')}


# ── MEMBER 2: Profile ─────────────────────────────────────────────────────────
class Profile(db.Model):
    __tablename__ = 'profiles'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    full_name  = db.Column(db.String(100), nullable=True)
    headline   = db.Column(db.String(200), nullable=True)
    bio        = db.Column(db.Text,        nullable=True)
    location   = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(300), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'user_id': self.user_id,
                'full_name': self.full_name or '', 'headline': self.headline or '',
                'bio': self.bio or '', 'location': self.location or '',
                'avatar_url': self.avatar_url or ''}


# ── MEMBER 3: Post ────────────────────────────────────────────────────────────
class Post(db.Model):
    __tablename__ = 'posts'
    id               = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content          = db.Column(db.Text,    nullable=False)
    image_url        = db.Column(db.String(300), nullable=True)
    is_repost        = db.Column(db.Boolean, default=False)
    original_post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    likes    = db.relationship('Like',    backref='post', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {'id': self.id, 'user_id': self.user_id, 'content': self.content,
                'image_url': self.image_url or '', 'is_repost': self.is_repost,
                'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
                'likes_count': len(self.likes), 'comments_count': len(self.comments)}


# ── MEMBER 4: Like & Comment ──────────────────────────────────────────────────
class Like(db.Model):
    __tablename__ = 'likes'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id    = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_like'),)

    def to_dict(self):
        return {'id': self.id, 'user_id': self.user_id, 'post_id': self.post_id}


class Comment(db.Model):
    __tablename__ = 'comments'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id    = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    content    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'user_id': self.user_id, 'post_id': self.post_id,
                'content': self.content, 'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')}


# ── FEATURE: Follow System ────────────────────────────────────────────────────
class Follow(db.Model):
    __tablename__ = 'follows'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='unique_follow'),)

    def to_dict(self):
        return {'id': self.id, 'follower_id': self.follower_id, 'followed_id': self.followed_id}


# ── FEATURE: Notifications ────────────────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = 'notifications'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    actor_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type       = db.Column(db.String(20), nullable=False)  # 'like','comment','follow'
    post_id    = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    actor = db.relationship('User', foreign_keys=[actor_id])
    post  = db.relationship('Post', foreign_keys=[post_id])

    def to_dict(self):
        return {'id': self.id, 'user_id': self.user_id, 'actor_id': self.actor_id,
                'type': self.type, 'post_id': self.post_id, 'is_read': self.is_read,
                'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
                'actor_username': self.actor.username if self.actor else ''}