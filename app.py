from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
import csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oes.db'
app.config['SECRET_KEY'] = 'mysecretkey'
db = SQLAlchemy(app)

# Define database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    user_type = db.Column(db.String(20), nullable=False)

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    teacher = db.relationship('User', backref=db.backref('classes', lazy=True))

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    class_ = db.relationship('Class', backref=db.backref('students', lazy=True))

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    class_ = db.relationship('Class', backref=db.backref('modules', lazy=True))
    notes = db.Column(db.Text, nullable=False)
    pdf_file = db.Column(db.String(255), nullable=True)

# Define routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        user = User.query.filter_by(username=username, email=email, user_type='teacher').first()
        if user:
            return redirect(url_for('teacher_dashboard', user_id=user.id))
        else:
            flash('Invalid username or email.')
    return render_template('teacher_login.html')

@app.route('/teacher_dashboard/<int:user_id>')
def teacher_dashboard(user_id):
    user = User.query.get(user_id)
    classes = user.classes
    return render_template('teacher_dashboard.html', user=user, classes=classes)

@app.route('/create_class/<int:user_id>', methods=['GET', 'POST'])
def create_class(user_id):
    if request.method == 'POST':
        name = request.form['name']
        subject = request.form['subject']
        class_ = Class(name=name, subject=subject, teacher_id=user_id)
        db.session.add(class_)
        db.session.commit()
        if 'csv_file' in request.files:
            csv_file = request.files['csv_file']
            if csv_file.filename != '':
                csv_file.save(os.path.join('uploads', csv_file.filename))
                with open(os.path.join('uploads', csv_file.filename), 'r') as f:
                    reader = csv.reader(f)
                    next(reader) # skip header
                    for row in reader:
                        student = Student(name=row[0], email=row[1], class_id=class_.id)
                        db.session.add(student)
                db.session.commit()
        return redirect(url_for('teacher_dashboard', user_id=user_id))
    return render_template('create_class.html', user_id=user_id)

@app.route('/upload_notes/<int:class_id>/<int:user_id>', methods=['GET', 'POST'])
def upload_notes(class_id, user_id):
    if request.method == 'POST':
        name = request.form['name']
        module = Module(name=name, class_id=class_id)
        db.session.add(module)
        db.session.commit()
        for i in range(1, 4):
            if request.files.get(f'module{i}_notes'):
                notes = request.files.get(f'module{i}_notes')
                module.notes += f'Module{i}:\n{notes.read().decode()}\n\n'
            if request.files.get(f'module{i}_pdf'):
                pdf = request.files.get(f'module{i}_pdf')
                if pdf.filename != '':
                    if pdf.content_length > 5 * 1024 * 1024:
                        flash('PDF file is too large.')
                        return redirect(url_for('upload_notes', class_id=class_id, user_id=user_id))
                    module.pdf_file = pdf.filename
                    db.session.commit()
                    pdf.save(os.path.join('uploads', pdf.filename))
        return redirect(url_for('teacher_dashboard', user_id=user_id))
    class_ = Class.query.get(class_id)
    modules = class_.modules
    return render_template('upload_notes.html', class_=class_, modules=modules, user_id=user_id)

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        class_name = request.form['class_name']
        student_name = request.form['student_name']
        student_email = request.form['student_email']
        class_ = Class.query.filter_by(name=class_name).first()
        if class_:
            student = Student.query.filter_by(name=student_name, email=student_email, class_=class_).first()
            if student:
                return redirect(url_for('student_dashboard', class_id=class_.id, student_id=student.id))
            else:
                flash('Invalid student name or email.')
        else:
            flash('Invalid class name.')
    return render_template('student_login.html')

@app.route('/student_dashboard/<int:class_id>/<int:student_id>')
def student_dashboard(class_id, student_id):
    class_ = Class.query.get(class_id)
    student = Student.query.get(student_id)
    modules = class_.modules
    return render_template('student_dashboard.html', class_=class_, student=student, modules=modules)

# Run the application
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)