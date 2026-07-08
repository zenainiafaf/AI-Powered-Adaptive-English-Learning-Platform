// ============================================
// exercise-menu.js
// ✅ FIX : passe subunit_id dans l'URL de comprehension-ecrite
//          pour ne pas dépendre du localStorage (perdu entre onglets)
// ✅ AJOUT : Calcul et affichage du score moyen de compréhension écrite
//          Moyenne = somme des scores / nombre d'exercices faits (1 à 4)
// ============================================

function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        subunit:   params.get('subunit')    || '1.1',
        title:     params.get('title')      || 'Exercise',
        subunitId: params.get('subunit_id') || null
    };
}

// ============================================
// CALCUL DU SCORE MOYEN DE COMPRÉHENSION ÉCRITE
// ============================================

/**
 * Charge et calcule le score moyen de compréhension écrite
 * Score = (somme des scores des exercices faits) / (nombre d'exercices faits)
 * Ex: Si fait original (80%) + 1 généré (70%) → Moyenne = (80+70)/2 = 75%
 * @param {string} subunitId - ID du subunit
 * @param {string} learnerId - ID de l'apprenant
 * @returns {Promise<{average: number|null, count: number}>} - Score moyen et nombre d'exercices faits
 */
async function loadReadingComprehensionScore(subunitId, learnerId) {
    if (!learnerId || !subunitId || subunitId === '') {
        return { average: null, count: 0 };
    }
    
    try {
        // 1. Récupérer le texte original pour avoir son ID
        const textResponse = await fetch(`http://localhost:8000/api/reading-exercise/?subunit_id=${subunitId}`);
        const textData = await textResponse.json();
        
        if (!textData.success || !textData.text) {
            console.log('❌ No original text found for subunit:', subunitId);
            return { average: null, count: 0 };
        }
        
        const originalTextId = textData.text.id;
        const scores = []; // Tableau des scores trouvés
        
        // 2. Récupérer le score du texte original (si fait)
        try {
            const originalResult = await fetch(
                `http://localhost:8000/api/check-reading-result/?text_id=${originalTextId}&learner_id=${learnerId}`
            );
            const originalData = await originalResult.json();
            
            if (originalData.success && originalData.has_result) {
                scores.push(originalData.score);
                console.log('✅ Original score:', originalData.score);
            }
        } catch (e) {
            console.log('ℹ️ No original score available');
        }
        
        // 3. Récupérer les scores des exercices générés (0 à 3 possibles)
        try {
            const genResponse = await fetch(
                `http://localhost:8000/api/gen-results/?learner_id=${learnerId}&original_id=${originalTextId}`
            );
            const genData = await genResponse.json();
            
            if (genData.success && genData.results && genData.results.length > 0) {
                genData.results.forEach(r => {
                    if (r.score_percentage !== null && r.score_percentage !== undefined) {
                        scores.push(r.score_percentage);
                    }
                });
                console.log('✅ Generated scores found:', genData.results.length);
            }
        } catch (e) {
            console.log('ℹ️ No generated scores available');
        }
        
        // 4. Calculer la moyenne si on a des scores
        const count = scores.length;
        
        if (count === 0) {
            console.log('ℹ️ No scores found - returning null');
            return { average: null, count: 0 }; // Aucun exercice fait
        }
        
        // ✅ CORRECTION : Diviser par le nombre réel d'exercices faits, pas toujours par 4
        const sum = scores.reduce((a, b) => a + b, 0);
        const average = Math.round(sum / 4);
        console.log(`📊 Average score: ${average}% (from ${count} exercise${count > 1 ? 's' : ''})`);
        console.log('   Scores:', scores);
        
        return { average, count };
        
    } catch (error) {
        console.error('❌ Error loading reading score:', error);
        return { average: null, count: 0 };
    }
}

/**
 * Met à jour l'affichage du badge de score
 * @param {number|null} score - Score moyen ou null
 * @param {number} count - Nombre d'exercices faits
 *@returns {Promise<{average: number|null, count: number}>} Score moyen et nombre d'exercices faits
 */
function updateReadingScoreBadge(score, count) {
    const badge = document.getElementById('reading-score-badge');
    if (!badge) {
        console.error('❌ Badge element not found');
        return;
    }
    
    if (score === null || count === 0) {
        // ✅ Aucun exercice fait - afficher "No progress yet !"
        badge.textContent = 'No progress yet !';
        badge.className = 'difficulty no-progress';
        badge.style.background = '#e9ecef';
        badge.style.color = '#6c757d';
        badge.title = 'Start your first reading exercise!';
    } else {
        // ✅ Score disponible - afficher "15% (1 exercise completed)" ou "75% (3 exercises completed)"
        const exerciseWord = count === 1 ? 'exercise' : 'exercises';
        badge.textContent = `${score}% (${count} ${exerciseWord} completed)`;
        
        // Texte au survol pour détails
        badge.title = `Average score from ${count} completed ${exerciseWord}`;
        
        // Couleur selon le score
        if (score >= 80) {
            badge.className = 'difficulty excellent';
            badge.style.background = '#d4edda';
            badge.style.color = '#155724';
        } else if (score >= 60) {
            badge.className = 'difficulty good';
            badge.style.background = '#fff3cd';
            badge.style.color = '#856404';
        } else if (score >= 40) {
            badge.className = 'difficulty average';
            badge.style.background = '#ffe5cc';
            badge.style.color = '#cc6600';
        } else {
            badge.className = 'difficulty needs-work';
            badge.style.background = '#f8d7da';
            badge.style.color = '#721c24';
        }
    }
}
// ============================================
// CALCUL DU SCORE MOYEN DE COMPRÉHENSION ORALE (LISTENING)
// ============================================

/**
 * Charge et calcule le score moyen de compréhension orale
 * Score = (somme des scores des exercices faits) / (nombre d'exercices faits)
 * @param {string} subunitId - ID du subunit
 * @param {string} learnerId - ID de l'apprenant
 * @returns {Promise<{average: number|null, count: number}>} - Score moyen et nombre d'exercices faits
 */
async function loadListeningComprehensionScore(subunitId, learnerId) {
    if (!learnerId || !subunitId || subunitId === '') {
        return { average: null, count: 0 };
    }
    
    try {
        // 1. Récupérer l'audio original pour avoir son audio_id
        const audioResponse = await fetch(`http://localhost:8000/api/listening-exercise/?subunit_id=${subunitId}`);
        const audioData = await audioResponse.json();
        
        if (!audioData.success || !audioData.audio) {
            console.log('❌ No original audio found for subunit:', subunitId);
            return { average: null, count: 0 };
        }
        
        const originalAudioId = audioData.audio.audio_id;
        const scores = []; // Tableau des scores trouvés
        
        // 2. Récupérer le score de l'audio original (si fait)
        try {
            const originalResult = await fetch(
                `http://localhost:8000/api/check-listening-result/?subunit_id=${subunitId}&learner_id=${learnerId}`
            );
            const originalData = await originalResult.json();
            
            if (originalData.success && originalData.has_result) {
                scores.push(originalData.score);
                console.log('✅ Original listening score:', originalData.score);
            }
        } catch (e) {
            console.log('ℹ️ No original listening score available');
        }
        
        // 3. Récupérer les scores des exercices générés (0 à 1 possible)
        try {
            const genResponse = await fetch(
                `http://localhost:8000/api/gen-listening-results/?learner_id=${learnerId}&original_audio_id=${originalAudioId}`
            );
            const genData = await genResponse.json();
            
            if (genData.success && genData.results && genData.results.length > 0) {
                genData.results.forEach(r => {
                    if (r.score_percentage !== null && r.score_percentage !== undefined) {
                        scores.push(r.score_percentage);
                    }
                });
                console.log('✅ Generated listening scores found:', genData.results.length);
            }
        } catch (e) {
            console.log('ℹ️ No generated listening scores available');
        }
        
        // 4. Calculer la moyenne si on a des scores
        const count = scores.length;
        
        if (count === 0) {
            console.log('ℹ️ No listening scores found - returning null');
            return { average: null, count: 0 }; // Aucun exercice fait
        }
        
        // ✅ FIX : Pour le listening, on divise TOUJOURS par 2 
        // (1 exercice original + 1 exercice généré maximum)
        // Si 1 seul exercice fait → (score + 0) / 2
        const sum = scores.reduce((a, b) => a + b, 0);
        const average = Math.round(sum / 2);
        return { average, count };
    } catch (error) {
        console.error('❌ Error loading listening score:', error);
        return { average: null, count: 0 };
    }
}

/**
 * Met à jour l'affichage du badge de score listening
 * @param {number|null} score - Score moyen ou null
 * @param {number} count - Nombre d'exercices faits
 */
function updateListeningScoreBadge(score, count) {
    const badge = document.getElementById('listening-score-badge');
    if (!badge) {
        console.error('❌ Listening badge element not found');
        return;
    }
    
    if (score === null || count === 0) {
        // ✅ Aucun exercice fait - afficher "No progress yet !"
        badge.textContent = 'No progress yet !';
        badge.className = 'difficulty no-progress';
        badge.style.background = '#e9ecef';
        badge.style.color = '#6c757d';
        badge.title = 'Start your first listening exercise!';
    } else {
        // ✅ Score disponible - afficher "X% (Y exercises completed)"
        const exerciseWord = count === 1 ? 'exercise' : 'exercises';
        badge.textContent = `${score}% (${count} ${exerciseWord} completed)`;
        
        // Texte au survol pour détails
        badge.title = `Average score from ${count} completed ${exerciseWord}`;
        
        // Couleur selon le score
        if (score >= 80) {
            badge.className = 'difficulty excellent';
            badge.style.background = '#d4edda';
            badge.style.color = '#155724';
        } else if (score >= 60) {
            badge.className = 'difficulty good';
            badge.style.background = '#fff3cd';
            badge.style.color = '#856404';
        } else if (score >= 40) {
            badge.className = 'difficulty average';
            badge.style.background = '#ffe5cc';
            badge.style.color = '#cc6600';
        } else {
            badge.className = 'difficulty needs-work';
            badge.style.background = '#f8d7da';
            badge.style.color = '#721c24';
        }
    }
}
// ============================================
// CALCUL DU SCORE MOYEN DE SPEAKING
// ============================================

/**
 * Charge et calcule le score moyen de speaking
 * Score = (somme des scores des exercices faits) / 2
 * (1 exercice original + 1 exercice généré maximum)
 * @param {string} subunitId - ID du subunit
 * @param {string} learnerId - ID de l'apprenant
 * @returns {Promise<{average: number|null, count: number}>} - Score moyen et nombre d'exercices faits
 */
async function loadSpeakingComprehensionScore(subunitId, learnerId) {
    if (!learnerId || !subunitId || subunitId === '') {
        return { average: null, count: 0 };
    }
    
    try {
        // 1. Récupérer l'exercice original pour avoir son ID
        const exerciseResponse = await fetch(`http://localhost:8000/api/speaking-exercise/?subunit_id=${subunitId}`);
        const exerciseData = await exerciseResponse.json();
        
        if (!exerciseData.success || !exerciseData.exercise) {
            console.log('❌ No original speaking exercise found for subunit:', subunitId);
            return { average: null, count: 0 };
        }
        
        const originalExerciseId = exerciseData.exercise.id;
        const scores = []; // Tableau des scores trouvés
        
        // 2. Récupérer le score de l'exercice original (si fait)
        try {
            const originalResult = await fetch(
                `http://localhost:8000/api/check-speaking-result/?subunit_id=${subunitId}&learner_id=${learnerId}`
            );
            const originalData = await originalResult.json();
            
            if (originalData.success && originalData.has_result) {
                scores.push(originalData.accuracy_score);
                console.log('✅ Original speaking score:', originalData.accuracy_score);
            }
        } catch (e) {
            console.log('ℹ️ No original speaking score available');
        }
        
        // 3. Récupérer le score de l'exercice généré (si fait)
        try {
            // Vérifier si un exercice généré existe
            const checkGenResponse = await fetch(
                `http://localhost:8000/api/check-generated-speaking-exists/?exercise_id=${originalExerciseId}&learner_id=${learnerId}`
            );
            const checkGenData = await checkGenResponse.json();
            
            if (checkGenData.success && checkGenData.has_generated) {
                // Un exercice généré existe → vérifier s'il a un résultat
                const genResultResponse = await fetch(
                    `http://localhost:8000/api/check-generated-speaking-result/?gen_exercise_id=${checkGenData.generated_exercise_id}&learner_id=${learnerId}`
                );
                const genResultData = await genResultResponse.json();
                
                if (genResultData.success && genResultData.has_result) {
                    scores.push(genResultData.accuracy_score);
                    console.log('✅ Generated speaking score:', genResultData.accuracy_score);
                }
            }
        } catch (e) {
            console.log('ℹ️ No generated speaking score available');
        }
        
        // 4. Calculer la moyenne si on a des scores
        const count = scores.length;
        
        if (count === 0) {
            console.log('ℹ️ No speaking scores found - returning null');
            return { average: null, count: 0 }; // Aucun exercice fait
        }
        
        // ✅ Pour le speaking, on divise TOUJOURS par 2 
        // (1 exercice original + 1 exercice généré maximum)
        // Si 1 seul exercice fait → (score + 0) / 2
        const sum = scores.reduce((a, b) => a + b, 0);
        const average = Math.round(sum / 2);
        return { average, count };
    } catch (error) {
        console.error('❌ Error loading speaking score:', error);
        return { average: null, count: 0 };
    }
}

/**
 * Met à jour l'affichage du badge de score speaking
 * @param {number|null} score - Score moyen ou null
 * @param {number} count - Nombre d'exercices faits
 */
function updateSpeakingScoreBadge(score, count) {
    const badge = document.getElementById('speaking-score-badge');
    if (!badge) {
        console.error('❌ Speaking badge element not found');
        return;
    }
    
    if (score === null || count === 0) {
        // ✅ Aucun exercice fait - afficher "No progress yet !"
        badge.textContent = 'No progress yet !';
        badge.className = 'difficulty no-progress';
        badge.style.background = '#e9ecef';
        badge.style.color = '#6c757d';
        badge.title = 'Start your first speaking exercise!';
    } else {
        // ✅ Score disponible - afficher "X% (Y exercises completed)"
        const exerciseWord = count === 1 ? 'exercise' : 'exercises';
        badge.textContent = `${score}% (${count} ${exerciseWord} completed)`;
        
        // Texte au survol pour détails
        badge.title = `Average score from ${count} completed ${exerciseWord}`;
        
        // Couleur selon le score
        if (score >= 80) {
            badge.className = 'difficulty excellent';
            badge.style.background = '#d4edda';
            badge.style.color = '#155724';
        } else if (score >= 60) {
            badge.className = 'difficulty good';
            badge.style.background = '#fff3cd';
            badge.style.color = '#856404';
        } else if (score >= 40) {
            badge.className = 'difficulty average';
            badge.style.background = '#ffe5cc';
            badge.style.color = '#cc6600';
        } else {
            badge.className = 'difficulty needs-work';
            badge.style.background = '#f8d7da';
            badge.style.color = '#721c24';
        }
    }
}

// ============================================
// CALCUL DU SCORE MOYEN DE WRITING
// ============================================

/**
 * Charge et calcule le score moyen de writing
 * Score = (somme des scores des exercices faits) / 2
 * (1 exercice original + 1 exercice généré maximum)
 * @param {string} subunitId - ID du subunit
 * @param {string} learnerId - ID de l'apprenant
 * @returns {Promise<{average: number|null, count: number}>} - Score moyen et nombre d'exercices faits
 */
async function loadWritingComprehensionScore(subunitId, learnerId) {
    if (!learnerId || !subunitId || subunitId === '') {
        return { average: null, count: 0 };
    }
    
    try {
        // 1. Récupérer l'exercice original pour avoir son ID
        const exerciseResponse = await fetch(`http://localhost:8000/api/writing-exercise/?subunit_id=${subunitId}`);
        const exerciseData = await exerciseResponse.json();
        
        if (!exerciseData.success || !exerciseData.exercise) {
            console.log('❌ No original writing exercise found for subunit:', subunitId);
            return { average: null, count: 0 };
        }
        
        const originalExerciseId = exerciseData.exercise.id;
        const scores = []; // Tableau des scores trouvés
        
        // 2. Récupérer le score de l'exercice original (si fait)
        try {
            const originalResult = await fetch(
                `http://localhost:8000/api/check-writing-result/?exercise_id=${originalExerciseId}&learner_id=${learnerId}`
            );
            const originalData = await originalResult.json();
            
            if (originalData.success && originalData.has_result) {
                scores.push(originalData.score);
                console.log('✅ Original writing score:', originalData.score);
            }
        } catch (e) {
            console.log('ℹ️ No original writing score available');
        }
        
        // 3. Récupérer le score de l'exercice généré (si fait)
        try {
            // Vérifier si un exercice généré existe
            const checkGenResponse = await fetch(
                `http://localhost:8000/api/check-generated-writing-exists/?exercise_id=${originalExerciseId}&learner_id=${learnerId}`
            );
            const checkGenData = await checkGenResponse.json();
            
            if (checkGenData.success && checkGenData.has_generated) {
                // Un exercice généré existe → vérifier s'il a un résultat
                const genResultResponse = await fetch(
                    `http://localhost:8000/api/check-generated-writing-result/?gen_exercise_id=${checkGenData.generated_exercise_id}&learner_id=${learnerId}`
                );
                const genResultData = await genResultResponse.json();
                
                if (genResultData.success && genResultData.has_result) {
                    scores.push(genResultData.score);
                    console.log('✅ Generated writing score:', genResultData.score);
                }
            }
        } catch (e) {
            console.log('ℹ️ No generated writing score available');
        }
        
        // 4. Calculer la moyenne si on a des scores
        const count = scores.length;
        
        if (count === 0) {
            console.log('ℹ️ No writing scores found - returning null');
            return { average: null, count: 0 }; // Aucun exercice fait
        }
        
        // ✅ Pour le writing, on divise TOUJOURS par 2 
        // (1 exercice original + 1 exercice généré maximum)
        // Si 1 seul exercice fait → (score + 0) / 2
        const sum = scores.reduce((a, b) => a + b, 0);
        const average = Math.round(sum / 2);
        return { average, count };
        
    } catch (error) {
        console.error('❌ Error loading writing score:', error);
        return { average: null, count: 0 };
    }
}

/**
 * Met à jour l'affichage du badge de score writing
 * @param {number|null} score - Score moyen ou null
 * @param {number} count - Nombre d'exercices faits
 */
function updateWritingScoreBadge(score, count) {
    const badge = document.getElementById('writing-score-badge');
    if (!badge) {
        console.error('❌ Writing badge element not found');
        return;
    }
    
    if (score === null || count === 0) {
        // ✅ Aucun exercice fait - afficher "No progress yet !"
        badge.textContent = 'No progress yet !';
        badge.className = 'difficulty no-progress';
        badge.style.background = '#e9ecef';
        badge.style.color = '#6c757d';
        badge.title = 'Start your first writing exercise!';
    } else {
        // ✅ Score disponible - afficher "X% (Y exercises completed)"
        const exerciseWord = count === 1 ? 'exercise' : 'exercises';
        badge.textContent = `${score}% (${count} ${exerciseWord} completed)`;
        
        // Texte au survol pour détails
        badge.title = `Average score from ${count} completed ${exerciseWord}`;
        
        // Couleur selon le score
        if (score >= 80) {
            badge.className = 'difficulty excellent';
            badge.style.background = '#d4edda';
            badge.style.color = '#155724';
        } else if (score >= 60) {
            badge.className = 'difficulty good';
            badge.style.background = '#fff3cd';
            badge.style.color = '#856404';
        } else if (score >= 40) {
            badge.className = 'difficulty average';
            badge.style.background = '#ffe5cc';
            badge.style.color = '#cc6600';
        } else {
            badge.className = 'difficulty needs-work';
            badge.style.background = '#f8d7da';
            badge.style.color = '#721c24';
        }
    }
}

// ============================================
// CALCUL DU % GLOBAL DE PROGRESSION SOUS-UNITÉ
// ============================================

/**
 * Calcule le pourcentage global de progression de la sous-unité
 * Basé sur : (reading% + listening% + speaking% + writing%) / 4
 * Chaque activité contribue 25% au total
 * @param {string} subunitId - ID du subunit
 * @param {string} learnerId - ID de l'apprenant
 * @returns {Promise<{percentage: number, completed: number, total: number}>}
 */
async function loadSubunitProgress(subunitId, learnerId) {
    if (!learnerId || !subunitId) {
        return { percentage: 0, completed: 0, total: 4 };
    }
    
    try {
        const [reading, listening, speaking, writing] = await Promise.all([
            loadReadingComprehensionScore(subunitId, learnerId),
            loadListeningComprehensionScore(subunitId, learnerId),
            loadSpeakingComprehensionScore(subunitId, learnerId),
            loadWritingComprehensionScore(subunitId, learnerId)
        ]);
        
        let completed = 0;
        let totalScoreSum = 0;
        
        if (reading.average !== null) {
            completed += 1;
            totalScoreSum += reading.average;
        }
        
        if (listening.average !== null) {
            completed += 1;
            totalScoreSum += listening.average;
        }
        
        if (speaking.average !== null) {
            completed += 1;
            totalScoreSum += speaking.average;
        }
        
        if (writing.average !== null) {
            completed += 1;
            totalScoreSum += writing.average;
        }
        
        // ✅ FIX : Toujours diviser par 4, même si une seule activité est faite
        const percentage = Math.round(totalScoreSum / 4);
        
        console.log(`📊 Subunit Progress: ${percentage}% (${completed}/4 activities started)`);
        
        return {
            percentage: percentage,
            completed: completed,
            total: 4,
            details: {
                reading: reading.average,
                listening: listening.average,
                speaking: speaking.average,
                writing: writing.average
            }
        };
        
    } catch (error) {
        console.error('❌ Error calculating subunit progress:', error);
        return { percentage: 0, completed: 0, total: 4 };
    }
}

/**
 * Met à jour la barre de progression globale de la sous-unité
 * @param {number} percentage - Pourcentage global (0-100)
 * @param {number} completed - Nombre d'activités commencées
 * @param {number} total - Total d'activités (4)
 */
function updateSubunitProgressBar(percentage, completed, total) {
    const progressBar = document.getElementById('subunit-progress-bar');
    const progressText = document.getElementById('subunit-progress-text');
    
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        
        // ✅ CORRECTION : Garder "progress-fill" comme classe de base
        // Supprimer les anciennes classes de couleur
        progressBar.classList.remove('not-started', 'needs-work', 'average', 'good', 'excellent');
        
        // Ajouter la bonne classe de couleur
        if (percentage >= 80) {
            progressBar.classList.add('excellent');
        } else if (percentage >= 60) {
            progressBar.classList.add('good');
        } else if (percentage >= 40) {
            progressBar.classList.add('average');
        } else if (percentage > 0) {
            progressBar.classList.add('needs-work');
        } else {
            progressBar.classList.add('not-started');
        }
    }
    
    if (progressText) {
        progressText.textContent = `${completed}/${total} exercises completed`;
    }
    
    // Badge global
    const globalBadge = document.getElementById('global-progress-badge');
    if (globalBadge) {
        // Supprimer anciennes classes
        globalBadge.classList.remove('not-started', 'needs-work', 'average', 'good', 'excellent');
        
        if (completed === 0) {
            globalBadge.textContent = 'Start learning!';
            globalBadge.classList.add('not-started');
        } else if (percentage < 60) {
            globalBadge.textContent = `${percentage}% - Keep practicing!`;
            globalBadge.classList.add('needs-work');
        } else if (percentage < 80) {
            globalBadge.textContent = `${percentage}% - Good progress!`;
            globalBadge.classList.add('good');
        } else {
            globalBadge.textContent = `${percentage}% - Excellent!`;
            globalBadge.classList.add('excellent');
        }
    }
}
// ============================================
// INITIALISATION
// ============================================

document.addEventListener('DOMContentLoaded', async function() {
    const { subunit, title, subunitId } = getUrlParams();
    const learnerId = localStorage.getItem('learner_id');

    // Mettre à jour le badge et le titre
    const subunitIdEl    = document.getElementById('subunit-id');
    const subunitTitleEl = document.getElementById('subunit-title');
    if (subunitIdEl)    subunitIdEl.textContent    = subunit;
    if (subunitTitleEl) subunitTitleEl.textContent = title;

    // Stocker en localStorage (fallback)
    localStorage.setItem('currentSubunit',      subunit);
    localStorage.setItem('currentSubunitTitle', title);
    if (subunitId) localStorage.setItem('currentSubunitId', subunitId);

    // ✅ Inclure subunit_id dans l'URL de comprehension-ecrite
    const comprehensionLink = document.getElementById('comprehension-ecrite');
    if (comprehensionLink) {
        comprehensionLink.href = `/comprehension-ecrite/?subunit=${subunit}&title=${encodeURIComponent(title)}&subunit_id=${subunitId}`;
    }

    const listeningLink = document.getElementById('comprehension-orale');
    if (listeningLink) {
        listeningLink.href = `/listening/?subunit=${subunit}&title=${encodeURIComponent(title)}&subunit_id=${subunitId}`;
        listeningLink.classList.remove('disabled');
        // Remplacer le cadenas par une flèche
        listeningLink.querySelector('.exercise-arrow i').className = 'fas fa-chevron-right';
    }

    // Lien Writing
    const writingLink = document.getElementById('expression-ecrite');
    if (writingLink) {
        writingLink.href = `/writing/?subunit=${subunit}&title=${encodeURIComponent(title)}&subunit_id=${subunitId}`;
        writingLink.classList.remove('disabled');
        writingLink.querySelector('.exercise-arrow i').className = 'fas fa-chevron-right';
    }

    const speakingLink = document.getElementById('expression-orale');
    if (speakingLink) {
        speakingLink.href = `/speaking/?subunit=${subunit}&title=${encodeURIComponent(title)}&subunit_id=${subunitId}`;
        speakingLink.classList.remove('disabled');
        speakingLink.querySelector('.exercise-arrow i').className = 'fas fa-chevron-right';
    }
    
    // ✅ Lien retour vers home avec learner_id
    const backBtn = document.querySelector('.back-btn');
    if (backBtn) {
        backBtn.href = learnerId ? `/?learner_id=${learnerId}` : '/';
    }

    // Corriger le menu actif dans la sidebar
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => item.classList.remove('active'));
    const homeLink = document.querySelector('.sidebar-nav a[href="home.html"]');
    if (homeLink) homeLink.classList.add('active');

    // ✅ CHARGER ET AFFICHER LE SCORE MOYEN
    if (subunitId && learnerId) {
        console.log('🔄 Loading reading comprehension score...');
        const { average, count } = await loadReadingComprehensionScore(subunitId, learnerId);
        updateReadingScoreBadge(average, count);
    } else {
        console.log('⚠️ Missing subunitId or learnerId, showing "No progress yet !"');
        updateReadingScoreBadge(null, 0);
    }

    // ✅ CHARGER ET AFFICHER LE SCORE MOYEN DE LISTENING
    if (subunitId && learnerId) {
        console.log('🔄 Loading listening comprehension score...');
        const { average: listeningAverage, count: listeningCount } = await loadListeningComprehensionScore(subunitId, learnerId);
        updateListeningScoreBadge(listeningAverage, listeningCount);
    } else {
        console.log('⚠️ Missing subunitId or learnerId for listening, showing "No progress yet !"');
        updateListeningScoreBadge(null, 0);
    }

    // ✅ CHARGER ET AFFICHER LE SCORE MOYEN DE SPEAKING
    if (subunitId && learnerId) {
        console.log('🔄 Loading speaking comprehension score...');
        const { average: speakingAverage, count: speakingCount } = await loadSpeakingComprehensionScore(subunitId, learnerId);
        updateSpeakingScoreBadge(speakingAverage, speakingCount);
    } else {
        console.log('⚠️ Missing subunitId or learnerId for speaking, showing "No progress yet !"');
        updateSpeakingScoreBadge(null, 0);
    }

    // ✅ CHARGER ET AFFICHER LE SCORE MOYEN DE WRITING
    if (subunitId && learnerId) {
        console.log('🔄 Loading writing comprehension score...');
        const { average: writingAverage, count: writingCount } = await loadWritingComprehensionScore(subunitId, learnerId);
        updateWritingScoreBadge(writingAverage, writingCount);
    } else {
        console.log('⚠️ Missing subunitId or learnerId for writing, showing "No progress yet !"');
        updateWritingScoreBadge(null, 0);
    }

    // ✅ CHARGER ET AFFICHER LA PROGRESSION GLOBALE DE LA SOUS-UNITÉ
    if (subunitId && learnerId) {
        console.log('🔄 Loading global subunit progress...');
        const { percentage, completed, total } = await loadSubunitProgress(subunitId, learnerId);
        updateSubunitProgressBar(percentage, completed, total);
    } else {
        console.log('⚠️ Missing subunitId or learnerId for global progress');
        updateSubunitProgressBar(0, 0, 4);
    }
});