import unittest
from app import create_app, db
from app.models import Country, Continent, User

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test_secret'
    REST_COUNTRIES_API_URL = "https://restcountries.com/v3.1/independent?status=true"

class GeographyAppTestCase(unittest.TestCase):
    def setUp(self):
        # Create the app with a test configuration
        self.app = create_app(TestConfig)
        # The test client can be used to make requests to the application
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Setup initial data for testing
            cont = Continent(name="TestContinent", description="A test continent.")
            db.session.add(cont)
            db.session.commit()
            
            c1 = Country(
                name="Testland",
                capital="Testville",
                region="Testia",
                continent_name="TestContinent",
                trivia="A test country.",
                flag_url_svg="http://test.com/flag.svg"
            )
            db.session.add(c1)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_countries_page(self):
        response = self.client.get('/countries')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Testland', response.data)

    def test_country_detail_page(self):
        response = self.client.get('/country/Testland')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Testville', response.data)

    def test_country_detail_with_borders_and_coordinates(self):
        with self.app.app_context():
            c2 = Country(
                name="Borderland",
                cca3="BRL",
                capital="Borderville",
                region="Borderia",
                continent_name="TestContinent",
                flag_url_svg="http://test.com/border.svg"
            )
            db.session.add(c2)
            
            c1 = Country.query.filter_by(name="Testland").first()
            c1.cca3 = "TSL"
            c1.latitude = 12.34
            c1.longitude = 56.78
            c1.borders = ["BRL"]
            db.session.commit()
            
        response = self.client.get('/country/Testland')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Lat: 12.3400', response.data)
        self.assertIn(b'Lng: 56.7800', response.data)
        self.assertIn(b'Borderland', response.data)

    def test_explore_feature(self):
        # Test plural bug fix
        response = self.client.get('/explore/oceans')
        self.assertEqual(response.status_code, 200)

    def test_quiz_get(self):
        with self.client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['lives'] = 3
        response = self.client.get('/quiz')
        self.assertEqual(response.status_code, 200)
        
    def test_quiz_post_no_session(self):
        # Testing posting without getting the question first (no session)
        # Should throw 400 error as we expected
        response = self.client.post('/quiz', data={'username': 'testuser', 'answer': 'Testville'})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Missing data', response.data)

    # --- New gamification tests ---

    def test_daily_challenge_redirect_if_not_logged_in(self):
        response = self.client.get('/daily')
        self.assertEqual(response.status_code, 302)

    def test_daily_challenge_page(self):
        with self.app.app_context():
            user = User(username='dailyuser', score=0, xp=0)
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess['username'] = 'dailyuser'
        response = self.client.get('/daily')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Daily Challenge', response.data)

    def test_collection_page(self):
        with self.app.app_context():
            user = User(username='collector', score=0, xp=0)
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess['username'] = 'collector'
        response = self.client.get('/collection')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Collection', response.data)

    def test_region_progress_page(self):
        with self.app.app_context():
            user = User(username='explorer', score=0, xp=0)
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess['username'] = 'explorer'
        response = self.client.get('/regions')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Region', response.data)

    def test_quiz_mode_selection(self):
        with self.client.session_transaction() as sess:
            sess['username'] = 'testuser'
        response = self.client.get('/quiz')
        self.assertEqual(response.status_code, 200)
        # Should show mode selection since no lives in session
        self.assertIn(b'Lightning', response.data)

    def test_quiz_lightning_mode_start(self):
        with self.client.session_transaction() as sess:
            sess['username'] = 'testuser'
        response = self.client.post('/quiz/lightning', data={'start_quiz': '1', 'mode': 'lightning'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_user_xp_level_properties(self):
        with self.app.app_context():
            user = User(username='leveltest', score=100, xp=200)
            db.session.add(user)
            db.session.commit()
            self.assertEqual(user.level, 3)
            self.assertEqual(user.rank_name, 'Trail Scout')

    def test_leaderboard_page(self):
        response = self.client.get('/leaderboard')
        self.assertEqual(response.status_code, 200)

    def test_leaderboard_page(self):
        with self.app.app_context():
            u1 = User(username='testuser', score=100)
            db.session.add(u1)
            db.session.commit()
            
        response = self.client.get('/leaderboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'testuser', response.data)

    # --- Learning & Progress Tracking tests ---

    def test_progress_report_redirect_if_not_logged_in(self):
        response = self.client.get('/progress')
        self.assertEqual(response.status_code, 302)

    def test_progress_report_page(self):
        with self.app.app_context():
            user = User(username='progressuser', score=0, xp=0)
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess['username'] = 'progressuser'
        response = self.client.get('/progress')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Progress', response.data)

    def test_quiz_history_page(self):
        with self.app.app_context():
            user = User(username='historyuser', score=0, xp=0)
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess['username'] = 'historyuser'
        response = self.client.get('/history')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Quiz History', response.data)

    def test_quiz_history_filter_wrong(self):
        with self.app.app_context():
            user = User(username='filteruser', score=0, xp=0)
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess['username'] = 'filteruser'
        response = self.client.get('/history?filter=wrong')
        self.assertEqual(response.status_code, 200)

    def test_mastery_page(self):
        with self.app.app_context():
            user = User(username='masteryuser', score=0, xp=0)
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess['username'] = 'masteryuser'
        response = self.client.get('/mastery')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Mastery', response.data)

    def test_skill_stats(self):
        from app.game_logic import get_skill_stats
        with self.app.app_context():
            user = User(username='skilluser', score=0, xp=0)
            db.session.add(user)
            db.session.commit()
            stats = get_skill_stats(user.id)
            self.assertIn('capital', stats)
            self.assertEqual(stats['capital']['total'], 0)
            self.assertEqual(stats['capital']['pct'], 0)

    def test_mastery_summary(self):
        from app.game_logic import get_mastery_summary
        with self.app.app_context():
            user = User(username='mastsumuser', score=0, xp=0)
            db.session.add(user)
            db.session.commit()
            summary = get_mastery_summary(user.id)
            self.assertEqual(summary['mastered'], 0)
            self.assertEqual(summary['in_progress'], 0)
            self.assertGreaterEqual(summary['total'], 0)

    def test_weekly_report_empty(self):
        from app.game_logic import get_weekly_report
        with self.app.app_context():
            user = User(username='weeklyuser', score=0, xp=0)
            db.session.add(user)
            db.session.commit()
            report = get_weekly_report(user.id)
            self.assertEqual(report['total_questions'], 0)
            self.assertEqual(report['accuracy'], 0)

if __name__ == '__main__':
    unittest.main()
