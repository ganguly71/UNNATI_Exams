from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Student, Exam, Question, Option, ExamAllotment, ExamSubmission, StudentAnswer, Assessment, SUBJECTS
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
            sid_int = int(sid)
            allotment = ExamAllotment(exam_id=exam.id, student_id=sid_int)
            db.session.add(allotment)
            # Create pending submission
            submission = ExamSubmission(exam_id=exam.id, student_id=sid_int, status='pending')
            db.session.add(submission)
            
        db.session.commit()
        return jsonify({'success': True, 'redirect': url_for('main.faculty_dashboard')})

    students = Student.query.all()
    departments = sorted(list(set(s.department for s in students if s.department)))
    return render_template('create_exam.html', students=students, subjects=SUBJECTS, departments=departments)

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
    elif not exam.allow_start:
        # Mark all pending submissions as absent (-1) when exam is stopped
        for submission in exam.submissions:
            if submission.status == 'pending':
                submission.score = -1.0
                submission.status = 'completed'
                submission.completed_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'allow_start': exam.allow_start, 'assignment_code': exam.assignment_code})

@main.route('/student/dashboard')
@login_required
def student_dashboard():
    if not isinstance(current_user._get_current_object(), Student):
        return redirect(url_for('main.faculty_dashboard'))
    
    student = current_user
    
    # 1. Fetch online exam submissions (from UNNATI-Exams)
    online_submissions = ExamSubmission.query.filter_by(student_id=student.id).all()
    
    # 2. Fetch manual assessments (from UNNATI)
    manual_assessments = Assessment.query.filter_by(student_id=student.id).all()
    
    # 3. Calculate counts
    online_total = len(online_submissions)
    online_completed = [s for s in online_submissions if s.status == 'completed']
    online_completed_count = len(online_completed)
    online_pending_count = online_total - online_completed_count
    
    manual_total = len(manual_assessments)
    manual_completed = [a for a in manual_assessments if a.marks != -1]
    manual_completed_count = len(manual_completed)
    manual_pending_count = manual_total - manual_completed_count # Absent manual assessments

    
    total_exams = online_total + manual_total
    completed_count = online_completed_count + manual_completed_count
    pending_count = online_pending_count + manual_pending_count
    
    # 4. Consolidate detailed list of completed tests/assignments for stats & chart
    completed_details = []
    total_percentage_sum = 0.0
    valid_scores_count = 0
    
    # Online exams
    for sub in online_submissions:
        if sub.status == 'completed':
            total_exam_marks = sum(q.marks_awarded for q in sub.exam.questions)
            percentage = 0.0
            # Only show scores in charts/stats after the teacher has stopped the exam (allow_start is False)
            if not sub.exam.allow_start:
                if total_exam_marks > 0 and sub.score is not None and sub.score != -1:
                    percentage = round((sub.score / total_exam_marks) * 100, 1)
                    total_percentage_sum += percentage
                    valid_scores_count += 1
                completed_details.append({
                    'title': sub.exam.title,
                    'subject': sub.exam.subject,
                    'score': sub.score,
                    'total_marks': total_exam_marks,
                    'percentage': percentage,
                    'date': sub.completed_at or sub.started_at,
                    'type': 'Online Exam'
                })

            
    # Manual assignments
    for a in manual_assessments:
        if a.marks != -1:
            total_marks = a.assignment_group.total_marks if a.assignment_group else 100.0
            percentage = round((a.marks / total_marks) * 100, 1) if total_marks > 0 else 0.0
            total_percentage_sum += percentage
            valid_scores_count += 1
            completed_details.append({
                'title': a.assignment_group.name if a.assignment_group else "Manual Assignment",
                'subject': a.subject,
                'score': a.marks,
                'total_marks': total_marks,
                'percentage': percentage,
                'date': a.date,
                'type': 'Manual Assignment'
            })
            
    # Sort completed_details by date to show correct chronological trend in chart
    completed_details.sort(key=lambda x: x['date'] if x['date'] else datetime.min)
    
    avg_percentage = round(total_percentage_sum / valid_scores_count, 1) if valid_scores_count > 0 else 0.0
    
    return render_template(
        'student_dashboard.html',
        submissions=online_submissions,
        manual_assessments=manual_assessments,
        student=student,
        total_exams=total_exams,
        completed_count=completed_count,
        pending_count=pending_count,
        avg_percentage=avg_percentage,
        completed_details=completed_details
    )

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
        scores = [s.score for s in completed if s.score is not None and s.score != -1]
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
    scores = [s.score for s in submissions if s.status == 'completed' and s.score is not None and s.score != -1]
    
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    
    return render_template('exam_stats.html', exam=exam, submissions=submissions, avg_score=avg_score, max_score=max_score, min_score=min_score)

@main.route('/faculty/student/<int:student_id>/edit', methods=['POST'])
@login_required
def faculty_edit_student(student_id):
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('main.index'))
        
    student = Student.query.get_or_404(student_id)
    student.name = request.form.get('name')
    student.roll_no = request.form.get('roll_no')
    student.semester = request.form.get('semester')
    student.department = request.form.get('department')
    
    password = request.form.get('password')
    if password:
        student.set_password(password)
        
    db.session.commit()
    flash('Student details updated successfully.', 'success')
    return redirect(url_for('main.faculty_students'))

@main.route('/faculty/exam/<int:exam_id>/delete', methods=['POST'])
@login_required
def delete_exam(exam_id):
    if not isinstance(current_user._get_current_object(), User):
        return jsonify({'error': 'Unauthorized'}), 403
    exam = Exam.query.get_or_404(exam_id)
    if exam.faculty_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    db.session.delete(exam)
    db.session.commit()
    return jsonify({'success': True})

@main.route('/faculty/exam/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_exam(exam_id):
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('main.index'))
        
    exam = Exam.query.get_or_404(exam_id)
    if exam.faculty_id != current_user.id and current_user.role != 'admin':
        flash('Unauthorized to edit this exam.', 'danger')
        return redirect(url_for('main.faculty_dashboard'))
        
    if exam.allow_start:
        flash('Cannot edit an exam while it is active.', 'warning')
        return redirect(url_for('main.faculty_dashboard'))
        
    if request.method == 'POST':
        data = request.json
        exam.title = data.get('title')
        exam.subject = data.get('subject')
        exam.time_limit_mins = int(data.get('time_limit_mins', 30))
        
        # 1. Update Student Allotments
        new_allotted_student_ids = [int(sid) for sid in data.get('allotted_students', [])]
        
        # Get existing allotments and submissions
        existing_allotments = ExamAllotment.query.filter_by(exam_id=exam.id).all()
        existing_allotted_ids = [a.student_id for a in existing_allotments]
        
        # Determine students to remove
        for allotment in existing_allotments:
            if allotment.student_id not in new_allotted_student_ids:
                db.session.delete(allotment)
                submission = ExamSubmission.query.filter_by(exam_id=exam.id, student_id=allotment.student_id).first()
                if submission:
                    StudentAnswer.query.filter_by(submission_id=submission.id).delete()
                    db.session.delete(submission)
                    
        # Determine students to add
        for sid in new_allotted_student_ids:
            if sid not in existing_allotted_ids:
                allotment = ExamAllotment(exam_id=exam.id, student_id=sid)
                db.session.add(allotment)
                
                submission = ExamSubmission.query.filter_by(exam_id=exam.id, student_id=sid).first()
                if not submission:
                    submission = ExamSubmission(exam_id=exam.id, student_id=sid, status='pending')
                    db.session.add(submission)
                else:
                    submission.status = 'pending'
                    submission.score = None
                    submission.started_at = None
                    submission.completed_at = None
        
        # 2. Update Questions and Options
        req_questions = data.get('questions', [])
        processed_question_ids = []
        
        for q_data in req_questions:
            q_id = q_data.get('id')
            question = None
            if q_id:
                try:
                    q_id = int(q_id)
                except ValueError:
                    q_id = None
            
            if q_id:
                question = Question.query.filter_by(id=q_id, exam_id=exam.id).first()
                
            if question:
                question.text = q_data['text']
                question.marks_awarded = float(q_data['marks_awarded'])
                question.marks_deducted = float(q_data['marks_deducted'])
            else:
                question = Question(exam_id=exam.id, text=q_data['text'], marks_awarded=float(q_data['marks_awarded']), marks_deducted=float(q_data['marks_deducted']))
                db.session.add(question)
                db.session.commit()
                
            processed_question_ids.append(question.id)
            
            # Update Options
            req_options = q_data.get('options', [])
            processed_option_ids = []
            
            for opt_data in req_options:
                opt_id = opt_data.get('id')
                option = None
                if opt_id:
                    try:
                        opt_id = int(opt_id)
                    except ValueError:
                        opt_id = None
                        
                if opt_id:
                    option = Option.query.filter_by(id=opt_id, question_id=question.id).first()
                    
                if option:
                    option.text = opt_data['text']
                    option.is_correct = opt_data['is_correct']
                else:
                    option = Option(question_id=question.id, text=opt_data['text'], is_correct=opt_data['is_correct'])
                    db.session.add(option)
                    db.session.commit()
                    
                processed_option_ids.append(option.id)
                
            # Delete options not in the payload
            existing_options = Option.query.filter_by(question_id=question.id).all()
            for opt in existing_options:
                if opt.id not in processed_option_ids:
                    StudentAnswer.query.filter_by(option_id=opt.id).delete()
                    db.session.delete(opt)
                    
        # Delete questions not in the payload
        existing_questions = Question.query.filter_by(exam_id=exam.id).all()
        for q in existing_questions:
            if q.id not in processed_question_ids:
                StudentAnswer.query.filter_by(question_id=q.id).delete()
                Option.query.filter_by(question_id=q.id).delete()
                db.session.delete(q)
                
        db.session.commit()
        return jsonify({'success': True, 'redirect': url_for('main.faculty_dashboard')})
        
    students = Student.query.all()
    departments = sorted(list(set(s.department for s in students if s.department)))
    allotted_student_ids = [a.student_id for a in ExamAllotment.query.filter_by(exam_id=exam.id).all()]
    
    return render_template('edit_exam.html', exam=exam, students=students, subjects=SUBJECTS, departments=departments, allotted_student_ids=allotted_student_ids)

@main.route('/faculty/exam/<int:exam_id>/download')
@login_required
def download_exam(exam_id):
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('main.index'))
        
    exam = Exam.query.get_or_404(exam_id)
    if exam.faculty_id != current_user.id and current_user.role != 'admin':
        flash('Unauthorized to download this exam.', 'danger')
        return redirect(url_for('main.faculty_dashboard'))
        
    if not exam.allow_start:
        flash('Cannot download the question paper when the exam is not active.', 'warning')
        return redirect(url_for('main.faculty_dashboard'))
        
    total_marks = sum(q.marks_awarded for q in exam.questions)
    faculty_name = exam.faculty.name if exam.faculty else "Unknown"
    created_time = exam.created_at.strftime('%Y-%m-%d %I:%M %p') if exam.created_at else "N/A"
    
    # Allotted students
    allotments = ExamAllotment.query.filter_by(exam_id=exam.id).all()
    assigned_students = []
    for allotment in allotments:
        student = allotment.student
        if student:
            assigned_students.append(f"- {student.name} (Roll No: {student.roll_no})")
            
    if not assigned_students:
        assigned_students_str = "*No students assigned to this exam.*"
    else:
        assigned_students_str = "\n".join(assigned_students)
        
    md = []
    md.append(f"# UNNATI EXAM QUESTION PAPER: {exam.title}")
    md.append("")
    md.append(f"**UNNATI EXAM ID:** {exam.assignment_code or f'EXAM-{exam.id}'}")
    md.append(f"**Subject of the test:** {exam.subject}")
    md.append(f"**Respected Faculty:** {faculty_name}")
    md.append(f"**Date and Time Created:** {created_time}")
    md.append(f"**Total Marks:** {total_marks}")
    md.append(f"**Time Limit:** {exam.time_limit_mins} minutes")
    md.append("")
    md.append("## Assigned Students")
    md.append(assigned_students_str)
    md.append("")
    md.append("---")
    md.append("")
    md.append("## Questions")
    md.append("")
    
    for idx, q in enumerate(exam.questions, 1):
        md.append(f"### Q{idx}. {q.text}")
        md.append(f"*Marks Awarded: {q.marks_awarded} | Marks Deducted: {q.marks_deducted}*")
        md.append("")
        for opt in q.options:
            if opt.is_correct:
                md.append(f"- [x] **{opt.text}** *(Correct)*")
            else:
                md.append(f"- [ ] {opt.text}")
        md.append("")
        
    markdown_content = "\n".join(md)
    filename = f"UNNATI_EXAM_{exam.assignment_code or exam.id}.md"
    
    return Response(
        markdown_content,
        mimetype="text/markdown",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

