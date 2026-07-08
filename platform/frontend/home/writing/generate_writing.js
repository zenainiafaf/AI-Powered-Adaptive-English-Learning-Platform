// ============================================
// generate_writing.js
// Gère l'exercice de writing généré par l'IA
// Flux identique à writing.js mais sur les APIs
// /api/generate-writing-exercise/ etc.
// ============================================

const API_BASE_URL = 'http://localhost:8000/api';
const POLL_INTERVAL_MS = 2500;   // intervalle polling (ms)
const MAX_POLL_ATTEMPTS = 80;    // 80 × 2.5s = 200s max

// ── State ─────────────────────────────────
let currentGenExercise = null;   // objet exercice généré
let currentGenId       = null;   // gen_exercise_id (int)
let learnerId          = null;
let isSubmitting       = false;
let pollTimer          = null;
let pollAttempts       = 0;
let currentSubunit     = null;
let currentTitle       = null;
let currentSubunitId   = null;
let currentOrigExId    = null;   // original exercise_id (pour back-link)

// ─────────────────────────────────────────
// UTILITY
// ─────────────────────────────────────────

function getUrlParams() {
    const p = new URLSearchParams(window.location.search);
    return {
        genExerciseId: p.get('gen_exercise_id') || null,
        subunit:       p.get('subunit')          || '1.1',
        title:         p.get('title')            || 'Writing Exercise',
        subunitId:     p.get('subunit_id')       || null,
    };
}

function getScoreColor(score) {
    if (score >= 80) return 'var(--success)';
    if (score >= 60) return 'var(--warning)';
    return 'var(--danger)';
}

// ─────────────────────────────────────────
// SHOW / HIDE SECTIONS
// ─────────────────────────────────────────

function showLoading(msg = 'Generating your exercise…', sub = 'Our AI is crafting a unique writing prompt.') {
    document.getElementById('loading-state').style.display    = 'flex';
    document.getElementById('exercise-content').style.display = 'none';
    document.getElementById('results-section').style.display  = 'none';
    document.getElementById('already-submitted').style.display= 'none';

    const txtEl = document.querySelector('#loading-state .loading-text');
    const subEl = document.querySelector('#loading-state .loading-sub');
    if (txtEl) txtEl.textContent = msg;
    if (subEl) subEl.textContent = sub;
}

function hideLoading() {
    document.getElementById('loading-state').style.display = 'none';
}

function showExercise() {
    document.getElementById('loading-state').style.display    = 'none';
    document.getElementById('exercise-content').style.display = 'block';
    document.getElementById('results-section').style.display  = 'none';
    document.getElementById('already-submitted').style.display= 'none';
}

function showResults() {
    document.getElementById('loading-state').style.display    = 'none';
    document.getElementById('exercise-content').style.display = 'none';
    document.getElementById('results-section').style.display  = 'block';
    document.getElementById('already-submitted').style.display= 'none';
}

function showAlreadySubmitted(result) {
    document.getElementById('loading-state').style.display    = 'none';
    document.getElementById('exercise-content').style.display = 'none';
    document.getElementById('results-section').style.display  = 'none';
    document.getElementById('already-submitted').style.display= 'block';

    if (!result) return;

    const score = result.overall_score ?? result.score ?? 0;
    const words = result.word_count ?? 0;
    const feedback = result.feedback || {};

    document.getElementById('previous-result').innerHTML = `
        <div class="label">Your Score</div>
        <div class="score-val" style="color:${getScoreColor(score)}">${score}%</div>
        <div class="words-info"><i class="fas fa-font"></i> ${words} words submitted</div>
    `;

    // "View My Result" button
    document.getElementById('view-result-btn').onclick = () => {
        const userText = result.submitted_text || '';
        const errors   = feedback.errors || [];
        let highlighted = userText;
        if (errors.length > 0 && userText) {
            highlighted = _highlightErrorsClientSide(userText, errors);
        }
        displayResults(
            {
                overall_score: score,
                word_count:    words,
                feedback:      feedback,
                your_text_highlighted: highlighted,
            },
            userText,
            currentGenExercise ? currentGenExercise.model_answer : null,
            true
        );
    };
}

// ─────────────────────────────────────────
// ERROR HIGHLIGHT (même logique que writing.js)
// ─────────────────────────────────────────

function _highlightErrorsClientSide(text, errors) {
    if (!errors || errors.length === 0) return text;
    const sorted = [...errors]
        .filter(e => e.word)
        .sort((a, b) => b.word.length - a.word.length);
    let result = text;
    const done = new Set();
    for (const err of sorted) {
        const word = err.word;
        if (!word || done.has(word)) continue;
        const safe   = w => w.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        const title  = `${safe(err.type||'error')}: ${safe(word)} → ${safe(err.correction||err.corrected_sentence||'')}`;
        const repl   = `<span class="error-word" title="${title}">${word}</span>`;
        const regex  = new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}\\b`, 'i');
        const next   = result.replace(regex, repl);
        if (next !== result) { result = next; done.add(word); }
    }
    return result;
}

// ─────────────────────────────────────────
// RENDER EXERCISE
// ─────────────────────────────────────────

function renderExercise(exercise) {
    currentGenExercise = exercise;

    document.getElementById('instruction-text').textContent  = exercise.instruction;
    document.getElementById('word-target').textContent       = exercise.word_count_target || '60-80 words';

    // Guiding points
    const list = document.getElementById('points-list');
    list.innerHTML = '';
    const points = exercise.guiding_points || [];
    if (points.length > 0) {
        points.forEach(pt => {
            const li = document.createElement('li');
            li.textContent = pt;
            list.appendChild(li);
        });
    } else {
        document.getElementById('guiding-points').style.display = 'none';
    }
}

// ─────────────────────────────────────────
// WORD COUNTER
// ─────────────────────────────────────────

function updateWordCount() {
    const text  = document.getElementById('writing-textarea').value.trim();
    const count = text ? text.split(/\s+/).length : 0;
    const el    = document.getElementById('word-counter');
    el.textContent = `${count} word${count !== 1 ? 's' : ''}`;
    el.className = 'word-counter';
    if (count < 50)              el.classList.add('warning');
    else if (count > 100)        el.classList.add('danger');
    else if (count >= 60 && count <= 80) el.classList.add('success');
}

// ─────────────────────────────────────────
// DISPLAY RESULTS (identique à writing.js)
// ─────────────────────────────────────────

function displayResults(result, userText, modelAnswer, isReviewMode = false, fullResponse = null) {
    const feedback = result.feedback || {};
    const score    = result.overall_score ?? 0;

    document.getElementById('score-value').textContent = score;

    // Score breakdown
    const scores = feedback.score_breakdown || {};
    document.getElementById('score-breakdown').innerHTML = `
        <div class="score-item">
            <div class="score-item-label">Content</div>
            <div class="score-item-value">${scores.content ?? 0}</div>
        </div>
        <div class="score-item">
            <div class="score-item-label">Vocabulary</div>
            <div class="score-item-value">${scores.vocabulary ?? 0}</div>
        </div>
        <div class="score-item">
            <div class="score-item-label">Grammar</div>
            <div class="score-item-value">${scores.grammar ?? 0}</div>
        </div>
        <div class="score-item">
            <div class="score-item-label">Length</div>
            <div class="score-item-value">${scores.length ?? 0}</div>
        </div>
    `;

    // Errors
    let errorsHtml = '';
    if (feedback.errors && feedback.errors.length > 0) {
        errorsHtml = `
            <div class="feedback-section improvements">
                <h4><i class="fas fa-exclamation-circle"></i> Errors to Fix</h4>
                <ul class="feedback-list improvements">
                    ${feedback.errors.map(e => {
                        const obj  = (typeof e === 'object' && e) ? e : { word: String(e) };
                        const word = obj.word || 'unknown';
                        const corr = obj.correction || obj.corrected_sentence || '';
                        const type = obj.type || '';
                        return `<li><i class="fas fa-times"></i> ${word}${corr ? ' → <strong>' + corr + '</strong>' : ''}${type ? ' <span style="color:var(--gray-500)">(' + type + ')</span>' : ''}</li>`;
                    }).join('')}
                </ul>
            </div>`;
    }

    // Warning banners
    let warningHtml = '';
    if (feedback.is_copied) {
        warningHtml = `<div style="background:var(--danger-light,#fee2e2);color:var(--danger);padding:.75rem 1rem;border-radius:.5rem;margin-bottom:1rem;">
            <i class="fas fa-copy"></i> ${feedback.general}</div>`;
    } else if (feedback.is_off_topic) {
        warningHtml = `<div style="background:#fef9c3;color:#92400e;padding:.75rem 1rem;border-radius:.5rem;margin-bottom:1rem;">
            <i class="fas fa-exclamation-triangle"></i> ${feedback.general}</div>`;
    }

    document.getElementById('feedback-content').innerHTML = `
        ${warningHtml}
        ${(!feedback.is_copied && !feedback.is_off_topic) ? `<div class="feedback-general">${feedback.general || ''}</div>` : ''}
        ${errorsHtml}
        ${feedback.word_count_feedback ? `<div style="margin-top:1rem;color:var(--gray-600);"><i class="fas fa-info-circle"></i> ${feedback.word_count_feedback}</div>` : ''}
    `;

    // User text (possibly with error highlights)
    const userTextDisplay = document.getElementById('user-text-display');
    const highlighted = (fullResponse && fullResponse.your_text_highlighted) || result.your_text_highlighted;
    if (highlighted) {
        userTextDisplay.innerHTML = highlighted;
    } else {
        userTextDisplay.textContent = userText || 'No text submitted';
    }
    document.getElementById('user-word-count').textContent = `${result.word_count ?? 0} words`;

    // Model answer (hidden by default)
    const modelSection = document.getElementById('model-answer-section');
    const toggleBtn    = document.getElementById('toggle-model-btn');
    const modelTextEl  = document.getElementById('model-text-display');

    if (modelAnswer) {
        modelTextEl.textContent        = modelAnswer.text || modelAnswer;
        modelSection.style.display     = 'none';
        if (toggleBtn) {
            toggleBtn.style.display    = 'inline-flex';
            toggleBtn.innerHTML        = '<i class="fas fa-eye"></i> Show Typical Example';
        }
    } else {
        if (toggleBtn) toggleBtn.style.display = 'none';
    }

    showResults();
}

function toggleModelAnswer() {
    const sec = document.getElementById('model-answer-section');
    const btn = document.getElementById('toggle-model-btn');
    if (sec.style.display === 'none' || !sec.style.display) {
        sec.style.display  = 'block';
        btn.innerHTML = '<i class="fas fa-eye-slash"></i> Hide Typical Example';
    } else {
        sec.style.display  = 'none';
        btn.innerHTML = '<i class="fas fa-eye"></i> Show Typical Example';
    }
}

// ─────────────────────────────────────────
// POLLING : attend que l'exercice soit prêt
// ─────────────────────────────────────────

function startPolling(genId) {
    pollAttempts = 0;
    pollTimer    = setInterval(async () => {
        pollAttempts++;
        if (pollAttempts > MAX_POLL_ATTEMPTS) {
            clearInterval(pollTimer);
            showErrorState('Generation timed out. Please refresh and try again.');
            return;
        }
        try {
            const r    = await fetch(`${API_BASE_URL}/check-generated-writing-status/?gen_exercise_id=${genId}`);
            const data = await r.json();

            if (!data.success) { return; }  // ignore, retry

            if (data.status === 'ready') {
                clearInterval(pollTimer);
                renderExercise(data.exercise);
                showExercise();
            } else if (data.status === 'error') {
                clearInterval(pollTimer);
                showErrorState(data.error_message || 'Generation failed. Please try again.');
            }
            // 'pending' ou 'generating' → continuer à attendre
        } catch (e) {
            // réseau momentanément indisponible → retry
            console.warn('[poll] retry…', e);
        }
    }, POLL_INTERVAL_MS);
}

function showErrorState(msg) {
    hideLoading();
    const main = document.querySelector('.main-content');
    const div  = document.createElement('div');
    div.style.cssText = 'text-align:center;padding:3rem 1rem;color:var(--danger);';
    div.innerHTML = `
        <div style="font-size:2.5rem;margin-bottom:1rem;">⚠️</div>
        <p style="font-size:1rem;font-weight:600;">${msg}</p>
        <button onclick="window.history.back()" class="btn btn-secondary" style="margin-top:1.5rem;">
            <i class="fas fa-arrow-left"></i> Go Back
        </button>`;
    document.getElementById('loading-state').replaceWith(div);
}

// ─────────────────────────────────────────
// API : SUBMIT
// ─────────────────────────────────────────

async function handleSubmit() {
    if (isSubmitting) return;

    const textarea = document.getElementById('writing-textarea');
    const text     = textarea.value.trim();

    if (!text) { alert('Please write something before submitting!'); return; }
    const wordCount = text.split(/\s+/).length;
    if (wordCount < 10) { alert('Your text is too short. Please write at least 10 words.'); return; }

    isSubmitting = true;
    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Evaluating…';

    try {
        const res  = await fetch(`${API_BASE_URL}/submit-generated-writing/`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                gen_exercise_id: currentGenId,
                learner_id:      learnerId,
                text:            text,
            }),
        });
        const data = await res.json();

        if (!data.success) {
            alert('Error: ' + (data.error || 'Submission failed'));
            return;
        }

        if (data.already_submitted) {
            // Déjà soumis → afficher résultat directement
            showAlreadySubmitted({
                overall_score:  data.result.overall_score,
                word_count:     data.result.word_count,
                feedback:       data.result.feedback,
                submitted_text: data.your_text,
            });
        } else {
            displayResults(
                data.result,
                text,
                currentGenExercise ? currentGenExercise.model_answer : { text: data.model_answer },
                false,
                data
            );
        }

    } catch (e) {
        console.error('Submit error:', e);
        alert('Network error. Please try again.');
    } finally {
        isSubmitting  = false;
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit';
    }
}

// ─────────────────────────────────────────
// WELL DONE MODAL (appelé depuis writing.js)
// ─────────────────────────────────────────

/**
 * Affiche le modal "Well done!" avec le score de l'exercice déjà soumis.
 * Appelé depuis writing.js → showWellDoneModal(genExerciseId, result)
 * @param {number} genExerciseId
 * @param {object} result { overall_score, word_count, ... }
 * @param {object} urlParams { subunit, title, subunitId }
 */
function showWellDoneModal(genExerciseId, result, urlParams = {}) {
    const modal    = document.getElementById('well-done-modal');
    const scoreEl  = document.getElementById('modal-score');
    const wordsEl  = document.getElementById('modal-words');

    const score = result.overall_score ?? result.score ?? 0;
    const words = result.word_count ?? 0;

    scoreEl.textContent = score + '%';
    scoreEl.style.color = getScoreColor(score);
    wordsEl.textContent = `✏️ ${words} words submitted`;

    // Bouton "Show Result" → redirect vers generate_writing.html
    document.getElementById('modal-show-result-btn').onclick = () => {
        const p = new URLSearchParams({
            gen_exercise_id: genExerciseId,
            subunit:  urlParams.subunit  || '1.1',
            title:    urlParams.title    || 'Writing Exercise',
            subunit_id: urlParams.subunitId || '',
        });
        window.location.href = `/writing/generated/?${p}`;
    };

    // Bouton "Close"
    document.getElementById('modal-close-btn').onclick = () => {
        modal.classList.remove('active');
    };

    // Clic fond
    modal.addEventListener('click', e => {
        if (e.target === modal) modal.classList.remove('active');
    });

    modal.classList.add('active');
}

// Exposer pour writing.js
window.showWellDoneModal = showWellDoneModal;

// ─────────────────────────────────────────
// INIT
// ─────────────────────────────────────────

async function init() {
    const { genExerciseId, subunit, title, subunitId } = getUrlParams();
    currentSubunit   = subunit;
    currentTitle     = title;
    currentSubunitId = subunitId;
    currentGenId     = genExerciseId ? parseInt(genExerciseId) : null;

    learnerId = localStorage.getItem('learner_id');

    // Header
    document.getElementById('subunit-id').textContent    = subunit;
    document.getElementById('subunit-title').textContent  = title;

    // Back button → retourne à writing.html
    document.getElementById('back-btn').href =
        `/writing/?subunit=${subunit}&title=${encodeURIComponent(title)}&subunit_id=${subunitId}`;

    // Back to writing (résultats)
    const backWriting = document.getElementById('back-to-writing-btn');
    if (backWriting) {
        backWriting.href =
            `/writing/?subunit=${subunit}&title=${encodeURIComponent(title)}&subunit_id=${subunitId}`;
    }

    // Events
    document.getElementById('writing-textarea').addEventListener('input', updateWordCount);
    document.getElementById('submit-btn').addEventListener('click', handleSubmit);

    if (!currentGenId) {
        showErrorState('No generated exercise ID provided. Please go back and click "Generate New Exercise".');
        return;
    }

    // ── Charger l'exercice ─────────────────────────────────────
    showLoading();

    try {
        // 1. Vérifier statut immédiatement
        const statusRes  = await fetch(`${API_BASE_URL}/check-generated-writing-status/?gen_exercise_id=${currentGenId}`);
        const statusData = await statusRes.json();

        if (!statusData.success) {
            showErrorState(statusData.error || 'Exercise not found.');
            return;
        }

        if (statusData.status === 'ready') {
            // Exercice prêt → vérifier si déjà soumis
            renderExercise(statusData.exercise);

            if (learnerId) {
                const checkRes  = await fetch(
                    `${API_BASE_URL}/check-generated-writing-result/?gen_exercise_id=${currentGenId}&learner_id=${learnerId}`
                );
                const checkData = await checkRes.json();

                if (checkData.success && checkData.has_result) {
                    showAlreadySubmitted({
                        overall_score:  checkData.score,
                        word_count:     checkData.word_count,
                        feedback:       checkData.feedback,
                        submitted_text: checkData.submitted_text,
                    });
                    return;
                }
            }

            showExercise();

        } else if (statusData.status === 'error') {
            showErrorState(statusData.error_message || 'Generation failed.');

        } else {
            // pending / generating → polling
            showLoading(
                'Generating your exercise…',
                'Our AI is crafting a unique writing prompt. This may take a moment.'
            );
            startPolling(currentGenId);
        }

    } catch (e) {
        console.error('Init error:', e);
        showErrorState('Failed to load exercise. Please check your connection and try again.');
    }
}

document.addEventListener('DOMContentLoaded', init);