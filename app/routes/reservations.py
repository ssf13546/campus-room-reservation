from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.forms import ReservationForm
from app.models import Reservation, Room
from app.services import reservation_service as service

reservations_bp = Blueprint("reservations", __name__)


@reservations_bp.route("/reservations/new", methods=["GET", "POST"])
@login_required
def new():
    rooms = Room.query.order_by(Room.id).all()
    room = None
    room_id = request.values.get("room_id")
    if room_id and str(room_id).isdigit():
        room = Room.query.get(int(room_id))

    default_date = request.args.get("date") or date.today().isoformat()

    if request.method == "POST":
        form = ReservationForm(
            room_id=request.form.get("room_id"),
            date_str=request.form.get("date"),
            start_str=request.form.get("start_time"),
            end_str=request.form.get("end_time"),
            purpose=request.form.get("purpose"),
            attendees=request.form.get("attendees"),
        )
        room = Room.query.get(form.room_id) if form.room_id else None
        reservation, errors = service.create_reservation(room, current_user, form)
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            flash("预约成功", "success")
            return redirect(url_for("reservations.my"))
        default_date = request.form.get("date") or default_date

    return render_template(
        "reservations/form.html", rooms=rooms, room=room, date=default_date
    )


@reservations_bp.route("/reservations/<int:reservation_id>/cancel", methods=["POST"])
@login_required
def cancel(reservation_id):
    reservation = Reservation.query.get(reservation_id)
    ok, msg = service.cancel_reservation(reservation, current_user)
    flash(msg, "success" if ok else "danger")
    if current_user.is_admin:
        return redirect(url_for("admin.reservations"))
    return redirect(url_for("reservations.my"))


@reservations_bp.route("/my-reservations")
@login_required
def my():
    service.update_completed_reservations()
    reservations = (
        Reservation.query.filter_by(user_id=current_user.id)
        .order_by(Reservation.date.desc(), Reservation.start_time.desc())
        .all()
    )
    return render_template("reservations/my.html", reservations=reservations)


@reservations_bp.route("/my-reservations/history")
@login_required
def history():
    service.update_completed_reservations()
    reservations = (
        Reservation.query.filter(
            Reservation.user_id == current_user.id,
            Reservation.status.in_(["cancelled", "completed"]),
        )
        .order_by(Reservation.date.desc(), Reservation.start_time.desc())
        .all()
    )
    return render_template("reservations/history.html", reservations=reservations)
