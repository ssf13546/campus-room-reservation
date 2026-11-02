from datetime import date

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.forms import parse_date
from app.models import Room
from app.services import reservation_service as service

rooms_bp = Blueprint("rooms", __name__)


@rooms_bp.route("/")
@rooms_bp.route("/rooms")
@login_required
def index():
    rooms = Room.query.order_by(Room.id).all()
    return render_template("rooms/list.html", rooms=rooms)


@rooms_bp.route("/rooms/<int:room_id>")
@login_required
def detail(room_id):
    room = Room.query.get_or_404(room_id)
    d = parse_date(request.args.get("date")) or date.today()
    slots = service.slot_grid(room.id, d)
    return render_template("rooms/detail.html", room=room, date=d, slots=slots)
