from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pages.db'
db = SQLAlchemy(app)
app.config['UPLOAD_FOLDER'] = 'static/images/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=True)

if not os.path.exists('pages.db'):
    with app.app_context(): 
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password=generate_password_hash('password'))
            db.session.add(admin)
            db.session.commit()

@app.route('/')
def index():
    return "Welcome to the Flask App!"

@app.route('/<path:pagename>')
def view_page(pagename):
    page = Page.query.filter_by(name=pagename).first()
    if page:
        return render_template('view_page.html', page=page)
    else:
        flash('Page not found.', 'danger')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user:
            is_valid_password = check_password_hash(user.password, password)
        
        if user and is_valid_password:
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        flash('Please log in to access the admin page.', 'warning')
        return redirect(url_for('login'))
    pages = Page.query.all()
    return render_template('admin.html', pages=pages)

@app.route('/admin/create_page', methods=['GET', 'POST'])
def create_page():
    if 'user_id' not in session:
        flash('Please log in to access the admin page.', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        if not re.match(r'^[a-zA-Z0-9_/]+$', name):
            flash('Invalid page name. Use only letters, numbers, underscores, and slashes.', 'danger')
            return redirect(url_for('create_page'))
        if Page.query.filter_by(name=name).first():
            flash('Page already exists!', 'danger')
        else:
            new_page = Page(name=name, content='')
            db.session.add(new_page)
            db.session.commit()
            flash('Page created successfully!', 'success')
            return redirect(url_for('edit_page', page_id=new_page.id))
    return render_template('create_page.html')

def get_all_images():
    images_path = app.config['UPLOAD_FOLDER']
    return [f for f in os.listdir(images_path) if allowed_file(f)]

@app.route('/admin/edit_page/<int:page_id>', methods=['GET', 'POST'])
def edit_page(page_id):
    if 'user_id' not in session:
        flash('Please log in to access the admin page.', 'warning')
        return redirect(url_for('login'))
    page = Page.query.get_or_404(page_id)
    images = [{'name': img, 'path': url_for('static', filename=f'images/{img}')} for img in get_all_images()]
    if request.method == 'POST':
        page.content = request.form['content']
        db.session.commit()
        flash('Page updated successfully!', 'success')
    return render_template('edit_page.html', page=page, images=images)


@app.route('/admin/upload_image', methods=['POST'])
def upload_image():
    if 'user_id' not in session:
        flash('Please log in to access the admin page.', 'warning')
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(request.referrer)

    file = request.files['file']
    if file.filename == '':
        flash('No file selected for uploading.', 'danger')
        return redirect(request.referrer)

    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('Image uploaded successfully!', 'success')
    else:
        flash('Allowed file types are png, jpg, jpeg, gif.', 'danger')
    return redirect(request.referrer)


if __name__ == '__main__':
    app.run(debug=True)