from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Visit, Order, Attendance, Customer, Payment
from app import db
from app.timezone_utils import now_ist, today_ist
from datetime import datetime, date

rep_bp = Blueprint('rep', __name__)


def rep_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@rep_bp.route('/dashboard')
@login_required
def dashboard():
    today = today_ist()

    # Today's attendance sessions
    active_attendance = Attendance.query.filter_by(
        rep_id=current_user.id,
        day_end=None
    ).order_by(Attendance.id.desc()).first()

    today_attendances = Attendance.query.filter_by(
        rep_id=current_user.id,
        attendance_date=today
    ).order_by(Attendance.day_start.asc()).all()

    total_hours_today = round(sum(a.hours_worked() for a in today_attendances), 2)
    attendance = active_attendance or (today_attendances[-1] if today_attendances else None)

    # Today's logged visits (ordered most recent first)
    today_visits = Visit.query.filter_by(
        rep_id=current_user.id,
        visit_date=today
    ).order_by(Visit.check_in_time.desc(), Visit.id.desc()).all()

    # Today's orders
    today_orders = Order.query.filter_by(rep_id=current_user.id, order_date=today).all()
    today_order_value = sum(o.total_amount for o in today_orders if o.status != 'no_order')

    # Today's collections
    today_payments = Payment.query.filter_by(rep_id=current_user.id, collection_date=today).all()
    today_payment_value = sum(p.cheque_amount for p in today_payments)

    # All active customers (open to all salesmen)
    my_customers = Customer.query.filter_by(is_active=True).all()

    return render_template('rep/dashboard.html',
        attendance=attendance,
        active_attendance=active_attendance,
        today_attendances=today_attendances,
        total_hours_today=total_hours_today,
        today_visits=today_visits,
        today_orders=today_orders,
        today_order_value=today_order_value,
        today_payments=today_payments,
        today_payment_value=today_payment_value,
        my_customers=my_customers,
        today=today
    )
