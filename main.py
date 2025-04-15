from collections import Counter
from datetime import timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):  # пользователь
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    in_cart = db.Column(db.String, default='')


class Products(db.Model):  # товар
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    rating = db.Column(db.Float)
    owner = db.Column(db.String(50))
    category = db.Column(db.String(30))
    image_url = db.Column(db.String(200))
    price = db.Column(db.Integer)


class Orders(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Integer, nullable=False)
    products = db.Column(db.Text, nullable=False)
    man_id = db.Column(db.Integer, nullable=False)


@app.template_filter('format_price')
def format_price(value):
    try:
        return f"{int(value):,}".replace(',', ' ')
    except (ValueError, TypeError):
        return value


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('market'))
    return render_template('index.html')


@app.route('/market', methods=['GET', 'POST'])
def market():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        user = User.query.filter_by(id=session['id']).first()
        if len(user.in_cart) > 0:
            user.in_cart += ' ' + product_id
        else:
            user.in_cart = product_id
        db.session.commit()
    if 'username' not in session:
        return redirect(url_for('login'))

    products = Products.query.all()
    categories = db.session.query(Products.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('market.html',
                           products=products,
                           categories=categories, username=session['username'])


@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product(product_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    product = Products.query.get_or_404(product_id)
    if request.method == 'POST':
        product_id = str(product.id)
        user = User.query.filter_by(id=session['id']).first()
        print(123)
        if len(user.in_cart) > 0:
            user.in_cart += ' ' + product_id
        else:
            user.in_cart = product_id
        db.session.commit()

    return render_template('product.html', product=product)


@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['id']).first()

    counts = user.in_cart.split() if user.in_cart else []
    product_counts = dict(Counter(counts))
    product_counts = {int(key): int(value) for key, value in product_counts.items()}

    if request.method == 'POST':
        selected_products = request.form.getlist('selected_products')
        session['selected_products'] = selected_products

        if 'increase' in request.form:
            product_id = request.form['increase']
            user.in_cart += ' ' + product_id
            product_counts[int(product_id)] += 1

        elif 'decrease' in request.form:
            product_id = request.form['decrease']
            cart_items = user.in_cart.split()
            if product_id in cart_items:
                cart_items.remove(product_id)
                user.in_cart = ' '.join(cart_items)
                product_counts[int(product_id)] -= 1

        elif 'remove' in request.form:
            product_id = request.form['remove']
            user.in_cart = ' '.join([p for p in user.in_cart.split() if p != product_id])
            flash('Товар удалён из корзины.', 'info')
            if 'selected_products' in session and product_id in session['selected_products']:
                session['selected_products'].remove(product_id)

        elif 'remove_selected' in request.form:
            selected_to_ord = session.get('selected_products', [])
            print(selected_to_ord)
            if selected_to_ord:
                session['order_products'] = selected_to_ord
                selected_ids1 = session.get('order_products', [])
                user.in_cart = ' '.join([p for p in user.in_cart.split() if p not in selected_ids1])
                db.session.commit()
                flash('выбранные товары удалены из корзины', 'info')


        elif 'order_selected' in request.form:
            selected_to_ord = session.get('selected_products', [])
            print(selected_to_ord)
            if selected_to_ord:
                session['order_products'] = selected_to_ord
                return redirect(url_for('order'))

        db.session.commit()
        return redirect(url_for('cart'))

    cart_items = user.in_cart.split() if user.in_cart else []
    products = Products.query.filter(Products.id.in_([int(x) for x in cart_items])).all()

    selected_products = session.get('selected_products', [])

    return render_template('cart.html',
                           products=products,
                           product_counts=product_counts,
                           selected_products=selected_products, total=1)


@app.route('/order', methods=['GET', 'POST'])
def order():
    if 'username' not in session:
        return redirect(url_for('login'))

    selected_ids1 = session.get('order_products', [])
    selected_ids = [int(x) for x in selected_ids1]

    products = Products.query.filter(Products.id.in_(selected_ids)).all()

    user = User.query.filter_by(id=session['id']).first()

    counts = user.in_cart.split() if user.in_cart else []
    product_counts = dict(Counter(counts))
    product_counts = {int(key): int(value) for key, value in product_counts.items() if int(key) in selected_ids}
    total = 0
    for key, value in product_counts.items():
        total += value * Products.query.filter_by(id=key).first().price

    if request.method == 'POST':
        city = request.form.get('city')
        new_order = Orders(
            city=city,
            total=total,
            products=' '.join(','.join([str(key), str(value)]) for key, value in product_counts.items()),
            man_id=session['id']
        )
        db.session.add(new_order)
        user.in_cart = ' '.join([p for p in user.in_cart.split() if p not in selected_ids1])
        db.session.commit()
        return redirect(url_for('orders'))

    return render_template('order.html', name=session['username'], products=products, product_counts=product_counts,
                           total=total)


@app.route('/orders')
def orders():
    if 'username' not in session:
        return redirect(url_for('login'))

    orders = Orders.query.filter_by(man_id=session['id']).all()
    return render_template('orders.html', orders=orders, Products=Products, int=int)


@app.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_details(order_id):
    order = Orders.query.get_or_404(order_id)

    user = User.query.filter_by(id=order.man_id).first()

    if request.method == 'POST' and 'cancel' in request.form:
        db.session.delete(order)
        db.session.commit()
        flash('dаш заказ был отменен', 'success')
        return redirect(url_for('orders'))

    product_counts = {}
    for product_info in order.products.split():
        product_id, quantity = map(int, product_info.split(','))
        product_counts[product_id] = quantity

    return render_template('about_order.html', order=order, name=user.username, product_counts=product_counts,
                           Products=Products)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('имя пользователя занято', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, in_cart='')
        db.session.add(new_user)
        db.session.commit()

        flash('вы зарегистрированы, теперь можно войти', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session.permanent = True
            session['username'] = username
            session['id'] = user.id
            flash('Вы успешно вошли', 'success')
            return redirect(url_for('market'))

        flash('неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('id', None)
    flash('вы успешно вышли из системы.', 'info')
    return redirect(url_for('index'))


def create_db():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_db()
    app.run(port=8080, host='127.0.0.1', debug=True)
