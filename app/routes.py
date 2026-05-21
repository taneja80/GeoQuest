# File: geography_app/app/routes.py

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from .models import db, Country, Continent, User, UserAchievement, CollectedCountry, RegionProgress, DailyCompletion, QuizAttempt, CountryMastery, MissionProgress
from . import game_logic
from datetime import date
import random

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    continents = Continent.query.all()
    # For a more engaging home, pick a few random countries or facts
    random_countries_query = Country.query.filter(Country.flag_url_svg != None).order_by(db.func.random()).limit(3)
    random_countries = random_countries_query.all()
    
    # If not enough countries with SVG flags, try PNG or just any
    if len(random_countries) < 3:
        random_countries = Country.query.order_by(db.func.random()).limit(3).all()

    return render_template('index.html', continents=continents, random_countries=random_countries)

@main_bp.route('/countries')
def list_countries():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '')
    
    query = Country.query
    if search_term:
        query = query.filter(Country.name.ilike(f'%{search_term}%'))
    
    countries_pagination = query.order_by(Country.name).paginate(page=page, per_page=20, error_out=False)
    return render_template('countries.html', countries_pagination=countries_pagination, search_term=search_term)

@main_bp.route('/country/<name>')
def country_detail(name):
    # Try to URL decode the name, as some country names might have spaces or special chars
    # that get URL-encoded. However, REST Countries API uses common names directly.
    # For now, assume name is as stored. If issues, consider unquote from urllib.parse
    country = Country.query.filter_by(name=name).first_or_404()
    
    border_countries = []
    if country.borders:
        border_countries = Country.query.filter(Country.cca3.in_(country.borders)).order_by(Country.name).all()
        
    return render_template('country_detail.html', country=country, border_countries=border_countries)

@main_bp.route('/continents')
def list_continents():
    continents = Continent.query.order_by(Continent.name).all()
    return render_template('continents.html', continents=continents)

@main_bp.route('/continent/<name>')
def continent_detail(name):
    continent = Continent.query.filter_by(name=name).first_or_404()
    countries_in_continent = Country.query.filter_by(continent_name=name).order_by(Country.name).all()
    return render_template('continent_detail.html', continent=continent, countries=countries_in_continent)


# --- User Authentication & Profiles ---

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('main.index'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = "Please fill in all fields."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        else:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                error = "Username is already taken."
            else:
                user = User(username=username, score=0)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()

                session['username'] = user.username
                session['user_id'] = user.id
                return redirect(url_for('main.index'))

    return render_template('register.html', error=error)


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('main.index'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = user.username
            session['user_id'] = user.id
            return redirect(url_for('main.index'))
        else:
            error = "Invalid username or password."

    return render_template('login.html', error=error)


@main_bp.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    session.pop('lives', None)
    session.pop('streak', None)
    session.pop('streak_no_hints', None)
    return redirect(url_for('main.index'))


@main_bp.route('/profile')
def my_profile():
    if 'username' not in session:
        return redirect(url_for('main.login'))
    return redirect(url_for('main.profile', username=session['username']))


@main_bp.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    accuracy = 0
    if user.total_questions_answered and user.total_questions_answered > 0:
        accuracy = round((user.correct_answers_count / user.total_questions_answered) * 100)

    rank = user.rank_name

    unlocked_ids = {a.achievement_id for a in user.achievements}

    achievements_list = []
    for ach_id, data in game_logic.ACHIEVEMENTS.items():
        is_unlocked = ach_id in unlocked_ids
        unlocked_time = None
        if is_unlocked:
            record = next((a for a in user.achievements if a.achievement_id == ach_id), None)
            if record:
                unlocked_time = record.unlocked_at.strftime('%Y-%m-%d %H:%M')

        achievements_list.append({
            'id': ach_id,
            'title': data['title'],
            'description': data['description'],
            'icon': data['icon'],
            'bonus': data['bonus'],
            'unlocked': is_unlocked,
            'unlocked_at': unlocked_time
        })

    collected_count = CollectedCountry.query.filter_by(user_id=user.id).count()
    total_countries = Country.query.count()

    skill_stats = game_logic.get_skill_stats(user.id)
    mastery_summary = game_logic.get_mastery_summary(user.id)

    return render_template(
        'profile.html',
        user=user,
        accuracy=accuracy,
        rank=rank,
        achievements=achievements_list,
        collected_count=collected_count,
        total_countries=total_countries,
        skill_stats=skill_stats,
        mastery_summary=mastery_summary,
    )


# --- Quiz Routes ---
@main_bp.route('/quiz', methods=['GET', 'POST'])
@main_bp.route('/quiz/<mode>', methods=['GET', 'POST'])
def quiz(mode='classic'):
    # Validate mode
    if mode not in game_logic.QUIZ_MODES:
        mode = 'classic'
    mode_cfg = game_logic.QUIZ_MODES[mode]

    if request.method == 'POST':
        data = request.form

        # 1. "Start Quiz" login POST
        if 'start_quiz' in data:
            if 'username' not in session or not session['username']:
                session['username'] = data.get('username', '').strip() or 'Hero'
            mode = data.get('mode', 'classic')
            if mode not in game_logic.QUIZ_MODES:
                mode = 'classic'
            mode_cfg = game_logic.QUIZ_MODES[mode]
            session['quiz_mode']     = mode
            session['lives']         = mode_cfg['lives']
            session['streak']        = 0
            session['questions_answered_in_mode'] = 0
            return redirect(url_for('main.quiz', mode=mode))

        # 2. Quiz Answer POST
        mode = session.get('quiz_mode', 'classic')
        if mode not in game_logic.QUIZ_MODES:
            mode = 'classic'
        mode_cfg = game_logic.QUIZ_MODES[mode]

        username                  = session.get('username')
        submitted_answer          = data.get('answer')
        question_id_from_session  = session.get('current_question_id')
        correct_answer_from_session = session.get('current_correct_answer')

        try:
            time_taken_ms = int(data.get('time_taken_ms', 0)) or None
        except (ValueError, TypeError):
            time_taken_ms = None

        if not username or not submitted_answer or not question_id_from_session or correct_answer_from_session is None:
            current_app.logger.warning(
                f"Quiz POST missing data: user={username}, answer={submitted_answer}"
            )
            return jsonify({'error': 'Missing data or session expired. Please refresh.'}), 400

        result = game_logic.check_answer_and_update_score(
            username,
            question_id_from_session,
            submitted_answer,
            correct_answer_from_session,
            time_taken_ms=time_taken_ms,
            xp_multiplier=mode_cfg['xp_multiplier'],
            mode=mode,
        )

        session.pop('current_question_id', None)
        session.pop('current_correct_answer', None)

        # Track questions answered in mode for question_limit modes
        session['questions_answered_in_mode'] = session.get('questions_answered_in_mode', 0) + 1
        q_limit = mode_cfg['question_limit']
        if q_limit and session['questions_answered_in_mode'] >= q_limit:
            result['game_over'] = True

        # Build feedback string
        if result['correct']:
            parts = [f'Correct! +{result["base_points"]} pts']
            if result['speed_bonus']:  parts.append(f'⚡ Speed +{result["speed_bonus"]}')
            if result['streak_bonus']: parts.append(f'🔥 Streak ×{1 + result["streak_bonus"]//10} +{result["streak_bonus"]}')
            feedback = '  '.join(parts)
        else:
            feedback = f'Oops! The answer was {result["correct_answer_was"]}.'

        response_data = {
            'correct':             result['correct'],
            'points':              result['points_earned'],
            'base_points':         result['base_points'],
            'speed_bonus':         result['speed_bonus'],
            'streak_bonus':        result['streak_bonus'],
            'streak':              result['streak'],
            'total_score':         result['total_score'],
            'correct_answer_was':  result['correct_answer_was'],
            'feedback':            feedback,
            'lives':               result['lives'],
            'game_over':           result['game_over'],
            'newly_unlocked':      result.get('newly_unlocked', []),
        }

        if result['game_over']:
            session.pop('lives', None)
            session.pop('streak', None)
            session.pop('streak_no_hints', None)
            session.pop('quiz_mode', None)
            session.pop('questions_answered_in_mode', None)

        return jsonify(response_data)

    # GET — serve next question
    if 'username' not in session:
        return redirect(url_for('main.login'))

    if 'lives' not in session or session.get('lives', 0) <= 0:
        return render_template('quiz_login.html', modes=game_logic.QUIZ_MODES)

    # Check question limit for mode
    active_mode = session.get('quiz_mode', 'classic')
    active_cfg = game_logic.QUIZ_MODES.get(active_mode, game_logic.QUIZ_MODES['classic'])
    q_limit = active_cfg['question_limit']
    if q_limit and session.get('questions_answered_in_mode', 0) >= q_limit:
        session.pop('lives', None)
        session.pop('quiz_mode', None)
        session.pop('questions_answered_in_mode', None)
        return render_template('quiz_login.html', modes=game_logic.QUIZ_MODES)

    question_data = game_logic.get_quiz_question()
    if not question_data:
        current_app.logger.error('Failed to generate a quiz question.')
        return render_template('quiz.html', question=None,
                               error_message='Could not load a question. Please refresh!')

    session['current_question_id']    = question_data['id']
    session['current_correct_answer'] = question_data['correct_answer']
    session['current_options']        = question_data['options']
    session['current_question_text']  = question_data['question_text']

    question_for_template = {
        'question':      question_data['question_text'],
        'image_url':     question_data.get('image_url'),
        'options':       question_data['options'],
        'question_type': question_data.get('type', ''),
        'difficulty':    question_data.get('difficulty', 1),
    }
    return render_template(
        'quiz.html',
        question=question_for_template,
        streak=session.get('streak', 0),
        score=0,
        mode=active_mode,
        mode_cfg=active_cfg,
    )


@main_bp.route('/quiz/hint', methods=['POST'])
def quiz_hint():
    """Remove 2 wrong options. Costs HINT_COST points from the user's score."""
    username = session.get('username')
    correct  = session.get('current_correct_answer')
    options  = session.get('current_options', [])

    if not username or not correct or not options:
        return jsonify({'error': 'No active question.'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, score=0)
        db.session.add(user)
        db.session.commit()

    # Deduct hint cost (floor at 0)
    cost = game_logic.HINT_COST
    user.score = max(0, user.score - cost)
    db.session.commit()

    # Return the 2 options to ELIMINATE (wrong ones)
    wrong = [o for o in options if o != correct]
    random.shuffle(wrong)
    eliminate = wrong[:2]

    return jsonify({
        'eliminate':   eliminate,
        'cost':        cost,
        'total_score': user.score,
    })


@main_bp.route('/leaderboard')
def leaderboard():
    top_users = game_logic.get_leaderboard()
    return render_template('leaderboard.html', users=top_users)

# Helper to get model class dynamically (use with caution or define explicitly)
def get_model_by_name(model_name_singular):
    # This is a simplified example. Real-world usage might need more robust mapping
    # or direct imports if the number of models is manageable.
    # Ensure models are imported in models.py and accessible via db.Model._decl_class_registry
    # or a custom registry.
    # For now, direct mapping is safer.
    from .models import Ocean, Mountain, River, Forest, Desert, Volcano, Wonder
    model_map = {
        "ocean": Ocean,
        "mountain": Mountain,
        "river": River,
        "forest": Forest,
        "desert": Desert,
        "volcano": Volcano,
        "wonder": Wonder,
    }
    return model_map.get(model_name_singular.lower())


@main_bp.route('/explore/<feature_type>')
def explore_feature(feature_type):
    items = []
    
    # Handle plural-to-singular: "volcanoes" → "volcano", "wonders" → "wonder"
    if feature_type.endswith('oes'):
        singular_name = feature_type[:-2]  # strip "es" → "volcanoe" → "volcano"
    elif feature_type.endswith('s'):
        singular_name = feature_type[:-1]  # strip "s" → "wonder"
    else:
        singular_name = feature_type
    ModelClass = get_model_by_name(singular_name)
    
    if ModelClass:
        # Basic check for a 'name' attribute for ordering, adapt if models differ
        if hasattr(ModelClass, 'name'):
            items = ModelClass.query.order_by(ModelClass.name).all()
        else:
            items = ModelClass.query.all() # Fallback if no 'name' attribute
    else:
        current_app.logger.warning(f"No model found for feature type: {feature_type}")
        # Optionally, render a specific "not found" or "coming soon" for this feature type
        # For now, let explore.html handle it if items is empty.

    # Capitalize feature_type for display in the template
    display_feature_type = feature_type.capitalize()
    return render_template('explore.html', items=items, feature_type=display_feature_type)

@main_bp.route('/map')
def world_map():
    return render_template('map.html')


# --- Daily Challenge ---
@main_bp.route('/daily', methods=['GET', 'POST'])
def daily_challenge():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    today = date.today()
    already_done = DailyCompletion.query.filter_by(user_id=user.id, completed_date=today).first() is not None

    if request.method == 'POST':
        if already_done:
            return jsonify({'error': 'Already completed today\'s challenge!'}), 400

        submitted_answer = request.form.get('answer')
        correct_answer = session.get('daily_correct_answer')

        if not submitted_answer or not correct_answer:
            return jsonify({'error': 'Missing data. Please refresh.'}), 400

        is_correct = (submitted_answer == correct_answer)
        bonus_info = {'bonus': 0, 'daily_streak': user.daily_streak or 0}

        if is_correct:
            bonus_info = game_logic.complete_daily_challenge(user)

        session.pop('daily_correct_answer', None)
        session.pop('daily_question_id', None)

        return jsonify({
            'correct': is_correct,
            'correct_answer_was': correct_answer,
            'bonus': bonus_info.get('bonus', 0),
            'daily_streak': bonus_info.get('daily_streak', user.daily_streak or 0),
            'total_score': user.score,
            'xp': user.xp or 0,
            'level': user.level,
        })

    # GET
    question = game_logic.get_daily_question()
    if question:
        session['daily_correct_answer'] = question['correct_answer']
        session['daily_question_id'] = question['id']

    return render_template('daily.html', question=question, already_done=already_done,
                           daily_streak=user.daily_streak or 0)


# --- Collection ---
@main_bp.route('/collection')
def collection():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    collected = CollectedCountry.query.filter_by(user_id=user.id).all()
    collected_ids = {c.country_id for c in collected}
    collected_countries = Country.query.filter(Country.id.in_(collected_ids)).order_by(Country.name).all() if collected_ids else []
    total_countries = Country.query.count()

    return render_template('collection.html',
                           collected=collected_countries,
                           total=total_countries,
                           count=len(collected_countries))


# --- Region Progress ---
@main_bp.route('/regions')
def region_progress():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    all_continents = ['Africa', 'Antarctica', 'Asia', 'Europe', 'North America', 'Oceania', 'South America']
    continent_icons = {
        'Africa': '🌍', 'Antarctica': '🧊', 'Asia': '🏯', 'Europe': '🗼',
        'North America': '🗽', 'Oceania': '🦘', 'South America': '🌿'
    }

    progress_map = {}
    for rp in user.region_progress:
        progress_map[rp.region_name] = rp

    regions = []
    for name in all_continents:
        rp = progress_map.get(name)
        correct = rp.correct_count if rp else 0
        unlocked = rp.unlocked if rp else False
        pct = min(100, round(correct / game_logic.REGION_UNLOCK_THRESHOLD * 100))
        regions.append({
            'name': name,
            'icon': continent_icons.get(name, '🗺️'),
            'correct': correct,
            'threshold': game_logic.REGION_UNLOCK_THRESHOLD,
            'unlocked': unlocked,
            'pct': pct,
        })

    return render_template('region_progress.html', regions=regions,
                           unlocked_count=sum(1 for r in regions if r['unlocked']),
                           total_count=len(regions))


# --- Progress Report ---
@main_bp.route('/progress')
def progress_report():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    report = game_logic.get_weekly_report(user.id)
    skill_stats = game_logic.get_skill_stats(user.id)
    mastery_summary = game_logic.get_mastery_summary(user.id)

    return render_template('progress.html',
                           user=user, report=report,
                           skill_stats=skill_stats,
                           mastery=mastery_summary)


# --- Quiz History ---
@main_bp.route('/history')
def quiz_history():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    show_filter = request.args.get('filter', 'all')  # all, wrong, correct
    limit = request.args.get('limit', 50, type=int)

    if show_filter == 'wrong':
        attempts = QuizAttempt.query.filter_by(user_id=user.id, is_correct=False) \
            .order_by(QuizAttempt.created_at.desc()).limit(limit).all()
    elif show_filter == 'correct':
        attempts = QuizAttempt.query.filter_by(user_id=user.id, is_correct=True) \
            .order_by(QuizAttempt.created_at.desc()).limit(limit).all()
    else:
        attempts = game_logic.get_quiz_history(user.id, limit=limit)

    return render_template('history.html', attempts=attempts, current_filter=show_filter)


# --- Mastery Page ---
@main_bp.route('/mastery')
def mastery():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    mastery_data = game_logic.get_mastery_summary(user.id)

    # Group masteries by star level
    by_stars = {i: [] for i in range(6)}
    for m in mastery_data['masteries']:
        country = Country.query.get(m.country_id)
        if country:
            by_stars[m.stars].append({
                'country': country,
                'mastery': m,
            })

    return render_template('mastery.html', mastery=mastery_data, by_stars=by_stars)


# ─────────────────────────────────────────────
# NEW CONTENT & MODES
# ─────────────────────────────────────────────

# --- Two Truths and a Lie ---
@main_bp.route('/two-truths', methods=['GET', 'POST'])
def two_truths():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        submitted_index = request.form.get('answer_index')
        correct_index = session.get('ttal_correct_index')
        lie_text = session.get('ttal_lie')

        if submitted_index is None or correct_index is None:
            return jsonify({'error': 'Missing data. Please refresh.'}), 400

        is_correct = (int(submitted_index) == int(correct_index))

        if is_correct:
            user.xp = (user.xp or 0) + 15
            user.score += 15
            user.correct_answers_count = (user.correct_answers_count or 0) + 1
        user.total_questions_answered = (user.total_questions_answered or 0) + 1

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        session.pop('ttal_correct_index', None)
        session.pop('ttal_lie', None)

        return jsonify({
            'correct': is_correct,
            'correct_index': correct_index,
            'lie_text': lie_text,
            'xp': user.xp or 0,
        })

    # GET
    question = game_logic.generate_two_truths_question()
    if question:
        session['ttal_correct_index'] = question['correct_index']
        session['ttal_lie'] = question['lie']

    return render_template('two_truths.html', question=question)


# --- Comparison Quiz ---
@main_bp.route('/comparison', methods=['GET', 'POST'])
def comparison_quiz():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        submitted = request.form.get('answer')
        correct = session.get('cmp_correct')

        if not submitted or not correct:
            return jsonify({'error': 'Missing data. Please refresh.'}), 400

        is_correct = (submitted == correct)
        if is_correct:
            user.xp = (user.xp or 0) + 12
            user.score += 12
            user.correct_answers_count = (user.correct_answers_count or 0) + 1
        user.total_questions_answered = (user.total_questions_answered or 0) + 1

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        session.pop('cmp_correct', None)

        return jsonify({
            'correct': is_correct,
            'correct_answer': correct,
            'xp': user.xp or 0,
        })

    # GET
    question = game_logic.generate_comparison_question()
    if question:
        session['cmp_correct'] = question['correct_answer']

    return render_template('comparison.html', question=question)


# --- Fact Match Mini-Game ---
@main_bp.route('/fact-match')
def fact_match():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    round_data = game_logic.generate_fact_match_round(6)
    return render_template('fact_match.html', round_data=round_data)


@main_bp.route('/fact-match/complete', methods=['POST'])
def fact_match_complete():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    correct_count = data.get('correct', 0)
    total = data.get('total', 0)

    xp_earned = correct_count * 8
    user.xp = (user.xp or 0) + xp_earned
    user.score += xp_earned
    user.correct_answers_count = (user.correct_answers_count or 0) + correct_count
    user.total_questions_answered = (user.total_questions_answered or 0) + total

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({'xp_earned': xp_earned, 'total_xp': user.xp or 0})


# --- Map Quiz (Where in the World) ---
@main_bp.route('/map-quiz')
def map_quiz():
    if 'username' not in session:
        return redirect(url_for('main.login'))
    return render_template('map_quiz.html')


@main_bp.route('/api/map-quiz-question')
def api_map_quiz_question():
    question = game_logic.generate_map_quiz_question()
    if not question:
        return jsonify({'error': 'Could not generate question'}), 500
    # Don't send the exact answer location to the client
    return jsonify({
        'country_name': question['country_name'],
        'flag_url': question['flag_url'],
        'target_lat': question['target_lat'],
        'target_lng': question['target_lng'],
    })


@main_bp.route('/api/map-quiz-answer', methods=['POST'])
def api_map_quiz_answer():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    distance_km = data.get('distance_km', 9999)

    # Score based on distance: <500km = perfect, <1500km = good, <3000km = ok
    is_correct = distance_km < 1500
    xp = 0
    if distance_km < 500:
        xp = 20
    elif distance_km < 1500:
        xp = 12
    elif distance_km < 3000:
        xp = 5

    if xp:
        user.xp = (user.xp or 0) + xp
        user.score += xp
    if is_correct:
        user.correct_answers_count = (user.correct_answers_count or 0) + 1
    user.total_questions_answered = (user.total_questions_answered or 0) + 1

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({
        'correct': is_correct,
        'xp_earned': xp,
        'distance_km': round(distance_km),
        'total_xp': user.xp or 0,
    })


# --- Story Mode / Missions ---
@main_bp.route('/missions')
def missions():
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    mission_list = game_logic.get_mission_status(user.id)
    return render_template('missions.html', missions=mission_list)


@main_bp.route('/mission/<mission_id>', methods=['GET', 'POST'])
def mission_play(mission_id):
    if 'username' not in session:
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('main.login'))

    mission_cfg = game_logic.MISSIONS.get(mission_id)
    if not mission_cfg:
        return redirect(url_for('main.missions'))

    progress = MissionProgress.query.filter_by(user_id=user.id, mission_id=mission_id).first()
    if not progress:
        progress = MissionProgress(user_id=user.id, mission_id=mission_id,
                                    questions_completed=0, correct_count=0)
        db.session.add(progress)
        db.session.commit()

    if request.method == 'POST':
        if progress.completed:
            return jsonify({'error': 'Mission already completed!'}), 400

        submitted = request.form.get('answer')
        correct = session.get('mission_correct_answer')
        q_id = session.get('mission_question_id')

        if not submitted or not correct:
            return jsonify({'error': 'Missing data'}), 400

        is_correct = (submitted == correct)
        progress.questions_completed += 1
        if is_correct:
            progress.correct_count += 1
            user.xp = (user.xp or 0) + 15
            user.score += 15

        # Check if mission complete
        mission_done = progress.questions_completed >= mission_cfg['question_count']
        newly_unlocked = []
        if mission_done and not progress.completed:
            progress.completed = True
            progress.completed_at = datetime.now(timezone.utc)
            # Award mission badge
            badge_id = mission_cfg['badge_id']
            existing_badge = UserAchievement.query.filter_by(
                user_id=user.id, achievement_id=badge_id).first()
            if not existing_badge:
                ua = UserAchievement(user_id=user.id, achievement_id=badge_id)
                db.session.add(ua)
                bonus = mission_cfg['xp_reward']
                user.xp = (user.xp or 0) + bonus
                user.score += bonus
                newly_unlocked.append({
                    'title': f'{mission_cfg["icon"]} {mission_cfg["name"]}',
                    'bonus': bonus,
                })

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        session.pop('mission_correct_answer', None)
        session.pop('mission_question_id', None)

        return jsonify({
            'correct': is_correct,
            'correct_answer': correct,
            'questions_completed': progress.questions_completed,
            'correct_count': progress.correct_count,
            'total_questions': mission_cfg['question_count'],
            'mission_complete': mission_done,
            'newly_unlocked': newly_unlocked,
            'xp': user.xp or 0,
        })

    # GET — serve mission question
    if progress.completed:
        return render_template('mission_complete.html', mission=mission_cfg, progress=progress)

    question = game_logic.get_mission_question(mission_id)
    if question:
        session['mission_correct_answer'] = question['correct_answer']
        session['mission_question_id'] = question['id']

    return render_template('mission_play.html',
                           mission=mission_cfg,
                           mission_id=mission_id,
                           question=question,
                           progress=progress)


@main_bp.route('/api/countries')
def api_countries():
    """JSON endpoint: returns all countries that have coordinates, for the map."""
    countries = Country.query.filter(
        Country.latitude.isnot(None),
        Country.longitude.isnot(None)
    ).all()
    data = []
    for c in countries:
        data.append({
            'name': c.name,
            'capital': c.capital or '',
            'population': c.population or 0,
            'area': c.area or 0,
            'continent': c.continent_name or 'Unknown',
            'flag_svg': c.flag_url_svg or c.flag_url_png or '',
            'lat': c.latitude,
            'lng': c.longitude,
            'url': url_for('main.country_detail', name=c.name)
        })
    return jsonify(data)


@main_bp.route('/about')
def about():
    return render_template('about.html') # You'll need to create about.html

# Error Handlers (Optional but good practice)
@main_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@main_bp.app_errorhandler(500)
def internal_server_error(e):
    # Log the error e
    current_app.logger.error(f"Server Error: {e}", exc_info=True)
    return render_template('500.html'), 500