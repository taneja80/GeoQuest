import random
from datetime import date, timedelta, datetime, timezone
from .models import Country, User, QuizQuestion, CollectedCountry, RegionProgress, DailyCompletion, QuizAttempt, CountryMastery, MissionProgress, db


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _build_options(correct, wrong_pool, fallbacks):
    """
    Build a clean 4-option list guaranteeing `correct` is present,
    deduplicating, and falling back gracefully when the pool is small.
    """
    options = [c for c in wrong_pool if c and c != correct][:3]
    options.append(correct)

    # If we don't have 4 unique options, pad from fallbacks
    for fb in fallbacks:
        if len(options) >= 4:
            break
        if fb and fb != correct and fb not in options:
            options.append(fb)

    options = list(dict.fromkeys(options))   # deduplicate, preserve order
    if correct not in options:
        if len(options) >= 4:
            options[random.randint(0, 3)] = correct
        else:
            options.append(correct)

    random.shuffle(options)
    return options[:4]


def _random_countries(n, exclude_id=None, require_attr=None):
    """Return n random Country objects, optionally excluding one id and requiring an attribute."""
    q = Country.query
    if exclude_id:
        q = q.filter(Country.id != exclude_id)
    if require_attr:
        q = q.filter(getattr(Country, require_attr).isnot(None))
        q = q.filter(getattr(Country, require_attr) != '')
    return q.order_by(db.func.random()).limit(n).all()


# ─────────────────────────────────────────────
# Question Generators
# ─────────────────────────────────────────────

def generate_capital_quiz_question():
    """What is the capital of [Country]?"""
    country = Country.query.filter(
        Country.capital.isnot(None), Country.capital != ''
    ).order_by(db.func.random()).first()
    if not country:
        return None

    wrong = _random_countries(3, exclude_id=country.id, require_attr='capital')
    options = _build_options(
        correct=country.capital,
        wrong_pool=[c.capital for c in wrong],
        fallbacks=['London', 'Paris', 'Berlin', 'Tokyo', 'Cairo']
    )
    return {
        'id': f'capital_{country.id}',
        'type': 'capital',
        'difficulty': 1,
        'question_text': f'What is the capital of {country.name}?',
        'image_url': None,
        'options': options,
        'correct_answer': country.capital,
    }


def generate_flag_quiz_question():
    """Which country does this flag belong to?"""
    country = Country.query.filter(
        Country.flag_url_svg.isnot(None)
    ).order_by(db.func.random()).first()
    if not country:
        return None

    wrong = _random_countries(3, exclude_id=country.id)
    options = _build_options(
        correct=country.name,
        wrong_pool=[c.name for c in wrong],
        fallbacks=['France', 'Germany', 'Japan', 'Brazil', 'Egypt']
    )
    return {
        'id': f'flag_{country.id}',
        'type': 'flag',
        'difficulty': 1,
        'question_text': 'Which country does this flag belong to?',
        'image_url': country.flag_url_svg or country.flag_url_png,
        'options': options,
        'correct_answer': country.name,
    }


def generate_population_quiz_question():
    """Which of these has the largest population?"""
    countries = Country.query.filter(
        Country.population > 0
    ).order_by(db.func.random()).limit(4).all()
    if len(countries) < 2:
        return None

    correct = max(countries, key=lambda c: c.population)
    options = [c.name for c in countries]
    random.shuffle(options)
    return {
        'id': f'pop_{correct.id}',
        'type': 'population',
        'difficulty': 2,
        'question_text': 'Which of these countries has the largest population?',
        'image_url': None,
        'options': options,
        'correct_answer': correct.name,
    }


def generate_area_quiz_question():
    """Which is the largest by land area?"""
    countries = Country.query.filter(
        Country.area > 0
    ).order_by(db.func.random()).limit(4).all()
    if len(countries) < 2:
        return None

    correct = max(countries, key=lambda c: c.area)
    options = [c.name for c in countries]
    random.shuffle(options)
    return {
        'id': f'area_{correct.id}',
        'type': 'area',
        'difficulty': 2,
        'question_text': 'Which of these countries is the largest by land area?',
        'image_url': None,
        'options': options,
        'correct_answer': correct.name,
    }


def generate_continent_quiz_question():
    """Which continent is [Country] in?"""
    country = Country.query.filter(
        Country.continent_name.isnot(None)
    ).order_by(db.func.random()).first()
    if not country:
        return None

    all_continents = [
        'Africa', 'Antarctica', 'Asia', 'Europe',
        'North America', 'Oceania', 'South America'
    ]
    options = _build_options(
        correct=country.continent_name,
        wrong_pool=[c for c in all_continents if c != country.continent_name],
        fallbacks=[]
    )
    return {
        'id': f'continent_{country.id}',
        'type': 'continent',
        'difficulty': 1,
        'question_text': f'Which continent is {country.name} located in?',
        'image_url': country.flag_url_svg or country.flag_url_png,
        'options': options,
        'correct_answer': country.continent_name,
    }


def generate_language_quiz_question():
    """Which language is spoken in [Country]?"""
    country = Country.query.filter(
        Country.languages.isnot(None)
    ).order_by(db.func.random()).first()
    if not country or not country.languages:
        return None

    # Pick one official language as the answer
    langs = list(country.languages.values())
    if not langs:
        return None
    correct_lang = random.choice(langs)

    # Wrong: pull languages from other countries
    other = _random_countries(6, exclude_id=country.id, require_attr='languages')
    wrong_langs = []
    for o in other:
        if o.languages:
            for l in o.languages.values():
                if l and l != correct_lang and l not in wrong_langs:
                    wrong_langs.append(l)
        if len(wrong_langs) >= 3:
            break

    options = _build_options(
        correct=correct_lang,
        wrong_pool=wrong_langs,
        fallbacks=['English', 'French', 'Spanish', 'Arabic', 'Mandarin']
    )
    return {
        'id': f'lang_{country.id}',
        'type': 'language',
        'difficulty': 2,
        'question_text': f'Which language is officially spoken in {country.name}?',
        'image_url': country.flag_url_svg or country.flag_url_png,
        'options': options,
        'correct_answer': correct_lang,
    }


def generate_landlocked_quiz_question():
    """Is [Country] landlocked or does it have a coastline?"""
    country = Country.query.filter(
        Country.landlocked.isnot(None)
    ).order_by(db.func.random()).first()
    if not country:
        return None

    correct = 'Landlocked' if country.landlocked else 'Has a Coastline'
    options = ['Landlocked', 'Has a Coastline']
    random.shuffle(options)
    return {
        'id': f'landlocked_{country.id}',
        'type': 'landlocked',
        'difficulty': 1,
        'question_text': f'Is {country.name} landlocked or does it have a coastline?',
        'image_url': country.flag_url_svg or country.flag_url_png,
        'options': options,
        'correct_answer': correct,
    }


# ─────────────────────────────────────────────
# Question Dispatcher
# ─────────────────────────────────────────────

ALL_GENERATORS = [
    generate_capital_quiz_question,
    generate_flag_quiz_question,
    generate_population_quiz_question,
    generate_area_quiz_question,
    generate_continent_quiz_question,
    generate_language_quiz_question,
    generate_landlocked_quiz_question,
]


def get_quiz_question():
    """Return a random quiz question, retrying up to 7 times on failure."""
    for _ in range(7):
        gen = random.choice(ALL_GENERATORS)
        q = gen()
        if q:
            return q

    # Ultimate fallback
    return {
        'id': 'fallback_001',
        'type': 'fallback',
        'difficulty': 1,
        'question_text': 'Is the Earth round?',
        'image_url': None,
        'options': ['Yes', 'No'],
        'correct_answer': 'Yes',
    }


# ─────────────────────────────────────────────
# Scoring & Session Logic
# ─────────────────────────────────────────────

# Points config
BASE_POINTS    = 10
SPEED_BONUS    = 5    # max extra for answering in < 5 s
HINT_COST      = 20   # points deducted per hint use

ACHIEVEMENTS = {
    'first_correct': {
        'title': '🌍 First Landmark',
        'description': 'Answered a quiz question correctly.',
        'icon': '📍',
        'bonus': 10
    },
    'streak_5': {
        'title': '🔥 Streak Starter',
        'description': 'Reached a correct answer streak of 5.',
        'icon': '⚡',
        'bonus': 30
    },
    'streak_10': {
        'title': '👑 Ultimate Explorer',
        'description': 'Reached a correct answer streak of 10.',
        'icon': '👑',
        'bonus': 100
    },
    'perfect_game': {
        'title': '🏆 Geographic Master',
        'description': 'Completed a game (3/3 lives remaining at 100+ points).',
        'icon': '🛡️',
        'bonus': 50
    },
    'speed_demon': {
        'title': '⚡ Speed Demon',
        'description': 'Answered a question in under 3 seconds.',
        'icon': '🏎️',
        'bonus': 20
    },
    'no_hint_hero': {
        'title': '🧠 Independent Scholar',
        'description': 'Answered 5 questions in a row without using hints.',
        'icon': '🧠',
        'bonus': 40
    },
    'globetrotter': {
        'title': '✈️ Globetrotter',
        'description': 'Accumulated a total score of 200 points.',
        'icon': '✈️',
        'bonus': 50
    },
    'legendary_navigator': {
        'title': '💫 Legendary Navigator',
        'description': 'Accumulated a total score of 500 points.',
        'icon': '🔮',
        'bonus': 150
    },
    'collector_10': {
        'title': '🃏 Card Starter',
        'description': 'Collected 10 country cards.',
        'icon': '🃏',
        'bonus': 25
    },
    'collector_50': {
        'title': '📚 Card Collector',
        'description': 'Collected 50 country cards.',
        'icon': '📚',
        'bonus': 75
    },
    'daily_streak_7': {
        'title': '📅 Weekly Warrior',
        'description': 'Completed daily challenges 7 days in a row.',
        'icon': '📅',
        'bonus': 60
    },
    # ── Continent Expert achievements ──
    'africa_expert': {
        'title': '🦁 African Expert',
        'description': 'Answered 20 Africa questions correctly.',
        'icon': '🦁',
        'bonus': 50
    },
    'asia_expert': {
        'title': '🏯 Asian Expert',
        'description': 'Answered 20 Asia questions correctly.',
        'icon': '🏯',
        'bonus': 50
    },
    'europe_expert': {
        'title': '🗼 European Expert',
        'description': 'Answered 20 Europe questions correctly.',
        'icon': '🗼',
        'bonus': 50
    },
    'americas_expert': {
        'title': '🗽 Americas Expert',
        'description': 'Answered 20 Americas questions correctly.',
        'icon': '🗽',
        'bonus': 50
    },
    'oceania_expert': {
        'title': '🦘 Oceania Expert',
        'description': 'Answered 20 Oceania questions correctly.',
        'icon': '🦘',
        'bonus': 50
    },
    # ── Category mastery achievements ──
    'flag_master': {
        'title': '🏳️ Flag Master',
        'description': 'Answered 50 flag questions correctly.',
        'icon': '🏳️',
        'bonus': 75
    },
    'capital_master': {
        'title': '🏛️ Capital Master',
        'description': 'Answered 50 capital questions correctly.',
        'icon': '🏛️',
        'bonus': 75
    },
    'population_master': {
        'title': '👥 Population Master',
        'description': 'Answered 50 population questions correctly.',
        'icon': '👥',
        'bonus': 75
    },
    # ── Speed achievements ──
    'speed_learner': {
        'title': '⚡ Speed Learner',
        'description': 'Earned 10 speed bonuses in a single session.',
        'icon': '⚡',
        'bonus': 40
    },
    'lightning_reflexes': {
        'title': '🏎️ Lightning Reflexes',
        'description': 'Answered 5 questions in under 3 seconds each in one session.',
        'icon': '🏎️',
        'bonus': 60
    },
    # ── Milestone achievements ──
    'centurion': {
        'title': '💯 Centurion',
        'description': 'Answered 100 questions correctly in total.',
        'icon': '💯',
        'bonus': 80
    },
    'five_hundred_club': {
        'title': '🌟 500 Club',
        'description': 'Answered 500 questions correctly in total.',
        'icon': '🌟',
        'bonus': 200
    },
    'thousand_club': {
        'title': '👑 1000 Club',
        'description': 'Answered 1000 questions correctly in total.',
        'icon': '👑',
        'bonus': 500
    },
    'streak_25': {
        'title': '🔥 Streak Legend',
        'description': 'Reached a correct answer streak of 25.',
        'icon': '🔥',
        'bonus': 150
    },
    'daily_streak_30': {
        'title': '📅 Monthly Devotee',
        'description': 'Completed daily challenges 30 days in a row.',
        'icon': '📅',
        'bonus': 200
    },
    'collector_100': {
        'title': '🗂️ Card Hoarder',
        'description': 'Collected 100 country cards.',
        'icon': '🗂️',
        'bonus': 120
    },
    'xp_1000': {
        'title': '🚀 XP Rocket',
        'description': 'Accumulated 1000 XP.',
        'icon': '🚀',
        'bonus': 100
    },
    'xp_5000': {
        'title': '💎 Diamond Explorer',
        'description': 'Accumulated 5000 XP.',
        'icon': '💎',
        'bonus': 300
    },
}

def calc_speed_bonus(time_taken_ms, time_limit_ms=15000):
    """
    Award up to SPEED_BONUS points for fast answers.
    Full bonus if answered in first 20% of time; scales linearly to 0.
    """
    if time_taken_ms is None or time_taken_ms <= 0:
        return 0
    ratio = max(0.0, 1.0 - (time_taken_ms / time_limit_ms))
    return round(SPEED_BONUS * ratio)


def check_answer_and_update_score(username, question_id, submitted_answer,
                                  stored_correct_answer, time_taken_ms=None,
                                  xp_multiplier=1.0, mode='classic'):
    """Check the answer, apply streak & speed bonuses, update stats, XP, collection & achievements."""
    from flask import session
    from .models import UserAchievement

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, score=0, xp=0)
        db.session.add(user)
        db.session.commit()

    is_correct = (submitted_answer == stored_correct_answer)

    lives       = session.get('lives', 3)
    streak      = session.get('streak', 0)
    points_earned = 0
    speed_bonus   = 0
    streak_bonus  = 0

    # 1. Update stats count
    user.total_questions_answered = (user.total_questions_answered or 0) + 1

    if is_correct:
        user.correct_answers_count = (user.correct_answers_count or 0) + 1
        streak += 1
        session['streak'] = streak
        user.highest_streak = max(user.highest_streak or 0, streak)

        speed_bonus  = calc_speed_bonus(time_taken_ms)
        multiplier   = 1 + min(2, (streak - 1) // 2)
        streak_bonus = BASE_POINTS * (multiplier - 1)

        points_earned = BASE_POINTS + speed_bonus + streak_bonus
        # Apply mode multiplier
        xp_earned = int(points_earned * xp_multiplier)
        user.score += points_earned
        user.xp    = (user.xp or 0) + xp_earned

        if not session.get('hint_used_for_current'):
            session['streak_no_hints'] = session.get('streak_no_hints', 0) + 1
        else:
            session['streak_no_hints'] = 0

        # Track speed bonuses and fast answers in session
        if speed_bonus > 0:
            session['session_speed_bonuses'] = session.get('session_speed_bonuses', 0) + 1
        if time_taken_ms is not None and time_taken_ms <= 3000:
            session['session_fast_answers'] = session.get('session_fast_answers', 0) + 1

        # -- Collect country & track region --
        _try_collect_country(user, question_id)
    else:
        streak = 0
        session['streak'] = 0
        session['streak_no_hints'] = 0
        lives -= 1
        session['lives'] = lives

    game_over = lives <= 0

    if game_over:
        user.games_played = (user.games_played or 0) + 1
        session.pop('streak', None)
        session.pop('streak_no_hints', None)

    # 2. Check and unlock achievements
    newly_unlocked = []
    unlocked_ids = {a.achievement_id for a in user.achievements}

    def unlock(achievement_id):
        if achievement_id not in unlocked_ids:
            ach_data = ACHIEVEMENTS[achievement_id]
            ua = UserAchievement(user_id=user.id, achievement_id=achievement_id)
            db.session.add(ua)
            user.score += ach_data['bonus']
            user.xp    = (user.xp or 0) + ach_data['bonus']
            newly_unlocked.append({
                'id': achievement_id,
                'title': ach_data['title'],
                'description': ach_data['description'],
                'icon': ach_data['icon'],
                'bonus': ach_data['bonus']
            })

    if 'first_correct' not in unlocked_ids and is_correct:
        unlock('first_correct')
    if 'streak_5' not in unlocked_ids and streak >= 5:
        unlock('streak_5')
    if 'streak_10' not in unlocked_ids and streak >= 10:
        unlock('streak_10')
    if 'speed_demon' not in unlocked_ids and is_correct and time_taken_ms is not None and time_taken_ms <= 3000:
        unlock('speed_demon')
    if 'no_hint_hero' not in unlocked_ids and session.get('streak_no_hints', 0) >= 5:
        unlock('no_hint_hero')
    if 'perfect_game' not in unlocked_ids and lives == 3 and user.score >= 100:
        unlock('perfect_game')
    if 'globetrotter' not in unlocked_ids and user.score >= 200:
        unlock('globetrotter')
    if 'legendary_navigator' not in unlocked_ids and user.score >= 500:
        unlock('legendary_navigator')
    # Collection achievements
    collected_count = CollectedCountry.query.filter_by(user_id=user.id).count()
    if 'collector_10' not in unlocked_ids and collected_count >= 10:
        unlock('collector_10')
    if 'collector_50' not in unlocked_ids and collected_count >= 50:
        unlock('collector_50')
    if 'collector_100' not in unlocked_ids and collected_count >= 100:
        unlock('collector_100')
    if 'daily_streak_7' not in unlocked_ids and (user.daily_streak or 0) >= 7:
        unlock('daily_streak_7')
    if 'daily_streak_30' not in unlocked_ids and (user.daily_streak or 0) >= 30:
        unlock('daily_streak_30')

    # Streak achievements
    if 'streak_25' not in unlocked_ids and streak >= 25:
        unlock('streak_25')

    # Milestone achievements — total correct
    correct_total = user.correct_answers_count or 0
    if 'centurion' not in unlocked_ids and correct_total >= 100:
        unlock('centurion')
    if 'five_hundred_club' not in unlocked_ids and correct_total >= 500:
        unlock('five_hundred_club')
    if 'thousand_club' not in unlocked_ids and correct_total >= 1000:
        unlock('thousand_club')

    # XP milestones
    total_xp = user.xp or 0
    if 'xp_1000' not in unlocked_ids and total_xp >= 1000:
        unlock('xp_1000')
    if 'xp_5000' not in unlocked_ids and total_xp >= 5000:
        unlock('xp_5000')

    # Speed session achievements
    if 'speed_learner' not in unlocked_ids and session.get('session_speed_bonuses', 0) >= 10:
        unlock('speed_learner')
    if 'lightning_reflexes' not in unlocked_ids and session.get('session_fast_answers', 0) >= 5:
        unlock('lightning_reflexes')

    # Category mastery achievements (flag, capital, population — 50 correct each)
    q_type_now, _ = _extract_question_info(question_id)
    if q_type_now == 'daily':
        q_type_now, _ = _extract_question_info(question_id.replace('daily_', '', 1))

    _CATEGORY_ACHIEVEMENTS = {
        'flag': 'flag_master',
        'capital': 'capital_master',
        'population': 'population_master',
    }
    if is_correct and q_type_now in _CATEGORY_ACHIEVEMENTS:
        ach_id = _CATEGORY_ACHIEVEMENTS[q_type_now]
        if ach_id not in unlocked_ids:
            cat_correct = QuizAttempt.query.filter_by(
                user_id=user.id, question_type=q_type_now, is_correct=True
            ).count()
            if cat_correct >= 50:
                unlock(ach_id)

    # Continent expert achievements (20 correct about countries in each continent)
    _CONTINENT_ACHIEVEMENTS = {
        'Africa': 'africa_expert',
        'Asia': 'asia_expert',
        'Europe': 'europe_expert',
        'Oceania': 'oceania_expert',
    }
    _AMERICAS_ACH = 'americas_expert'
    if is_correct:
        _, cid = _extract_question_info(question_id)
        if q_type_now == 'daily':
            _, cid = _extract_question_info(question_id.replace('daily_', '', 1))
        if cid:
            country_obj = Country.query.get(cid)
            if country_obj and country_obj.continent_name:
                cont = country_obj.continent_name
                # Check single-continent achievements
                if cont in _CONTINENT_ACHIEVEMENTS:
                    ach_id = _CONTINENT_ACHIEVEMENTS[cont]
                    if ach_id not in unlocked_ids:
                        cont_ids = [c.id for c in Country.query.filter_by(continent_name=cont).all()]
                        cont_correct = QuizAttempt.query.filter(
                            QuizAttempt.user_id == user.id,
                            QuizAttempt.country_id.in_(cont_ids),
                            QuizAttempt.is_correct == True
                        ).count()
                        if cont_correct >= 20:
                            unlock(ach_id)
                # Americas (North + South)
                if cont in ('North America', 'South America') and _AMERICAS_ACH not in unlocked_ids:
                    americas_ids = [c.id for c in Country.query.filter(
                        Country.continent_name.in_(['North America', 'South America'])
                    ).all()]
                    americas_correct = QuizAttempt.query.filter(
                        QuizAttempt.user_id == user.id,
                        QuizAttempt.country_id.in_(americas_ids),
                        QuizAttempt.is_correct == True
                    ).count()
                    if americas_correct >= 20:
                        unlock(_AMERICAS_ACH)

    final_score = user.score

    # 3. Record quiz attempt for history / skills / spaced repetition
    _record_attempt(user, question_id, submitted_answer, stored_correct_answer,
                    is_correct, time_taken_ms, mode)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return {
        'correct':             is_correct,
        'points_earned':       points_earned,
        'base_points':         BASE_POINTS if is_correct else 0,
        'speed_bonus':         speed_bonus,
        'streak_bonus':        streak_bonus,
        'streak':              streak,
        'total_score':         final_score,
        'xp':                  user.xp or 0,
        'level':               user.level,
        'correct_answer_was':  stored_correct_answer,
        'lives':               lives,
        'game_over':           game_over,
        'newly_unlocked':      newly_unlocked,
    }


# ─────────────────────────────────────────────
# Country Collection & Region Tracking
# ─────────────────────────────────────────────

REGION_UNLOCK_THRESHOLD = 10  # correct answers about a region to unlock it

def _try_collect_country(user, question_id):
    """After a correct answer, try to add the country to the user's collection and track region."""
    # Extract country id from question_id like 'capital_42', 'flag_7', etc.
    parts = question_id.rsplit('_', 1)
    if len(parts) != 2:
        return
    try:
        country_id = int(parts[1])
    except (ValueError, TypeError):
        return

    country = Country.query.get(country_id)
    if not country:
        return

    # Collect country (ignore if already collected)
    existing = CollectedCountry.query.filter_by(user_id=user.id, country_id=country.id).first()
    if not existing:
        cc = CollectedCountry(user_id=user.id, country_id=country.id)
        db.session.add(cc)
        user.countries_collected = (user.countries_collected or 0) + 1

    # Track region progress
    if country.continent_name:
        rp = RegionProgress.query.filter_by(user_id=user.id, region_name=country.continent_name).first()
        if not rp:
            rp = RegionProgress(user_id=user.id, region_name=country.continent_name, correct_count=0)
            db.session.add(rp)
        rp.correct_count += 1
        if rp.correct_count >= REGION_UNLOCK_THRESHOLD and not rp.unlocked:
            rp.unlocked = True


def _extract_question_info(question_id):
    """Parse question_id like 'capital_42' → ('capital', 42)."""
    parts = question_id.rsplit('_', 1)
    if len(parts) != 2:
        return None, None
    try:
        return parts[0], int(parts[1])
    except (ValueError, TypeError):
        return parts[0], None


def _record_attempt(user, question_id, submitted_answer, correct_answer,
                    is_correct, time_taken_ms, mode):
    """Record every answer in QuizAttempt and update CountryMastery."""
    from flask import session as flask_session

    q_type, country_id = _extract_question_info(question_id)
    # Strip 'daily_' prefix if present
    if q_type == 'daily':
        q_type, country_id = _extract_question_info(question_id.replace('daily_', '', 1))

    q_text = flask_session.get('current_question_text', question_id)

    attempt = QuizAttempt(
        user_id=user.id,
        country_id=country_id,
        question_type=q_type or 'unknown',
        question_text=q_text,
        submitted_answer=submitted_answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
        time_taken_ms=time_taken_ms,
        quiz_mode=mode,
    )
    db.session.add(attempt)

    # Update country mastery
    if country_id and q_type:
        _update_country_mastery(user.id, country_id, q_type, is_correct)


def _update_country_mastery(user_id, country_id, question_type, is_correct):
    """Update mastery stars for a country. Stars = # distinct categories answered correctly (max 5)."""
    mastery = CountryMastery.query.filter_by(user_id=user_id, country_id=country_id).first()
    if not mastery:
        mastery = CountryMastery(user_id=user_id, country_id=country_id,
                                 stars=0, categories_correct=[], total_correct=0, total_attempts=0)
        db.session.add(mastery)

    mastery.total_attempts += 1
    mastery.last_answered = datetime.now(timezone.utc)

    if is_correct:
        mastery.total_correct += 1
        cats = mastery.categories_correct or []
        if question_type not in cats:
            cats = cats + [question_type]   # avoid mutating in-place (JSON column)
            mastery.categories_correct = cats
        mastery.stars = min(5, len(mastery.categories_correct))


# ─────────────────────────────────────────────
# Skill Radar Stats
# ─────────────────────────────────────────────

QUESTION_TYPES = ['capital', 'flag', 'population', 'area', 'continent', 'language', 'landlocked']
QUESTION_TYPE_LABELS = {
    'capital': 'Capitals', 'flag': 'Flags', 'population': 'Population',
    'area': 'Area', 'continent': 'Continents', 'language': 'Languages',
    'landlocked': 'Coastlines',
}

def get_skill_stats(user_id):
    """Return accuracy % per question type for the radar chart."""
    stats = {}
    for qt in QUESTION_TYPES:
        total = QuizAttempt.query.filter_by(user_id=user_id, question_type=qt).count()
        correct = QuizAttempt.query.filter_by(user_id=user_id, question_type=qt, is_correct=True).count()
        pct = round(correct / total * 100) if total > 0 else 0
        stats[qt] = {'total': total, 'correct': correct, 'pct': pct,
                      'label': QUESTION_TYPE_LABELS.get(qt, qt.title())}
    return stats


# ─────────────────────────────────────────────
# Spaced Repetition
# ─────────────────────────────────────────────

def get_spaced_repetition_question(user_id):
    """Weighted question selection: favour countries/types the user gets wrong more often."""
    # 1. Find countries the user has gotten wrong (most errors first)
    wrong_attempts = (
        db.session.query(QuizAttempt.country_id, db.func.count().label('wrong_count'))
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.is_correct == False,
                QuizAttempt.country_id.isnot(None))
        .group_by(QuizAttempt.country_id)
        .order_by(db.desc('wrong_count'))
        .limit(20)
        .all()
    )

    if not wrong_attempts:
        return get_quiz_question()  # no history, fall back to random

    # 2. Build weighted list: more wrong = more likely to appear
    weighted_ids = []
    for country_id, wrong_count in wrong_attempts:
        weighted_ids.extend([country_id] * wrong_count)

    target_id = random.choice(weighted_ids)
    country = Country.query.get(target_id)
    if not country:
        return get_quiz_question()

    # 3. Also find weakest question type for this user
    weak_types = (
        db.session.query(QuizAttempt.question_type, db.func.count().label('wrong_count'))
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.is_correct == False)
        .group_by(QuizAttempt.question_type)
        .order_by(db.desc('wrong_count'))
        .limit(5)
        .all()
    )
    preferred_types = [qt for qt, _ in weak_types] if weak_types else QUESTION_TYPES

    # 4. Try to generate a question about target_country in a weak type
    type_gen_map = {
        'capital': generate_capital_quiz_question,
        'flag': generate_flag_quiz_question,
        'population': generate_population_quiz_question,
        'area': generate_area_quiz_question,
        'continent': generate_continent_quiz_question,
        'language': generate_language_quiz_question,
        'landlocked': generate_landlocked_quiz_question,
    }

    for qt in preferred_types:
        gen = type_gen_map.get(qt)
        if gen:
            q = gen()
            if q:
                return q

    return get_quiz_question()


# ─────────────────────────────────────────────
# Weekly Progress Report
# ─────────────────────────────────────────────

def get_weekly_report(user_id):
    """Aggregate last 7 days of quiz activity."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    attempts = QuizAttempt.query.filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.created_at >= week_ago,
    ).all()

    if not attempts:
        return {
            'total_questions': 0, 'correct': 0, 'accuracy': 0,
            'by_day': [], 'by_type': {}, 'strongest': None, 'weakest': None,
            'new_countries_mastered': 0, 'streak_best': 0,
        }

    total = len(attempts)
    correct = sum(1 for a in attempts if a.is_correct)
    accuracy = round(correct / total * 100) if total else 0

    # By day
    day_map = {}
    for a in attempts:
        day_key = a.created_at.strftime('%a') if a.created_at else 'Unknown'
        if day_key not in day_map:
            day_map[day_key] = {'total': 0, 'correct': 0}
        day_map[day_key]['total'] += 1
        if a.is_correct:
            day_map[day_key]['correct'] += 1

    # By type
    type_map = {}
    for a in attempts:
        qt = a.question_type
        if qt not in type_map:
            type_map[qt] = {'total': 0, 'correct': 0}
        type_map[qt]['total'] += 1
        if a.is_correct:
            type_map[qt]['correct'] += 1

    for qt in type_map:
        t = type_map[qt]
        t['pct'] = round(t['correct'] / t['total'] * 100) if t['total'] else 0
        t['label'] = QUESTION_TYPE_LABELS.get(qt, qt.title())

    # Strongest / weakest (min 3 attempts)
    qualified = {k: v for k, v in type_map.items() if v['total'] >= 3}
    strongest = max(qualified, key=lambda k: qualified[k]['pct']) if qualified else None
    weakest = min(qualified, key=lambda k: qualified[k]['pct']) if qualified else None

    # Countries mastered this week
    new_mastered = CountryMastery.query.filter(
        CountryMastery.user_id == user_id,
        CountryMastery.stars >= 5,
        CountryMastery.last_answered >= week_ago,
    ).count()

    # Ordered days for chart
    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    by_day = []
    for dl in day_labels:
        d = day_map.get(dl, {'total': 0, 'correct': 0})
        by_day.append({'day': dl, 'total': d['total'], 'correct': d['correct']})

    return {
        'total_questions': total,
        'correct': correct,
        'accuracy': accuracy,
        'by_day': by_day,
        'by_type': type_map,
        'strongest': QUESTION_TYPE_LABELS.get(strongest, strongest) if strongest else None,
        'weakest': QUESTION_TYPE_LABELS.get(weakest, weakest) if weakest else None,
        'new_countries_mastered': new_mastered,
    }


# ─────────────────────────────────────────────
# Quiz History
# ─────────────────────────────────────────────

def get_quiz_history(user_id, limit=50):
    """Return recent quiz attempts for the history log."""
    return (
        QuizAttempt.query
        .filter_by(user_id=user_id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(limit)
        .all()
    )


def get_mastery_summary(user_id):
    """Return mastery summary: total mastered (5 stars), in-progress, untouched."""
    total_countries = Country.query.count()
    masteries = CountryMastery.query.filter_by(user_id=user_id).all()
    mastered = sum(1 for m in masteries if m.stars >= 5)
    in_progress = sum(1 for m in masteries if 0 < m.stars < 5)
    return {
        'total': total_countries,
        'mastered': mastered,
        'in_progress': in_progress,
        'untouched': total_countries - mastered - in_progress,
        'masteries': masteries,
    }


# ─────────────────────────────────────────────
# Two Truths and a Lie
# ─────────────────────────────────────────────

def _format_pop(pop):
    if pop >= 1_000_000_000:
        return f'{pop / 1_000_000_000:.1f} billion'
    if pop >= 1_000_000:
        return f'{pop / 1_000_000:.1f} million'
    return f'{pop:,}'


def _format_area(area):
    if area >= 1_000_000:
        return f'{area / 1_000_000:.2f} million km²'
    return f'{area:,.0f} km²'


def generate_two_truths_question():
    """Generate a 'Two Truths and a Lie' question about a country."""
    country = Country.query.filter(
        Country.capital.isnot(None),
        Country.population > 0,
        Country.area > 0,
        Country.continent_name.isnot(None),
    ).order_by(db.func.random()).first()
    if not country:
        return None

    # Build a pool of true facts
    true_facts = []
    if country.capital:
        true_facts.append(f'Its capital is {country.capital}.')
    if country.population:
        true_facts.append(f'It has a population of about {_format_pop(country.population)}.')
    if country.continent_name:
        true_facts.append(f'It is located in {country.continent_name}.')
    if country.area:
        true_facts.append(f'It covers an area of {_format_area(country.area)}.')
    if country.landlocked is not None:
        true_facts.append(f'It is {"landlocked" if country.landlocked else "not landlocked"}.')
    if country.driving_side:
        true_facts.append(f'People drive on the {country.driving_side} side of the road.')
    if country.languages:
        langs = list(country.languages.values())
        if langs:
            true_facts.append(f'One official language is {langs[0]}.')

    if len(true_facts) < 2:
        return None

    # Build a lie
    wrong_country = Country.query.filter(
        Country.id != country.id,
        Country.capital.isnot(None),
    ).order_by(db.func.random()).first()

    lies = []
    if wrong_country and wrong_country.capital:
        lies.append(f'Its capital is {wrong_country.capital}.')
    all_continents = ['Africa', 'Asia', 'Europe', 'North America', 'South America', 'Oceania']
    wrong_continent = random.choice([c for c in all_continents if c != country.continent_name])
    lies.append(f'It is located in {wrong_continent}.')
    if country.landlocked is not None:
        lies.append(f'It is {"not landlocked" if country.landlocked else "landlocked"}.')

    if not lies:
        return None

    chosen_truths = random.sample(true_facts, min(2, len(true_facts)))
    chosen_lie = random.choice(lies)

    statements = chosen_truths + [chosen_lie]
    random.shuffle(statements)

    return {
        'id': f'ttal_{country.id}',
        'type': 'two_truths',
        'country_name': country.name,
        'flag_url': country.flag_url_svg or country.flag_url_png,
        'statements': statements,
        'lie': chosen_lie,
        'correct_index': statements.index(chosen_lie),
    }


# ─────────────────────────────────────────────
# Comparison Quiz
# ─────────────────────────────────────────────

COMPARISON_TEMPLATES = [
    {
        'attr': 'population',
        'label': 'larger population',
        'question': 'Which country has a larger population?',
        'filter': lambda q: q.filter(Country.population > 0),
        'key': lambda c: c.population or 0,
    },
    {
        'attr': 'area',
        'label': 'larger land area',
        'question': 'Which country has a larger land area?',
        'filter': lambda q: q.filter(Country.area > 0),
        'key': lambda c: c.area or 0,
    },
    {
        'attr': 'latitude',
        'label': 'closer to the equator',
        'question': 'Which country is closer to the equator?',
        'filter': lambda q: q.filter(Country.latitude.isnot(None)),
        'key': lambda c: -(abs(c.latitude or 90)),  # less absolute lat = closer to equator
    },
    {
        'attr': 'population',
        'label': 'smaller population',
        'question': 'Which country has a smaller population?',
        'filter': lambda q: q.filter(Country.population > 0),
        'key': lambda c: -(c.population or 0),
    },
]


def generate_comparison_question():
    """Generate a comparison question: which is bigger/more populated/closer."""
    template = random.choice(COMPARISON_TEMPLATES)
    base_q = Country.query
    q = template['filter'](base_q)
    countries = q.order_by(db.func.random()).limit(2).all()
    if len(countries) < 2:
        return None

    correct = max(countries, key=template['key'])
    other = countries[0] if countries[1] == correct else countries[1]

    return {
        'id': f'cmp_{correct.id}',
        'type': 'comparison',
        'question_text': template['question'],
        'options': [
            {'name': countries[0].name, 'flag': countries[0].flag_url_svg or countries[0].flag_url_png},
            {'name': countries[1].name, 'flag': countries[1].flag_url_svg or countries[1].flag_url_png},
        ],
        'correct_answer': correct.name,
        'country_a': countries[0].name,
        'country_b': countries[1].name,
    }


# ─────────────────────────────────────────────
# Fact Match Mini-Game
# ─────────────────────────────────────────────

def generate_fact_match_round(count=6):
    """Generate a set of country-fact pairs for the matching game."""
    countries = Country.query.filter(
        Country.capital.isnot(None),
        Country.capital != '',
        Country.flag_url_svg.isnot(None),
    ).order_by(db.func.random()).limit(count).all()

    if len(countries) < 3:
        return None

    # Pick a fact type at random
    fact_types = ['capital', 'continent', 'language']
    chosen_type = random.choice(fact_types)

    pairs = []
    for c in countries:
        if chosen_type == 'capital':
            fact = c.capital
        elif chosen_type == 'continent':
            fact = c.continent_name
        elif chosen_type == 'language':
            if c.languages:
                langs = list(c.languages.values())
                fact = langs[0] if langs else None
            else:
                fact = None
        else:
            fact = c.capital

        if fact:
            pairs.append({
                'country_id': c.id,
                'country_name': c.name,
                'flag': c.flag_url_svg or c.flag_url_png,
                'fact': fact,
            })

    if len(pairs) < 3:
        return None

    return {
        'fact_type': chosen_type,
        'fact_label': {'capital': 'Capital City', 'continent': 'Continent', 'language': 'Language'}.get(chosen_type, chosen_type),
        'pairs': pairs,
    }


# ─────────────────────────────────────────────
# Map Quiz (Where in the World)
# ─────────────────────────────────────────────

def generate_map_quiz_question():
    """Generate a 'find this country on the map' question."""
    country = Country.query.filter(
        Country.latitude.isnot(None),
        Country.longitude.isnot(None),
        Country.flag_url_svg.isnot(None),
    ).order_by(db.func.random()).first()
    if not country:
        return None

    return {
        'id': f'mapq_{country.id}',
        'type': 'map_quiz',
        'country_name': country.name,
        'flag_url': country.flag_url_svg or country.flag_url_png,
        'target_lat': country.latitude,
        'target_lng': country.longitude,
        'continent': country.continent_name,
    }


# ─────────────────────────────────────────────
# Story Mode / Missions
# ─────────────────────────────────────────────

MISSIONS = {
    'african_safari': {
        'name': 'African Safari',
        'icon': '🦁',
        'continent': 'Africa',
        'description': 'Journey across the savannas and deserts of Africa!',
        'story_intro': 'Your expedition starts on the banks of the Nile. The African continent awaits — from the Sahara Desert to the Cape of Good Hope. Answer 10 questions to earn your Safari Badge!',
        'question_count': 10,
        'xp_reward': 100,
        'badge_id': 'mission_african_safari',
    },
    'asian_expedition': {
        'name': 'Asian Expedition',
        'icon': '🏯',
        'continent': 'Asia',
        'description': 'Explore the temples, mountains, and megacities of Asia!',
        'story_intro': 'From the Great Wall of China to the temples of Angkor Wat, Asia is a land of ancient wonders and modern marvels. Prove your knowledge across 10 questions!',
        'question_count': 10,
        'xp_reward': 100,
        'badge_id': 'mission_asian_expedition',
    },
    'european_tour': {
        'name': 'European Tour',
        'icon': '🗼',
        'continent': 'Europe',
        'description': 'Tour the capitals, cultures, and landmarks of Europe!',
        'story_intro': 'Pack your bags! From the Eiffel Tower to the Northern Lights, Europe has centuries of history to explore. 10 questions stand between you and the Tour Badge!',
        'question_count': 10,
        'xp_reward': 100,
        'badge_id': 'mission_european_tour',
    },
    'americas_adventure': {
        'name': 'Americas Adventure',
        'icon': '🗽',
        'continent': None,   # Both Americas
        'continents': ['North America', 'South America'],
        'description': 'From the Grand Canyon to the Amazon — discover the Americas!',
        'story_intro': 'Two continents, one incredible journey! From the frozen tundra of Canada to the rainforests of Brazil, every question brings a new discovery.',
        'question_count': 10,
        'xp_reward': 100,
        'badge_id': 'mission_americas_adventure',
    },
    'oceania_quest': {
        'name': 'Oceania Quest',
        'icon': '🦘',
        'continent': 'Oceania',
        'description': 'Dive into the islands and wonders of Oceania!',
        'story_intro': 'G\'day mate! From the Great Barrier Reef to the volcanic islands of Polynesia, Oceania is full of surprises. Ready for 10 questions?',
        'question_count': 10,
        'xp_reward': 100,
        'badge_id': 'mission_oceania_quest',
    },
    'world_explorer': {
        'name': 'World Explorer',
        'icon': '🌍',
        'continent': None,
        'description': 'The ultimate challenge — questions from every corner of the globe!',
        'story_intro': 'You\'ve traveled far, but the world is vast. This final mission draws from ALL continents. 15 questions to become a true World Explorer!',
        'question_count': 15,
        'xp_reward': 200,
        'badge_id': 'mission_world_explorer',
    },
}

# Register mission achievements
for _mid, _mdata in MISSIONS.items():
    ACHIEVEMENTS[_mdata['badge_id']] = {
        'title': f'{_mdata["icon"]} {_mdata["name"]}',
        'description': f'Completed the {_mdata["name"]} mission!',
        'icon': _mdata['icon'],
        'bonus': _mdata['xp_reward'],
    }


def get_mission_question(mission_id):
    """Generate a question filtered to the mission's continent(s)."""
    mission = MISSIONS.get(mission_id)
    if not mission:
        return get_quiz_question()

    continent = mission.get('continent')
    continents = mission.get('continents')

    # Build filtered generators
    def _filtered_gen(gen_func):
        q = gen_func()
        if not q:
            return None
        # Check if the country matches the mission continent
        parts = q['id'].rsplit('_', 1)
        if len(parts) == 2:
            try:
                cid = int(parts[1])
                country = Country.query.get(cid)
                if country:
                    if continent and country.continent_name != continent:
                        return None
                    if continents and country.continent_name not in continents:
                        return None
            except (ValueError, TypeError):
                pass
        return q

    # Try to get a continent-filtered question
    for _ in range(20):
        gen = random.choice(ALL_GENERATORS)
        q = _filtered_gen(gen)
        if q:
            return q

    # Fall back to any question
    return get_quiz_question()


def get_mission_status(user_id):
    """Get all missions with their progress for a user."""
    progress_map = {}
    progress_rows = MissionProgress.query.filter_by(user_id=user_id).all()
    for p in progress_rows:
        progress_map[p.mission_id] = p

    result = []
    for mid, mdata in MISSIONS.items():
        p = progress_map.get(mid)
        result.append({
            'id': mid,
            'name': mdata['name'],
            'icon': mdata['icon'],
            'description': mdata['description'],
            'story_intro': mdata['story_intro'],
            'question_count': mdata['question_count'],
            'xp_reward': mdata['xp_reward'],
            'questions_completed': p.questions_completed if p else 0,
            'correct_count': p.correct_count if p else 0,
            'completed': p.completed if p else False,
            'completed_at': p.completed_at if p else None,
        })
    return result


# ─────────────────────────────────────────────
# Daily Challenge
# ─────────────────────────────────────────────

DAILY_BONUS_XP = 25
DAILY_STREAK_BONUS = 5  # extra XP per day of streak

def get_daily_question():
    """Generate a deterministic daily question based on the date."""
    today = date.today()
    seed = today.toordinal()
    rng = random.Random(seed)
    gen = rng.choice(ALL_GENERATORS)
    # Try up to 7 times
    for _ in range(7):
        q = gen()
        if q:
            q['id'] = f"daily_{q['id']}"
            q['daily'] = True
            return q
        gen = rng.choice(ALL_GENERATORS)
    return None

def complete_daily_challenge(user):
    """Mark daily challenge as done, award bonus XP, update daily streak."""
    today = date.today()

    # Already done today?
    existing = DailyCompletion.query.filter_by(user_id=user.id, completed_date=today).first()
    if existing:
        return {'already_done': True, 'bonus': 0}

    # Update daily streak
    yesterday = today - timedelta(days=1)
    if user.last_daily_date == yesterday:
        user.daily_streak = (user.daily_streak or 0) + 1
    elif user.last_daily_date != today:
        user.daily_streak = 1
    user.last_daily_date = today

    streak_xp = (user.daily_streak or 1) * DAILY_STREAK_BONUS
    total_bonus = DAILY_BONUS_XP + streak_xp

    user.xp    = (user.xp or 0) + total_bonus
    user.score += total_bonus

    dc = DailyCompletion(user_id=user.id, completed_date=today, bonus_xp=total_bonus)
    db.session.add(dc)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return {'already_done': False, 'bonus': total_bonus, 'daily_streak': user.daily_streak}


# ─────────────────────────────────────────────
# Quiz Mode Configs
# ─────────────────────────────────────────────

QUIZ_MODES = {
    'classic': {
        'name': 'Classic',
        'icon': '🎮',
        'description': '3 lives, 15 s timer. Streaks & speed bonuses.',
        'lives': 3,
        'timer_sec': 15,
        'xp_multiplier': 1.0,
        'question_limit': None,
    },
    'lightning': {
        'name': 'Lightning Round',
        'icon': '⚡',
        'description': '10 questions, 8 seconds each. 1.5× XP!',
        'lives': 1,
        'timer_sec': 8,
        'xp_multiplier': 1.5,
        'question_limit': 10,
    },
    'survival': {
        'name': 'Survival',
        'icon': '💀',
        'description': 'One wrong answer = game over. 2× XP!',
        'lives': 1,
        'timer_sec': 15,
        'xp_multiplier': 2.0,
        'question_limit': None,
    },
    'marathon': {
        'name': 'Marathon',
        'icon': '🏃',
        'description': '25 questions, no timer, no lives lost. Track accuracy.',
        'lives': 999,
        'timer_sec': 0,
        'xp_multiplier': 0.8,
        'question_limit': 25,
    },
}


def get_leaderboard(limit=10):
    """Returns top users for the leaderboard."""
    return User.query.order_by(User.score.desc()).limit(limit).all()