/* ===================================================
   GeoQuest — Enhanced Quiz JS
   Features: countdown timer, streak tracking,
             speed bonus, hint system, bonus breakdown,
             multi-mode support
   =================================================== */

const TIME_LIMIT_SEC = (typeof window.QUIZ_TIMER_SEC === 'number') ? window.QUIZ_TIMER_SEC : 15;
const TIME_LIMIT_MS  = TIME_LIMIT_SEC * 1000;
const NO_TIMER       = (TIME_LIMIT_SEC <= 0);
const QUIZ_POST_URL  = (typeof window.QUIZ_POST_URL === 'string') ? window.QUIZ_POST_URL : '/quiz';

let timerInterval  = null;
let questionStart  = null;
let currentStreak  = (typeof window.INITIAL_STREAK === 'number') ? window.INITIAL_STREAK : 0;
let currentScore   = 0;
let hintUsed       = false;

// ── DOM refs ──
const form          = document.getElementById('quiz-form');
const submitBtn     = document.getElementById('submit-btn');
const resultDiv     = document.getElementById('result');
const bonusWrap     = document.getElementById('bonus-breakdown');
const hudScore      = document.getElementById('hud-score');
const hudStreak     = document.getElementById('hud-streak');
const hudLives      = document.getElementById('hud-lives');
const timerNum      = document.getElementById('timer-num');
const timerArc      = document.getElementById('timer-arc');
const hintBtn       = document.getElementById('hint-btn');
const timeTakenField = document.getElementById('time-taken-ms');

// ── Init ──
if (form) {
    updateHUD({ streak: currentStreak });
    if (!NO_TIMER) {
        startTimer();
    } else {
        // No timer mode — show infinity
        if (timerNum) timerNum.textContent = '∞';
        if (timerArc) timerArc.style.strokeDasharray = '100 100';
    }
    form.addEventListener('submit', handleSubmit);
}

if (hintBtn) {
    hintBtn.addEventListener('click', handleHint);
}

// ─────────────────────────────────────────────
// Timer
// ─────────────────────────────────────────────

function startTimer() {
    questionStart = Date.now();
    let remaining = TIME_LIMIT_SEC;

    setTimerDisplay(remaining, TIME_LIMIT_SEC);

    timerInterval = setInterval(() => {
        remaining--;
        setTimerDisplay(remaining, TIME_LIMIT_SEC);

        if (remaining <= 0) {
            clearInterval(timerInterval);
            timerInterval = null;
            onTimerExpired();
        }
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function setTimerDisplay(remaining, total) {
    if (!timerNum || !timerArc) return;

    timerNum.textContent = remaining;

    // SVG dash progress: 100 = full circle, 0 = empty
    const pct = (remaining / total) * 100;
    timerArc.style.strokeDasharray = `${pct} 100`;

    // Colour shift as time runs out
    timerArc.classList.remove('warn', 'danger');
    if (remaining <= 5)      timerArc.classList.add('danger');
    else if (remaining <= 9) timerArc.classList.add('warn');
}

function onTimerExpired() {
    // Auto-submit a blank answer so the server deducts a life
    if (!form || submitBtn.disabled) return;

    // Set a sentinel answer that won't match any real answer
    const hidden = document.createElement('input');
    hidden.type  = 'hidden';
    hidden.name  = 'answer';
    hidden.value = '__TIME_EXPIRED__';
    form.appendChild(hidden);

    if (timeTakenField) timeTakenField.value = TIME_LIMIT_MS;
    submitBtn.disabled = true;
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
}

// ─────────────────────────────────────────────
// Submit handler
// ─────────────────────────────────────────────

function handleSubmit(e) {
    e.preventDefault();
    stopTimer();

    const formData = new FormData(form);
    const answer   = formData.get('answer');

    if (!answer) {
        flashResult('Please select an answer!', false);
        startTimer();   // restart timer so player can still pick
        return;
    }

    // Record time taken
    if (timeTakenField && questionStart) {
        timeTakenField.value = Date.now() - questionStart;
    }

    submitBtn.disabled = true;
    if (hintBtn) hintBtn.disabled = true;

    fetch(QUIZ_POST_URL, { method: 'POST', body: new FormData(form) })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                flashResult('⚠️ ' + data.error, false);
                submitBtn.disabled = false;
                return;
            }
            handleResult(data);
        })
        .catch(() => {
            flashResult('Connection error. Please try again.', false);
            submitBtn.disabled = false;
            if (hintBtn) hintBtn.disabled = false;
        });
}

// ─────────────────────────────────────────────
// Result handling
// ─────────────────────────────────────────────

function handleResult(data) {
    currentScore  = data.total_score;
    currentStreak = data.streak;

    // Highlight the correct answer in the option labels
    highlightOptions(data.correct_answer_was, data.correct);

    // Update HUD
    updateHUD(data);

    // Check and trigger achievements
    if (data.newly_unlocked && data.newly_unlocked.length > 0) {
        data.newly_unlocked.forEach(ach => {
            showAchievementToast(ach);
        });
    }

    if (data.game_over) {
        flashResult(`💔 Game Over!  The answer was "${data.correct_answer_was}".  Final score: ${data.total_score} pts.`, false);
        hideSubmit();
        showPlayAgain();
        showBonusChips(data);
    } else {
        flashResult(data.feedback, data.correct);
        showBonusChips(data);
        
        // Delay reload slightly longer if there's an achievement popup so they can read it!
        const delay = (data.newly_unlocked && data.newly_unlocked.length > 0) ? 4200 : (data.correct ? 1800 : 2600);
        setTimeout(() => location.reload(), delay);
    }
}

function highlightOptions(correctAnswer, wasCorrect) {
    document.querySelectorAll('.quiz-option-label').forEach(label => {
        const input = document.getElementById(label.htmlFor);
        if (!input) return;
        if (input.value === correctAnswer) {
            label.style.borderColor   = 'rgba(74,222,128,0.7)';
            label.style.background    = 'rgba(74,222,128,0.12)';
            label.style.color         = '#4ade80';
        } else if (input.checked && !wasCorrect) {
            label.style.borderColor   = 'rgba(248,113,113,0.7)';
            label.style.background    = 'rgba(248,113,113,0.12)';
            label.style.color         = '#f87171';
        }
        // Lock all options
        input.disabled = true;
    });
}

function flashResult(msg, correct) {
    if (!resultDiv) return;
    resultDiv.textContent  = msg;
    resultDiv.className    = correct ? 'correct' : 'incorrect';
    // Reset animation
    resultDiv.style.animation = 'none';
    void resultDiv.offsetWidth;
    resultDiv.style.animation = '';
}

function showBonusChips(data) {
    if (!bonusWrap || !data.correct) { return; }
    bonusWrap.innerHTML = '';

    if (data.base_points) {
        bonusWrap.innerHTML += `<span class="bonus-chip chip-base">+${data.base_points} pts</span>`;
    }
    if (data.speed_bonus) {
        bonusWrap.innerHTML += `<span class="bonus-chip chip-speed" style="animation-delay:0.1s">⚡ Speed +${data.speed_bonus}</span>`;
    }
    if (data.streak_bonus) {
        bonusWrap.innerHTML += `<span class="bonus-chip chip-streak" style="animation-delay:0.2s">🔥 Streak +${data.streak_bonus}</span>`;
    }
    bonusWrap.style.display = 'flex';
}

// ─────────────────────────────────────────────
// HUD updates
// ─────────────────────────────────────────────

function updateHUD(data) {
    if (hudScore) {
        hudScore.textContent = currentScore || '0';
    }
    if (hudStreak) {
        const s = data.streak !== undefined ? data.streak : currentStreak;
        hudStreak.textContent = s > 0 ? `🔥 ${s}` : '—';
    }
    if (hudLives && data.lives !== undefined) {
        const max    = 3;
        const alive  = Math.max(0, data.lives);
        const dead   = max - alive;
        hudLives.textContent = '❤️'.repeat(alive) + '🖤'.repeat(dead);
    }
}

// ─────────────────────────────────────────────
// Hint
// ─────────────────────────────────────────────

function handleHint() {
    if (hintUsed) return;
    hintUsed = true;
    hintBtn.disabled = true;
    hintBtn.textContent = '💡 Hint used';

    fetch('/quiz/hint', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                hintBtn.textContent = '💡 Hint unavailable';
                return;
            }

            // Visually strike out the 2 eliminated options
            data.eliminate.forEach(val => {
                document.querySelectorAll('.quiz-option-label').forEach(label => {
                    const input = document.getElementById(label.htmlFor);
                    if (input && input.value === val) {
                        label.classList.add('eliminated');
                        input.disabled = true;
                    }
                });
            });

            // Update score
            currentScore = data.total_score;
            if (hudScore) hudScore.textContent = currentScore;
        })
        .catch(() => {
            hintBtn.disabled = false;
            hintUsed = false;
        });
}

// ─────────────────────────────────────────────
// UI helpers
// ─────────────────────────────────────────────

function hideSubmit() {
    const c = document.getElementById('submit-btn-container');
    if (c) c.style.display = 'none';
    const hb = document.getElementById('hint-btn');
    if (hb) hb.style.display = 'none';
}

function showPlayAgain() {
    const c = document.getElementById('play-again-container');
    if (c) c.style.display = 'block';
}

function showAchievementToast(ach) {
    const toast = document.createElement('div');
    toast.className = 'achievement-toast';
    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: #0f172a;
        border: 2px solid var(--accent);
        border-radius: var(--radius-sm);
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 16px;
        box-shadow: 0 0 25px rgba(247, 201, 72, 0.35);
        z-index: 99999;
        max-width: 360px;
        animation: toast-in 0.5s cubic-bezier(.18,.89,.32,1.28) forwards;
        backdrop-filter: blur(8px);
    `;

    toast.innerHTML = `
        <div style="font-size: 2.2rem; width: 50px; height: 50px; border-radius: 12px; background: rgba(247, 201, 72, 0.1); display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 0 10px rgba(247, 201, 72, 0.2);">${ach.icon}</div>
        <div style="flex-grow: 1; text-align: left;">
            <div style="font-size: 0.65rem; color: var(--accent); font-weight: 900; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 2px;">🏆 Achievement Unlocked!</div>
            <div style="font-size: 1.05rem; font-weight: 800; color: var(--text); font-family: 'Outfit', sans-serif; margin-bottom: 2px;">${ach.title}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); line-height: 1.3; margin-bottom: 4px;">${ach.description}</div>
            <div style="font-size: 0.7rem; color: var(--primary); font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">+${ach.bonus} XP Bonus Added!</div>
        </div>
    `;

    document.body.appendChild(toast);

    // Auto-remove animation
    setTimeout(() => {
        toast.style.animation = 'toast-out 0.4s ease-in forwards';
        setTimeout(() => toast.remove(), 400);
    }, 3800);
}