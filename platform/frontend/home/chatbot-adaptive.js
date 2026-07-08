/**
 * chatbot-adaptive.js
 * ─────────────────────────────────────────────────────────────────
 * Chatbot flottant pour la session de pratique adaptative.
 * S'attache à la page comprehension-ecrite.html.
 *
 * Flux utilisateur :
 *   1. Bouton flottant + tooltip "Would you like to practice?"
 *   2. L'utilisateur clique → fenêtre de chat s'ouvre
 *   3. Bot propose : [Yes, let's start!] / [Maybe later]
 *   4. Si Yes → appel POST /api/adaptive/start/
 *      → Affiche le texte de pratique + première question
 *   5. L'apprenant répond → POST /api/adaptive/answer/
 *      → Feedback adaptatif (hint / guided / explanation / validation)
 *      → Question suivante ou résumé de fin de session
 * ─────────────────────────────────────────────────────────────────
 */

const API_BASE = 'http://localhost:8000';

// ── État global du chatbot ────────────────────────────────────────
const ChatState = {
    sessionId:    null,
    phase:        'idle',    // idle | proposing | loading | questioning | finished
    questionNum:  1,
    maxQuestions: 8,         // cohérent avec adaptive_practice.py MAX_QUESTIONS
};

// ── DOM helpers ───────────────────────────────────────────────────
const $  = id  => document.getElementById(id);
const $$ = sel => document.querySelector(sel);

// ── Init — injecte le HTML du chatbot dans la page ────────────────
function initChatbot() {
    injectChatbotHTML();
    bindEvents();
    scheduleTooltip();
}

function injectChatbotHTML() {
    const html = `
    <!-- Tooltip -->
    <div class="chat-tooltip" id="chat-tooltip" style="display:none;">
        <i class="fas fa-robot"></i>
        Would you like to practice?
    </div>

    <!-- Bouton flottant -->
    <button id="adaptive-chat-btn" title="Practice with AI tutor" aria-label="Open AI practice chat">
        <i class="fas fa-robot"></i>
        <span class="chat-badge" id="chat-badge" style="display:none;">1</span>
    </button>

    <!-- Fenêtre de chat -->
    <div id="adaptive-chat-window" role="dialog" aria-label="Adaptive practice chat">
        <!-- Barre de progression -->
        <div class="chat-progress-bar">
            <div class="chat-progress-fill" id="chat-progress-fill" style="width:0%"></div>
        </div>

        <!-- Header -->
        <div class="chat-header">
            <div class="chat-bot-avatar"><i class="fas fa-robot"></i></div>
            <div class="chat-header-info">
                <h4>AI Tutor</h4>
                <span id="chat-status-text">Ready to practice</span>
            </div>
            <button class="chat-close-btn" id="chat-close-btn" title="Close">
                <i class="fas fa-times"></i>
            </button>
        </div>

        <!-- Messages -->
        <div class="chat-messages" id="chat-messages"></div>

        <!-- Boutons rapides (Yes / No) -->
        <div class="chat-quick-btns" id="chat-quick-btns" style="display:none;"></div>

        <!-- Saisie libre -->
        <div class="chat-input-area hidden" id="chat-input-area">
            <textarea
                id="chat-input"
                placeholder="Type your answer…"
                rows="1"
                aria-label="Your answer"
            ></textarea>
            <button id="chat-send-btn" title="Send" aria-label="Send answer">
                <i class="fas fa-paper-plane"></i>
            </button>
        </div>
    </div>`;

    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    document.body.appendChild(wrapper);
}

// ── Events ────────────────────────────────────────────────────────
function bindEvents() {
    $('adaptive-chat-btn').addEventListener('click', toggleChat);
    $('chat-close-btn').addEventListener('click', closeChat);

    $('chat-send-btn').addEventListener('click', sendAnswer);
    $('chat-input').addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendAnswer(); }
    });
    // Auto-resize textarea
    $('chat-input').addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 80) + 'px';
    });
}

// ── Tooltip affiché après 2 s ─────────────────────────────────────
function scheduleTooltip() {
    setTimeout(() => {
        const t = $('chat-tooltip');
        if (t && ChatState.phase === 'idle') {
            t.style.display = 'flex';
            // Badge rouge
            const badge = $('chat-badge');
            if (badge) badge.style.display = 'flex';
            // Masquer après 6 s
            setTimeout(() => {
                if (t) t.style.display = 'none';
            }, 6000);
        }
    }, 2000);
}

// ── Ouvrir / fermer ───────────────────────────────────────────────
function toggleChat() {
    const win = $('adaptive-chat-window');
    const tip = $('chat-tooltip');
    if (tip) tip.style.display = 'none';

    const badge = $('chat-badge');
    if (badge) badge.style.display = 'none';

    if (win.classList.contains('open')) {
        closeChat();
    } else {
        win.classList.add('open');
        if (ChatState.phase === 'idle') {
            startProposal();
        }
    }
}

function closeChat() {
    $('adaptive-chat-window')?.classList.remove('open');
}

// ── Phase 1 : Proposal ────────────────────────────────────────────
function startProposal() {
    ChatState.phase = 'proposing';
    clearMessages();

    botTyping(1000).then(() => {
        addBotMsg(
            "👋 Hi! <br>" +
            "Would you like a <strong>personalized adaptive practice</strong> session? " +
            "I'll give you a new text on the same topic and ask questions adapted to your level!"
        );
        showQuickBtns([
            { label: "✅ Yes, let's start!", cls: 'primary', cb: startSession },
            { label: "⏱️ Maybe later",       cls: '',         cb: closeChat   },
        ]);
    });
}

// ── Phase 2 : Démarrer la session ─────────────────────────────────
async function startSession() {
    hideQuickBtns();
    hideInputArea();
    ChatState.phase = 'loading';

    addUserMsg("Yes, let's start!");
    await botTyping(800);
    addBotMsg("Great! 🎉 Let me prepare a practice text just for you…");
    const loadMsg = addBotTypingIndicator();

    // Récupérer text_id depuis le JS de l'exercice principal
    const textId    = typeof originalTextId !== 'undefined' ? originalTextId : null;
    const learnerId = localStorage.getItem('learner_id');

    if (!textId) {
        removeBubble(loadMsg);
        addBotMsg("⚠️ I couldn't find the exercise text. Please reload the page and try again.", 'feedback-incorrect');
        ChatState.phase = 'idle';
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/api/adaptive/start/`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ text_id: textId, learner_id: learnerId }),
        });
        const data = await resp.json();
        removeBubble(loadMsg);

        if (!data.success) throw new Error(data.error || 'Server error');

        ChatState.sessionId   = data.session_id;
        ChatState.phase       = 'questioning';
        ChatState.questionNum = 1;

        updateStatus(`Level: ${data.cefr_level}`);

        // Afficher le texte de pratique
        await botTyping(500);
        addBotMsg(
            `<h5>📖 ${escHtml(data.practice_title)}</h5>` +
            `<div style="margin-top:6px;">${escHtml(data.practice_content).replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>')}</div>`,
            'reading-text'
        );

        await botTyping(700);
        addBotMsg("Read the text carefully, then answer my questions. Take your time! 😊");
        await botTyping(600);
        askQuestion(data.question);

    } catch (err) {
        removeBubble(loadMsg);
        addBotMsg(`❌ Error starting session: ${escHtml(err.message)}`, 'feedback-incorrect');
        ChatState.phase = 'idle';
    }
}

// ── Poser une question ────────────────────────────────────────────
function askQuestion(q) {
    const diffIcon = { easy: '🟢', medium: '🟡', hard: '🔴' }[q.difficulty] || '⚪';
    addBotMsg(
        `<strong>Question ${q.number}</strong> ${diffIcon}<br><br>${escHtml(q.text)}`
    );
    updateProgress(q.number);
    updateStatus(`Question ${q.number} · ${q.difficulty}`);
    showInputArea();
    focusInput();
}

// ── Envoyer une réponse ───────────────────────────────────────────
async function sendAnswer() {
    if (ChatState.phase !== 'questioning') return;

    const input  = $('chat-input');
    const answer = input.value.trim();
    if (!answer) return;

    input.value = '';
    input.style.height = 'auto';
    hideInputArea();
    setSendDisabled(true);

    addUserMsg(answer);

    const loadMsg = addBotTypingIndicator();

    try {
        const resp = await fetch(`${API_BASE}/api/adaptive/answer/`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ session_id: ChatState.sessionId, answer }),
        });
        const data = await resp.json();
        removeBubble(loadMsg);

        if (!data.success) throw new Error(data.error || 'Server error');

        // Afficher le feedback avec style selon l'action
        const feedbackCls = feedbackClass(data.action);
        const feedbackIcon = feedbackIcon_(data.action);
        await botTyping(400);
        addBotMsg(`${feedbackIcon} ${escHtml(data.feedback)}`, feedbackCls);

        if (!data.question_done) {
            // L'apprenant peut réessayer
            await botTyping(300);
            addBotMsg("Give it another try! 💪");
            showInputArea();
            focusInput();
            setSendDisabled(false);
            return;
        }

        if (data.session_done) {
            // ── FIN DE SESSION ──────────────────────────────
            await showSessionSummary(data.summary);
            return;
        }

        // ── Question suivante ───────────────────────────────
        await botTyping(500);
        ChatState.questionNum = data.next_question.number;
        askQuestion(data.next_question);
        setSendDisabled(false);

    } catch (err) {
        removeBubble(loadMsg);
        addBotMsg(`❌ Error: ${escHtml(err.message)}`, 'feedback-incorrect');
        showInputArea();
        setSendDisabled(false);
    }
}

// ── Résumé de fin ─────────────────────────────────────────────────
async function showSessionSummary(summary) {
    ChatState.phase = 'finished';
    hideInputArea();
    updateProgress(ChatState.maxQuestions);
    updateStatus('Session complete');

    await botTyping(600);

    const levelEmoji = {
        mastered:        '🏆',
        good:            '⭐',
        partial:         '📈',
        needs_more_work: '💪',
    }[summary.level] || '📊';

    // Bulle de résumé colorée
    const summaryHTML = `
        <div class="session-summary">
            <div class="big-score">${summary.weighted_score}%</div>
            <div class="score-label">${summary.questions_answered} question${summary.questions_answered > 1 ? 's' : ''} answered</div>
            <div class="summary-msg">${levelEmoji} ${escHtml(summary.message)}</div>
            <div class="summary-rec">${escHtml(summary.recommendation)}</div>
        </div>`;

    // On ajoute directement le HTML de résumé dans les messages
    const msgEl = document.createElement('div');
    msgEl.className = 'msg bot';
    msgEl.innerHTML = summaryHTML;
    $('chat-messages').appendChild(msgEl);
    scrollToBottom();

    await botTyping(700);
    addBotMsg("Thanks for practicing! Keep it up! 🌟");

    showQuickBtns([
        { label: '🔄 Practice again', cls: 'primary', cb: resetSession },
        { label: '✖️ Close',          cls: '',        cb: closeChat    },
    ]);
}

// ── Réinitialiser pour une nouvelle session ───────────────────────
function resetSession() {
    hideQuickBtns();
    ChatState.sessionId    = null;
    ChatState.phase        = 'idle';
    ChatState.questionNum  = 1;
    updateProgress(0);
    clearMessages();
    startProposal();
}

// ══════════════════════════════════════════════════════════════════
//  HELPERS UI
// ══════════════════════════════════════════════════════════════════

function addBotMsg(html, extraCls = '') {
    const el = document.createElement('div');
    el.className = 'msg bot';
    el.innerHTML = `
        <div class="msg-avatar"><i class="fas fa-robot"></i></div>
        <div class="msg-bubble ${extraCls}">${html}</div>`;
    $('chat-messages').appendChild(el);
    scrollToBottom();
    return el;
}

function addUserMsg(text) {
    const el = document.createElement('div');
    el.className = 'msg user';
    el.innerHTML = `<div class="msg-bubble">${escHtml(text)}</div>`;
    $('chat-messages').appendChild(el);
    scrollToBottom();
}

function addBotTypingIndicator() {
    const el = document.createElement('div');
    el.className = 'msg bot typing-msg';
    el.innerHTML = `
        <div class="msg-avatar"><i class="fas fa-robot"></i></div>
        <div class="msg-bubble typing">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>`;
    $('chat-messages').appendChild(el);
    scrollToBottom();
    return el;
}

function removeBubble(el) {
    el?.remove();
}

function botTyping(ms) {
    return new Promise(res => setTimeout(res, ms));
}

function clearMessages() {
    $('chat-messages').innerHTML = '';
}

function scrollToBottom() {
    const msgs = $('chat-messages');
    msgs.scrollTop = msgs.scrollHeight;
}

function showQuickBtns(buttons) {
    const container = $('chat-quick-btns');
    container.innerHTML = '';
    buttons.forEach(({ label, cls, cb }) => {
        const btn = document.createElement('button');
        btn.className = `quick-btn ${cls}`;
        btn.innerHTML = label;
        btn.addEventListener('click', cb);
        container.appendChild(btn);
    });
    container.style.display = 'flex';
}

function hideQuickBtns() {
    const container = $('chat-quick-btns');
    container.style.display = 'none';
    container.innerHTML = '';
}

function showInputArea() {
    $('chat-input-area')?.classList.remove('hidden');
}

function hideInputArea() {
    $('chat-input-area')?.classList.add('hidden');
}

function focusInput() {
    setTimeout(() => $('chat-input')?.focus(), 100);
}

function setSendDisabled(disabled) {
    const btn = $('chat-send-btn');
    if (btn) btn.disabled = disabled;
}

function updateProgress(questionNum) {
    const pct = Math.min((questionNum / ChatState.maxQuestions) * 100, 100);
    const fill = $('chat-progress-fill');
    if (fill) fill.style.width = `${pct}%`;
}

function updateStatus(text) {
    const el = $('chat-status-text');
    if (el) el.textContent = text;
}

function feedbackClass(action) {
    return {
        validation:       'feedback-correct',
        hint:             'feedback-hint',
        guided_feedback:  'feedback-hint',
        explanation:      'feedback-incorrect',
    }[action] || '';
}

function feedbackIcon_(action) {
    return {
        validation:       '✅',
        hint:             '💡',
        guided_feedback:  '🔍',
        explanation:      '📚',
    }[action] || '💬';
}

function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ── Lancer au chargement ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initChatbot);