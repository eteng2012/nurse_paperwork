from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # 请替换为您的密钥
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库和迁移
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 未登录时重定向到登录页面

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(150), nullable=False)

# 患者模型
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    record = db.Column(db.Text, nullable=False)
    tests = db.Column(db.Text, nullable=True)

# 护士笔记模型
class NurseNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    note = db.Column(db.Text, nullable=False)

    nurse = db.relationship('User', backref=db.backref('notes', lazy=True))
    patient = db.relationship('Patient', backref=db.backref('notes', lazy=True))

# 加载用户
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 数据导入函数
def import_data():
    if os.path.exists('patients.json'):
        with open('patients.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                # 添加或更新患者信息
                existing_patient = Patient.query.get(item['id'])
                if existing_patient:
                    existing_patient.name = item['name']
                    existing_patient.age = item['age']
                    existing_patient.record = item['record']
                    existing_patient.tests = item.get('tests')
                else:
                    patient = Patient(
                        id=item['id'],
                        name=item['name'],
                        age=item['age'],
                        record=item['record'],
                        tests=item.get('tests')
                    )
                    db.session.add(patient)
                
                # 处理护士笔记
                if 'nurse_notes' in item:
                    for note in item['nurse_notes']:
                        nurse = User.query.filter_by(username=note['nurse_username']).first()
                        if nurse:
                            # 检查是否已有相同的笔记
                            existing_note = NurseNote.query.filter_by(
                                nurse_id=nurse.id,
                                patient_id=item['id'],
                                note=note['note']
                            ).first()
                            if not existing_note:
                                nurse_note = NurseNote(
                                    nurse_id=nurse.id,
                                    patient_id=item['id'],
                                    note=note['note']
                                )
                                db.session.add(nurse_note)
    db.session.commit()

# 创建预定义的护士账号
def create_nurse_accounts():
    nurse_count = User.query.count()
    if nurse_count == 0:
        nurses = [
            {'username': 'nurse1', 'password': 'password1'},
            {'username': 'nurse2', 'password': 'password2'},
            {'username': 'nurse3', 'password': 'password3'}
        ]
        for nurse in nurses:
            new_nurse = User(
                username=nurse['username'],
                password_hash=generate_password_hash(nurse['password'])
            )
            db.session.add(new_nurse)
        db.session.commit()
        print("Nurse accounts created.")
    else:
        print("Nurse accounts already exist.")

# 初始化数据库和数据，避免使用 before_first_request
def initialize():
    with app.app_context():
        db.create_all()
        create_nurse_accounts()
        import_data()

# 登录视图
@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=False)
            flash('Logged in successfully.')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    return render_template('login.html')

# 注销视图
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

# 患者列表视图
@app.route('/patients')
@login_required
def index():
    patients = Patient.query.all()
    return render_template('index.html', patients=patients)

# 患者详情视图（通过 AJAX 获取）
@app.route('/patient/<int:patient_id>/details', methods=['GET'])
@login_required
def get_patient_details_ajax(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
    
    # 获取所有护士对该患者的笔记
    all_notes = NurseNote.query.filter_by(patient_id=patient_id).all()
    notes = []
    for note in all_notes:
        notes.append({
            'nurse_username': note.nurse.username,
            'note': note.note
        })
    
    patient_details = {
        'name': patient.name,
        'age': patient.age,
        'record': patient.record,
        'tests': patient.tests,
        'nurse_notes': notes
    }
    
    return jsonify(patient_details)

if __name__ == '__main__':
    initialize()
    app.run(debug=True)
