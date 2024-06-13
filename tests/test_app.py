import unittest
from flask_testing import TestCase
from app import app, db, FeedbackSession, Participant, Feedback

class FeedbackAppTestCase(TestCase):

    def create_app(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'your_secret_key'
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_home_page(self):
        response = self.client.get('/')
        self.assert200(response)
        self.assertIn(b'Welcome to the Feedback App', response.data)

    def test_create_session(self):
        self.client.post('/', data=dict(secret_key='test_secret_key'))
        response = self.client.post('/create_session', data=dict(session_name='Test Session'))
        self.assert200(response)
        self.assertIn(b'Session Created', response.data)
        self.assertIn(b'Test Session', response.data)

    def test_register_feedback(self):
        self.client.post('/', data=dict(secret_key='test_secret_key'))
        self.client.post('/create_session', data=dict(session_name='Test Session'))
        session = FeedbackSession.query.first()
        token = session.token

        response = self.client.post(f'/register_feedback/{token}', data=dict(user_name='John Doe'))
        self.assert200(response)
        self.assertIn(b'You have registered successfully!', response.data)
        participant = Participant.query.first()
        self.assertEqual(participant.name, 'John Doe')

    def test_start_feedback(self):
        self.client.post('/', data=dict(secret_key='test_secret_key'))
        self.client.post('/create_session', data=dict(session_name='Test Session'))
        session = FeedbackSession.query.first()
        token = session.token
        self.client.post(f'/register_feedback/{token}', data=dict(user_name='John Doe'))

        response = self.client.post(f'/admin_start_session/{token}')
        self.assertRedirects(response, f'/monitor_feedback/{token}')
        session = FeedbackSession.query.first()
        self.assertTrue(session.started)

    def test_feedback_submission(self):
        self.client.post('/', data=dict(secret_key='test_secret_key'))
        self.client.post('/create_session', data=dict(session_name='Test Session'))
        session = FeedbackSession.query.first()
        token = session.token
        self.client.post(f'/register_feedback/{token}', data=dict(user_name='John Doe'))
        self.client.post(f'/admin_start_session/{token}')
        self.client.post(f'/start_feedback/{token}', data={
            'question_1_1': 'Valuable quality',
            'question_2_1': 'Helpful advice'
        })

        feedback = Feedback.query.first()
        self.assertEqual(feedback.question_1, 'Valuable quality')
        self.assertEqual(feedback.question_2, 'Helpful advice')

    def test_review_feedback(self):
        self.client.post('/', data=dict(secret_key='test_secret_key'))
        self.client.post('/create_session', data=dict(session_name='Test Session'))
        session = FeedbackSession.query.first()
        token = session.token
        self.client.post(f'/register_feedback/{token}', data=dict(user_name='John Doe'))
        self.client.post(f'/admin_start_session/{token}')
        self.client.post(f'/start_feedback/{token}', data={
            'question_1_1': 'Valuable quality',
            'question_2_1': 'Helpful advice'
        })
        response = self.client.get(f'/review_feedback/{token}')
        self.assert200(response)
        self.assertIn(b'Valuable quality', response.data)
        self.assertIn(b'Helpful advice', response.data)

    def test_delete_session(self):
        self.client.post('/', data=dict(secret_key='test_secret_key'))
        self.client.post('/create_session', data=dict(session_name='Test Session'))
        session = FeedbackSession.query.first()
        session_id = session.id
        token = session.token
        self.client.post(f'/register_feedback/{token}', data=dict(user_name='John Doe'))
        response = self.client.post(f'/delete_session/{session_id}')
        self.assertRedirects(response, '/admin_sessions')
        session = FeedbackSession.query.get(session_id)
        self.assertIsNone(session)

if __name__ == '__main__':
    unittest.main()

