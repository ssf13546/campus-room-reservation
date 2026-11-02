from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(50))
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    capacity = db.Column(db.Integer, nullable=False)
    equipment = db.Column(db.String(255))
    status = db.Column(db.String(20), default="available")  # available / maintenance
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.String(200))
    attendees = db.Column(db.Integer)
    status = db.Column(db.String(20), default="booked")  # booked / cancelled / completed
    created_at = db.Column(db.DateTime, default=datetime.now)
    cancelled_at = db.Column(db.DateTime)
    cancel_reason = db.Column(db.String(255))

    user = db.relationship("User", backref="reservations")
    room = db.relationship("Room", backref="reservations")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
