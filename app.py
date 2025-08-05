from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import os
import io
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stit.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
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
    domain = db.Column(db.String(50))
    user = db.relationship('User', backref=db.backref('internships', lazy=True))

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    tools = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    github_link = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Pending')
    dataset_used = db.Column(db.String(100))
    user = db.relationship('User', backref=db.backref('projects', lazy=True))

def create_visualizations():
    internships = Internship.query.all()
    projects = Project.query.all()
    
    intern_df = pd.DataFrame([(i.company, i.domain, i.status) for i in internships], 
                           columns=['Company', 'Domain', 'Status'])
    proj_df = pd.DataFrame([(p.tools, p.dataset_used, p.status) for p in projects],
                          columns=['Tools', 'Dataset', 'Status'])
    
    internship_status_plot = None
    domain_plot = None
    tools_plot = None
    
    if not intern_df.empty:
        plt.figure(figsize=(8, 6))
        sns.countplot(data=intern_df, x='Status')
        plt.title('Internship Status Distribution')
        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        internship_status_plot = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    if not intern_df.empty and 'Domain' in intern_df and intern_df['Domain'].notna().any():
        plt.figure(figsize=(10, 6))
        sns.countplot(data=intern_df, y='Domain', order=intern_df['Domain'].value_counts().index)
        plt.title('Popular Data Science Domains')
        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        domain_plot = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    if not proj_df.empty and 'Tools' in proj_df and proj_df['Tools'].notna().any():
        tools = proj_df['Tools'].str.split(',', expand=True).stack().str.strip()
        if not tools.empty:
            plt.figure(figsize=(10, 6))
            sns.countplot(y=tools, order=tools.value_counts().index)
            plt.title('Popular Data Science Tools')
            buf = BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            tools_plot = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return internship_status_plot, domain_plot, tools_plot

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
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        session.pop('role', None)
        flash('User not found. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    if session['role'] == 'student':
        internships = Internship.query.filter_by(user_id=user.id).all()
        projects = Project.query.filter_by(user_id=user.id).all()
        return render_template('student_dashboard.html', user=user, internships=internships, projects=projects)
    else:
        users = User.query.filter_by(role='student').all()
        internships = Internship.query.all()
        projects = Project.query.all()
        status_plot, domain_plot, tools_plot = create_visualizations()
        return render_template('faculty_dashboard.html', users=users, internships=internships, 
                             projects=projects, status_plot=status_plot, domain_plot=domain_plot, 
                             tools_plot=tools_plot)

@app.route('/add_internship', methods=['GET', 'POST'])
def add_internship():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        session.pop('role', None)
        flash('User not found. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        duration = request.form['duration']
        domain = request.form['domain']
        certificate = request.files['certificate']
        
        if certificate:
            certificate_path = os.path.join(app.config['UPLOAD_FOLDER'], certificate.filename)
            certificate.save(certificate_path)
        else:
            certificate_path = None
            
        new_internship = Internship(
            user_id=user.id,
            title=title,
            company=company,
            duration=duration,
            domain=domain,
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
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        session.pop('role', None)
        flash('User not found. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        tools = request.form['tools']
        description = request.form['description']
        github_link = request.form['github_link']
        dataset_used = request.form['dataset_used']
        
        new_project = Project(
            user_id=user.id,
            title=title,
            tools=tools,
            description=description,
            github_link=github_link,
            dataset_used=dataset_used
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
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        session.pop('role', None)
        flash('User not found. Please log in again.', 'error')
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
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        session.pop('role', None)
        flash('User not found. Please log in again.', 'error')
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
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        session.pop('role', None)
        flash('User not found. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Data Science Internship & Project Report", styles['Title']))
    
    internships = Internship.query.all()
    data = [['ID', 'Student', 'Title', 'Company', 'Domain', 'Duration', 'Status']]
    for i in internships:
        user = User.query.get(i.user_id)
        data.append([i.id, user.username if user else 'Unknown', i.title, i.company, i.domain or 'N/A', i.duration, i.status])
    
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
    
    elements.append(Paragraph("Projects", styles['Heading2']))
    projects = Project.query.all()
    data = [['ID', 'Student', 'Title', 'Tools', 'Dataset', 'Status']]
    for p in projects:
        user = User.query.get(p.user_id)
        data.append([p.id, user.username if user else 'Unknown', p.title, p.tools, p.dataset_used or 'N/A', p.status])
    
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
    return send_file(buffer, as_attachment=True, download_name='data_science_report.pdf', mimetype='application/pdf')

@app.route('/filter_students', methods=['GET', 'POST'])
def filter_students():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        session.pop('role', None)
        flash('User not found. Please log in again.', 'error')
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
    status_plot, domain_plot, tools_plot = create_visualizations()
    
    return render_template('faculty_dashboard.html', users=users, internships=internships, 
                         projects=projects, status_plot=status_plot, domain_plot=domain_plot, 
                         tools_plot=tools_plot)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)