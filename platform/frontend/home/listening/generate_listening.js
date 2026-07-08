// ============================================================
// generate_listening.js
// Gère l'exercice de listening GÉNÉRÉ par l'IA
//
// Flux :
//   1. Lit exercise_id + learner_id depuis l'URL
//   2. Polling GET /api/check-generated-listening-status/
//      → pending/generating : spinner
//      → ready + has_result  : ouvre la modal "Well done!"
//      → ready + no result   : affiche l'exercice
//   3. L'apprenant écoute + répond aux questions
//   4. POST /api/submit-generated-listening/
//   5. Affiche le résultat avec le corrigé
// ============================================================

const API_BASE = 'http://localhost:8000';
const POLL_INTERVAL_MS = 3000;   // Polling toutes les 3 secondes
const MAX_POLL_ATTEMPTS = 80;    // 80 × 3s = 4 minutes max

// ── État global ──────────────────────────────────────────────
const state = {
    exerciseId:          null,
    audioId:             null,
    learnerId:           null,
    subunit:             null,
    title:               null,
    subunitId:           null,

    questions:           [],
    answers:             {},
    currentIndex:        0,
    submitted:           false,
    hasListened:         false,

    firstResultData:     null,   // Sauvegardé pour "Show Results"
    pollAttempts:        0,
    pollTimer:           null,
};

// ── Paramètres URL ───────────────────────────────────────────
function getUrlParams() {
    const p = new URLSearchParams(window.location.search);
    return {
        exerciseId: p.get('exercise_id') || null,
        audioId:    p.get('audio_id')    || null,
        learnerId:  p.get('learner_id')  || localStorage.getItem('learner_id') || null,
        subunit:    p.get('subunit')     || '',
        title:      p.get('title')       || 'Listening',
        subunitId:  p.get('subunit_id')  || null,
    };
}

// ════════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    const params        = getUrlParams();
    state.exerciseId    = params.exerciseId;
    state.audioId       = params.audioId;
    state.learnerId     = params.learnerId;
    state.subunit       = params.subunit;
    state.title         = params.title;
    state.subunitId     = params.subunitId;

    // ── Header ─────────────────────────────────────────────
    document.getElementById('page-title').textContent = params.title || 'AI Listening Exercise';

    // ── Bouton retour ───────────────────────────────────────
    const backBtn = document.getElementById('back-btn');
    if (backBtn && params.subunitId) {
        backBtn.href = `/listening/?subunit=${params.subunit}&title=${encodeURIComponent(params.title)}&subunit_id=${params.subunitId}`;
    }
    const errorBackBtn = document.getElementById('error-back-btn');
    if (errorBackBtn) errorBackBtn.href = backBtn?.href || '/listening/';

    if (!state.exerciseId) {
        showError('Missing exercise ID. Please go back and try again.');
        return;
    }

    // ── Premier check du statut ─────────────────────────────
    await checkStatus();
});

// ════════════════════════════════════════════════════════════
//  POLLING — check statut de génération
// ════════════════════════════════════════════════════════════

async function checkStatus() {
    state.pollAttempts++;

    if (state.pollAttempts > MAX_POLL_ATTEMPTS) {
        clearPoll();
        showError('Generation is taking too long. Please go back and try again.');
        return;
    }

    try {
        const url = `${API_BASE}/api/check-generated-listening-status/?exercise_id=${state.exerciseId}&learner_id=${state.learnerId || ''}`;
        const res  = await fetch(url);
        const data = await res.json();

        if (!data.success) {
            showError(data.error || 'Failed to check exercise status.');
            return;
        }

        if (data.status === 'pending' || data.status === 'generating') {
            showGeneratingState(data.status);
            schedulePoll();
            return;
        }

        if (data.status === 'error') {
            clearPoll();
            showError(data.error || 'Generation failed. Please go back and try again.');
            return;
        }

        if (data.status === 'ready') {
            clearPoll();

            // Mettre à jour le header avec le thème
            if (data.theme) {
                document.getElementById('page-theme').textContent = data.theme;
                document.getElementById('audio-title').textContent = data.theme;
            }
            if (data.cefr_level) {
                const badge = document.getElementById('level-badge');
                badge.textContent = data.cefr_level;
                badge.style.display = 'inline-flex';
            }

            state.questions = data.questions || [];

            if (data.has_result && data.result) {
                // ── Exercice déjà soumis → modal "Well done!" ────────────
                state.firstResultData = data.result;
                state.submitted       = true;

                // Afficher quand même l'exercice en arrière-plan
                showExerciseContent(data);
                // Puis ouvrir le modal par-dessus
                openAlreadyDoneModal(data.result);
            } else {
                // ── Premier passage → afficher l'exercice ────────────────
                showExerciseContent(data);
            }
        }

    } catch (err) {
        console.error('[GL] checkStatus error:', err);
        schedulePoll();  // Réessayer en cas d'erreur réseau
    }
}

function schedulePoll() {
    clearPoll();
    state.pollTimer = setTimeout(checkStatus, POLL_INTERVAL_MS);
}

function clearPoll() {
    if (state.pollTimer) {
        clearTimeout(state.pollTimer);
        state.pollTimer = null;
    }
}

// ════════════════════════════════════════════════════════════
//  STATES D'AFFICHAGE
// ════════════════════════════════════════════════════════════

function showGeneratingState(status) {
    document.getElementById('generating-state').style.display = 'flex';
    document.getElementById('error-state').style.display      = 'none';
    document.getElementById('exercise-content').style.display = 'none';

    // Mise à jour du texte de statut
    const txt = document.getElementById('gen-status-text');
    if (status === 'pending') {
        txt.textContent = 'Waiting for AI to start…';
        setStep(1, 'active');
    } else {
        txt.textContent = 'Writing transcript and generating audio…';
        setStep(1, 'active');
    }
}

function setStep(stepNum, cls) {
    // Marquer les étapes précédentes comme done
    for (let i = 1; i < stepNum; i++) {
        const el = document.getElementById(`step-${i}`);
        const line = el ? el.nextElementSibling : null;
        if (el) { el.className = 'gl-step done'; }
        if (line && line.classList.contains('gl-step-line')) {
            line.classList.add('done');
        }
    }
    const current = document.getElementById(`step-${stepNum}`);
    if (current) current.className = `gl-step ${cls}`;
}

function showError(message) {
    clearPoll();
    document.getElementById('generating-state').style.display = 'none';
    document.getElementById('exercise-content').style.display = 'none';
    document.getElementById('error-state').style.display      = 'flex';
    document.getElementById('error-message').textContent      = message;
}

function showExerciseContent(data) {
    document.getElementById('generating-state').style.display = 'none';
    document.getElementById('error-state').style.display      = 'none';
    document.getElementById('exercise-content').style.display = 'block';

    // Setup audio
    setupAudioPlayer(data.audio_url);

    // Setup questions (si pas déjà soumis)
    if (!state.submitted) {
        renderQuestions();
    } else {
        // Exercice déjà fait : cacher la section questions et afficher résultat
        document.getElementById('questions-section').style.display = 'none';
        document.getElementById('submit-section').style.display    = 'none';
    }
}

// ════════════════════════════════════════════════════════════
//  AUDIO PLAYER
// ════════════════════════════════════════════════════════════

function setupAudioPlayer(audioUrl) {
    const audioEl = document.getElementById('audio-element');
    audioEl.src   = audioUrl.startsWith('http') ? audioUrl : `${API_BASE}${audioUrl}`;

    const btnPlay   = document.getElementById('btn-play');
    const playIcon  = document.getElementById('play-icon');
    const waveBars  = document.getElementById('wave-bars');

    // ── Play / Pause ────────────────────────────────────────
    btnPlay.addEventListener('click', () => {
        if (audioEl.paused) {
            audioEl.play();
            playIcon.className = 'fas fa-pause';
            waveBars.classList.add('playing');
        } else {
            audioEl.pause();
            playIcon.className = 'fas fa-play';
            waveBars.classList.remove('playing');
        }
    });

    // ── Fin de lecture ──────────────────────────────────────
    audioEl.addEventListener('ended', () => {
        playIcon.className = 'fas fa-play';
        waveBars.classList.remove('playing');
        state.hasListened  = true;

        const hint = document.getElementById('listen-hint');
        hint.innerHTML     = '<i class="fas fa-check-circle"></i> <span>Ready to answer!</span>';
        hint.classList.add('ready');
        updateNavButtons();
    });

    // ── Progress bar ────────────────────────────────────────
    audioEl.addEventListener('timeupdate', () => {
        if (!audioEl.duration) return;
        const pct = (audioEl.currentTime / audioEl.duration) * 100;
        document.getElementById('progress-fill').style.width = pct + '%';

        const cur = formatTime(audioEl.currentTime);
        const dur = formatTime(audioEl.duration);
        document.getElementById('time-display').textContent = `${cur} / ${dur}`;
    });

    // ── Seek ────────────────────────────────────────────────
    document.getElementById('progress-container').addEventListener('click', (e) => {
        if (!audioEl.duration) return;
        const track = e.currentTarget.querySelector('.gl-seek-track');
        const rect  = track.getBoundingClientRect();
        const pct   = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        audioEl.currentTime = pct * audioEl.duration;
    });

    // ── Replay ──────────────────────────────────────────────
    document.getElementById('btn-replay').addEventListener('click', () => {
        audioEl.currentTime = 0;
        audioEl.play();
        playIcon.className = 'fas fa-pause';
        waveBars.classList.add('playing');
    });

    // ── Speed ───────────────────────────────────────────────
    document.querySelectorAll('.gl-speed-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const speed = parseFloat(btn.dataset.speed);
            audioEl.playbackRate = speed;
            document.querySelectorAll('.gl-speed-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    audioEl.playbackRate = 1;
}

function formatTime(secs) {
    if (isNaN(secs)) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

// ════════════════════════════════════════════════════════════
//  QUESTIONS
// ════════════════════════════════════════════════════════════

function renderQuestions() {
    buildDots();
    renderCurrentQuestion();
    setupNav();
}

function buildDots() {
    const container = document.getElementById('question-dots');
    container.innerHTML = '';
    state.questions.forEach((_, i) => {
        const dot = document.createElement('span');
        dot.className = 'q-dot' + (i === 0 ? ' active' : '');
        dot.dataset.index = i;
        dot.addEventListener('click', () => goToQuestion(i));
        container.appendChild(dot);
    });
}

function updateDots() {
    document.querySelectorAll('.q-dot').forEach((dot, i) => {
        dot.className = 'q-dot';
        if (i === state.currentIndex)                             dot.classList.add('active');
        else if (state.answers[state.questions[i]?.id] !== undefined &&
                 state.answers[state.questions[i]?.id] !== '')    dot.classList.add('done');
    });
    document.getElementById('question-counter').textContent =
        `${state.currentIndex + 1} / ${state.questions.length}`;
}

function renderCurrentQuestion() {
    const q    = state.questions[state.currentIndex];
    const card = document.getElementById('question-card');
    if (!q) return;
    const saved = state.answers[q.id];
    card.innerHTML = buildQuestionHTML(q, saved, state.submitted);
    updateDots();
    updateNavButtons();
    attachAnswerListeners(q);
}

function buildQuestionHTML(q, savedAnswer, isSubmitted) {
    const num = state.currentIndex + 1;

    const typeLabels = {
        true_false:  'True / False',
        mcq:         'Multiple Choice',
        fill_blank:  'Fill in the Blank',
        word_order:  'Word Order',
        synonym:     'Synonym',
        grammar:     'Grammar',
        vocabulary:  'Vocabulary',
    };

    let html = `
        <div class="question-header">
            <span class="question-num">Q${num}</span>
            <span class="question-type-badge">${typeLabels[q.type] || q.type}</span>
        </div>
        <p class="question-text">${q.question}</p>
    `;

    if (q.type === 'true_false') {
        html += buildTrueFalse(q, savedAnswer, isSubmitted);
    } else if (['mcq', 'grammar', 'vocabulary'].includes(q.type)) {
        html += buildMCQ(q, savedAnswer, isSubmitted);
    } else if (q.type === 'fill_blank') {
        html += buildFillBlank(q, savedAnswer, isSubmitted);
    } else if (q.type === 'word_order') {
        html += buildWordOrder(q, savedAnswer, isSubmitted);
    } else if (q.type === 'synonym') {
        html += buildSynonym(q, savedAnswer, isSubmitted);
    } else {
        html += buildTextInput(q, savedAnswer, isSubmitted);
    }

    return html;
}

function buildTrueFalse(q, saved, submitted) {
    return `
        <div class="tf-options">
            ${['True', 'False'].map(opt => {
                let cls = 'choice-btn tf-btn';
                if (saved === opt) cls += ' selected';
                return `<button class="${cls}" data-value="${opt}" ${submitted ? 'disabled' : ''}>${opt}</button>`;
            }).join('')}
        </div>
    `;
}

function buildMCQ(q, saved, submitted) {
    if (!q.choices || !q.choices.length) return '<p style="color:#aaa;font-size:13px;">No choices available.</p>';

    let savedLetter = null;
    if (saved) {
        if (saved.length === 1 && saved.toUpperCase() >= 'A' && saved.toUpperCase() <= 'Z') {
            savedLetter = saved.toUpperCase();
        } else {
            const idx = q.choices.findIndex(c => c === saved);
            if (idx >= 0) savedLetter = String.fromCharCode(65 + idx);
        }
    }

    return `
        <div class="mcq-options">
            ${q.choices.map((choice, i) => {
                const letter = String.fromCharCode(65 + i);
                let cls = 'choice-btn mcq-btn';
                if (savedLetter === letter) cls += ' selected';
                return `
                    <button class="${cls}" data-value="${letter}" data-text="${choice}" ${submitted ? 'disabled' : ''}>
                        <span class="choice-letter">${letter}</span>
                        <span class="choice-text">${choice}</span>
                    </button>
                `;
            }).join('')}
        </div>
    `;
}

function buildFillBlank(q, saved, submitted) {
    if (q.choices && q.choices.length > 0) {
        return `
            <div class="mcq-options">
                ${q.choices.map((choice, i) => {
                    const letter = String.fromCharCode(65 + i);
                    // Extrait le mot sans le préfixe lettre (ex: "B) buy" → "buy")
                    const wordValue = choice.replace(/^[A-D][\)\.\s\-]+\s*/, '').trim();
                    
                    let cls = 'choice-btn fill-btn';
                    // Accepte mot, texte complet, ou lettre (compatibilité)
                    if (saved === wordValue || saved === choice || saved === letter) cls += ' selected';
                    return `<button class="${cls}" data-value="${wordValue}" data-text="${choice}" ${submitted ? 'disabled' : ''}>${choice}</button>`;
                }).join('')}
            </div>
        `;
    }
    return `
        <input type="text" class="text-input" id="fill-input-${q.id}"
               placeholder="Type your answer…"
               value="${saved || ''}" ${submitted ? 'disabled' : ''}/>
    `;
}

function buildWordOrder(q, saved, submitted) {
    const words    = q.choices || (q.correct_order ? [...q.correct_order] : []);
    const shuffled = [...words].sort(() => Math.random() - 0.5);
    return `
        <div class="word-order-section">
            <div class="word-bank" id="word-bank-${q.id}">
                ${shuffled.map(w => `
                    <button class="word-chip${submitted ? ' disabled' : ''}"
                            data-word="${w}" ${submitted ? 'disabled' : ''}>${w}</button>
                `).join('')}
            </div>
            <div class="word-answer-area" id="word-area-${q.id}">
                <p class="word-area-placeholder">Click words to build your sentence…</p>
            </div>
            <input type="hidden" id="word-input-${q.id}" value="${saved || ''}"/>
        </div>
    `;
}

function buildSynonym(q, saved, submitted) {
    return `
        <input type="text" class="text-input" id="synonym-input-${q.id}"
               placeholder="Type a synonym for '${q.target_word || ''}'…"
               value="${saved || ''}" ${submitted ? 'disabled' : ''}/>
    `;
}

function buildTextInput(q, saved, submitted) {
    return `
        <input type="text" class="text-input" id="text-input-${q.id}"
               placeholder="Your answer…"
               value="${saved || ''}" ${submitted ? 'disabled' : ''}/>
    `;
}

// ════════════════════════════════════════════════════════════
//  EVENT LISTENERS DES RÉPONSES
// ════════════════════════════════════════════════════════════

function attachAnswerListeners(q) {
    document.querySelectorAll('.choice-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (state.submitted) return;
            document.querySelectorAll('.choice-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');

            const value = btn.dataset.value;
            const text  = btn.dataset.text || value;

            if (q.type === 'true_false') {
                state.answers[q.id] = value;
            } else if (['mcq', 'grammar', 'vocabulary'].includes(q.type)) {
                state.answers[q.id] = value;   // lettre A/B/C/D
            } else if (q.type === 'fill_blank') {
                state.answers[q.id] = value;
            } else {
                state.answers[q.id] = value;
            }

            updateNavButtons();
        });
    });

    // Inputs texte
    ['fill-input', 'synonym-input', 'text-input'].forEach(prefix => {
        const el = document.getElementById(`${prefix}-${q.id}`);
        if (el) {
            el.addEventListener('input', () => {
                state.answers[q.id] = el.value.trim();
                updateNavButtons();
            });
        }
    });

    if (q.type === 'word_order') {
        setupWordOrder(q);
    }
}

function setupWordOrder(q) {
    const bank   = document.getElementById(`word-bank-${q.id}`);
    const area   = document.getElementById(`word-area-${q.id}`);
    const hidden = document.getElementById(`word-input-${q.id}`);
    if (!bank || !area) return;

    bank.querySelectorAll('.word-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            if (chip.classList.contains('used')) return;
            chip.classList.add('used');

            const placed = document.createElement('span');
            placed.className    = 'placed-word';
            placed.textContent  = chip.dataset.word;
            placed.dataset.word = chip.dataset.word;

            placed.addEventListener('click', () => {
                chip.classList.remove('used');
                placed.remove();
                updateWordAnswer();
            });

            area.querySelector('.word-area-placeholder')?.remove();
            area.appendChild(placed);
            updateWordAnswer();
        });
    });

    function updateWordAnswer() {
        const sentence = [...area.querySelectorAll('.placed-word')].map(s => s.dataset.word).join(' ');
        if (hidden) hidden.value = sentence;
        state.answers[q.id] = sentence;
        updateNavButtons();
    }
}

// ════════════════════════════════════════════════════════════
//  NAVIGATION
// ════════════════════════════════════════════════════════════

function setupNav() {
    document.getElementById('btn-prev').addEventListener('click', () => {
        if (state.currentIndex > 0) goToQuestion(state.currentIndex - 1);
    });
    document.getElementById('btn-next').addEventListener('click', () => {
        if (state.currentIndex < state.questions.length - 1) {
            goToQuestion(state.currentIndex + 1);
        } else {
            showSubmitSection();
        }
    });
    document.getElementById('btn-submit').addEventListener('click', submitAnswers);
}

function goToQuestion(index) {
    state.currentIndex = index;
    renderCurrentQuestion();
}

function updateNavButtons() {
    const q         = state.questions[state.currentIndex];
    const hasAnswer = q && state.answers[q.id] !== undefined && state.answers[q.id] !== '';
    const isLast    = state.currentIndex === state.questions.length - 1;

    document.getElementById('btn-prev').disabled = state.currentIndex === 0;
    document.getElementById('btn-next').disabled = !hasAnswer && !state.submitted;

    document.getElementById('btn-next').innerHTML = isLast
        ? 'Finish <i class="fas fa-check"></i>'
        : 'Next <i class="fas fa-chevron-right"></i>';
}

function showSubmitSection() {
    const el = document.getElementById('submit-section');
    el.style.display = 'block';
    el.scrollIntoView({ behavior: 'smooth' });
}

// ════════════════════════════════════════════════════════════
//  SOUMISSION
// ════════════════════════════════════════════════════════════

async function submitAnswers() {
    const btnSubmit = document.getElementById('btn-submit');
    btnSubmit.disabled  = true;
    btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting…';

    try {
        const res  = await fetch(`${API_BASE}/api/submit-generated-listening/`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                exercise_id: parseInt(state.exerciseId),
                learner_id:  state.learnerId ? parseInt(state.learnerId) : null,
                answers:     state.answers,
            }),
        });
        const data = await res.json();

        if (!data.success) {
            alert('Error submitting answers. Please try again.');
            btnSubmit.disabled  = false;
            btnSubmit.innerHTML = '<i class="fas fa-check"></i> Submit Answers';
            return;
        }

        state.submitted = true;

        if (!state.firstResultData) {
            state.firstResultData = data;
        }

        if (data.already_done) {
            openAlreadyDoneModal(state.firstResultData);
        } else {
            showResult(data);
        }

    } catch (err) {
        console.error('[GL] submitAnswers error:', err);
        btnSubmit.disabled  = false;
        btnSubmit.innerHTML = '<i class="fas fa-check"></i> Submit Answers';
    }
}

// ════════════════════════════════════════════════════════════
//  RÉSULTAT
// ════════════════════════════════════════════════════════════

function showResult(data) {
    document.getElementById('questions-section').style.display = 'none';
    document.getElementById('submit-section').style.display    = 'none';
    document.getElementById('result-panel').style.display      = 'block';

    // Fermer le modal si ouvert
    closeAlreadyDoneModal();

    // Score
    const scoreEl = document.getElementById('result-score');
    scoreEl.textContent = data.score;

    document.getElementById('result-feedback').textContent =
        data.feedback || getFeedback(data.score);
    document.getElementById('result-detail').textContent =
        `${data.correct_count} / ${data.total} correct answers`;

    // Cercle SVG animé
    animateScoreCircle('score-ring-fill', data.score);

    // Couleur cercle
    const fill = document.getElementById('score-ring-fill');
    fill.className = 'gl-ring-fill';
    if (data.score >= 80)      fill.classList.add('score-high');
    else if (data.score >= 50) fill.classList.add('score-mid');
    else                       fill.classList.add('score-low');

    // Actions
    renderResultActions(data);

    // Afficher le corrigé directement (1ère soumission)
    if (!data.already_done) {
        renderReview(data);
    }

    document.getElementById('result-panel').scrollIntoView({ behavior: 'smooth' });
}

function renderResultActions(data) {
    const actionsEl = document.getElementById('result-actions');

    if (data.already_done) {
        // Exercice déjà fait : afficher Show Results
        actionsEl.innerHTML = `
            <button id="btn-show-result" class="gl-btn gl-btn-outline">
                <i class="fas fa-chart-bar"></i> Show Results
            </button>
        `;
        document.getElementById('btn-show-result').addEventListener('click', () => {
            renderReview(state.firstResultData);
            document.getElementById('btn-show-result').style.display = 'none';
        });
    } else {
        // 1ère soumission : pas de boutons supplémentaires (résultats déjà affichés dessous)
        actionsEl.innerHTML = '';
    }
}

function renderReview(data) {
    const reviewEl = document.getElementById('result-review');
    reviewEl.style.display = 'block';

    // results peut être un objet {id: {...}} ou un tableau
    let resultsArr = [];

    if (data.results) {
        if (Array.isArray(data.results)) {
            resultsArr = data.results;
        } else {
            // Object: {question_id: {user_answer, correct_answer, is_correct, question_text, ...}}
            resultsArr = Object.values(data.results);
        }
    }

    if (!resultsArr.length) {
        reviewEl.innerHTML = '<p class="already-done-msg"><i class="fas fa-info-circle"></i> No detailed results available.</p>';
        return;
    }

    reviewEl.innerHTML = `
        <h4 style="font-family:var(--gl-font-head);font-size:15px;font-weight:700;color:var(--gl-text-1);margin-bottom:16px;padding-top:8px;">
            <i class="fas fa-list-check" style="color:var(--gl-primary);margin-right:6px;"></i>
            Detailed Results
        </h4>
        ${resultsArr.map((r, i) => `
            <div class="review-item ${r.is_correct ? 'correct' : 'incorrect'}">
                <span class="review-icon">
                    <i class="fas ${r.is_correct ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                </span>
                <div class="review-content">
                    <p class="review-question">
                        <strong>Q${i + 1}:</strong> ${r.question_text || r.question || ''}
                    </p>
                    ${r.user_answer ? `<p class="review-your-answer">Your answer: <em>${r.user_answer}</em></p>` : ''}
                    ${!r.is_correct ? `<p class="review-correct">
                        Correct answer: <strong>${r.correct_answer}</strong>
                    </p>` : ''}
                    ${r.explanation ? `<p class="review-your-answer" style="font-style:italic;margin-top:2px;">${r.explanation}</p>` : ''}
                </div>
            </div>
        `).join('')}
    `;

    reviewEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function getFeedback(score) {
    if (score >= 90) return 'Excellent work!';
    if (score >= 80) return 'Very good!';
    if (score >= 70) return 'Good job!';
    if (score >= 60) return 'Well done!';
    if (score >= 50) return 'Keep trying!';
    if (score >= 40) return 'Need practice!';
    return 'Try more!';
}

// ── Cercle SVG animé ─────────────────────────────────────────
function animateScoreCircle(fillId, score) {
    const fill        = document.getElementById(fillId);
    if (!fill) return;
    const circumference = 2 * Math.PI * 50;  // r=50
    fill.style.strokeDasharray  = circumference;
    fill.style.strokeDashoffset = circumference;

    // Force reflow
    fill.getBoundingClientRect();

    const offset = circumference - (score / 100) * circumference;
    fill.style.transition       = 'stroke-dashoffset .9s cubic-bezier(.4,0,.2,1)';
    fill.style.strokeDashoffset = offset;
}

// ════════════════════════════════════════════════════════════
//  MODAL — Already Done
// ════════════════════════════════════════════════════════════

function openAlreadyDoneModal(result) {
    const modal = document.getElementById('already-done-modal');
    modal.style.display = 'flex';

    // Score
    document.getElementById('modal-score').textContent  = result.score;
    document.getElementById('modal-feedback').textContent =
        result.feedback || getFeedback(result.score);
    document.getElementById('modal-detail').textContent =
        `${result.correct_count} / ${result.total} correct answers`;

    // Cercle animé
    animateScoreCircle('modal-ring-fill', result.score);

    // Couleur
    const fill = document.getElementById('modal-ring-fill');
    fill.className = 'gl-ring-fill';
    if (result.score >= 80)      fill.classList.add('score-high');
    else if (result.score >= 50) fill.classList.add('score-mid');
    else                         fill.classList.add('score-low');

    // ── "Show Results" → ferme le modal + affiche le résultat + corrigé ──
    document.getElementById('modal-show-result-btn').onclick = () => {
        closeAlreadyDoneModal();
        showResult({ ...result, already_done: true });
        // Afficher le corrigé immédiatement
        setTimeout(() => renderReview(result), 100);
    };

    // ── Close ──────────────────────────────────────────────────────────
    document.getElementById('modal-close-btn').onclick = closeAlreadyDoneModal;
    document.getElementById('modal-close-x').onclick   = closeAlreadyDoneModal;

    // Fermer en cliquant sur l'overlay
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeAlreadyDoneModal();
    });
}

function closeAlreadyDoneModal() {
    const modal = document.getElementById('already-done-modal');
    if (modal) modal.style.display = 'none';
}