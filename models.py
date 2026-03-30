from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer as Serializer, SignatureExpired
from flask import current_app
from flask_login import UserMixin

db = SQLAlchemy()
bcrypt = Bcrypt()


# Enums for various fields

class ItemStatusEnum(Enum):
    LOST = 'lost'
    FOUND = 'found'

class CourseEnum(Enum):
    Btech = 'Btech'
    Barch = 'Barch'
    Mtech = 'Mtech'
    Msc = 'Msc'
    PHD = 'PHD'

class BranchEnum(Enum):
    CSE = 'CSE'
    ECE = 'ECE'
    EEE = 'EEE'
    ICE = 'ICE'
    Chem = 'Chem'
    Civil = 'Civil'
    MECH = 'MECH'
    Prod = 'Prod'
    Other = 'Other'



class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    profile_pic = db.Column(db.String(255), default='default.jpg')
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    roll_number = db.Column(db.String(20), nullable=False)
    batch = db.Column(db.Integer, nullable=False)
    course = db.Column(db.Enum(CourseEnum), nullable=False)
    branch = db.Column(db.Enum(BranchEnum), nullable=False)

    items = db.relationship('Item', backref='owner', lazy=True)
    password_reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    claimed_items = db.relationship('ClaimedItem', backref='claimer', lazy=True)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt=current_app.config['SECURITY_PASSWORD_SALT'])

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt=current_app.config['SECURITY_PASSWORD_SALT'], max_age=1800)
        except (SignatureExpired, ValueError):
            return None
        return User.query.get(data['user_id'])

    def __repr__(self):
        return f"User('{self.email}', '{self.first_name}', '{self.last_name}')"

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    items = db.relationship('Item', backref='category', lazy=True)

    def __repr__(self):
        return f"Category('{self.name}')"


class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    image_file = db.Column(db.String(255), default='default.jpg')
    status = db.Column(db.Enum('lost', 'found'), nullable=False)  # Updated Enum
    date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    claimed = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(255))  # Add this line to include the location field

    def __repr__(self):
        return f"Item('{self.name}', '{self.status}', '{self.date}')"



class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"PasswordResetToken('{self.user_id}', '{self.otp}')"

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Notification('{self.user_id}', '{self.item_id}', '{self.message}')"

class ClaimedItem(db.Model):
    __tablename__ = 'claimed_items'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    claimer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    claimed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"ClaimedItem('{self.item_id}', '{self.claimer_id}')"
