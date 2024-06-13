import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session as flask_session, make_response
from functools import wraps
from models import db, Session as FeedbackSession, Participant, Feedback
import string
import random
from weasyprint import HTML

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Use absolute path for SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'feedback.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.before_request
def create_tables():
    db.create_all()

def admin_required(f):
    """Decorator to check if the admin is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not flask_session.get('admin_authenticated'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def index():
    if flask_session.get('admin_authenticated'):
        return render_template('index.html')
    if request.method == 'POST':
        secret_key = request.form['secret_key']
        if secret_key == app.config['SECRET_KEY']:
            flask_session['admin_authenticated'] = True
            return redirect(url_for('create_session'))
        else:
            flash('Invalid secret key!', 'danger')
    return render_template('index.html')

@app.route('/create_session', methods=['GET', 'POST'])
@admin_required
def create_session():
    if request.method == 'POST':
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        session_name = request.form['session_name']
        new_session = FeedbackSession(token=token, name=session_name)
        db.session.add(new_session)
        db.session.commit()
        session_url = url_for('register_feedback', token=token, _external=True)
        admin_url = url_for('admin_start_session', token=token, _external=True)
        return render_template('session_created.html', session_url=session_url, admin_url=admin_url)
    return render_template('create_session.html')

@app.route('/register_feedback/<token>', methods=['GET', 'POST'])
def register_feedback(token):
    session_data = FeedbackSession.query.filter_by(token=token).first_or_404()
    if request.method == 'POST':
        user_name = request.form['user_name']
        new_participant = Participant(session_id=session_data.id, name=user_name)
        db.session.add(new_participant)
        db.session.commit()
        flash('You have registered successfully!', 'success')
        return redirect(url_for('register_feedback', token=token))
    participants = Participant.query.filter_by(session_id=session_data.id).all()
    return render_template('register_feedback.html', session=session_data, participants=participants)

@app.route('/admin_start_session/<token>', methods=['GET', 'POST'])
@admin_required
def admin_start_session(token):
    session_data = FeedbackSession.query.filter_by(token=token).first_or_404()
    participants = Participant.query.filter_by(session_id=session_data.id).all()
    if request.method == 'POST':
        session_data.started = True
        db.session.commit()
        return redirect(url_for('monitor_feedback', token=token))
    return render_template('admin_start_session.html', session=session_data, participants=participants)

@app.route('/start_feedback/<token>', methods=['GET', 'POST'])
def start_feedback(token):
    session_data = FeedbackSession.query.filter_by(token=token).first_or_404()
    participants = Participant.query.filter_by(session_id=session_data.id).all()
    if request.method == 'POST':
        for participant in participants:
            question_1 = request.form[f'question_1_{participant.id}']
            question_2 = request.form[f'question_2_{participant.id}']
            feedback = Feedback(session_id=session_data.id, recipient_id=participant.id, question_1=question_1, question_2=question_2)
            db.session.add(feedback)
        db.session.commit()
        flash('Feedback submitted successfully!', 'success')
        return redirect(url_for('thanks_feedback', token=token))
    return render_template('start_feedback.html', session=session_data, participants=participants)

@app.route('/thanks_feedback/<token>', methods=['GET'])
def thanks_feedback(token):
    return render_template('thanks_feedback.html')

@app.route('/check_session_started/<token>', methods=['GET'])
def check_session_started(token):
    session_data = FeedbackSession.query.filter_by(token=token).first()
    if session_data and session_data.started:
        return jsonify({'started': True})
    return jsonify({'started': False})

@app.route('/monitor_feedback/<token>', methods=['GET'])
@admin_required
def monitor_feedback(token):
    session_data = FeedbackSession.query.filter_by(token=token).first_or_404()
    participants = Participant.query.filter_by(session_id=session_data.id).all()
    feedbacks = Feedback.query.filter_by(session_id=session_data.id).all()

    feedback_data = {participant.name: {'submitted': 0, 'total': len(participants) - 1} for participant in participants}

    for feedback in feedbacks:
        recipient = Participant.query.get(feedback.recipient_id)
        if recipient:
            feedback_data[recipient.name]['submitted'] += 1

    return render_template('monitor_feedback.html', session=session_data, participants=participants, feedback_data=feedback_data)

@app.route('/close_session/<token>', methods=['POST'])
@admin_required
def close_session(token):
    session_data = FeedbackSession.query.filter_by(token=token).first_or_404()
    session_data.started = False
    db.session.commit()
    return redirect(url_for('review_feedback', token=token))

@app.route('/review_feedback/<token>', methods=['GET'])
@admin_required
def review_feedback(token):
    session_data = FeedbackSession.query.filter_by(token=token).first_or_404()
    feedbacks = Feedback.query.filter_by(session_id=session_data.id).all()
    feedback_data = {}
    for feedback in feedbacks:
        participant = Participant.query.get(feedback.recipient_id)
        if participant.name not in feedback_data:
            feedback_data[participant.name] = []
        feedback_data[participant.name].append({
            'question_1': feedback.question_1,
            'question_2': feedback.question_2,
            'recipient_id': participant.id
        })
    return render_template('review_feedback.html', session=session_data, feedback_data=feedback_data)

@app.route('/admin_sessions', methods=['GET'])
@admin_required
def admin_sessions():
    sessions = FeedbackSession.query.all()
    return render_template('admin_sessions.html', sessions=sessions)

@app.route('/delete_session/<int:session_id>', methods=['POST'])
@admin_required
def delete_session(session_id):
    session_data = FeedbackSession.query.get_or_404(session_id)

    # Delete related feedback
    Feedback.query.filter_by(session_id=session_data.id).delete()

    # Delete related participants
    Participant.query.filter_by(session_id=session_data.id).delete()

    # Delete the session itself
    db.session.delete(session_data)
    db.session.commit()

    flash('Session deleted successfully!', 'success')
    return redirect(url_for('admin_sessions'))

@app.route('/download_feedback/<token>/<participant_id>', methods=['GET'])
@admin_required
def download_feedback(token, participant_id):
    session_data = FeedbackSession.query.filter_by(token=token).first_or_404()
    participant = Participant.query.get_or_404(participant_id)
    feedbacks = Feedback.query.filter_by(session_id=session_data.id, recipient_id=participant.id).all()

    rendered_html = render_template('feedback_pdf.html', participant=participant, feedbacks=feedbacks)
    pdf = HTML(string=rendered_html).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=feedback_{participant.name}.pdf'

    return response

@app.route('/logout')
def logout():
    flask_session.pop('admin_authenticated', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(os.path.join(basedir, 'instance')):
        os.makedirs(os.path.join(basedir, 'instance'))
    app.run(debug=True)

