from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Add the name column
    started = db.Column(db.Boolean, default=False)

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    session = db.relationship('Session', back_populates='participants')

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    question_1 = db.Column(db.String(500), nullable=False)
    question_2 = db.Column(db.String(500), nullable=False)

Session.participants = db.relationship('Participant', order_by=Participant.id, back_populates='session')

