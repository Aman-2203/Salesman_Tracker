from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Visit, Customer, Order, Payment, Attendance, User
from app import db
from app.timezone_utils import now_ist, today_ist
from datetime import datetime, date
import uuid

visits_bp = Blueprint('visits', __name__)


@visits_bp.route('/')
@login_required
def list_visits():
    today = today_ist()
    q = request.args.get('q', '').strip()
    outcome = request.args.get('outcome', '').strip()
    date_filter = request.args.get('date', '').strip()
    rep_filter = request.args.get('rep_id', type=int)

    query = Visit.query
    if current_user.role != 'admin':
        query = query.filter(Visit.rep_id == current_user.id)
    elif rep_filter:
        query = query.filter(Visit.rep_id == rep_filter)

    if outcome:
        query = query.filter(Visit.outcome == outcome)

    if date_filter:
        try:
            # Handle dd/mm/yyyy or yyyy-mm-dd
            if '/' in date_filter:
                parts = date_filter.split('/')
                parsed_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
            else:
                parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Visit.visit_date == parsed_date)
        except Exception:
            pass

    if q:
        search_pattern = f'%{q}%'
        query = query.join(Customer).filter(
            db.or_(
                Customer.name.ilike(search_pattern),
                Customer.area.ilike(search_pattern),
                Customer.phone.ilike(search_pattern),
                Visit.notes.ilike(search_pattern)
            )
        )

    visits = query.order_by(Visit.visit_date.desc(), Visit.check_in_time.desc(), Visit.id.desc()).limit(200).all()
    reps = User.query.filter_by(role='rep', is_active=True).order_by(User.name).all() if current_user.role == 'admin' else []

    return render_template(
        'visits/list.html',
        visits=visits,
        today=today,
        reps=reps,
        selected_q=q,
        selected_outcome=outcome,
        selected_date=date_filter,
        selected_rep=rep_filter
    )


@visits_bp.route('/new', methods=['GET', 'POST'])
@visits_bp.route('/record', methods=['GET', 'POST'])
@login_required
def record_visit():
    """Unified Visit -> Order -> Payment Collection workflow."""
    if current_user.role == 'rep':
        active_attendance = Attendance.query.filter_by(
            rep_id=current_user.id,
            day_end=None
        ).first()
        if not active_attendance:
            flash('Please start your day before recording customer visits.', 'warning')
            return redirect(url_for('rep.dashboard'))

    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        if not customer_id:
            flash('Please select a customer.', 'danger')
            return redirect(url_for('visits.record_visit'))

        customer = Customer.query.get_or_404(customer_id)
        lat = request.form.get('lat', type=float)
        lng = request.form.get('lng', type=float)
        outcome = request.form.get('outcome', 'met')
        notes = request.form.get('notes', '').strip()

        now = now_ist()
        today = today_ist()

        # 1. Create Visit Record with location & time in GMT+5:30
        visit = Visit(
            rep_id=current_user.id,
            customer_id=customer_id,
            visit_date=today,
            check_in_time=now,
            check_in_lat=lat,
            check_in_lng=lng,
            check_out_time=now,
            check_out_lat=lat,
            check_out_lng=lng,
            status='completed',
            outcome=outcome,
            notes=notes
        )
        db.session.add(visit)
        db.session.flush()

        messages = [f'Visit to {customer.name} recorded!']

        # 2. Unified Order Booking (if placed)
        order_placed = request.form.get('order_placed', 'no')
        if order_placed == 'yes':
            order_amount = request.form.get('order_amount', type=float) or 0.0
            order = Order(
                rep_id=current_user.id,
                customer_id=customer_id,
                order_date=today,
                order_number=f'ORD-{now.strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}',
                total_amount=order_amount,
                status='confirmed',
                notes=f'From Visit #{visit.id}: {notes}' if notes else f'From Visit #{visit.id}'
            )
            order.items = []
            db.session.add(order)
            messages.append(f'Order booked (₹{order_amount:,.2f})')

        # 3. Unified Payment / Cheque Collection (if collected)
        payment_collected = request.form.get('payment_collected', 'no')
        if payment_collected == 'yes':
            payment_amount = request.form.get('payment_amount', type=float) or 0.0
            cheque_number = request.form.get('cheque_number', '').strip() or f'COL-{now.strftime("%H%M%S")}'
            bank_name = request.form.get('bank_name', '').strip()
            payment = Payment(
                rep_id=current_user.id,
                customer_id=customer_id,
                collection_date=today,
                cheque_number=cheque_number,
                cheque_amount=payment_amount,
                cheque_date=today,
                bank_name=bank_name,
                notes=f'From Visit #{visit.id}: {notes}' if notes else f'From Visit #{visit.id}'
            )
            db.session.add(payment)
            messages.append(f'Collection recorded (₹{payment_amount:,.2f})')

        db.session.commit()
        flash(' · '.join(messages), 'success')
        return redirect(url_for('rep.dashboard'))

    # GET Request: ANY salesman can see and visit ANY customer
    selected_customer_id = request.args.get('customer_id', type=int)
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()

    return render_template(
        'visits/record_visit.html',
        customers=customers,
        selected_customer_id=selected_customer_id,
        today=today_ist()
    )


@visits_bp.route('/mark/<int:visit_id>', methods=['GET', 'POST'])
@login_required
def mark_visit(visit_id):
    """Backwards compatibility: redirect to record visit with customer pre-selected."""
    visit = Visit.query.get_or_404(visit_id)
    return redirect(url_for('visits.record_visit', customer_id=visit.customer_id))


@visits_bp.route('/plan', methods=['GET', 'POST'])
@login_required
def plan_beat():
    """Beat planning removed: redirect to direct visit recording."""
    return redirect(url_for('visits.record_visit'))
