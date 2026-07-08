const LEARNER_ID = localStorage.getItem('learner_id') || 1;
let currentType  = 'vocabulary';
let allData      = {};

// ── Fetch recommendations ──────────────────────────────
async function loadRecommendations() {
    try {
        const res  = await fetch(`/api/recommendations/?learner_id=${LEARNER_ID}`);
        const data = await res.json();

        document.getElementById('loading').style.display = 'none';
        document.getElementById('cefr-badge').textContent = data.cefr_level;

        allData = data.recommendations;
        renderSection(currentType);

    } catch (err) {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').style.display   = 'block';
        document.getElementById('error').textContent     = 'Failed to load recommendations.';
    }
}

// ── Render a section ───────────────────────────────────
function renderSection(type) {
    document.querySelectorAll('.section').forEach(s => s.style.display = 'none');

    const section = document.getElementById(`section-${type}`);
    section.style.display = 'block';
    section.innerHTML = '';

    if (type === 'vocabulary') {
        const vocab = allData['vocabulary'] || {};
        const personalized = vocab.personalized || [];
        const others       = vocab.others       || [];

        // Section 1 — Personalized
        if (personalized.length > 0) {
            section.innerHTML += `
                <p style="font-size:13px; font-weight:600; color:#2563eb; 
                           text-transform:uppercase; letter-spacing:.05em; 
                           margin-bottom:12px;">
                    🎯 Personalized Vocabulary
                </p>`;
            const grid1 = document.createElement('div');
            grid1.className = 'section';
            grid1.style.marginBottom = '28px';
            personalized.forEach(item => grid1.appendChild(buildCard('vocabulary', item)));
            section.appendChild(grid1);
        }

        // Section 2 — Others
        if (others.length > 0) {
            const div = document.createElement('p');
            div.style.cssText = 'font-size:13px; font-weight:600; color:#2563eb; text-transform:uppercase; letter-spacing:.05em; margin-bottom:12px;';
            div.textContent = '📚 Other Recommendations';
            section.appendChild(div);
            const grid2 = document.createElement('div');
            grid2.className = 'section';
            others.forEach(item => grid2.appendChild(buildCard('vocabulary', item)));
            section.appendChild(grid2);
        }

        if (personalized.length === 0 && others.length === 0) {
            section.innerHTML = '<p style="color:#718096">No recommendations available.</p>';
        }
        return;
    }

    // autres types (grammar, reading, tasks) — comportement normal
    section.style.display = 'grid';
    const items = allData[type] || [];
    if (items.length === 0) {
        section.innerHTML = '<p style="color:#718096">No recommendations available.</p>';
        return;
    }
    items.forEach(item => section.appendChild(buildCard(type, item)));
}

// ── Build a card ───────────────────────────────────────
function buildCard(type, item) {
    const card = document.createElement('div');
    card.className = 'card';

    const scorePct = Math.round(item.score * 100);

    if (type === 'vocabulary') {
        card.innerHTML = `
            <div class="card-title">${item.headword}</div>
            <div class="card-meta">
                <span class="badge">${item.cefr}</span>
                <span class="badge">${item.pos || ''}</span>
            </div>
            ${item.definition ? `<div class="card-body">${item.definition}...</div>` : ''}
            <div class="score-bar"><div class="score-fill" style="width:${scorePct}%"></div></div>`
            
            
            
            ;



        card.style.cursor = 'pointer';
        card.addEventListener('click', () => {
            markClicked('vocabulary', item.model_idx);
            openVocabularyModal(item);
    });
    } else if (type === 'grammar') {
    card.innerHTML = `
        <div class="card-title">${item.super_category}</div>
        <div class="card-meta"><span class="badge">${item.cefr}</span></div>
        <div class="card-body">${item.guideword || ''}</div>
        <div class="card-body" style="margin-top:8px;font-style:italic;color:#a0aec0">${item.example || ''}</div>
        <div class="score-bar"><div class="score-fill" style="width:${scorePct}%"></div></div>`;
    card.style.cursor = 'pointer';
    card.addEventListener('click', () => {
    markClicked('grammar', item.model_idx);
    openGrammarModal(item);
});

    } else if (type === 'reading') {
card.innerHTML = `
        <div class="card-title">${item.title}</div>
        <div class="card-meta">
            <span class="badge">${item.cefr}</span>
            <span>${item.word_count} words</span>
        </div>
        <div class="score-bar"><div class="score-fill" style="width:${scorePct}%"></div></div>`;
    card.style.cursor = 'pointer';
    card.addEventListener('click', () => {
    markClicked('reading', item.model_idx);
    openReadingModal(item.model_idx, item.title);
});

    } else if (type === 'tasks') {
    card.innerHTML = `
            <div class="card-title">${item.title}</div>
            <div class="card-meta">
                <span class="badge">${item.cefr}</span>
                <span>${item.topic}</span>
            </div>
            <div class="card-body">${item.written_task ? item.written_task.substring(0, 100) + '...' : ''}</div>
            <div class="score-bar"><div class="score-fill" style="width:${scorePct}%"></div></div>`;
        card.style.cursor = 'pointer';
        card.addEventListener('click', () => {
    markClicked('task', item.model_idx);
    openTaskModal(item.title, item.topic, item.written_task, item.cefr);
});
    }

    return card;
}
// ── Reading Modal ──────────────────────────────────────
async function openReadingModal(modelIdx, title) {
    // Créer le modal
    const overlay = document.createElement('div');
    overlay.id = 'reading-overlay';
    overlay.style.cssText = `
        position:fixed; inset:0; background:rgba(0,0,0,0.5);
        z-index:1000; display:flex; align-items:center; justify-content:center;`;

    overlay.innerHTML = `
        <div style="background:white; border-radius:16px; width:720px; max-width:90vw;
                    max-height:85vh; display:flex; flex-direction:column; overflow:hidden;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.2);">
            <div style="padding:24px 28px; border-bottom:1px solid #e5e7eb; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="font-size:18px; font-weight:600; color:#1a1d2e;">${title}</h2>
                <button onclick="closeReadingModal()" style="background:none; border:none; font-size:22px; cursor:pointer; color:#6b7280;">✕</button>
            </div>
            <div id="modal-body" style="padding:28px; overflow-y:auto; flex:1; font-size:15px; line-height:1.9; color:#4a5568;">
                <p style="color:#6b7280; text-align:center;">Loading...</p>
            </div>
            <div style="padding:20px 28px; border-top:1px solid #e5e7eb; text-align:center;">
                <button onclick="closeReadingModal()" style="
                    background:#2563eb; color:white; border:none;
                    padding:12px 32px; border-radius:10px; font-size:15px;
                    font-weight:600; cursor:pointer; font-family:'DM Sans',sans-serif;">
                    ✅ Reading Completed!
                </button>
            </div>
        </div>`;

    document.body.appendChild(overlay);
    overlay.addEventListener('click', e => { if (e.target === overlay) closeReadingModal(); });

    // Charger le texte
    try {
        const res  = await fetch(`/api/recommendations/reading/${modelIdx}/`);
        const data = await res.json();
        document.getElementById('modal-body').textContent = data.text;
    } catch {
        document.getElementById('modal-body').textContent = 'Failed to load text.';
    }
}

function closeReadingModal() {
    document.getElementById('reading-overlay')?.remove();
}

// ── Task Modal ─────────────────────────────────────────
function openTaskModal(title, topic, writtenTask, cefr) {
    const overlay = document.createElement('div');
    overlay.id = 'task-overlay';
    overlay.style.cssText = `
        position:fixed; inset:0; background:rgba(0,0,0,0.5);
        z-index:1000; display:flex; align-items:center; justify-content:center;`;

    overlay.innerHTML = `
        <div style="background:white; border-radius:16px; width:720px; max-width:90vw;
                    max-height:85vh; display:flex; flex-direction:column; overflow:hidden;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.2);">
            <div style="padding:24px 28px; border-bottom:1px solid #e5e7eb; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="font-size:18px; font-weight:600; color:#1a1d2e;">${title}</h2>
                <button onclick="closeTaskModal()" style="background:none; border:none; font-size:22px; cursor:pointer; color:#6b7280;">✕</button>
            </div>
            <div style="padding:28px; overflow-y:auto; flex:1;">
                <div style="margin-bottom:16px; display:flex; gap:8px;">
                    <span style="background:#dbeafe; color:#2563eb; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:600;">${cefr}</span>
                    <span style="background:#f3f4f6; color:#6b7280; padding:4px 10px; border-radius:6px; font-size:12px;">${topic}</span>
                </div>
                <p style="font-size:15px; line-height:1.9; color:#4a5568;">${writtenTask || ''}</p>
            </div>
            <div style="padding:20px 28px; border-top:1px solid #e5e7eb; text-align:center;">
                <button onclick="closeTaskModal()" style="
                    background:#2563eb; color:white; border:none;
                    padding:12px 32px; border-radius:10px; font-size:15px;
                    font-weight:600; cursor:pointer; font-family:'DM Sans',sans-serif;">
                    ✅ Task Completed!
                </button>
            </div>
        </div>`;

    document.body.appendChild(overlay);
    overlay.addEventListener('click', e => { if (e.target === overlay) closeTaskModal(); });
}

function closeTaskModal() {
    document.getElementById('task-overlay')?.remove();
}

// ── Grammar Modal ──────────────────────────────────────
function openGrammarModal(item) {
    const overlay = document.createElement('div');
    overlay.id = 'grammar-overlay';
    overlay.style.cssText = `
        position:fixed; inset:0; background:rgba(0,0,0,0.5);
        z-index:1000; display:flex; align-items:center; justify-content:center;`;

    overlay.innerHTML = `
        <div style="background:white; border-radius:16px; width:720px; max-width:90vw;
                    max-height:85vh; display:flex; flex-direction:column; overflow:hidden;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.2);">
            <div style="padding:24px 28px; border-bottom:1px solid #e5e7eb; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="font-size:18px; font-weight:600; color:#1a1d2e;">${item.super_category}</h2>
                <button onclick="closeGrammarModal()" style="background:none; border:none; font-size:22px; cursor:pointer; color:#6b7280;">✕</button>
            </div>
            <div style="padding:28px; overflow-y:auto; flex:1;">
                <div style="margin-bottom:20px; display:flex; gap:8px;">
                    <span style="background:#dbeafe; color:#2563eb; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:600;">${item.cefr}</span>
                </div>

                <div style="margin-bottom:20px;">
                    <p style="font-size:12px; font-weight:600; color:#9ca3af; text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px;">Rule</p>
                    <p style="font-size:15px; color:#1a1d2e; font-weight:500;">${item.guideword || ''}</p>
                </div>

                <div style="margin-bottom:20px;">
                    <p style="font-size:12px; font-weight:600; color:#9ca3af; text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px;">Can Do</p>
                    <p style="font-size:15px; line-height:1.8; color:#4a5568;">${item.can_do || ''}</p>
                </div>

                <div style="background:#f8fafc; border-radius:10px; padding:16px; border-left:4px solid #2563eb;">
                    <p style="font-size:12px; font-weight:600; color:#9ca3af; text-transform:uppercase; letter-spacing:.05em; margin-bottom:8px;">Example</p>
                    <p style="font-size:15px; font-style:italic; color:#4a5568; line-height:1.8;">${item.example || ''}</p>
                </div>
            </div>
            <div style="padding:20px 28px; border-top:1px solid #e5e7eb; text-align:center;">
                <button onclick="closeGrammarModal()" style="
                    background:#2563eb; color:white; border:none;
                    padding:12px 32px; border-radius:10px; font-size:15px;
                    font-weight:600; cursor:pointer; font-family:'DM Sans',sans-serif;">
                    ✅ Got it!
                </button>
            </div>
        </div>`;

    document.body.appendChild(overlay);
    overlay.addEventListener('click', e => { if (e.target === overlay) closeGrammarModal(); });
}

function closeGrammarModal() {
    document.getElementById('grammar-overlay')?.remove();
}

// ── Marquer un clic dans rec_log ───────────────────────
async function markClicked(contentType, contentId) {
    try {
        await fetch('/api/recommendations/clicked/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                learner_id:   LEARNER_ID,
                content_type: contentType,
                content_id:   contentId,
            })
        });
    } catch (e) { console.log('click log failed', e); }
}

// ── Tabs ───────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentType = tab.dataset.type;
        renderSection(currentType);
    });
});


// ── Vocabulary Modal ───────────────────────────────────
function openVocabularyModal(item) {
    const overlay = document.createElement('div');
    overlay.id = 'vocabulary-overlay';
    overlay.style.cssText = `
        position:fixed; inset:0; background:rgba(0,0,0,0.5);
        z-index:1000; display:flex; align-items:center; justify-content:center;`;

    overlay.innerHTML = `
        <div style="background:white; border-radius:16px; width:600px; max-width:90vw;
                    max-height:85vh; display:flex; flex-direction:column; overflow:hidden;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.2);">
            <div style="padding:24px 28px; border-bottom:1px solid #e5e7eb; display:flex; justify-content:space-between; align-items:center;">
                <h2 style="font-size:22px; font-weight:700; color:#1a1d2e;">${item.headword}</h2>
                <button onclick="closeVocabularyModal()" style="background:none; border:none; font-size:22px; cursor:pointer; color:#6b7280;">✕</button>
            </div>
            <div style="padding:28px; overflow-y:auto; flex:1;">

                <div style="margin-bottom:8px; display:flex; gap:8px;">
                    <span style="background:#dbeafe; color:#2563eb; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:600;">${item.cefr}</span>
                    <span style="background:#f3f4f6; color:#6b7280; padding:4px 10px; border-radius:6px; font-size:12px;">${item.pos || ''}</span>
                </div>

                ${item.definition ? `
                <div style="margin-top:20px;">
                    <p style="font-size:12px; font-weight:600; color:red; text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px;">Definition</p>
                    <p style="font-size:15px; color:#1a1d2e; line-height:1.7;">${item.definition}</p>
                </div>` : ''}

                ${item.synonym && item.synonym !== '_' ? `
                <div style="margin-top:20px;">
                    <p style="font-size:12px; font-weight:600; color:red; text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px;">Synonym</p>
                    <span style="background:#dcfce7; color:#16a34a; padding:6px 14px; border-radius:20px; font-size:14px; font-weight:600;">${item.synonym}</span>
                </div>` : ''}

                ${item.example ? `
                <div style="margin-top:20px; background:#f8fafc; border-radius:10px; padding:16px; border-left:4px solid #2563eb;">
                    <p style="font-size:12px; font-weight:600; color:red; text-transform:uppercase; letter-spacing:.05em; margin-bottom:8px;">Example</p>
                    <p style="font-size:15px; font-style:italic; color:#4a5568; line-height:1.8;">${item.example}</p>
                </div>` : ''}

            </div>
            <div style="padding:20px 28px; border-top:1px solid #e5e7eb; text-align:center;">
                <button onclick="closeVocabularyModal()" style="
                    background:#2563eb; color:white; border:none;
                    padding:12px 32px; border-radius:10px; font-size:15px;
                    font-weight:600; cursor:pointer; font-family:'DM Sans',sans-serif;">
                    ✅ Got it!
                </button>
            </div>
        </div>`;

    document.body.appendChild(overlay);
    overlay.addEventListener('click', e => { if (e.target === overlay) closeVocabularyModal(); });
}

function closeVocabularyModal() {
    document.getElementById('vocabulary-overlay')?.remove();
}

// ── Init ───────────────────────────────────────────────
loadRecommendations();