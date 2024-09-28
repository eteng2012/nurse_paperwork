from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # 请替换为您的密钥
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SESSION_PERMANENT'] = False  # 会话将在浏览器关闭后失效
app.config['REMEMBER_COOKIE_DURATION'] = 0  # 禁用“记住我”功能的持续时间
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 未登录时重定向到登录页面

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(150), nullable=False)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    record = db.Column(db.Text, nullable=False)
    tests = db.Column(db.Text, nullable=True)
    nurse_notes = db.Column(db.Text, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        return db.session.get(User, int(user_id))

def import_data():
    with app.app_context():
        with open('patients.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                existing_patient = db.session.get(Patient, item['id'])
                if existing_patient:
                    existing_patient.name = item['name']
                    existing_patient.age = item['age']
                    existing_patient.record = item['record']
                    existing_patient.tests = item.get('tests')
                    existing_patient.nurse_notes = item.get('nurse_notes')
                else:
                    patient = Patient(
                        id=item['id'],
                        name=item['name'],
                        age=item['age'],
                        record=item['record'],
                        tests=item.get('tests'),
                        nurse_notes=item.get('nurse_notes')
                    )
                    db.session.add(patient)
            db.session.commit()

if not os.path.exists('patients.db'):
    with app.app_context():
        db.create_all()
        import_data()
else:
    # 使用Flask-Migrate进行迁移，然后更新数据
    import_data()

@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user, remember=False)  # 显式设置remember为False
                flash('Logged in successfully.')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                flash('Invalid username or password')
                return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with app.app_context():
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists')
                return redirect(url_for('register'))
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/patients')
@login_required
def index():
    with app.app_context():
        patients = Patient.query.all()
        return render_template('index.html', patients=patients)

@app.route('/patient/<int:patient_id>')
@login_required
def get_patient(patient_id):
    with app.app_context():
        patient = db.session.get(Patient, patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        return jsonify({
            'id': patient.id,
            'name': patient.name,
            'age': patient.age,
            'record': patient.record
        })

@app.route('/patient/details/<int:patient_id>')
@login_required
def get_patient_details(patient_id):
    with app.app_context():
        patient = db.session.get(Patient, patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        return jsonify({
            'tests': patient.tests,
            'nurse_notes': patient.nurse_notes
        })

if __name__ == '__main__':
    app.run(debug=True)
