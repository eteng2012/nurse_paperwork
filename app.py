from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import json
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    record = db.Column(db.Text, nullable=False)
    tests = db.Column(db.Text, nullable=True)
    nurse_notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Patient {self.name}>'

def import_data():
    with app.app_context():
        with open('patients.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                existing_patient = Patient.query.get(item['id'])
                if existing_patient:
                    # Update existing record
                    existing_patient.name = item['name']
                    existing_patient.age = item['age']
                    existing_patient.record = item['record']
                    existing_patient.tests = item.get('tests')
                    existing_patient.nurse_notes = item.get('nurse_notes')
                else:
                    # Add new record
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
    # Update data to ensure it's up-to-date
    import_data()

@app.route('/')
def index():
    with app.app_context():
        patients = Patient.query.all()
        return render_template('index.html', patients=patients)

@app.route('/patient/<int:patient_id>')
def get_patient(patient_id):
    with app.app_context():
        patient = Patient.query.get_or_404(patient_id)
        return jsonify({
            'id': patient.id,
            'name': patient.name,
            'age': patient.age,
            'record': patient.record
        })

@app.route('/patient/details/<int:patient_id>')
def get_patient_details(patient_id):
    with app.app_context():
        patient = Patient.query.get_or_404(patient_id)
        return jsonify({
            'tests': patient.tests,
            'nurse_notes': patient.nurse_notes
        })

if __name__ == '__main__':
    app.run(debug=True)
