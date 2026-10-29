from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models import User, Visit, Attendance, Order
from app import db
from datetime import datetime

api_bp = Blueprint('api', __name__)


@api_bp.route('/location/update', methods=['POST'])
@login_required
def update_location():
    """No-op: background GPS tracking has been removed."""
    return jsonify({'status': 'disabled', 'message': 'Continuous background tracking removed'})


@api_bp.route('/locations/live')
@login_required
def live_locations():
    """Get all rep visit locations for the admin live map."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    reps = User.query.filter_by(role='rep', is_active=True).all()
    result = []
    for rep in reps:
        # Get latest visit with coordinates
        visit = Visit.query.filter(
            Visit.rep_id == rep.id,
            Visit.check_in_lat != None,
            Visit.check_in_lng != None
        ).order_by(Visit.check_in_time.desc(), Visit.id.desc()).first()

        if visit:
            att = Attendance.query.filter_by(
                rep_id=rep.id,
                day_end=None
            ).first()
            result.append({
                'rep_id': rep.id,
                'name': rep.name,
                'lat': visit.check_in_lat,
                'lng': visit.check_in_lng,
                'timestamp': visit.check_in_time.isoformat() if visit.check_in_time else datetime.utcnow().isoformat(),
                'last_seen_customer': visit.customer.name if visit.customer else 'Customer',
                'is_active': att is not None
            })
    return jsonify(result)


@api_bp.route('/stats/today')
@login_required
def today_stats():
    today = datetime.utcnow().date()
    data = {
        'visits_today': Visit.query.filter_by(visit_date=today).count(),
        'orders_today': Order.query.filter(Order.order_date == today, Order.status != 'no_order').count(),
        'reps_active': db.session.query(Attendance.rep_id).filter(
            Attendance.attendance_date == today,
            Attendance.day_start != None,
            Attendance.day_end == None
        ).distinct().count(),
    }
    return jsonify(data)
