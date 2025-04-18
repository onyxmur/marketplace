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
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    phone_number = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    in_cart = db.Column(db.String, default='')
    liked_products = db.Column(db.Text, default='')


class Product(db.Model):  # товар
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


class Order(db.Model):  # заказ
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


class Review(db.Model):  # отзыв
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text)
    product_id = db.Column(db.Integer, nullable=False)
    man_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


def check_login():
    if 'id' not in session:
        flash('сначала войдите или зарегистрируйтесь', 'danger')
        return redirect(url_for('index'))
    return None


def apply_filter(products_query, request_args, user):
    selected_category = request_args.get('category', '')
    selected_seller = request_args.get('seller', '')
    price_min = request_args.get('price_min', type=int, default=None)
    price_max = request_args.get('price_max', type=int, default=None)
    rating_min = request_args.get('rating_min', type=float, default=None)
    sort_filter = request_args.get('sort', 'id')

    categories = [c[0] for c in db.session.query(Product.category).filter_by(is_delete=0).distinct().all()]
    sellers = [c[0] for c in db.session.query(Product.owner).filter_by(is_delete=0).distinct().all()]
    product_counts = {int(k): int(v) for k, v in dict(Counter(user.in_cart.split())).items()}
    liked_products = [int(x) for x in user.liked_products.split()]

    if selected_category:
        products_query = products_query.filter_by(category=selected_category)
    if selected_seller:
        products_query = products_query.filter_by(owner=selected_seller)
    if price_min:
        products_query = products_query.filter(Product.price >= price_min)
    if price_max:
        products_query = products_query.filter(Product.price <= price_max)
    if rating_min:
        products_query = products_query.filter(Product.rating >= rating_min)

    if sort_filter == 'price':
        products_query = products_query.order_by(Product.price)
    elif sort_filter == 'rating':
        products_query = products_query.order_by(Product.rating.desc())
    else:
        products_query = products_query.order_by(Product.id)

    return categories, sellers, product_counts, liked_products, products_query.all(), [None, selected_category,
                                                                                       selected_seller, price_min,
                                                                                       price_max, rating_min,
                                                                                       sort_filter]


def change_quantity(product_id, user, request_form):
    cart_items = user.in_cart.split()
    print(cart_items, request_form)

    if 'increase' in request_form:
        cart_items.append(product_id)
    elif 'decrease' in request_form:
        cart_items.remove(product_id)
    elif 'remove' in request_form:
        cart_items = [p for p in cart_items if p != product_id]
    elif 'back' in request_form:
        return
    else:
        cart_items.append(product_id)

    user.in_cart = ' '.join(cart_items)
    db.session.commit()


def delete_product(product, user, users):
    product.is_delete = 1
    product_id = product.id
    for us in users:
        us.in_cart = ' '.join([p for p in user.in_cart.split() if p != str(product_id)])
        us.liked_products = ' '.join([p for p in user.liked_products.split() if p != str(product_id)])

    db.session.commit()
    flash('товар успешно удален', 'success')


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
    is_login = check_login()
    if is_login is not None:
        return is_login

    search_query = request.args.get('search')
    if search_query:
        return redirect(url_for('search', query=search_query))

    user = User.query.filter_by(id=session['id']).first()

    categories, sellers, product_counts, liked_products, products, session['url_back'] = apply_filter(Product.query,
                                                                                                      request.args,
                                                                                                      user)
    session['url_back'][0] = 'market'
    selected_category, selected_seller, price_min, price_max, rating_min, sort_filter = session['url_back'][1:]

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        change_quantity(product_id, user, request.form)
        return redirect(url_for('market', category=selected_category, seller=selected_seller,
                                price_min=price_min, price_max=price_max, rating_min=rating_min, sort=sort_filter))

    return render_template('market.html',
                           products=products,
                           categories=categories,
                           product_counts=product_counts,
                           selected_category=selected_category,
                           price_min=price_min,
                           price_max=price_max,
                           rating_min=rating_min,
                           sort_filter=sort_filter,
                           sellers=sellers,
                           selected_seller=selected_seller,
                           liked_products=liked_products
                           )


@app.route('/search/<query>', methods=['GET', 'POST'])
def search(query):
    is_login = check_login()
    if is_login is not None:
        return is_login

    user = User.query.filter_by(id=session['id']).first()
    query_lower = query.strip().lower()

    match = re.search(r'id(\d+)', query_lower)
    if match:
        try:
            pr = Product.query.filter_by(id=int(match.group(1))).first()
            if pr:
                return redirect(url_for('product', product_id=pr.id))
        except Exception:
            pass

    search_query = Product.query
    search_query = search_query.filter(
        db.or_(
            Product.name_lower.ilike(f"%{query_lower}%"),
            Product.description_lower.ilike(f"%{query_lower}%"),
            Product.owner_lower.ilike(f"%{query_lower}%"),
            Product.category_lower.ilike(f"%{query_lower}%")
        )
    )

    categories, sellers, product_counts, liked_products, products, session['url_back'] = apply_filter(search_query,
                                                                                                      request.args,
                                                                                                      user)
    session['url_back'][0] = 'search'
    selected_category, selected_seller, price_min, price_max, rating_min, sort_filter = session['url_back'][1:]
    session['url_back'].append(query)

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        change_quantity(product_id, user, request.form)
        print(selected_category, selected_seller, price_min, price_max, rating_min, sort_filter)
        return redirect(url_for('search', query=query, category=selected_category, seller=selected_seller,
                                price_min=price_min, price_max=price_max, rating_min=rating_min, sort=sort_filter))

    return render_template('search.html',
                           query=query,
                           products=products,
                           product_counts=product_counts,
                           categories=categories,
                           sellers=sellers,
                           selected_category=selected_category,
                           selected_seller=selected_seller,
                           price_min=price_min,
                           price_max=price_max,
                           rating_min=rating_min,
                           sort_filter=sort_filter,
                           liked_products=liked_products)


@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product(product_id):
    is_login = check_login()
    if is_login is not None:
        return is_login

    product = Product.query.get_or_404(product_id)
    user = User.query.filter_by(id=session['id']).first()
    users = User.query.all()
    url_back = session['url_back']

    product_counts = {int(k): int(v) for k, v in dict(Counter(user.in_cart.split())).items()}
    count_in_cart = product_counts.get(product_id, 0)
    liked_products = [int(x) for x in user.liked_products.split()]
    is_owner = product.man_id == user.id

    if request.method == 'POST':
        print(request.form)
        change_quantity(str(product_id), user, request.form)

        if 'delete_product' in request.form and is_owner:
            delete_product(product, user, users)

        if 'back' in request.form:
            if url_back[0] in ['likes', 'cart', 'added_products']:
                return redirect(url_for(url_back[0]))
            else:
                return redirect(url_for(url_back[0], category=url_back[1], seller=url_back[2], price_min=url_back[3],
                                        price_max=url_back[4], rating_min=url_back[5], sort=url_back[6],
                                        query=None if url_back[0] == 'market' else url_back[7]))

        return redirect(url_for('product', product_id=product_id))

    return render_template('product.html',
                           product=product,
                           count_in_cart=count_in_cart,
                           liked_products=liked_products,
                           is_owner=is_owner)


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    is_login = check_login()
    if is_login is not None:
        return is_login

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        owner = request.form.get('owner')
        category = request.form.get('category')
        image_url = request.form.get('image_url')
        price = request.form.get('price', type=int)

        if not all([name, description, owner, category, image_url, price]):
            flash('заполните все поля', 'danger')
            return redirect(url_for('add_product'))

        new_product = Product(
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
    is_login = check_login()
    if is_login is not None:
        return is_login

    user = User.query.filter_by(id=session['id']).first()
    users = User.query.all()
    session['url_back'] = ['added_products']

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        product = Product.query.filter_by(id=product_id).first()

        if 'delete_product' in request.form:
            delete_product(product, user, users)

        elif 'restore_product' in request.form:
            product.is_delete = 0
            db.session.commit()
            flash('товар успешно восстановлен', 'success')

        return redirect(url_for('added_products'))

    products = Product.query.filter_by(man_id=user.id).all()

    return render_template('added_products.html', products=products)


@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    is_login = check_login()
    if is_login is not None:
        return is_login

    product = Product.query.filter_by(id=product_id).first_or_404()

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


@app.route('/cart', methods=['GET', 'POST'])
def cart():
    is_login = check_login()
    if is_login is not None:
        return is_login

    user = User.query.filter_by(id=session['id']).first()
    session['url_back'] = ['cart']

    counts = user.in_cart.split() if user.in_cart else []
    product_counts = {int(key): int(value) for key, value in dict(Counter(counts)).items()}

    if request.method == 'POST':
        selected_products = request.form.getlist('selected_products')
        session['selected_products'] = selected_products
        if 'increase' in request.form or 'decrease' in request.form or 'remove' in request.form:
            if 'increase' in request.form:
                product_id = request.form['increase']
            elif 'decrease' in request.form:
                product_id = request.form['decrease']
            elif 'remove' in request.form:
                product_id = request.form['remove']
            change_quantity(product_id, user, request.form)

        elif 'remove_selected' in request.form:
            selectedd = session.get('selected_products')
            if selectedd:
                session['order_products'] = selectedd
                selected_ids = session.get('order_products')
                user.in_cart = ' '.join([p for p in user.in_cart.split() if p not in selected_ids])
                db.session.commit()
                flash('выбранные товары удалены из корзины', 'info')
                session['selected_products'] = []


        elif 'order_selected' in request.form:
            selectedd = session.get('selected_products', [])
            if selectedd:
                session['order_products'] = selectedd
                session['flag_for_again'] = False
                return redirect(url_for('order'))


        elif 'save_selected' in request.form:
            selectedd = request.form.getlist('selected_products')
            session['selected_products'] = selectedd
            flash('выбранные товары сохранены', 'success')


        elif 'like_product' in request.form:
            product_id = request.form['like_product']
            liked = user.liked_products.split()
            if product_id in liked:
                liked.remove(product_id)
            else:
                liked.append(product_id)
            user.liked_products = ' '.join(liked)

        db.session.commit()
        return redirect(url_for('cart'))

    cart_items = user.in_cart.split()
    products = Product.query.filter(Product.id.in_([int(x) for x in cart_items])).all()

    selectedd = session.get('selected_products', [])
    session['selected_products'] = selectedd
    total = sum(product.price * product_counts.get(product.id, 1) for product in
                Product.query.filter(Product.id.in_(selectedd)).all())

    liked_products = [int(x) for x in user.liked_products.split()]

    return render_template('cart.html',
                           products=products,
                           product_counts=product_counts,
                           selected_products=selectedd, total=total, liked_products=liked_products)


@app.route('/order', methods=['GET', 'POST'])
def order():
    is_login = check_login()
    if is_login is not None:
        return is_login

    user = User.query.filter_by(id=session['id']).first()

    if 'flag_for_again' in session and session['flag_for_again']:
        order = Order.query.filter_by(id=session['flag_for_again']).first()
        selected_ids = [int(x.split(',')[0]) for x in order.products.split()]
        products = Product.query.filter(Product.id.in_(selected_ids)).all()
        product_counts = {int(x.split(',')[0]): int(x.split(',')[1]) for x in order.products.split()}

    else:
        selected_ids1 = session.get('order_products', [])
        selected_ids = [int(x) for x in selected_ids1]
        products = Product.query.filter(Product.id.in_(selected_ids)).all()
        counts = user.in_cart.split() if user.in_cart else []
        product_counts = dict(Counter(counts))
        product_counts = {int(key): int(value) for key, value in product_counts.items() if int(key) in selected_ids}
        user.in_cart = ' '.join([p for p in user.in_cart.split() if p not in selected_ids1])

    total = sum(Product.query.filter_by(id=key).first().price * value for key, value in product_counts.items())

    if request.method == 'POST':
        city = request.form.get('city') or session.get('city', '')
        session['city'] = city
        date = datetime.now()
        new_order = Order(
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
    is_login = check_login()
    if is_login is not None:
        return is_login

    orders = Order.query.filter_by(man_id=session['id']).all()

    if request.method == 'POST':
        order_id = request.form.get('order_id')
        order = Order.query.filter_by(id=order_id).first()
        if 'received' in request.form:
            date = datetime.now()
            formated_date = date.strftime(f"%d {months[date.month - 1]} в %H:%M")
            order.date_done = date
            order.formated_date_done = formated_date

            order.status = '✅ доставлен'

        elif 'again' in request.form:
            session['flag_for_again'] = order_id
            return redirect(url_for('order'))

        db.session.commit()

    return render_template('orders.html', orders=orders, Products=Product, int=int)


@app.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_details(order_id):
    is_login = check_login()
    if is_login is not None:
        return is_login

    order = Order.query.get_or_404(order_id)
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

    liked_products = [int(x) for x in user.liked_products.split()]

    flag = False
    for product_id, quantity in product_counts.items():
        product = Product.query.get(product_id)
        if product.is_delete:
            flag = True
            pass
    print(flag)

    return render_template('about_order.html', order=order, name=user.username, product_counts=product_counts,
                           Products=Product, liked_products=liked_products, number=user.phone_number, flag=flag)


@app.route('/likes', methods=['GET', 'POST'])
def likes():
    is_login = check_login()
    if is_login is not None:
        return is_login

    user = User.query.filter_by(id=session['id']).first()
    session['url_back'] = ['likes']
    liked_products = [int(pid) for pid in user.liked_products.split()]

    if request.method == 'POST':
        product_id = request.form.get('product_id')

        if 'unlike' in request.form:
            liked_items = user.liked_products.split()
            liked_items = [p for p in liked_items if p != product_id]
            user.liked_products = ' '.join(liked_items)
        else:
            change_quantity(product_id, user, request.form)

        db.session.commit()
        return redirect(url_for('likes'))

    products = Product.query.filter(Product.id.in_(liked_products)).all()
    cart_items = user.in_cart.split()
    product_counts = {int(k): int(v) for k, v in dict(Counter(cart_items)).items()}

    return render_template('likes.html',
                           products=products,
                           product_counts=product_counts
                           )


@app.route('/toggle_like/<int:product_id>', methods=['GET', 'POST'])
def toggle_like(product_id):
    is_login = check_login()
    if is_login is not None:
        return is_login

    user = User.query.filter_by(id=session['id']).first()
    liked = user.liked_products.split()

    if str(product_id) in liked:
        liked.remove(str(product_id))
    else:
        liked.append(str(product_id))

    user.liked_products = ' '.join(liked)
    db.session.commit()

    return redirect(request.referrer or url_for('market'))


@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    is_login = check_login()
    if is_login is not None:
        return is_login

    user_id = session['id']

    if request.method == 'POST':
        if 'product_id' in request.form:
            product_id = request.form.get('product_id')
            rating = request.form.get('rating')
            text = request.form.get('text', '').strip()

            if not product_id or not rating:
                flash('выберите оценку для товара', 'danger')
                return redirect(url_for('reviews'))

            new_review = Review(
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
            review = Review.query.filter_by(id=review_id, man_id=user_id).first()

            db.session.delete(review)
            db.session.commit()
            flash('отзыв удален', 'success')

        elif 'product_id_update' in request.form:
            product_id = request.form.get('product_id_update')
            rating = request.form.get('rating_update')
            text = request.form.get('text_update', '').strip()

            product_id = int(product_id)
            rating = int(rating)

            review = Review.query.filter_by(man_id=user_id, product_id=product_id).first()

            review.rating = rating
            review.text = text
            db.session.commit()
            flash('отзыв обновлен', 'success')

        return redirect(url_for('reviews'))

    received_products_ids = set()
    orders = Order.query.filter_by(man_id=user_id, status='✅ доставлен').all()
    for order in orders:
        for item in order.products.split():
            pdd, _ = map(int, item.split(','))
            received_products_ids.add(pdd)

    reviewed_products_ids = {r.product_id for r in Review.query.filter_by(man_id=user_id).all()}
    available_products = Product.query.filter(Product.id.in_(received_products_ids - reviewed_products_ids)).all()

    user_reviews = []
    reviews = Review.query.filter_by(man_id=user_id).all()
    for review in reviews:
        product = Product.query.get(review.product_id)
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
    is_login = check_login()
    if is_login is not None:
        return is_login

    user = User.query.get(session['id'])

    if request.method == 'POST':
        if 'delete_account' in request.form:
            delete_password = request.form['delete_password']
            if not check_password_hash(user.password, delete_password):
                flash('неверный пароль, аккаунт не удален', 'danger')
                return redirect(url_for('settings'))

            db.session.delete(user)
            Order.query.filter_by(man_id=user.id).delete()
            Review.query.filter_by(man_id=user.id).delete()
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
    session.clear()
    flash('вы успешно вышли из системы', 'info')
    return redirect(url_for('index'))


def create_db():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_db()
    app.run(port=8080, host='127.0.0.1', debug=True)
