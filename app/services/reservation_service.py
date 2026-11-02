"""预约核心业务逻辑：冲突检测、创建/取消预约、状态刷新、统计。"""

from datetime import date, datetime, timedelta

from flask import current_app

from app import db
from app.forms import parse_time
from app.models import Reservation, Room


def open_time():
    return parse_time(current_app.config["OPEN_TIME"])


def close_time():
    return parse_time(current_app.config["CLOSE_TIME"])


def find_conflict(room_id, reserve_date, new_start, new_end, exclude_id=None):
    """返回与 [new_start, new_end) 重叠的第一条 booked 预约，无则返回 None。"""
    q = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.date == reserve_date,
        Reservation.status == "booked",
        Reservation.start_time < new_end,
        Reservation.end_time > new_start,
    )
    if exclude_id is not None:
        q = q.filter(Reservation.id != exclude_id)
    return q.first()


def has_conflict(room_id, reserve_date, new_start, new_end, exclude_id=None):
    return find_conflict(room_id, reserve_date, new_start, new_end, exclude_id) is not None


def create_reservation(room, user, form):
    """创建预约。返回 (reservation, errors)。"""
    form.validate_basic()
    errors = form.errors

    if room is None:
        return None, errors

    if room.status == "maintenance":
        errors.append("该房间正在维护，暂不可预约")

    if form.date is not None and form.date < date.today():
        errors.append("不能预约过去的日期")

    if form.start_time is not None and form.end_time is not None:
        if form.start_time < open_time() or form.end_time > close_time():
            errors.append(
                "预约时间必须在营业时间 "
                f"{current_app.config['OPEN_TIME']} - {current_app.config['CLOSE_TIME']} 内"
            )

    if form.attendees is not None and form.attendees > room.capacity:
        errors.append("人数超过房间容量")

    if form.date is not None and form.start_time is not None and form.end_time is not None:
        conflict = find_conflict(room.id, form.date, form.start_time, form.end_time)
        if conflict is not None:
            if conflict.user_id == user.id:
                errors.append("您已预约该时段")
            else:
                errors.append("该时间段已被预约")

    if errors:
        return None, errors

    reservation = Reservation(
        user_id=user.id,
        room_id=room.id,
        date=form.date,
        start_time=form.start_time,
        end_time=form.end_time,
        purpose=form.purpose,
        attendees=form.attendees,
        status="booked",
    )
    db.session.add(reservation)
    db.session.commit()
    return reservation, []


def is_completed(reservation):
    """预约是否已过期（date + end_time 早于当前时间）。"""
    now = datetime.now()
    if reservation.date < now.date():
        return True
    if reservation.date == now.date() and reservation.end_time <= now.time():
        return True
    return False


def cancel_reservation(reservation, user):
    """取消预约。返回 (ok, message)。"""
    if reservation is None:
        return False, "预约不存在"
    if reservation.user_id != user.id and not user.is_admin:
        return False, "无权取消该预约"
    if reservation.status != "booked":
        return False, "该预约已取消或已完成"
    if is_completed(reservation):
        return False, "该预约已完成，无法取消"

    reservation.status = "cancelled"
    reservation.cancelled_at = datetime.now()
    db.session.commit()
    return True, "预约已取消"


def update_completed_reservations():
    """将已过期且仍为 booked 的预约批量标记为 completed。返回更新条数。"""
    now = datetime.now()
    today = now.date()
    now_time = now.time()

    expired = Reservation.query.filter(
        Reservation.status == "booked",
        db.or_(
            Reservation.date < today,
            db.and_(Reservation.date == today, Reservation.end_time <= now_time),
        ),
    ).all()

    count = 0
    for r in expired:
        r.status = "completed"
        count += 1
    if count:
        db.session.commit()
    return count


def booked_slots(room_id, reserve_date):
    """某房间某天的全部 booked 预约（按开始时间排序）。"""
    return Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.date == reserve_date,
        Reservation.status == "booked",
    ).order_by(Reservation.start_time).all()


def slot_grid(room_id, reserve_date):
    """生成按小时划分的时段占用情况（08:00-22:00），供详情页展示。"""
    booked = booked_slots(room_id, reserve_date)
    slots = []
    t = open_time()
    close = close_time()
    while t < close:
        nxt = (datetime.combine(reserve_date, t) + timedelta(hours=1)).time()
        free = all(not (r.start_time < nxt and r.end_time > t) for r in booked)
        slots.append({"start": t.strftime("%H:%M"), "end": nxt.strftime("%H:%M"), "free": free})
        t = nxt
    return slots


# ---------- 统计 ----------

def _hours_between(t1, t2):
    base = date.today()
    return (datetime.combine(base, t2) - datetime.combine(base, t1)).total_seconds() / 3600


def reservation_count_by_room():
    rooms = Room.query.order_by(Room.id).all()
    return [{"name": r.name, "value": len(r.reservations)} for r in rooms]


def usage_rate_by_room(days=7):
    daily = _hours_between(open_time(), close_time())
    result = []
    for room in Room.query.order_by(Room.id).all():
        total = sum(
            _hours_between(r.start_time, r.end_time)
            for r in room.reservations
            if r.status in ("booked", "completed")
        )
        pct = (total / (daily * days)) * 100 if daily and days else 0
        result.append({"name": room.name, "value": round(pct, 1)})
    return result


def status_distribution():
    return [
        {"name": "已预约", "value": Reservation.query.filter_by(status="booked").count()},
        {"name": "已取消", "value": Reservation.query.filter_by(status="cancelled").count()},
        {"name": "已完成", "value": Reservation.query.filter_by(status="completed").count()},
    ]


def time_heat():
    """按预约 start_time 所在小时统计预约次数（booked + completed）。"""
    rows = Reservation.query.filter(Reservation.status.in_(["booked", "completed"])).all()
    counts = {}
    for r in rows:
        h = r.start_time.hour
        counts[h] = counts.get(h, 0) + 1

    return [
        {"hour": f"{h:02d}", "value": counts.get(h, 0)}
        for h in range(open_time().hour, close_time().hour)
    ]
