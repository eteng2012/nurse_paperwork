from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
    UserMixin,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json
import os
from datetime import datetime
from process_audio import run

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secure_random_secret_key'  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuration for file uploads
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads', 'audio')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16 MB upload size

# Ensure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to 'login' view if not authenticated

# User model (Doctors)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(150), nullable=False)

# Patient model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)

# DoctorNote model (Updated to exclude audio_file)
class DoctorNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    subjective = db.Column(db.Text, nullable=False)
    objective = db.Column(db.Text, nullable=False)
    assessment = db.Column(db.Text, nullable=False)
    plan = db.Column(db.Text, nullable=False)
    intervention = db.Column(db.Text, nullable=False)
    other = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('doctor_notes', lazy=True))

@app.route('/')
def root():
    return redirect(url_for('login'))

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Placeholder helper function to process audio and extract note data
def helper(audio_path):
    """
    This function is a placeholder for processing the audio file.
    It should take the path to the audio file, process it (e.g., using speech-to-text),
    and extract the required fields: subjective, objective, assessment, plan, intervention, other.
    For demonstration purposes, it returns dummy data.
    """
    # TODO: Implement actual audio processing logic here
    return {
        'subjective': 'Extracted subjective data from audio.',
        'objective': 'Extracted objective data from audio.',
        'assessment': 'Extracted assessment data from audio.',
        'plan': 'Extracted plan data from audio.',
        'intervention': 'Extracted intervention data from audio.',
        'other': 'Extracted other data from audio.'
    }

# Function to import data from JSON
def import_data():
    if os.path.exists('patients.json'):
        with open('patients.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                # Add or update patient
                patient = Patient.query.get(item['id'])
                if not patient:
                    patient = Patient(
                        id=item['id'],
                        name=item['name'],
                        age=item['age']
                    )
                    db.session.add(patient)
                else:
                    patient.name = item['name']
                    patient.age = item['age']
                
                # Add doctor notes
                for note in item.get('doctor_notes', []):
                    # Parse the date string into a datetime object
                    try:
                        note_date = datetime.strptime(note['date'], '%Y-%m-%d %H:%M')
                    except ValueError:
                        # Handle incorrect date format
                        print(f"Incorrect date format for patient ID {patient.id}")
                        continue

                    # Check if the exact note already exists to prevent duplicates
                    existing_note = DoctorNote.query.filter_by(
                        patient_id=patient.id,
                        subjective=note['subjective'],
                        objective=note['objective'],
                        assessment=note['assessment'],
                        plan=note['plan'],
                        intervention=note['intervention'],
                        other=note['other'],
                        date=note_date
                    ).first()
                    if not existing_note:
                        doctor_note = DoctorNote(
                            patient_id=patient.id,
                            subjective=note['subjective'],
                            objective=note['objective'],
                            assessment=note['assessment'],
                            plan=note['plan'],
                            intervention=note['intervention'],
                            other=note['other'],
                            date=note_date
                        )
                        db.session.add(doctor_note)
    db.session.commit()

# Function to create predefined doctor accounts
def create_doctor_accounts():
    with app.app_context():
        doctor_count = User.query.count()
        if doctor_count == 0:
            doctors = [
                {'username': 'doctor1', 'password': 'password1'},
                {'username': 'doctor2', 'password': 'password2'},
                {'username': 'doctor3', 'password': 'password3'}
            ]
            for doc in doctors:
                new_doctor = User(
                    username=doc['username'],
                    password_hash=generate_password_hash(doc['password'])
                )
                db.session.add(new_doctor)
            db.session.commit()
            print("Doctor accounts created.")
        else:
            print("Doctor accounts already exist.")

# Initialization function
def initialize():
    with app.app_context():
        db.create_all()
        create_doctor_accounts()
        import_data()

# Login view
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=False)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')  # Ensure you have a separate login template

# Logout view
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Main patient list view
@app.route('/patients')
@login_required
def index():
    patients = Patient.query.all()
    return render_template('index.html', patients=patients)

# AJAX route to fetch patient details
@app.route('/patient/<int:patient_id>/details', methods=['GET'])
@login_required
def get_patient_details_ajax(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    # Fetch all doctor notes for the patient
    notes = DoctorNote.query.filter_by(patient_id=patient_id).order_by(DoctorNote.date.desc()).all()
    notes_data = []
    for note in notes:
        notes_data.append({
            'date': note.date.strftime('%Y-%m-%d %H:%M'),
            'subjective': note.subjective,
            'objective': note.objective,
            'assessment': note.assessment,
            'plan': note.plan,
            'intervention': note.intervention,
            'other': note.other
        })

    patient_details = {
        'name': patient.name,
        'age': patient.age,
        'doctor_notes': notes_data
    }

    return jsonify(patient_details)

# Route to add a new patient
@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        
        if not name or not age:
            flash('Please provide both name and age for the patient.', 'danger')
            return redirect(url_for('add_patient'))
        
        # Create and save the new patient
        new_patient = Patient(name=name, age=int(age))
        db.session.add(new_patient)
        db.session.commit()
        
        flash('New patient added successfully.', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_patient.html')

# Route to add a new doctor note with optional audio upload
@app.route('/patient/<int:patient_id>/add_note', methods=['GET', 'POST'])
@login_required
def add_doctor_note(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        # Handle file upload
        if 'audio' not in request.files:
            flash('No audio file part in the request.', 'danger')
            return redirect(request.url)
        
        file = request.files['audio']
        
        if file.filename == '':
            flash('No selected audio file.', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{current_user.username}_{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Pass the audio file path to the helper function to extract note data
            note_data = run(file_path)

            # Create and save the new doctor note
            new_note = DoctorNote(
                patient_id=patient.id,
                subjective=note_data['subjective'],
                objective=note_data['objective'],
                assessment=note_data['assessment'],
                plan=note_data['plan'],
                intervention=note_data['intervention'],
                other=note_data['other'],
                date=datetime.utcnow()
            )
            db.session.add(new_note)
            db.session.commit()
            
            # Optionally, delete the audio file after processing
            os.remove(file_path)
            
            flash('Doctor note added successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid file type. Allowed types are mp3, wav, ogg.', 'danger')
            return redirect(request.url)
    
    return render_template('upload_audio.html', patient=patient)

# Route to serve uploaded audio files (if needed)
@app.route('/uploads/audio/<filename>')
@login_required
def uploaded_audio(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    initialize()
    app.run(debug=True)
