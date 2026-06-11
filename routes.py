from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Student, Exam, Question, Option, ExamAllotment, ExamSubmission, StudentAnswer
from datetime import datetime
import uuid

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        if isinstance(current_user._get_current_object(), User):
            return redirect(url_for('main.faculty_dashboard'))
        elif isinstance(current_user._get_current_object(), Student):
            return redirect(url_for('main.student_dashboard'))
    return render_template('index.html')

@main.route('/login/faculty', methods=['POST'])
def login_faculty():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user)
        return redirect(url_for('main.faculty_dashboard'))
    flash('Invalid faculty email or password.', 'danger')
    return redirect(url_for('main.index'))

@main.route('/login/student', methods=['POST'])
def login_student():
    roll_no = request.form.get('roll_no')
    password = request.form.get('password')

    student = Student.query.filter_by(roll_no=roll_no).first()
    if student:
        if not student.password_hash:
            student.set_password(password)
            db.session.commit()
            login_user(student)
            return redirect(url_for('main.student_dashboard'))
        elif student.check_password(password):
            login_user(student)
            return redirect(url_for('main.student_dashboard'))
        else:
            flash('Incorrect password.', 'danger')
    else:
        flash('Roll No not found in system. Please ask faculty to add you in UNNATI first.', 'danger')
        
    return redirect(url_for('main.index'))

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('main.student_dashboard'))
    exams = Exam.query.filter_by(faculty_id=current_user.id).order_by(Exam.created_at.desc()).all()
    return render_template('faculty_dashboard.html', exams=exams)

@main.route('/faculty/exam/create', methods=['GET', 'POST'])
@login_required
def create_exam():
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        data = request.json
        title = data.get('title')
        subject = data.get('subject')
        time_limit = int(data.get('time_limit_mins', 30))
        
        exam = Exam(title=title, subject=subject, faculty_id=current_user.id, time_limit_mins=time_limit, is_active=True, allow_start=False)
        db.session.add(exam)
        db.session.commit() # Get exam.id
        
        # Add questions
        for q_data in data.get('questions', []):
            question = Question(exam_id=exam.id, text=q_data['text'], marks_awarded=float(q_data['marks_awarded']), marks_deducted=float(q_data['marks_deducted']))
            db.session.add(question)
            db.session.commit()
            
            for opt_data in q_data.get('options', []):
                option = Option(question_id=question.id, text=opt_data['text'], is_correct=opt_data['is_correct'])
                db.session.add(option)
                
        # Allot students
        for sid in data.get('allotted_students', []):
            allotment = ExamAllotment(exam_id=exam.id, student_id=sid)
            db.session.add(allotment)
            # Create pending submission
            submission = ExamSubmission(exam_id=exam.id, student_id=sid, status='pending')
            db.session.add(submission)
            
        db.session.commit()
        return jsonify({'success': True, 'redirect': url_for('main.faculty_dashboard')})

    students = Student.query.all()
    return render_template('create_exam.html', students=students)

@main.route('/faculty/exam/<int:exam_id>/start', methods=['POST'])
@login_required
def start_exam(exam_id):
    if not isinstance(current_user._get_current_object(), User):
        return jsonify({'error': 'Unauthorized'}), 403
    exam = Exam.query.get_or_404(exam_id)
    if exam.faculty_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    exam.allow_start = not exam.allow_start
    if exam.allow_start and not exam.assignment_code:
        exam.assignment_code = f"EXAM-{uuid.uuid4().hex[:8].upper()}"
    db.session.commit()
    return jsonify({'success': True, 'allow_start': exam.allow_start, 'assignment_code': exam.assignment_code})

@main.route('/student/dashboard')
@login_required
def student_dashboard():
    if not isinstance(current_user._get_current_object(), Student):
        return redirect(url_for('main.faculty_dashboard'))
    submissions = ExamSubmission.query.filter_by(student_id=current_user.id).all()
    return render_template('student_dashboard.html', submissions=submissions)

@main.route('/student/exam/<int:exam_id>')
@login_required
def take_exam(exam_id):
    if not isinstance(current_user._get_current_object(), Student):
        return redirect(url_for('main.index'))
        
    submission = ExamSubmission.query.filter_by(exam_id=exam_id, student_id=current_user.id).first_or_404()
    if submission.status == 'completed':
        flash('You have already completed this exam.', 'warning')
        return redirect(url_for('main.student_dashboard'))
        
    if not submission.exam.allow_start:
        flash('This exam has not started yet.', 'warning')
        return redirect(url_for('main.student_dashboard'))
        
    if not submission.started_at:
        submission.started_at = datetime.utcnow()
        db.session.commit()
        
    return render_template('take_exam.html', exam=submission.exam, submission=submission)

@main.route('/student/exam/<int:exam_id>/submit', methods=['POST'])
@login_required
def submit_exam(exam_id):
    if not isinstance(current_user._get_current_object(), Student):
        return jsonify({'error': 'Unauthorized'}), 403
        
    submission = ExamSubmission.query.filter_by(exam_id=exam_id, student_id=current_user.id).first_or_404()
    if submission.status == 'completed':
        return jsonify({'error': 'Already submitted'}), 400
        
    data = request.json
    answers_data = data.get('answers', {})
    
    total_score = 0.0
    
    for q in submission.exam.questions:
        selected_option_ids = answers_data.get(str(q.id), [])
        if not isinstance(selected_option_ids, list):
            selected_option_ids = [selected_option_ids]
            
        correct_options = [opt for opt in q.options if opt.is_correct]
        correct_option_ids = [opt.id for opt in correct_options]
        
        for opt_id in selected_option_ids:
            if opt_id:
                ans = StudentAnswer(submission_id=submission.id, question_id=q.id, option_id=int(opt_id))
                db.session.add(ans)
                
        correctly_selected = sum(1 for oid in selected_option_ids if int(oid) in correct_option_ids)
        incorrectly_selected = sum(1 for oid in selected_option_ids if int(oid) not in correct_option_ids)
        
        q_score = 0
        if len(correct_options) > 0:
            q_score += (correctly_selected / len(correct_options)) * q.marks_awarded
            
        if incorrectly_selected > 0:
            q_score -= q.marks_deducted
            
        total_score += q_score
        
    submission.score = total_score
    submission.status = 'completed'
    submission.completed_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'redirect': url_for('main.student_dashboard')})

@main.route('/faculty/students')
@login_required
def faculty_students():
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('main.index'))
    students = Student.query.order_by(Student.roll_no).all()
    student_data = []
    for s in students:
        completed = ExamSubmission.query.filter_by(student_id=s.id, status='completed').count()
        total = ExamSubmission.query.filter_by(student_id=s.id).count()
        student_data.append({
            'student': s,
            'completed': completed,
            'total': total
        })
    return render_template('fac_students.html', student_data=student_data)

@main.route('/faculty/student/<int:student_id>/report')
@login_required
def faculty_student_report(student_id):
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('main.index'))
    student = Student.query.get_or_404(student_id)
    submissions = ExamSubmission.query.filter_by(student_id=student.id).all()
    return render_template('fac_student_report.html', student=student, submissions=submissions)

@main.route('/faculty/exams')
@login_required
def faculty_exams():
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('main.index'))
    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    exam_stats = []
    for exam in exams:
        submissions = ExamSubmission.query.filter_by(exam_id=exam.id).all()
        total_allotted = len(submissions)
        completed = [s for s in submissions if s.status == 'completed']
        completed_count = len(completed)
        scores = [s.score for s in completed if s.score is not None]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0
        max_score = max(scores) if scores else 0
        exam_stats.append({
            'exam': exam,
            'total_allotted': total_allotted,
            'completed_count': completed_count,
            'avg_score': avg_score,
            'max_score': max_score
        })
    return render_template('fac_exams.html', exam_stats=exam_stats)

@main.route('/faculty/exam/<int:exam_id>/stats')
@login_required
def exam_stats(exam_id):
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('main.index'))
    exam = Exam.query.get_or_404(exam_id)
    submissions = ExamSubmission.query.filter_by(exam_id=exam.id).all()
    scores = [s.score for s in submissions if s.status == 'completed' and s.score is not None]
    
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    
    return render_template('exam_stats.html', exam=exam, submissions=submissions, avg_score=avg_score, max_score=max_score, min_score=min_score)

