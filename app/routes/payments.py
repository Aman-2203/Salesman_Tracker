from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Payment, Customer, User
from app import db
from app.timezone_utils import today_ist
from datetime import datetime, date

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/')
@login_required
def list_payments():
    q = request.args.get('q', '').strip()
    date_filter = request.args.get('date', '').strip()
    rep_filter = request.args.get('rep_id', type=int)

    query = Payment.query
    if current_user.role != 'admin':
        query = query.filter(Payment.rep_id == current_user.id)
    elif rep_filter:
        query = query.filter(Payment.rep_id == rep_filter)

    if date_filter:
        try:
            if '/' in date_filter:
                parts = date_filter.split('/')
                parsed_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
            else:
                parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Payment.collection_date == parsed_date)
        except Exception:
            pass

    if q:
        search_pattern = f'%{q}%'
        query = query.join(Customer).filter(
            db.or_(
                Payment.cheque_number.ilike(search_pattern),
                Customer.name.ilike(search_pattern),
                Payment.bank_name.ilike(search_pattern),
                Payment.notes.ilike(search_pattern)
            )
        )

    payments = query.order_by(Payment.collection_date.desc(), Payment.id.desc()).limit(200).all()
    total = sum(p.cheque_amount for p in payments)
    reps = User.query.filter_by(role='rep', is_active=True).order_by(User.name).all() if current_user.role == 'admin' else []

    return render_template(
        'payments/list.html',
        payments=payments,
        total=total,
        reps=reps,
        selected_q=q,
        selected_date=date_filter,
        selected_rep=rep_filter
    )


@payments_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_payment():
    if current_user.role == 'rep':
        flash('Payment collections can only be recorded during a customer visit.', 'info')
        return redirect(url_for('visits.record_visit'))

    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        cheque_number = request.form.get('cheque_number', '').strip()
        cheque_amount = request.form.get('cheque_amount', type=float)
        cheque_date_str = request.form.get('cheque_date', '')
        bank_name = request.form.get('bank_name', '').strip()
        notes = request.form.get('notes', '').strip()

        if not all([customer_id, cheque_number, cheque_amount, cheque_date_str]):
            flash('All required fields must be filled.', 'danger')
        else:
            try:
                if '/' in cheque_date_str:
                    parts = cheque_date_str.split('/')
                    cheque_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
                else:
                    cheque_date = datetime.strptime(cheque_date_str, '%Y-%m-%d').date()
            except Exception:
                cheque_date = today_ist()

            payment = Payment(
                rep_id=current_user.id,
                customer_id=customer_id,
                collection_date=today_ist(),
                cheque_number=cheque_number,
                cheque_amount=cheque_amount,
                cheque_date=cheque_date,
                bank_name=bank_name,
                notes=notes
            )
            db.session.add(payment)
            db.session.commit()
            flash(f'Payment collection of ₹{cheque_amount:,.2f} recorded!', 'success')
            return redirect(url_for('payments.list_payments'))

    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    return render_template('payments/new_payment.html', customers=customers)
