from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.models import User, Customer, Visit, Order, Attendance, Payment, RepLocation, BeatRoute
from app import db
from app.timezone_utils import now_ist, today_ist
from datetime import datetime, date, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    today = today_ist()
    total_reps = User.query.filter_by(role='rep', is_active=True).count()
    total_customers = Customer.query.filter_by(is_active=True).count()

    today_visits = Visit.query.filter(Visit.visit_date == today).count()

    today_orders = Order.query.filter(Order.order_date == today, Order.status != 'no_order').count()
    today_order_value = db.session.query(func.sum(Order.total_amount)).filter(
        Order.order_date == today,
        Order.status != 'no_order'
    ).scalar() or 0

    today_collections = Payment.query.filter(Payment.collection_date == today).count()
    today_collection_value = db.session.query(func.sum(Payment.cheque_amount)).filter(
        Payment.collection_date == today
    ).scalar() or 0

    today_attendance = db.session.query(Attendance.rep_id).filter(
        Attendance.attendance_date == today,
        Attendance.day_start != None
    ).distinct().count()

    # Weekly stats
    week_start = today - timedelta(days=today.weekday())
    weekly_orders_value = db.session.query(func.sum(Order.total_amount)).filter(
        Order.order_date >= week_start,
        Order.status != 'no_order'
    ).scalar() or 0

    # Recent visits with rep and customer info
    recent_visits = Visit.query.order_by(Visit.check_in_time.desc(), Visit.id.desc()).limit(10).all()

    # Live rep locations (last 30 mins)
    thirty_mins_ago = datetime.utcnow() - timedelta(minutes=30)
    live_locations = RepLocation.query.filter(
        RepLocation.timestamp >= thirty_mins_ago
    ).all()

    # Rep activity summary
    reps = User.query.filter_by(role='rep', is_active=True).all()
    rep_activity = []
    for rep in reps:
        active_att = Attendance.query.filter_by(rep_id=rep.id, day_end=None).order_by(Attendance.id.desc()).first()
        latest_att = Attendance.query.filter_by(rep_id=rep.id, attendance_date=today).order_by(Attendance.id.desc()).first()
        att = active_att or latest_att
        visits_today = Visit.query.filter_by(rep_id=rep.id, visit_date=today).count()
        orders_today = Order.query.filter(Order.rep_id == rep.id, Order.order_date == today, Order.status != 'no_order').count()
        last_visit = Visit.query.filter(
            Visit.rep_id == rep.id,
            Visit.check_in_time != None
        ).order_by(Visit.check_in_time.desc()).first()
        rep_activity.append({
            'rep': rep,
            'attendance': att,
            'visits_today': visits_today,
            'orders_today': orders_today,
            'last_visit': last_visit
        })
    return render_template('admin/dashboard.html',
        total_reps=total_reps,
        total_customers=total_customers,
        today_visits=today_visits,
        today_orders=today_orders,
        today_order_value=today_order_value,
        today_collections=today_collections,
        today_collection_value=today_collection_value,
        today_attendance=today_attendance,
        weekly_orders_value=weekly_orders_value,
        recent_visits=recent_visits,
        live_locations=live_locations,
        rep_activity=rep_activity,
        today=today
    )


@admin_bp.route('/team')
@login_required
@admin_required
def team():
    reps = User.query.filter_by(role='rep').order_by(User.name).all()
    today = today_ist()
    rep_data = []
    for rep in reps:
        active_att = Attendance.query.filter_by(rep_id=rep.id, day_end=None).order_by(Attendance.id.desc()).first()
        latest_att = Attendance.query.filter_by(rep_id=rep.id, attendance_date=today).order_by(Attendance.id.desc()).first()
        att = active_att or latest_att
        visits_today = Visit.query.filter_by(rep_id=rep.id, visit_date=today).count()
        total_customers = Customer.query.filter_by(assigned_rep_id=rep.id, is_active=True).count()
        last_visit = Visit.query.filter(
            Visit.rep_id == rep.id,
            Visit.check_in_time != None
        ).order_by(Visit.check_in_time.desc()).first()
        rep_data.append({'rep': rep, 'attendance': att, 'visits_today': visits_today,
                         'total_customers': total_customers, 'last_visit': last_visit})
    return render_template('admin/team.html', rep_data=rep_data, today=today)


@admin_bp.route('/team/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_rep():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'rep')

        if not name or not email or not password:
            flash('Name, email and password are required.', 'danger')
            return render_template('admin/add_rep.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/add_rep.html')

        user = User(name=name, email=email, phone=phone, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'User {name} created successfully.', 'success')
        return redirect(url_for('admin.team'))

    return render_template('admin/add_rep.html')


@admin_bp.route('/team/<int:rep_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_rep(rep_id):
    rep = User.query.get_or_404(rep_id)
    rep.is_active = not rep.is_active
    db.session.commit()
    status = 'activated' if rep.is_active else 'deactivated'
    flash(f'{rep.name} has been {status}.', 'success')
    return redirect(url_for('admin.team'))


@admin_bp.route('/reports/visits')
@login_required
@admin_required
def reports_visits():
    rep_id = request.args.get('rep_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Visit.query
    if rep_id:
        query = query.filter_by(rep_id=rep_id)
    if start_date:
        query = query.filter(Visit.visit_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Visit.visit_date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    visits = query.order_by(Visit.visit_date.desc(), Visit.created_at.desc()).limit(200).all()
    reps = User.query.filter_by(role='rep').all()
    return render_template('admin/reports_visits.html', visits=visits, reps=reps,
                           rep_id=rep_id, start_date=start_date, end_date=end_date)


@admin_bp.route('/reports/orders')
@login_required
@admin_required
def reports_orders():
    rep_id = request.args.get('rep_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Order.query
    if rep_id:
        query = query.filter_by(rep_id=rep_id)
    if start_date:
        query = query.filter(Order.order_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Order.order_date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    orders = query.order_by(Order.order_date.desc()).limit(200).all()
    total_value = sum(o.total_amount for o in orders if o.status != 'no_order')
    reps = User.query.filter_by(role='rep').all()
    return render_template('admin/reports_orders.html', orders=orders, reps=reps,
                           total_value=total_value, rep_id=rep_id,
                           start_date=start_date, end_date=end_date)


@admin_bp.route('/reports/attendance')
@login_required
@admin_required
def reports_attendance():
    rep_id = request.args.get('rep_id', type=int)
    month = request.args.get('month', today_ist().strftime('%Y-%m'))

    query = Attendance.query
    if rep_id:
        query = query.filter_by(rep_id=rep_id)
    if month:
        year, m = month.split('-')
        query = query.filter(
            func.strftime('%Y', Attendance.attendance_date) == year,
            func.strftime('%m', Attendance.attendance_date) == m
        )

    records = query.order_by(Attendance.attendance_date.desc(), Attendance.day_start.desc(), Attendance.id.desc()).all()
    reps = User.query.filter_by(role='rep').all()
    return render_template('admin/reports_attendance.html', records=records, reps=reps,
                           rep_id=rep_id, month=month)
