from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Order, Customer, User
from app import db
from app.timezone_utils import now_ist, today_ist
from datetime import datetime, date
import uuid

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/')
@login_required
def list_orders():
    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    date_filter = request.args.get('date', '').strip()
    rep_filter = request.args.get('rep_id', type=int)

    query = Order.query
    if current_user.role != 'admin':
        query = query.filter(Order.rep_id == current_user.id)
    elif rep_filter:
        query = query.filter(Order.rep_id == rep_filter)

    if status_filter:
        query = query.filter(Order.status == status_filter)

    if date_filter:
        try:
            if '/' in date_filter:
                parts = date_filter.split('/')
                parsed_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
            else:
                parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Order.order_date == parsed_date)
        except Exception:
            pass

    if q:
        search_pattern = f'%{q}%'
        query = query.join(Customer).filter(
            db.or_(
                Order.order_number.ilike(search_pattern),
                Customer.name.ilike(search_pattern),
                Order.notes.ilike(search_pattern)
            )
        )

    orders = query.order_by(Order.order_date.desc(), Order.id.desc()).limit(200).all()
    reps = User.query.filter_by(role='rep', is_active=True).order_by(User.name).all() if current_user.role == 'admin' else []

    return render_template(
        'orders/list.html',
        orders=orders,
        reps=reps,
        selected_q=q,
        selected_status=status_filter,
        selected_date=date_filter,
        selected_rep=rep_filter
    )


@orders_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_order():
    if current_user.role == 'rep':
        flash('Orders can only be recorded during a customer visit.', 'info')
        return redirect(url_for('visits.record_visit'))

    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        order_placed = request.form.get('order_placed')  # 'yes' or 'no'
        amount = request.form.get('amount', type=float) or 0.0
        notes = request.form.get('notes', '')

        status = 'confirmed' if order_placed == 'yes' else 'no_order'
        now = now_ist()
        today = today_ist()

        order = Order(
            rep_id=current_user.id,
            customer_id=customer_id,
            order_date=today,
            order_number=f'ORD-{now.strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}',
            total_amount=amount,
            notes=notes,
            status=status
        )
        order.items = []
        db.session.add(order)
        db.session.commit()
        flash(f'Order {order.order_number} recorded successfully!', 'success')
        return redirect(url_for('orders.list_orders'))

    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    return render_template('orders/new_order.html', customers=customers)


@orders_bp.route('/<int:order_id>')
@login_required
def view_order(order_id):
    order = Order.query.get_or_404(order_id)
    if current_user.role != 'admin' and order.rep_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('orders.list_orders'))
    return render_template('orders/view_order.html', order=order)


@orders_bp.route('/<int:order_id>/status', methods=['POST'])
@login_required
def update_status(order_id):
    if current_user.role != 'admin':
        flash('Admin only.', 'danger')
        return redirect(url_for('orders.list_orders'))
    order = Order.query.get_or_404(order_id)
    order.status = request.form.get('status', order.status)
    db.session.commit()
    flash('Order status updated.', 'success')
    return redirect(url_for('orders.view_order', order_id=order_id))
