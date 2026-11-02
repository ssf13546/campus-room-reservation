"""预约核心业务逻辑测试：冲突检测、创建/取消、完成机制、异常校验。"""

from datetime import date, time, timedelta

import pytest

from app import create_app, db
from app.forms import ReservationForm
from app.models import Reservation, Room, User
from app.services import reservation_service as service


class TestConfig:
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPEN_TIME = "08:00"
    CLOSE_TIME = "22:00"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()

        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        student = User(username="student", role="student")
        student.set_password("student123")
        student2 = User(username="student2", role="student")
        student2.set_password("student123")
        room = Room(name="A101", location="A栋", capacity=10,
                    equipment="投影仪", status="available")
        db.session.add_all([admin, student, student2, room])
        db.session.commit()

        yield app
        db.drop_all()


def _student():
    return User.query.filter_by(username="student").first()


def _other():
    return User.query.filter_by(username="admin").first()


def _student2():
    return User.query.filter_by(username="student2").first()


def _room():
    return Room.query.filter_by(name="A101").first()


def _form(start, end, attendees="5", date_str=None):
    return ReservationForm(room_id=_room().id, date_str=date_str or (date.today() + timedelta(days=1)).isoformat(),
                           start_str=start, end_str=end, attendees=attendees)


def test_create_success(app):
    with app.app_context():
        res, errors = service.create_reservation(_room(), _student(), _form("14:00", "15:00"))
        assert not errors
        assert res.status == "booked"


def test_overlap_conflict_same_user(app):
    with app.app_context():
        service.create_reservation(_room(), _student(), _form("14:00", "15:00"))
        _, errors = service.create_reservation(_room(), _student(), _form("14:30", "15:30"))
        assert "您已预约该时段" in errors


def test_overlap_conflict_other_user(app):
    with app.app_context():
        service.create_reservation(_room(), _student(), _form("14:00", "15:00"))
        _, errors = service.create_reservation(_room(), _other(), _form("14:30", "15:30"))
        assert "该时间段已被预约" in errors


def test_boundary_no_conflict(app):
    with app.app_context():
        service.create_reservation(_room(), _student(), _form("14:00", "15:00"))
        _, e1 = service.create_reservation(_room(), _student(), _form("15:00", "16:00"))
        _, e2 = service.create_reservation(_room(), _student(), _form("13:00", "14:00"))
        assert not e1
        assert not e2


def test_invalid_time(app):
    with app.app_context():
        _, errors = service.create_reservation(_room(), _student(), _form("16:00", "15:00"))
        assert "开始时间必须早于结束时间" in errors


def test_outside_business_hours(app):
    with app.app_context():
        _, errors = service.create_reservation(_room(), _student(), _form("06:00", "07:00"))
        assert any("营业时间" in e for e in errors)


def test_capacity_exceeded(app):
    with app.app_context():
        _, errors = service.create_reservation(_room(), _student(), _form("14:00", "15:00", attendees="11"))
        assert "人数超过房间容量" in errors


def test_past_date(app):
    with app.app_context():
        _, errors = service.create_reservation(
            _room(), _student(), ReservationForm(
                room_id=_room().id, date_str="2000-01-01",
                start_str="14:00", end_str="15:00"))
        assert "不能预约过去的日期" in errors


def test_cancel_releases_slot(app):
    with app.app_context():
        res, _ = service.create_reservation(_room(), _student(), _form("14:00", "15:00"))
        ok, msg = service.cancel_reservation(res, _student())
        assert ok
        assert res.status == "cancelled"
        # 取消后同一时段可重新预约
        _, errors = service.create_reservation(_room(), _student(), _form("14:00", "15:00"))
        assert not errors


def test_cancel_other_user_forbidden(app):
    with app.app_context():
        res, _ = service.create_reservation(_room(), _student(), _form("14:00", "15:00"))
        ok, msg = service.cancel_reservation(res, _student2())
        assert not ok
        assert "无权取消该预约" in msg


def test_update_completed_reservations(app):
    with app.app_context():
        r = Reservation(user_id=_student().id, room_id=_room().id,
                        date=date(2000, 1, 1), start_time=time(9, 0),
                        end_time=time(10, 0), status="booked")
        db.session.add(r)
        db.session.commit()

        assert service.update_completed_reservations() >= 1
        assert r.status == "completed"
