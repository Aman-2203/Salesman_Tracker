from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Attendance, User
from app import db
from app.timezone_utils import now_ist, today_ist
from datetime import datetime, date

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/')
@login_required
def list_attendance():
    date_filter = request.args.get('date', '').strip()
    rep_filter = request.args.get('rep_id', type=int)

    query = Attendance.query
    if current_user.role != 'admin':
        query = query.filter(Attendance.rep_id == current_user.id)
    elif rep_filter:
        query = query.filter(Attendance.rep_id == rep_filter)

    if date_filter:
        try:
            if '/' in date_filter:
                parts = date_filter.split('/')
                parsed_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
            else:
                parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Attendance.attendance_date == parsed_date)
        except Exception:
            pass

    records = query.order_by(
        Attendance.attendance_date.desc(), Attendance.day_start.desc(), Attendance.id.desc()
    ).limit(200).all()

    reps = User.query.filter_by(role='rep', is_active=True).order_by(User.name).all() if current_user.role == 'admin' else []

    return render_template(
        'attendance/list.html',
        records=records,
        reps=reps,
        selected_date=date_filter,
        selected_rep=rep_filter
    )


@attendance_bp.route('/start', methods=['POST'])
@login_required
def day_start():
    today = today_ist()
    # Check if user already has an active ongoing session
    active = Attendance.query.filter_by(rep_id=current_user.id, day_end=None).first()
    if active:
        flash('You already have an active session running. Please end it before starting a new one.', 'warning')
        return redirect(url_for('rep.dashboard'))

    lat = request.form.get('lat', type=float)
    lng = request.form.get('lng', type=float)

    att = Attendance(
        rep_id=current_user.id,
        attendance_date=today,
        day_start=now_ist(),
        start_lat=lat,
        start_lng=lng,
        status='present'
    )
    db.session.add(att)
    db.session.commit()

    today_count = Attendance.query.filter_by(rep_id=current_user.id, attendance_date=today).count()
    if today_count > 1:
        flash(f'Session #{today_count} started! Have a productive session!', 'success')
    else:
        flash('Day started! Have a productive day!', 'success')
    return redirect(url_for('rep.dashboard'))


@attendance_bp.route('/end', methods=['POST'])
@login_required
def day_end():
    today = today_ist()
    # Find currently active session
    active = Attendance.query.filter_by(
        rep_id=current_user.id,
        day_end=None
    ).order_by(Attendance.id.desc()).first()

    if not active:
        flash('No active session found to end.', 'warning')
        return redirect(url_for('rep.dashboard'))

    lat = request.form.get('lat', type=float)
    lng = request.form.get('lng', type=float)

    active.day_end = now_ist()
    active.end_lat = lat
    active.end_lng = lng
    db.session.commit()

    today_sessions = Attendance.query.filter_by(rep_id=current_user.id, attendance_date=today).all()
    total_hours = round(sum(s.hours_worked() for s in today_sessions), 2)
    flash(f'Session ended ({active.hours_worked()}h). Total today: {total_hours}h across {len(today_sessions)} session(s). You can start again anytime.', 'success')
    return redirect(url_for('rep.dashboard'))
