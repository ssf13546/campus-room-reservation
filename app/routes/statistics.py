from flask import Blueprint, jsonify
from flask_login import login_required

from app.routes.admin import admin_required
from app.services import reservation_service as service

statistics_bp = Blueprint("statistics", __name__, url_prefix="/api/statistics")


@statistics_bp.route("/reservation-count")
@login_required
@admin_required
def reservation_count():
    return jsonify(service.reservation_count_by_room())


@statistics_bp.route("/room-usage")
@login_required
@admin_required
def room_usage():
    return jsonify(service.usage_rate_by_room())


@statistics_bp.route("/status")
@login_required
@admin_required
def status():
    return jsonify(service.status_distribution())


@statistics_bp.route("/time-heat")
@login_required
@admin_required
def time_heat():
    return jsonify(service.time_heat())
