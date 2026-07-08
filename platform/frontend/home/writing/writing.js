// ============================================
// writing.js - Writing Exercise Frontend
// ============================================

// Configuration
const API_BASE_URL = 'http://localhost:8000/api';
const DEFAULT_SUBUNIT = '1.1';

// State
let currentExercise = null;
let currentSubunit = null;
let learnerId = null;
let isSubmitting = false;

// ============================================
// UTILITY FUNCTIONS
// ============================================

function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        subunit: params.get('subunit') || DEFAULT_SUBUNIT,
        title: params.get('title') || 'Writing Exercise',
        subunitId: params.get('subunit_id') || null
    };
}

function showLoading() {
    document.getElementById('loading-state').style.display = 'flex';
    document.getElementById('exercise-content').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('already-submitted').style.display = 'none';
}

function hideLoading() {
    document.getElementById('loading-state').style.display = 'none';
}

function showExercise() {
    document.getElementById('exercise-content').style.display = 'block';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('already-submitted').style.display = 'none';
}

function showResults(isReviewMode = false) {
    document.getElementById('exercise-content').style.display = 'none';
    document.getElementById('results-section').style.display = 'block';
    document.getElementById('already-submitted').style.display = 'none';
}

function showAlreadySubmitted(result = null) {
    document.getElementById('exercise-content').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('already-submitted').style.display = 'block';
    
    if (result) {
        const prevResultDiv = document.getElementById('previous-result');
        prevResultDiv.innerHTML = `
            <div class="score-item">
                <div class="score-item-label">Your Score</div>
                <div class="score-item-value" style="color: ${getScoreColor(result.score)}">${result.score}%</div>
            </div>
            <div style="margin-top: 1rem; color: var(--gray-600);">
                <i class="fas fa-font"></i> ${result.word_count} words submitted
            </div>
        `;
        
        // Store result for view button
        const userSubmittedText = result.submitted_text || result.text || '';
        document.getElementById('view-result-btn').onclick = () => {

            const feedback = result.feedback || {};
        const errors = feedback.errors || [];
        
        // 🔥 RECONSTRUIRE le texte surligné côté client
        let highlightedText = userSubmittedText;
        if (errors.length > 0 && userSubmittedText) {
            highlightedText = _highlightErrorsClientSide(userSubmittedText, errors);
        }



            displayResults({
                overall_score: result.score,
                word_count: result.word_count,
                feedback: result.feedback,
                your_text_highlighted: highlightedText
            }, userSubmittedText, currentExercise.model_answer, true);
        };
            document.getElementById('generate-exercise-btn').onclick = () => {
            console.log('Generate another exercise - à implémenter');
            handleGenerateNewExercise();
        };
    }   
}
function _highlightErrorsClientSide(text, errors) {
    if (!errors || errors.length === 0) return text;
    
    // Trier par longueur décroissante pour éviter les conflits
    const sorted = [...errors]
        .filter(e => e.word)
        .sort((a, b) => b.word.length - a.word.length);
    
    let result = text;
    const alreadyDone = new Set();
    
    for (const err of sorted) {
        const word = err.word;
        if (!word || alreadyDone.has(word)) continue;
        
        // Escape HTML pour éviter d'injecter du HTML dans le title
        const safeWord = word.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        const safeCorrection = (err.correction || err.corrected_sentence || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        const safeType = (err.type || 'error').replace(/&/g,'&amp;').replace(/"/g,'&quot;');
        
        const title = `${safeType}: ${safeWord} → ${safeCorrection}`;
        const replacement = `<span class="error-word" title="${title}">${word}</span>`;
        
        // Remplacer la première occurrence (case-insensitive, mot entier)
        const regex = new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
        const newResult = result.replace(regex, replacement);
        
        if (newResult !== result) {
            result = newResult;
            alreadyDone.add(word);
        }
    }
    return result;
}
function getScoreColor(score) {
    if (score >= 80) return 'var(--success)';
    if (score >= 60) return 'var(--warning)';
    return 'var(--danger)';
}

// ============================================
// API FUNCTIONS
// ============================================

async function fetchExercise(subunitId) {
    try {
        const response = await fetch(`${API_BASE_URL}/writing-exercise/?subunit_id=${subunitId}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load exercise');
        }
        
        return data.exercise;
    } catch (error) {
        console.error('Error fetching exercise:', error);
        throw error;
    }
}

async function checkExistingResult(exerciseId, learnerId) {
    if (!learnerId) return null;
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/check-writing-result/?exercise_id=${exerciseId}&learner_id=${learnerId}`
        );
        const data = await response.json();
        
        if (data.success && data.has_result) {
            return data;
        }
        return null;
    } catch (error) {
        console.error('Error checking result:', error);
        return null;
    }
}

async function submitWriting(exerciseId, text, learnerId) {
    const payload = {
        exercise_id: exerciseId,
        text: text,
        learner_id: learnerId
    };
    
    const response = await fetch(`${API_BASE_URL}/submit-writing-exercise/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    return await response.json();
}

// ============================================
// UI UPDATE FUNCTIONS
// ============================================

function updateHeader(subunit, title) {
    document.getElementById('subunit-id').textContent = subunit;
    document.getElementById('subunit-title').textContent = title;
}

function renderExercise(exercise) {
    // Update instruction text
    document.getElementById('instruction-text').textContent = exercise.instruction;
    
    // Update word target
    document.getElementById('word-target').textContent = exercise.word_count_target;
    
    // Render guiding points
    const pointsList = document.getElementById('points-list');
    pointsList.innerHTML = '';
    
    if (exercise.guiding_points && exercise.guiding_points.length > 0) {
        exercise.guiding_points.forEach(point => {
            const li = document.createElement('li');
            li.textContent = point;
            pointsList.appendChild(li);
        });
    } else {
        document.getElementById('guiding-points').style.display = 'none';
    }
    
    // Store model answer for later
    currentExercise = exercise;
}

function updateWordCount() {
    const textarea = document.getElementById('writing-textarea');
    const counter = document.getElementById('word-counter');
    
    const text = textarea.value.trim();
    const wordCount = text ? text.split(/\s+/).length : 0;
    
    counter.textContent = `${wordCount} word${wordCount !== 1 ? 's' : ''}`;
    
    // Update counter color based on target (60-80 words)
    counter.className = 'word-counter';
    if (wordCount < 50) {
        counter.classList.add('warning');
    } else if (wordCount > 100) {
        counter.classList.add('danger');
    } else if (wordCount >= 60 && wordCount <= 80) {
        counter.classList.add('success');
    }
}

function displayResults(result, userText, modelAnswer, isReviewMode = false, fullResponse = null) {
    const feedback = result.feedback;
    
    // Update score circle
    const score = result.overall_score;
    document.getElementById('score-value').textContent = score;
    
    // Score breakdown
    const breakdown = document.getElementById('score-breakdown');
    const scores = feedback.score_breakdown || {};
    breakdown.innerHTML = `
        <div class="score-item">
            <div class="score-item-label">Content</div>
            <div class="score-item-value">${scores.content || 0}</div>
        </div>
        <div class="score-item">
            <div class="score-item-label">Vocabulary</div>
            <div class="score-item-value">${scores.vocabulary || 0}</div>
        </div>
        <div class="score-item">
            <div class="score-item-label">Grammar</div>
            <div class="score-item-value">${scores.grammar || 0}</div>
        </div>
        <div class="score-item">
            <div class="score-item-label">Length</div>
            <div class="score-item-value">${scores.length || 0}</div>
        </div>
    `;
    
    // Feedback content
    const feedbackContent = document.getElementById('feedback-content');

    // Errors list
    let errorsHtml = '';
    if (feedback.errors && feedback.errors.length > 0) {
        errorsHtml = `
            <div class="feedback-section improvements">
                <h4><i class="fas fa-exclamation-circle"></i> Errors to Fix</h4>
                <ul class="feedback-list improvements">
                   ${feedback.errors.map(e => {
                       const errObj = (typeof e === 'object' && e !== null) ? e : { word: String(e) };
                       const word = errObj.word || 'unknown';
                       const correction = errObj.correction || errObj.corrected_sentence || '';
                       const type = errObj.type || '';
                       return `<li><i class="fas fa-times"></i> ${word} ${correction ? '→ <strong>' + correction + '</strong>' : ''} ${type ? '<span style="color:var(--gray-500)">(' + type + ')</span>' : ''}</li>`;
                   }).join('')}
                </ul>
            </div>
        `;
    }

    // Warning banners for copied / off-topic
    let warningHtml = '';
    if (feedback.is_copied) {
        warningHtml = `<div style="background:var(--danger-light, #fee2e2);color:var(--danger);padding:.75rem 1rem;border-radius:.5rem;margin-bottom:1rem;">
            <i class="fas fa-copy"></i> ${feedback.general}
        </div>`;
    } else if (feedback.is_off_topic) {
        warningHtml = `<div style="background:#fef9c3;color:#92400e;padding:.75rem 1rem;border-radius:.5rem;margin-bottom:1rem;">
            <i class="fas fa-exclamation-triangle"></i> ${feedback.general}
        </div>`;
    }

    feedbackContent.innerHTML = `
        ${warningHtml}
        ${!feedback.is_copied && !feedback.is_off_topic ? `<div class="feedback-general">${feedback.general}</div>` : ''}
        ${errorsHtml}
        ${feedback.word_count_feedback ? `<div style="margin-top: 1rem; color: var(--gray-600);"><i class="fas fa-info-circle"></i> ${feedback.word_count_feedback}</div>` : ''}
    `;
    
    // User text display
    const userTextDisplay = document.getElementById('user-text-display');
    const highlighted = (fullResponse && fullResponse.your_text_highlighted) 
                        || result.your_text_highlighted;
    
    if (highlighted) {
        userTextDisplay.innerHTML = highlighted;
    } else {
        userTextDisplay.textContent = userText || 'No text submitted';
    }
    document.getElementById('user-word-count').textContent = `${result.word_count || 0} words`;
    
    // Model answer — hidden by default, with toggle button under user text
    const modelSection = document.getElementById('model-answer-section');
    const toggleBtn = document.getElementById('toggle-model-btn');
    const modelTextDisplay = document.getElementById('model-text-display');
    
    if (modelAnswer) {
        modelTextDisplay.textContent = modelAnswer.text || modelAnswer;
        modelSection.style.display = 'none';
        if (toggleBtn) {
            toggleBtn.style.display = 'inline-flex';
            toggleBtn.innerHTML = '<i class="fas fa-eye"></i> Show Typical Example';
        }
    } else {
        if (toggleBtn) toggleBtn.style.display = 'none';
    }
    
    showResults(isReviewMode);
}
function toggleModelAnswer() {
    const modelSection = document.getElementById('model-answer-section');
    const toggleBtn = document.getElementById('toggle-model-btn');
    
    if (modelSection.style.display === 'none' || modelSection.style.display === '') {
        modelSection.style.display = 'block';
        toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i> Hide Typical Example';
    } else {
        modelSection.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-eye"></i> Show Typical Example';
    }
}
// ============================================
// EVENT HANDLERS
// ============================================

async function handleSubmit() {
    if (isSubmitting) return;
    
    const textarea = document.getElementById('writing-textarea');
    const text = textarea.value.trim();
    
    if (!text) {
        alert('Please write something before submitting!');
        return;
    }
    
    const wordCount = text.split(/\s+/).length;
    if (wordCount < 10) {
        alert('Your text is too short. Please write at least 10 words.');
        return;
    }
    
    isSubmitting = true;
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    
    try {
        const response = await submitWriting(currentExercise.id, text, learnerId);
        
        if (response.success) {
            if (response.already_submitted) {
                showAlreadySubmitted(response);
            } else {
                displayResults(response.result, text, currentExercise.model_answer, false, response);
            }
        } else {
            alert('Error: ' + (response.error || 'Failed to submit'));
        }
    } catch (error) {
        console.error('Submit error:', error);
        alert('Failed to submit. Please try again.');
    } finally {
        isSubmitting = false;
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit';
    }
}

function handleTryAgain() {
    document.getElementById('writing-textarea').value = '';
    updateWordCount();
    showExercise();
}

// ============================================
// INITIALIZATION
// ============================================

async function init() {
    // Get URL parameters
    const { subunit, title, subunitId } = getUrlParams();
    currentSubunit = subunit;
    
    // Get learner ID from localStorage
    learnerId = localStorage.getItem('learner_id');
    
    // Update header
    updateHeader(subunit, title);
    
    // Setup back button
    document.getElementById('back-btn').href = `/exercise-menu/?subunit=${subunit}&title=${encodeURIComponent(title)}&subunit_id=${subunitId}`;
    
    // Setup event listeners
    document.getElementById('writing-textarea').addEventListener('input', updateWordCount);
    document.getElementById('submit-btn').addEventListener('click', handleSubmit);
       
    if (!subunitId) {
        alert('No subunit specified!');
        return;
    }
    
    showLoading();
    
    try {
        // Fetch exercise
        const exercise = await fetchExercise(subunitId);
        renderExercise(exercise);
        
        // Check for existing result
        if (learnerId) {
            const existingResult = await checkExistingResult(exercise.id, learnerId);
            if (existingResult) {
                showAlreadySubmitted(existingResult);
                hideLoading();
                return;
            }
        }
        
        showExercise();
        
    } catch (error) {
        alert('Failed to load exercise: ' + error.message);
        console.error(error);
    } finally {
        hideLoading();
    }
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);


// ============================================
// GENERATE NEW EXERCISE — écriture via IA
// ============================================
 
async function handleGenerateNewExercise() {
    if (!currentExercise) return;
    if (!learnerId) {
        alert('Please log in to generate a new exercise.');
        return;
    }
 
    const btn = document.getElementById('generate-exercise-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating…';
 
    try {
        const res  = await fetch(`${API_BASE_URL}/generate-writing-exercise/`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                exercise_id: currentExercise.id,
                learner_id:  learnerId,
            }),
        });
        const data = await res.json();
 
        if (!data.success) {
            alert('Error: ' + (data.error || 'Could not generate exercise.'));
            return;
        }
 
        const urlParams = getUrlParams();
 
        if (data.already_generated && data.has_result) {
            // ── Exercice déjà soumis → modal "Well done!" ──────────
            _showWellDoneModal(data.gen_exercise_id, data.result, urlParams);
 
        } else {
            // ── Exercice nouveau ou pas encore soumis → rediriger ──
            const p = new URLSearchParams({
                gen_exercise_id: data.gen_exercise_id,
                subunit:         urlParams.subunit  || currentSubunit || '1.1',
                title:           urlParams.title    || document.getElementById('subunit-title')?.textContent || 'Writing Exercise',
                subunit_id:      urlParams.subunitId || '',
            });
            window.location.href = `/writing/generated/?${p}`;
        }
 
    } catch (e) {
        console.error('Generate error:', e);
        alert('Network error. Please try again.');
    } finally {
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-pencil-alt"></i> Generate Another Exercise';
    }
}
 
/**
 * Affiche le modal "Well done!" inline dans writing.html.
 * Crée le modal dynamiquement si absent (pas besoin d'HTML supplémentaire).
 */
function _showWellDoneModal(genExerciseId, result, urlParams) {
    // ── Supprimer un éventuel modal précédent ─────────────────
    const old = document.getElementById('_wdm');
    if (old) old.remove();
 
    const score = result.overall_score ?? result.score ?? 0;
    const words = result.word_count ?? 0;
    const color = score >= 80 ? 'var(--success)' : score >= 60 ? 'var(--warning)' : 'var(--danger)';
 
    // ── Construire le modal ───────────────────────────────────
    const modal = document.createElement('div');
    modal.id = '_wdm';
    modal.style.cssText = `
        position:fixed; inset:0;
        background:rgba(0,0,0,.45);
        display:flex; align-items:center; justify-content:center;
        z-index:9999; padding:1rem;
        backdrop-filter:blur(3px);
        animation: _wdmFadeIn .2s ease;
    `;
 
    // Injection de l'animation keyframe (une seule fois)
    if (!document.getElementById('_wdm-style')) {
        const style = document.createElement('style');
        style.id = '_wdm-style';
        style.textContent = `
            @keyframes _wdmFadeIn  { from{opacity:0} to{opacity:1} }
            @keyframes _wdmCardIn  { from{transform:scale(.88) translateY(20px);opacity:0}
                                      to{transform:scale(1) translateY(0);opacity:1} }
        `;
        document.head.appendChild(style);
    }
 
    modal.innerHTML = `
        <div style="
            background:#fff; border-radius:20px; padding:2.5rem 2rem;
            max-width:440px; width:100%; text-align:center;
            box-shadow:0 20px 60px rgba(0,0,0,.18);
            animation:_wdmCardIn .3s cubic-bezier(.34,1.56,.64,1);
        ">
            <div style="font-size:3.5rem;line-height:1;margin-bottom:1rem;">🎉</div>
            <h2 style="font-size:1.6rem;font-weight:900;color:#1f2937;margin-bottom:.4rem;">Well done!</h2>
            <p style="font-size:.9rem;color:#6b7280;margin-bottom:1.5rem;">
                You have already completed your AI-generated exercise.
            </p>
 
            <!-- Score box -->
            <div style="
                background:linear-gradient(135deg,#f3f0ff,#faf8ff);
                border:1px solid rgba(139,92,246,.2);
                border-radius:12px; padding:1.25rem; margin-bottom:1.5rem;
            ">
                <div style="font-size:.7rem;font-weight:700;text-transform:uppercase;
                            letter-spacing:.08em;color:#9ca3af;margin-bottom:.25rem;">
                    Your Score
                </div>
                <div style="font-size:3rem;font-weight:900;line-height:1;
                            color:${color};margin-bottom:.35rem;">
                    ${score}%
                </div>
                <div style="font-size:.85rem;color:#6b7280;">
                    ✏️ ${words} words submitted
                </div>
            </div>
 
            <!-- Actions -->
            <div style="display:flex;flex-direction:column;gap:.6rem;">
                <button id="_wdm-show" style="
                    background:linear-gradient(135deg,#8b5cf6,#7c3aed);
                    color:#fff; border:none; border-radius:10px;
                    padding:.85rem 1.5rem; font-size:.95rem; font-weight:700;
                    cursor:pointer; width:100%; display:flex;
                    align-items:center; justify-content:center; gap:.5rem;
                ">
                    <span>👁️</span> Show Result
                </button>
                <button id="_wdm-close" style="
                    background:#fff; color:#6b7280;
                    border:1.5px solid #e5e7eb; border-radius:10px;
                    padding:.75rem 1.5rem; font-size:.9rem; font-weight:600;
                    cursor:pointer; width:100%;
                ">
                    Close
                </button>
            </div>
        </div>
    `;
 
    document.body.appendChild(modal);
 
    // ── Bouton "Show Result" ──────────────────────────────────
    modal.querySelector('#_wdm-show').addEventListener('click', () => {
        const p = new URLSearchParams({
            gen_exercise_id: genExerciseId,
            subunit:         urlParams.subunit   || currentSubunit || '1.1',
            title:           urlParams.title     || document.getElementById('subunit-title')?.textContent || 'Writing Exercise',
            subunit_id:      urlParams.subunitId || '',
        });
        window.location.href = `/writing/generated/?${p}`;
    });
 
    // ── Bouton "Close" ────────────────────────────────────────
    modal.querySelector('#_wdm-close').addEventListener('click', () => modal.remove());
 
    // ── Clic sur le fond ──────────────────────────────────────
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}