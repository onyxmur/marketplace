from datetime import timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):  # пользователь
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)


class Product(db.Model):  # товар
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(100))


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('market'))
    return render_template('index.html')


@app.route('/market')
def market():
    if 'username' not in session:
        return redirect(url_for('login'))

    products = Product.query.all()
    return render_template('market.html',
                           username=session['username'],
                           products=products)


@app.route('/product/<int:product_id>')
def product(product_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Имя пользователя занято', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Вы зарегистрированы, теперь можно войти', 'success')
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
            flash('Вы успешно вошли', 'success')
            return redirect(url_for('market'))

        flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('index'))


def create_db():
    with app.app_context():
        db.create_all()

        if Product.query.count() == 0:
            products = [
                Product(name="Смартфон", price=20000,
                        description="смартфон смартфон",
                        image="phone.jpg"),
                Product(name="Ноутбук", price=50000,
                        description="Ноутбук Ноутбук",
                        image="laptop.jpg"),
                Product(name="Наушники", price=5000,
                        description="Наушники Наушники",
                        image="headphones.jpg")
            ]
            db.session.bulk_save_objects(products)
            db.session.commit()


if __name__ == '__main__':
    create_db()
    app.run(port=8080, host='127.0.0.1', debug=True)
