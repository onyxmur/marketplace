import random
import re
from collections import Counter
from datetime import timedelta, datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября",
          "декабря"]


class User(db.Model):  # пользователь
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    phone_number = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    in_cart = db.Column(db.String, default='')
    liked_products = db.Column(db.Text, default='')


class Products(db.Model):  # товар
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    name_lower = db.Column(db.String)

    description = db.Column(db.Text)
    description_lower = db.Column(db.Text)

    rating = db.Column(db.Float)
    owner = db.Column(db.String)
    owner_lower = db.Column(db.String)

    category = db.Column(db.String)
    category_lower = db.Column(db.String)

    image_url = db.Column(db.String)
    price = db.Column(db.Integer)
    man_id = db.Column(db.Integer)
    is_delete = db.Column(db.Integer)


class Orders(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Integer, nullable=False)
    products = db.Column(db.Text, nullable=False)
    date = db.Column(db.Text)
    formated_date = db.Column(db.Text)
    man_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Text, nullable=False)
    date_done = db.Column(db.Text)
    formated_date_done = db.Column(db.Text)


class Reviews(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text)
    product_id = db.Column(db.Integer, nullable=False)
    man_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


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
    search_query = request.args.get('search')
    if search_query:
        return redirect(url_for('search', query=search_query))

    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['id']).first()
    categories = db.session.query(Products.category).distinct().all()
    categories = [c[0] for c in categories]

    owners = db.session.query(Products.owner).distinct().all()
    owners = [c[0] for c in owners]

    selected_category = request.args.get('category', '')
    selected_seller = request.args.get('seller', '')
    price_min = request.args.get('price_min', type=int, default=None)
    price_max = request.args.get('price_max', type=int, default=None)
    rating_min = request.args.get('rating_min', type=float, default=None)
    rating_max = request.args.get('rating_max', type=float, default=None)
    sort_filter = request.args.get('sort', 'id')
    session['url_back'] = ['market', selected_category, selected_seller, price_min, price_max, rating_min, rating_max,
                           sort_filter]

    query = Products.query
    if selected_category:
        query = query.filter_by(category=selected_category)

    if selected_seller:
        query = query.filter(Products.owner == selected_seller)

    if price_min is not None:
        query = query.filter(Products.price >= price_min)
    if price_max is not None:
        query = query.filter(Products.price <= price_max)

    if rating_min is not None:
        query = query.filter(Products.rating >= rating_min)
    if rating_max is not None:
        query = query.filter(Products.rating <= rating_max)

    if sort_filter == 'price':
        query = query.order_by(Products.price)
    elif sort_filter == 'rating':
        query = query.order_by(Products.rating.desc())
    else:
        query = query.order_by(Products.id)

    products = query.all()

    if request.method == 'POST':
        product_id = request.form.get('product_id')

        cart_items = user.in_cart.split() if user.in_cart else []

        if 'increase' in request.form:
            cart_items.append(product_id)
        elif 'decrease' in request.form:
            if product_id in cart_items:
                cart_items.remove(product_id)
        elif 'remove' in request.form:
            cart_items = [p for p in cart_items if p != product_id]
        else:
            cart_items.append(product_id)

        user.in_cart = ' '.join(cart_items)
        db.session.commit()

        return redirect(url_for('market', category=selected_category, seller=selected_seller, price_min=price_min,
                                price_max=price_max, rating_min=rating_min, rating_max=rating_max, sort=sort_filter))

    cart_items = user.in_cart.split() if user.in_cart else []
    product_counts = dict(Counter(cart_items))
    product_counts = {int(k): int(v) for k, v in product_counts.items()}
    liked_products = user.liked_products.split() if user.liked_products else []
    liked_products = [int(pid) for pid in liked_products]

    return render_template('market.html',
                           products=products,
                           categories=categories,
                           product_counts=product_counts,
                           username=session['username'],
                           selected_category=selected_category,
                           price_min=price_min,
                           price_max=price_max,
                           rating_min=rating_min,
                           rating_max=rating_max,
                           sort_filter=sort_filter,
                           owners=owners,
                           selected_seller=selected_seller,
                           liked_products=liked_products
                           )


@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product(product_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    product = Products.query.get_or_404(product_id)
    user = User.query.filter_by(id=session['id']).first()
    users = User.query.all()
    g = session.get('url_back', [])

    cart_items = user.in_cart.split() if user.in_cart else []
    product_counts = dict(Counter(cart_items))
    product_counts = {int(k): int(v) for k, v in product_counts.items()}
    count_in_cart = product_counts.get(product_id, 0)
    is_owner = product.man_id == user.id

    if request.method == 'POST':
        if 'add' in request.form:
            user.in_cart += f' {product_id}' if user.in_cart else str(product_id)
            db.session.commit()
            return redirect(url_for('product', product_id=product_id))

        if 'increase' in request.form:
            user.in_cart += f' {product_id}'
            db.session.commit()
            return redirect(url_for('product', product_id=product_id))

        if 'decrease' in request.form:
            items = user.in_cart.split()
            if str(product_id) in items:
                items.remove(str(product_id))
                user.in_cart = ' '.join(items)
                db.session.commit()
            return redirect(url_for('product', product_id=product_id))

        if 'remove' in request.form:
            user.in_cart = ' '.join([p for p in user.in_cart.split() if p != str(product_id)])
            db.session.commit()
            return redirect(url_for('product', product_id=product_id))

        if 'delete_product' in request.form and is_owner:
            product = Products.query.filter_by(id=product.id, man_id=user.id).first()
            product.is_delete = 1
            for us in users:
                us.in_cart = ' '.join([p for p in user.in_cart.split() if p != str(product_id)])
                us.liked_products = ' '.join([p for p in user.liked_products.split() if p != str(product_id)])

            db.session.commit()
            flash('товар успешно удален', 'success')
            return redirect(url_for('added_products'))

        if 'back' in request.form:
            if g[0] == 'market':
                return redirect(url_for('market',
                                        category=g[1], seller=g[2], price_min=g[3],
                                        price_max=g[4], rating_min=g[5], rating_max=g[6], sort=g[7]))
            elif g[0] == 'search':
                return redirect(url_for('search', category=g[1], seller=g[2], price_min=g[3],
                                        price_max=g[4], rating_min=g[5], rating_max=g[6], sort=g[7], query=g[8]))
            elif g[0] in ['likes', 'cart', 'added_products']:
                return redirect(url_for(g[0]))

    liked_products = user.liked_products.split() if user.liked_products else []
    liked_products = [int(pid) for pid in liked_products]

    return render_template('product.html',
                           product=product,
                           count_in_cart=count_in_cart,
                           liked_products=liked_products,
                           is_owner=is_owner)


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        owner = request.form.get('owner')
        category = request.form.get('category')
        image_url = request.form.get('image_url')
        price = request.form.get('price', type=int)

        if not all([name, description, owner, category, image_url, price]):
            flash('заполните все обязательные поля', 'danger')
            return redirect(url_for('add_product'))

        new_product = Products(
            name=name,
            name_lower=name.lower(),
            description=description,
            description_lower=description.lower(),
            rating=round(random.uniform(4.0, 5.0), 1),
            owner=owner,
            owner_lower=owner.lower(),
            category=category,
            category_lower=category.lower(),
            image_url=image_url,
            price=price,
            man_id=session['id'],
            is_delete=0
        )

        db.session.add(new_product)
        db.session.commit()

        flash('товар успешно добавлен', 'success')
        return redirect(url_for('product', product_id=new_product.id))

    return render_template('add_product.html')


@app.route('/added_products', methods=['GET', 'POST'])
def added_products():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['id']
    user = User.query.filter_by(id=session['id']).first()
    users = User.query.all()
    print(users)
    session['url_back'] = ['added_products']

    if request.method == 'POST':
        if 'delete_product' in request.form:
            product_id = request.form.get('product_id')
            product = Products.query.filter_by(id=product_id, man_id=user_id).first()

            if product:
                product.is_delete = 1
                for us in users:
                    us.in_cart = ' '.join([p for p in user.in_cart.split() if p != str(product_id)])
                    us.liked_products = ' '.join([p for p in user.liked_products.split() if p != str(product_id)])
                db.session.commit()
                flash('товар перемещен в архив', 'success')

        elif 'restore_product' in request.form:
            product_id = request.form.get('product_id')
            product = Products.query.filter_by(id=product_id, man_id=user_id).first()

            if product:
                product.is_delete = 0
                db.session.commit()
                flash('товар восстановлен из архива', 'success')

        return redirect(url_for('added_products'))

    products = Products.query.filter_by(man_id=user_id).all()

    return render_template('added_products.html', products=products)


@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    product = Products.query.filter_by(id=product_id, man_id=session['id']).first_or_404()

    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.owner = request.form['owner']
        product.category = request.form['category']
        product.image_url = request.form['image_url']
        product.price = int(request.form['price'])

        product.name_lower = product.name.lower()
        product.description_lower = product.description.lower()
        product.owner_lower = product.owner.lower()
        product.category_lower = product.category.lower()

        db.session.commit()
        flash('товар успешно обновлен', 'success')
        return redirect(url_for('added_products'))

    return render_template('edit_product.html', product=product)


@app.route('/search/<query>', methods=['GET', 'POST'])
def search(query):
    query1 = query.strip().lower()

    match = re.search(r'id(\d+)', query)
    if match:
        try:
            pr = Products.query.filter_by(id=int(match.group(1))).first()
            if pr:
                return redirect(url_for('product', product_id=pr.id))
        except Exception:
            pass

    categories = [c[0] for c in db.session.query(Products.category).distinct().all()]
    owners = [o[0] for o in db.session.query(Products.owner).distinct().all()]
    user = User.query.filter_by(id=session['id']).first()

    selected_category = request.args.get('category', '')
    selected_seller = request.args.get('seller', '')
    price_min = request.args.get('price_min', type=int, default=None)
    price_max = request.args.get('price_max', type=int, default=None)
    rating_min = request.args.get('rating_min', type=float, default=None)
    sort_filter = request.args.get('sort', 'id')
    session['url_back'] = ['search', selected_category, selected_seller, price_min, price_max, rating_min, None,
                           sort_filter, query]

    query_set = Products.query
    print(query1)
    query_set = query_set.filter(
        db.or_(
            Products.name_lower.ilike(f"%{query1}%"),
            Products.description_lower.ilike(f"%{query1}%"),
            Products.owner_lower.ilike(f"%{query1}%"),
            Products.category_lower.ilike(f"%{query1}%")
        )
    )

    if selected_category:
        query_set = query_set.filter_by(category=selected_category)
    if selected_seller:
        query_set = query_set.filter(Products.owner == selected_seller)
    if price_min is not None:
        query_set = query_set.filter(Products.price >= price_min)
    if price_max is not None:
        query_set = query_set.filter(Products.price <= price_max)
    if rating_min is not None:
        query_set = query_set.filter(Products.rating >= rating_min)

    if sort_filter == 'price':
        query_set = query_set.order_by(Products.price)
    elif sort_filter == 'rating':
        query_set = query_set.order_by(Products.rating.desc())
    else:
        query_set = query_set.order_by(Products.id)

    products = query_set.all()

    if request.method == 'POST':
        product_id = request.form.get('product_id')

        cart_items = user.in_cart.split() if user.in_cart else []

        if 'increase' in request.form:
            cart_items.append(product_id)
        elif 'decrease' in request.form:
            if product_id in cart_items:
                cart_items.remove(product_id)
        elif 'remove' in request.form:
            cart_items = [p for p in cart_items if p != product_id]
        else:
            cart_items.append(product_id)

        user.in_cart = ' '.join(cart_items)
        db.session.commit()

        return redirect(url_for('search', query=query, category=selected_category, seller=selected_seller,
                                price_min=price_min, price_max=price_max, rating_min=rating_min,
                                sort=sort_filter))
    cart_items = user.in_cart.split() if user.in_cart else []
    product_counts = dict(Counter(cart_items))
    product_counts = {int(k): int(v) for k, v in product_counts.items()}
    liked_products = user.liked_products.split() if user.liked_products else []
    liked_products = [int(pid) for pid in liked_products]

    return render_template('search.html',
                           query=query,
                           products=products,
                           product_counts=product_counts,
                           categories=categories,
                           owners=owners,
                           selected_category=selected_category,
                           selected_seller=selected_seller,
                           price_min=price_min,
                           price_max=price_max,
                           rating_min=rating_min,
                           sort_filter=sort_filter,
                           liked_products=liked_products)


@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['id']).first()
    session['url_back'] = ['cart']
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
            flash('товар удален из корзины', 'info')
            if 'selected_products' in session and product_id in session['selected_products']:
                session['selected_products'].remove(product_id)

        elif 'remove_selected' in request.form:
            selected_to_ord = session.get('selected_products', [])
            if selected_to_ord:
                session['order_products'] = selected_to_ord
                selected_ids1 = session.get('order_products', [])
                user.in_cart = ' '.join([p for p in user.in_cart.split() if p not in selected_ids1])
                db.session.commit()
                flash('выбранные товары удалены из корзины', 'info')
                session['selected_products'] = []


        elif 'order_selected' in request.form:
            selected_to_ord = session.get('selected_products', [])
            if selected_to_ord:
                session['order_products'] = selected_to_ord
                session['flag_for_again'] = False
                return redirect(url_for('order'))


        elif 'save_selected' in request.form:
            selected_products = request.form.getlist('selected_products')
            session['selected_products'] = selected_products
            flash('выбранные товары сохранены', 'success')


        elif 'like_product' in request.form:
            product_id = request.form['like_product']
            user = User.query.filter_by(id=session['id']).first()
            liked = user.liked_products.split() if user.liked_products else []
            if product_id in liked:
                liked.remove(product_id)
            else:
                liked.append(product_id)
            user.liked_products = ' '.join(liked)
            db.session.commit()

        db.session.commit()
        return redirect(url_for('cart'))

    cart_items = user.in_cart.split() if user.in_cart else []
    products = Products.query.filter(Products.id.in_([int(x) for x in cart_items])).all()

    selected_to_ord = session.get('selected_products', [])
    session['selected_products'] = selected_to_ord
    selected_ids1 = session.get('selected_products', [])

    selected_products = session.get('selected_products', [])
    total = sum(product.price * product_counts.get(product.id, 1) for product in
                Products.query.filter(Products.id.in_(selected_products)).all())

    liked_products = user.liked_products.split() if user.liked_products else []

    liked_products = [int(pid) for pid in liked_products]

    return render_template('cart.html',
                           products=products,
                           product_counts=product_counts,
                           selected_products=selected_products, total=total, liked_products=liked_products)


@app.route('/order', methods=['GET', 'POST'])
def order():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(id=session['id']).first()

    if 'flag_for_again' in session and session['flag_for_again']:
        order = Orders.query.filter_by(id=session['flag_for_again']).first()
        selected_ids = [int(x.split(',')[0]) for x in order.products.split()]
        products = Products.query.filter(Products.id.in_(selected_ids)).all()
        product_counts = {int(x.split(',')[0]): int(x.split(',')[1]) for x in order.products.split()}
    else:
        selected_ids1 = session.get('order_products', [])
        selected_ids = [int(x) for x in selected_ids1]
        products = Products.query.filter(Products.id.in_(selected_ids)).all()
        counts = user.in_cart.split() if user.in_cart else []
        product_counts = dict(Counter(counts))
        product_counts = {int(key): int(value) for key, value in product_counts.items() if int(key) in selected_ids}
        user.in_cart = ' '.join([p for p in user.in_cart.split() if p not in selected_ids1])

    total = sum(Products.query.filter_by(id=key).first().price * value for key, value in product_counts.items())

    if request.method == 'POST':
        city = request.form.get('city') or session.get('city', '')
        session['city'] = city
        date = datetime.now()
        new_order = Orders(
            city=city,
            total=total,
            products=' '.join(','.join([str(key), str(value)]) for key, value in product_counts.items()),
            date=date,
            formated_date=date.strftime(f"%d {months[date.month - 1]} в %H:%M"),
            man_id=session['id'],
            status='✈️ доставка'
        )
        db.session.add(new_order)
        db.session.commit()
        return redirect(url_for('orders'))

    saved_city = session.get('city', '')

    return render_template(
        'order.html',
        name=session['username'],
        products=products,
        product_counts=product_counts,
        total=total,
        saved_city=saved_city,
        number=user.phone_number
    )


@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'username' not in session:
        return redirect(url_for('login'))

    orders = Orders.query.filter_by(man_id=session['id']).all()

    if request.method == 'POST':
        order_id = request.form.get('order_id')
        order = Orders.query.filter_by(id=order_id).first()
        if 'received' in request.form:
            date = datetime.now()
            formated_date = date.strftime(f"%d {months[date.month - 1]} в %H:%M")
            order.date_done = date
            order.formated_date_done = formated_date
            order.status = '✅ доставлен'
        elif 'again' in request.form:
            print(order_id)
            session['flag_for_again'] = order_id
            return redirect(url_for('order'))
        db.session.commit()

    return render_template('orders.html', orders=orders, Products=Products, int=int)


@app.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_details(order_id):
    order = Orders.query.get_or_404(order_id)

    user = User.query.filter_by(id=order.man_id).first()

    if request.method == 'POST':
        if 'cancel' in request.form:
            order.status = '❌ отменен'
            flash('ваш заказ был отменен', 'success')
            db.session.commit()
            return redirect(url_for('orders'))

        elif 'done' in request.form and order.status not in ['✅ доставлен', '❌ отменен']:
            date = datetime.now()
            formated_date = date.strftime(f"%d {months[date.month - 1]} в %H:%M")
            order.date_done = date
            order.formated_date_done = formated_date
            order.status = '✅ доставлен'
            db.session.commit()
            flash('заказ доставлен', 'success')
            return redirect(url_for('order_details', order_id=order_id))

        elif 'again' in request.form:
            print(order_id)
            session['flag_for_again'] = order_id
            return redirect(url_for('order'))

    product_counts = {}
    for product_info in order.products.split():
        product_id, quantity = map(int, product_info.split(','))
        product_counts[product_id] = quantity

    liked_products = user.liked_products.split() if user.liked_products else []
    liked_products = [int(pid) for pid in liked_products]

    flag = False
    for product_id, quantity in product_counts.items():
        product = Products.query.get(product_id)
        if product.is_delete:
            flag = True
            pass
    print(flag)

    return render_template('about_order.html', order=order, name=user.username, product_counts=product_counts,
                           Products=Products, liked_products=liked_products, number=user.phone_number, flag=flag)


@app.route('/likes', methods=['GET', 'POST'])
def likes():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['id']).first()
    session['url_back'] = ['likes']
    liked_ids = [int(pid) for pid in user.liked_products.split()] if user.liked_products else []

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        cart_items = user.in_cart.split() if user.in_cart else []
        liked_items = user.liked_products.split() if user.liked_products else []

        if 'increase' in request.form:
            cart_items.append(product_id)
        elif 'decrease' in request.form:
            if product_id in cart_items:
                cart_items.remove(product_id)
        elif 'remove' in request.form:
            cart_items = [p for p in cart_items if p != product_id]
        elif 'unlike' in request.form:
            liked_items = [p for p in liked_items if p != product_id]

        user.in_cart = ' '.join(cart_items)
        user.liked_products = ' '.join(liked_items)
        db.session.commit()

        return redirect(url_for('likes'))

    products = Products.query.filter(Products.id.in_(liked_ids)).all()
    cart_items = user.in_cart.split() if user.in_cart else []
    product_counts = dict(Counter(cart_items))
    product_counts = {int(k): int(v) for k, v in product_counts.items()}

    return render_template('likes.html',
                           products=products,
                           product_counts=product_counts
                           )


@app.route('/toggle_like/<int:product_id>', methods=['GET', 'POST'])
def toggle_like(product_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['id']).first()
    liked = user.liked_products.split() if user.liked_products else []
    print(product_id)

    if str(product_id) in liked:
        liked.remove(str(product_id))
    else:
        liked.append(str(product_id))

    user.liked_products = ' '.join(liked)
    db.session.commit()

    return redirect(request.referrer or url_for('market'))


@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['id']

    if request.method == 'POST':
        if 'product_id' in request.form:
            product_id = request.form.get('product_id')
            rating = request.form.get('rating')
            text = request.form.get('text', '').strip()

            if not product_id or not rating:
                flash('выберите оценку для товара', 'danger')
                return redirect(url_for('reviews'))

            new_review = Reviews(
                rating=rating,
                text=text,
                product_id=product_id,
                man_id=user_id
            )
            db.session.add(new_review)
            db.session.commit()
            flash('cпасибо за отзыв', 'success')

        elif 'delete_review' in request.form:
            review_id = request.form.get('review_id')
            review = Reviews.query.filter_by(id=review_id, man_id=user_id).first()

            db.session.delete(review)
            db.session.commit()
            flash('отзыв удален', 'success')

        elif 'product_id_update' in request.form:
            product_id = request.form.get('product_id_update')
            rating = request.form.get('rating_update')
            text = request.form.get('text_update', '').strip()

            product_id = int(product_id)
            rating = int(rating)

            review = Reviews.query.filter_by(man_id=user_id, product_id=product_id).first()

            review.rating = rating
            review.text = text
            db.session.commit()
            flash('отзыв обновлен', 'success')

        return redirect(url_for('reviews'))

    received_products_ids = set()
    orders = Orders.query.filter_by(man_id=user_id, status='✅ доставлен').all()
    for order in orders:
        for item in order.products.split():
            pdd, _ = map(int, item.split(','))
            received_products_ids.add(pdd)

    reviewed_products_ids = {r.product_id for r in Reviews.query.filter_by(man_id=user_id).all()}
    available_products = Products.query.filter(
        Products.id.in_(received_products_ids - reviewed_products_ids)
    ).all()

    user_reviews = []
    reviews = Reviews.query.filter_by(man_id=user_id).all()
    for review in reviews:
        product = Products.query.get(review.product_id)
        if product:
            user_reviews.append({
                'review': review,
                'product': product
            })

    return render_template('reviews.html',
                           available_products=available_products,
                           user_reviews=user_reviews)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'id' not in session:
        flash('сначала войдите в аккаунт', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['id'])

    if request.method == 'POST':
        if 'delete_account' in request.form:
            delete_password = request.form['delete_password']
            if not check_password_hash(user.password, delete_password):
                flash('неверный пароль, аккаунт не удален', 'danger')
                return redirect(url_for('settings'))

            db.session.delete(user)
            Orders.query.filter_by(man_id=user.id).delete()
            Reviews.query.filter_by(man_id=user.id).delete()
            db.session.commit()
            session.clear()
            flash('аккаунт успешно удален', 'success')
            return redirect(url_for('index'))

        username = request.form['username']
        email = request.form['email']
        phone_number = request.form['phone_number']
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        new_password_confirm = request.form['new_password_confirm']

        if phone_number.startswith('8'):
            phone_number = '+7' + phone_number[1:]

        if username != user.username and User.query.filter_by(username=username).first():
            flash('имя пользователя занято', 'danger')
            return redirect(url_for('settings'))

        if email != user.email and User.query.filter_by(email=email).first():
            flash('эта почта уже используется', 'danger')
            return redirect(url_for('settings'))

        if phone_number != user.phone_number and User.query.filter_by(phone_number=phone_number).first():
            flash('этот номер телефона уже используется', 'danger')
            return redirect(url_for('settings'))

        if len(phone_number) != 12 or not phone_number.startswith('+7'):
            flash('номер телефона должен быть в формате +7xxxxxxxxxx или 8xxxxxxxxxx', 'danger')
            return redirect(url_for('settings'))

        user.username = username
        session['username'] = user.username
        user.email = email
        user.phone_number = phone_number

        if current_password or new_password or new_password_confirm:
            if not check_password_hash(user.password, current_password):
                flash('неверный текущий пароль', 'danger')
                return redirect(url_for('settings'))
            if new_password != new_password_confirm:
                flash('новые пароли не совпадают', 'danger')
                return redirect(url_for('settings'))
            user.password = generate_password_hash(new_password)

        db.session.commit()
        flash('настройки обновлены', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        phone_number = request.form['phone_number']
        email = request.form['email']
        errors = []

        if password != password_confirm:
            errors.append('пароли не совпадают')

        if User.query.filter_by(username=username).first():
            errors.append('имя пользователя уже занято')

        if User.query.filter_by(email=email).first():
            errors.append('эта почта уже используется')

        if phone_number.startswith('8'):
            phone_number = '+7' + phone_number[1:]

        if len(phone_number) != 12 or not phone_number.startswith('+7'):
            errors.append('номер телефона должен быть в формате +7xxxxxxxxxx или 8xxxxxxxxxx')

        if User.query.filter_by(phone_number=phone_number).first():
            errors.append('этот номер телефона уже используется')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            password=hashed_password,
            phone_number=phone_number,
            email=email,
            in_cart='',
            liked_products=''
        )

        db.session.add(new_user)
        db.session.commit()

        flash('вы зарегистрированы, теперь можно войти', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(email=login_input).first()

        if not user:
            phone_input = login_input
            if phone_input.isdigit() and phone_input.startswith('8'):
                phone_input = '+7' + phone_input[1:]
            user = User.query.filter_by(phone_number=phone_input).first()

        if not user:
            user = User.query.filter_by(username=login_input).first()

        if user and check_password_hash(user.password, password):
            session.permanent = True
            session['username'] = user.username
            session['id'] = user.id
            flash('вы успешно вошли', 'success')
            return redirect(url_for('market'))

        flash('неверное имя пользователя, почта, номер или пароль', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('id', None)
    flash('вы успешно вышли из системы', 'info')
    return redirect(url_for('index'))


def create_db():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_db()
    app.run(port=8080, host='127.0.0.1', debug=True)
