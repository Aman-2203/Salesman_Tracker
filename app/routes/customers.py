from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Customer, User
from app import db
from functools import wraps

customers_bp = Blueprint('customers', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('rep.dashboard'))
        return f(*args, **kwargs)
    return decorated


@customers_bp.route('/')
@login_required
def list_customers():
    q = request.args.get('q', '').strip()
    area_filter = request.args.get('area', '').strip()

    query = Customer.query
    if current_user.role != 'admin':
        query = query.filter_by(is_active=True)

    if q:
        search_pattern = f'%{q}%'
        query = query.filter(
            db.or_(
                Customer.name.ilike(search_pattern),
                Customer.area.ilike(search_pattern),
                Customer.phone.ilike(search_pattern)
            )
        )

    if area_filter:
        query = query.filter(Customer.area == area_filter)

    customers = query.order_by(Customer.name).all()

    # Distinct non-empty areas for quick filter dropdown
    all_areas = db.session.query(Customer.area).filter(Customer.area != None, Customer.area != '').distinct().all()
    areas = sorted([a[0] for a in all_areas if a[0]])

    return render_template(
        'customers/list.html',
        customers=customers,
        areas=areas,
        selected_q=q,
        selected_area=area_filter
    )


@customers_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_customer():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        area = request.form.get('area', '').strip() or None
        phone = request.form.get('phone', '').strip() or None

        if not name:
            flash('Customer name is required.', 'danger')
        else:
            c = Customer(name=name, area=area, phone=phone)
            db.session.add(c)
            db.session.commit()
            flash(f'Customer {name} added!', 'success')
            return redirect(url_for('customers.list_customers'))

    return render_template('customers/new_customer.html')


@customers_bp.route('/<int:cid>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_customer(cid):
    c = Customer.query.get_or_404(cid)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Customer name is required.', 'danger')
        else:
            c.name = name
            c.area = request.form.get('area', '').strip() or None
            c.phone = request.form.get('phone', '').strip() or None
            db.session.commit()
            flash(f'Customer {c.name} updated.', 'success')
            return redirect(url_for('customers.list_customers'))

    return render_template('customers/edit_customer.html', customer=c)


@customers_bp.route('/<int:cid>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_customer(cid):
    c = Customer.query.get_or_404(cid)
    c.is_active = not c.is_active
    db.session.commit()
    flash(f'Customer {"activated" if c.is_active else "deactivated"}.', 'success')
    return redirect(url_for('customers.list_customers'))
