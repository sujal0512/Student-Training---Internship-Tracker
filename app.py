from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import os
from datetime import datetime
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stit.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'faculty'
    batch = db.Column(db.String(10))
    semester = db.Column(db.String(10))
    course = db.Column(db.String(50))

class Internship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    certificate = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Pending')
    user = db.relationship('User', backref=db.backref('internships', lazy=True))

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    tools = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    github_link = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Pending')
    user = db.relationship('User', backref=db.backref('projects', lazy=True))

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        batch = request.form.get('batch')
        semester = request.form.get('semester')
        course = request.form.get('course')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('signup'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, role=role, 
                       batch=batch, semester=semester, course=course)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if session['role'] == 'student':
        internships = Internship.query.filter_by(user_id=user.id).all()
        projects = Project.query.filter_by(user_id=user.id).all()
        return render_template('student_dashboard.html', user=user, internships=internships, projects=projects)
    else:
        users = User.query.filter_by(role='student').all()
        internships = Internship.query.all()
        projects = Project.query.all()
        return render_template('faculty_dashboard.html', users=users, internships=internships, projects=projects)

@app.route('/add_internship', methods=['GET', 'POST'])
def add_internship():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        duration = request.form['duration']
        certificate = request.files['certificate']
        
        if certificate:
            certificate_path = os.path.join(app.config['UPLOAD_FOLDER'], certificate.filename)
            certificate.save(certificate_path)
        else:
            certificate_path = None
            
        new_internship = Internship(
            user_id=session['user_id'],
            title=title,
            company=company,
            duration=duration,
            certificate=certificate_path
        )
        db.session.add(new_internship)
        db.session.commit()
        flash('Internship added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_internship.html')

@app.route('/add_project', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        tools = request.form['tools']
        description = request.form['description']
        github_link = request.form['github_link']
        
        new_project = Project(
            user_id=session['user_id'],
            title=title,
            tools=tools,
            description=description,
            github_link=github_link
        )
        db.session.add(new_project)
        db.session.commit()
        flash('Project added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_project.html')

@app.route('/verify_internship/<int:id>/<action>')
def verify_internship(id, action):
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))
    
    internship = Internship.query.get(id)
    if internship:
        internship.status = 'Verified' if action == 'verify' else 'Pending'
        db.session.commit()
        flash(f'Internship {action}d successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/verify_project/<int:id>/<action>')
def verify_project(id, action):
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))
    
    project = Project.query.get(id)
    if project:
        project.status = 'Verified' if action == 'verify' else 'Pending'
        db.session.commit()
        flash(f'Project {action}d successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/download_report')
def download_report():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Student Internship & Project Report", styles['Title']))
    
    # Internship Data
    internships = Internship.query.all()
    data = [['ID', 'Student', 'Title', 'Company', 'Duration', 'Status']]
    for i in internships:
        user = User.query.get(i.user_id)
        data.append([i.id, user.username, i.title, i.company, i.duration, i.status])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='report.pdf', mimetype='application/pdf')

@app.route('/filter_students', methods=['GET', 'POST'])
def filter_students():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))
    
    batch = request.form.get('batch', '')
    semester = request.form.get('semester', '')
    course = request.form.get('course', '')
    
    query = User.query.filter_by(role='student')
    if batch:
        query = query.filter_by(batch=batch)
    if semester:
        query = query.filter_by(semester=semester)
    if course:
        query = query.filter_by(course=course)
    
    users = query.all()
    internships = Internship.query.join(User).filter(User.id.in_([u.id for u in users])).all()
    projects = Project.query.join(User).filter(User.id.in_([u.id for u in users])).all()
    
    return render_template('faculty_dashboard.html', users=users, internships=internships, projects=projects)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)