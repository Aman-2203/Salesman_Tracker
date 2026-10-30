from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.models import User, Customer, Visit, Order, Attendance, Payment, RepLocation
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
    timeframe = request.args.get('timeframe', 'today')

    week_start = today - timedelta(days=today.weekday())
    month_start = date(today.year, today.month, 1)

    # Base visit filters based on timeframe
    if timeframe == 'week':
        time_label = 'This Week'
        visit_date_filter = Visit.visit_date >= week_start
    elif timeframe == 'month':
        time_label = 'This Month'
        visit_date_filter = Visit.visit_date >= month_start
    elif timeframe == 'all':
        time_label = 'All Time'
        visit_date_filter = True
    else:
        timeframe = 'today'
        time_label = "Today's"
        visit_date_filter = Visit.visit_date == today

    total_reps = User.query.filter_by(role='rep', is_active=True).count()
    total_customers = Customer.query.filter_by(is_active=True).count()

    # Core 3 Insights
    # 1. Order Strike Rate (Visits with Order / Met Visits)
    scoped_visits = Visit.query.filter(visit_date_filter)
    total_scoped_visits = scoped_visits.count()
    total_met_visits = scoped_visits.filter(Visit.outcome == 'met').count()
    total_order_visits = scoped_visits.filter(Visit.has_order == True).count()
    team_strike_rate = round((total_order_visits / total_met_visits * 100), 1) if total_met_visits > 0 else 0.0

    # 2. Dual-Hit Index (Both Order + Payment in same visit)
    total_dual_hits = scoped_visits.filter(Visit.has_order == True, Visit.has_payment == True).count()

    # 3. Pure Debt Recovery Visits (Cash Rescue: Payment = Yes, Order = No)
    total_cash_rescues = scoped_visits.filter(Visit.has_payment == True, Visit.has_order == False).count()

    # General Attendance & Order Stats
    today_attendance = db.session.query(Attendance.rep_id).filter(
        Attendance.attendance_date == today,
        Attendance.day_start != None
    ).distinct().count()

    today_orders = Order.query.filter(Order.order_date == today, Order.status != 'no_order').count()
    today_collections = Payment.query.filter(Payment.collection_date == today).count()

    # Recent visits
    recent_visits = Visit.query.order_by(Visit.check_in_time.desc(), Visit.id.desc()).limit(10).all()

    # Live rep locations
    thirty_mins_ago = datetime.utcnow() - timedelta(minutes=30)
    live_locations = RepLocation.query.filter(
        RepLocation.timestamp >= thirty_mins_ago
    ).all()

    # Rep Scorecard with Strike Rate, Dual-Hits & Cash Rescues
    reps = User.query.filter_by(role='rep', is_active=True).order_by(User.name).all()
    rep_activity = []
    for rep in reps:
        active_att = Attendance.query.filter_by(rep_id=rep.id, day_end=None).order_by(Attendance.id.desc()).first()
        latest_att = Attendance.query.filter_by(rep_id=rep.id, attendance_date=today).order_by(Attendance.id.desc()).first()
        att = active_att or latest_att

        rep_scoped = Visit.query.filter(Visit.rep_id == rep.id, visit_date_filter)
        visits_count = rep_scoped.count()
        met_count = rep_scoped.filter(Visit.outcome == 'met').count()
        orders_secured = rep_scoped.filter(Visit.has_order == True).count()
        dual_hits = rep_scoped.filter(Visit.has_order == True, Visit.has_payment == True).count()
        cash_rescues = rep_scoped.filter(Visit.has_payment == True, Visit.has_order == False).count()
        strike_rate = round((orders_secured / met_count * 100), 1) if met_count > 0 else 0.0

        last_visit = Visit.query.filter(
            Visit.rep_id == rep.id,
            Visit.check_in_time != None
        ).order_by(Visit.check_in_time.desc()).first()

        rep_activity.append({
            'rep': rep,
            'attendance': att,
            'visits_count': visits_count,
            'met_count': met_count,
            'orders_secured': orders_secured,
            'strike_rate': strike_rate,
            'dual_hits': dual_hits,
            'cash_rescues': cash_rescues,
            'last_visit': last_visit
        })

    # Sort scorecard by strike rate and dual-hits descending
    rep_activity.sort(key=lambda x: (x['dual_hits'], x['strike_rate'], x['orders_secured']), reverse=True)

    return render_template('admin/dashboard.html',
        total_reps=total_reps,
        total_customers=total_customers,
        timeframe=timeframe,
        time_label=time_label,
        total_scoped_visits=total_scoped_visits,
        total_met_visits=total_met_visits,
        total_order_visits=total_order_visits,
        team_strike_rate=team_strike_rate,
        total_dual_hits=total_dual_hits,
        total_cash_rescues=total_cash_rescues,
        today_attendance=today_attendance,
        today_orders=today_orders,
        today_collections=today_collections,
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
    visit_type = request.args.get('visit_type', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Visit.query
    if rep_id:
        query = query.filter_by(rep_id=rep_id)
    if visit_type == 'dual_hit':
        query = query.filter(Visit.has_order == True, Visit.has_payment == True)
    elif visit_type == 'cash_rescue':
        query = query.filter(Visit.has_payment == True, Visit.has_order == False)
    elif visit_type == 'order_only':
        query = query.filter(Visit.has_order == True, Visit.has_payment == False)
    if start_date:
        query = query.filter(Visit.visit_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Visit.visit_date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    visits = query.order_by(Visit.visit_date.desc(), Visit.created_at.desc()).limit(200).all()
    reps = User.query.filter_by(role='rep').all()
    return render_template('admin/reports_visits.html', visits=visits, reps=reps,
                           rep_id=rep_id, visit_type=visit_type, start_date=start_date, end_date=end_date)


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
        try:
            year, m = map(int, month.split('-'))
            import calendar
            _, last_day = calendar.monthrange(year, m)
            start_d = date(year, m, 1)
            end_d = date(year, m, last_day)
            query = query.filter(Attendance.attendance_date >= start_d, Attendance.attendance_date <= end_d)
        except Exception:
            pass

    records = query.order_by(Attendance.attendance_date.desc(), Attendance.day_start.desc(), Attendance.id.desc()).all()
    reps = User.query.filter_by(role='rep').all()
    return render_template('admin/reports_attendance.html', records=records, reps=reps,
                           rep_id=rep_id, month=month)
