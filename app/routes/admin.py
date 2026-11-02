from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import parse_date
from app.models import Reservation, Room
from app.services import reservation_service as service

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("需要管理员权限", "danger")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def _validate_room_form():
    """校验房间表单，返回 (data, errors)。"""
    data = {
        "name": request.form.get("name", "").strip(),
        "location": request.form.get("location", "").strip(),
        "capacity": request.form.get("capacity", "").strip(),
        "equipment": request.form.get("equipment", "").strip(),
        "status": request.form.get("status", "available").strip(),
        "description": request.form.get("description", "").strip(),
    }
    errors = []
    if not data["name"]:
        errors.append("房间名称不能为空")
    try:
        data["capacity"] = int(data["capacity"])
        if data["capacity"] < 1:
            errors.append("容量必须为正整数")
    except (ValueError, TypeError):
        errors.append("容量必须为正整数")
    if data["status"] not in ("available", "maintenance"):
        data["status"] = "available"
    return data, errors


@admin_bp.route("/rooms", methods=["GET", "POST"])
@login_required
@admin_required
def rooms():
    if request.method == "POST":
        data, errors = _validate_room_form()
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            db.session.add(Room(**data))
            db.session.commit()
            flash("房间已添加", "success")
            return redirect(url_for("admin.rooms"))

    rooms = Room.query.order_by(Room.id).all()
    return render_template("admin/rooms.html", rooms=rooms)


@admin_bp.route("/rooms/<int:room_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    data, errors = _validate_room_form()
    if errors:
        for e in errors:
            flash(e, "danger")
    else:
        room.name = data["name"]
        room.location = data["location"]
        room.capacity = data["capacity"]
        room.equipment = data["equipment"]
        room.status = data["status"]
        room.description = data["description"]
        db.session.commit()
        flash("房间已更新", "success")
    return redirect(url_for("admin.rooms"))


@admin_bp.route("/rooms/<int:room_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    if room.reservations:
        flash("该房间存在预约记录，无法删除", "danger")
    else:
        db.session.delete(room)
        db.session.commit()
        flash("房间已删除", "success")
    return redirect(url_for("admin.rooms"))


@admin_bp.route("/reservations")
@login_required
@admin_required
def reservations():
    service.update_completed_reservations()

    q = Reservation.query
    room_id = request.args.get("room_id")
    status = request.args.get("status")
    date_str = request.args.get("date")

    if room_id and room_id.isdigit():
        q = q.filter(Reservation.room_id == int(room_id))
    if status in ("booked", "cancelled", "completed"):
        q = q.filter(Reservation.status == status)
    if date_str:
        d = parse_date(date_str)
        if d:
            q = q.filter(Reservation.date == d)

    reservations = q.order_by(Reservation.date.desc(), Reservation.start_time.desc()).all()
    rooms = Room.query.order_by(Room.id).all()
    return render_template(
        "admin/reservations.html", reservations=reservations, rooms=rooms, filters=request.args
    )


@admin_bp.route("/statistics")
@login_required
@admin_required
def statistics():
    service.update_completed_reservations()
    return render_template("admin/statistics.html")
