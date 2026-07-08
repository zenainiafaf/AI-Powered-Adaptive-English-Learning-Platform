// ============================================
// home.js - servi par Live Server :8080
// ✅ FIX 1 : récupère learner_id depuis l'URL (?learner_id=...)
//            car localStorage :8000 (login) ≠ localStorage :8080 (home)
// ✅ FIX 2 : learner_id est un entier AutoField (pas UUID)
//            → parseInt est correct ici pour le modèle Learner
// ============================================

const API_BASE = 'http://localhost:8000';

const userState = {
    learnerId: null,
    name: '',
    email: '',
    cefrLevel: '',
    progress: 0
};

let profileTrigger = null;
let profileDropdown = null;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    getLearnerId();      // ✅ récupère depuis URL ou localStorage
    fetchLearnerData();
    initProfileDropdown();
    
    // (quand l'user revient depuis exercise-menu avec le bouton retour)
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            fetchLearnerData();
        }
    });

    //  Rafraîchir aussi quand la fenêtre reprend le focus
    window.addEventListener('focus', function() {
        fetchLearnerData();
    });


    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href && href !== '#') return;
            e.preventDefault();
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
            this.style.transform = 'scale(0.98)';
            setTimeout(() => { this.style.transform = ''; }, 150);
        });
    });

    animateCards();
    console.log('EnglishLearn Dashboard loaded ✅');
});

// ============================================
// USER FUNCTIONS
// ============================================

function getLearnerId() {
    // Récupérer learner_id depuis l'URL en priorité
    const urlParams = new URLSearchParams(window.location.search);
    let idFromUrl = urlParams.get('learner_id');
    const cefrFromUrl = urlParams.get('cefr_level');
    const nameFromUrl = urlParams.get('name');
    const emailFromUrl = urlParams.get('email');
    
    // ✅ VALIDATION STRICTE : rejeter "null", "undefined", chaîne vide
    if (idFromUrl && idFromUrl !== 'null' && idFromUrl !== 'undefined' && idFromUrl.trim() !== '') {
        console.log('✅ learner_id valide depuis URL:', idFromUrl);
        
        // Stocker dans localStorage pour les prochaines visites
        localStorage.setItem('learner_id', idFromUrl);
        
        // Stocker les autres paramètres avec décodage
        if (nameFromUrl && nameFromUrl !== 'null' && nameFromUrl !== 'undefined') {
            const decodedName = decodeURIComponent(nameFromUrl);
            localStorage.setItem('learner_name', decodedName);
            console.log('✅ name stocké:', decodedName);
        }
        if (emailFromUrl && emailFromUrl !== 'null' && emailFromUrl !== 'undefined') {
            const decodedEmail = decodeURIComponent(emailFromUrl);
            localStorage.setItem('learner_email', decodedEmail);
            console.log('✅ email stocké:', decodedEmail);
        }
        if (cefrFromUrl && cefrFromUrl !== 'null' && cefrFromUrl !== 'undefined') {
            localStorage.setItem('learner_cefr_level', cefrFromUrl);
            console.log('✅ cefr_level stocké:', cefrFromUrl);
        }
        
        // Nettoyer l'URL
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (idFromUrl) {
        console.warn('⚠️ learner_id invalide dans URL:', idFromUrl);
    }

    // Récupérer depuis localStorage
    const storedId = localStorage.getItem('learner_id');
    const storedName = localStorage.getItem('learner_name');
    const storedEmail = localStorage.getItem('learner_email');
    const storedCefr = localStorage.getItem('learner_cefr_level');
    const storedProgress = localStorage.getItem('learner_progress');
    
    // ✅ VALIDATION : vérifier que storedId est valide
    if (storedId && storedId !== 'null' && storedId !== 'undefined' && storedId.trim() !== '') {
        const parsedId = parseInt(storedId);
        
        // Vérifier que c'est un nombre valide
        if (!isNaN(parsedId) && parsedId > 0) {
            userState.learnerId = parsedId;
            userState.name = storedName || '';
            userState.email = storedEmail || '';
            userState.cefrLevel = storedCefr || '';
            userState.progress = parseInt(storedProgress) || 0;
            
            console.log('📋 Données utilisateur chargées:', userState);
            return userState.learnerId;
        } else {
            console.error('❌ learner_id n\'est pas un nombre valide:', storedId);
        }
    }
    
    console.error('❌ Non connecté, redirection vers login...');
    window.location.href = '/login/';
    return null;
}

async function fetchLearnerData() {
    if (!userState.learnerId) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/learner/?learner_id=${userState.learnerId}`);
        const result = await response.json();
        
        if (result.success) {
            const learner = result.learner;
            
            userState.name      = learner.name;
            userState.email     = learner.email;
            userState.cefrLevel = learner.cefr_level;
            userState.progress  = learner.progress;
            
            // ✅ AJOUT : stocker la photo pour usage futur
            if (learner.picture) {
                localStorage.setItem('learner_picture', learner.picture);
            }
            
            localStorage.setItem('learner_name',       userState.name);
            localStorage.setItem('learner_email',      userState.email);
            localStorage.setItem('learner_cefr_level', userState.cefrLevel);
            localStorage.setItem('learner_progress',   userState.progress);
            
            updateDashboard();
            updateDropdown();

           
        }
    } catch (error) {
        console.error('Erreur fetchLearnerData:', error);
    }
}
async function refreshProgressFromScores() {
    try {
         // Progress
        const response = await fetch(`${API_BASE}/api/learner-progress/?learner_id=${userState.learnerId}`);
        const result = await response.json();
        
        console.log('📊 API response complète:', result);

        if (result.success) {
            userState.progress = result.progress;
            localStorage.setItem('learner_progress', result.progress);
            localStorage.removeItem('progress_needs_refresh');
            // Mettre à jour l'affichage
            const progressValue = document.getElementById('progress-value');
            if (progressValue) progressValue.textContent = result.progress + '%';
            
            console.log(`✅ Progress updated: ${result.progress}%`);
        }

        // Activities count
        const actResp = await fetch(`${API_BASE}/api/activities-count/?learner_id=${userState.learnerId}`);
        const actResult = await actResp.json();

        if (actResult.success) {
            const activitiesValue = document.getElementById('activities-count-value');
            if (activitiesValue) activitiesValue.textContent = actResult.total;
            console.log(`✅ Activities updated: ${actResult.total}`, actResult.detail);
        }



    } catch (error) {
        console.error('❌ Error refreshing progress:', error);
    }
}

function updateDashboard() {
    const welcomeTitle = document.querySelector('.welcome-title');
    if (welcomeTitle && userState.name) {
        welcomeTitle.textContent = `Welcome, ${userState.name}!`;
    }
    
    const levelBadge = document.querySelector('.level-badge');
    if (levelBadge && userState.cefrLevel) {
        levelBadge.textContent = `CEFR Level: ${userState.cefrLevel}`;
    }
    
    const cefrValue = document.querySelector('.stat-card:nth-child(1) .stat-value');
    if (cefrValue && userState.cefrLevel) {
        cefrValue.textContent = userState.cefrLevel;
    }
    
    const progressValue = document.querySelector('.stat-card:nth-child(2) .stat-value');
    if (progressValue && userState.progress !== undefined) {
        progressValue.textContent = userState.progress + '%';
    }
    
    // ✅ AJOUT : Gestion avatar avec photo Google
    const avatarImg = document.getElementById('avatar-img');
    const avatarInitials = document.getElementById('avatar-initials');
    const picture = localStorage.getItem('learner_picture') || '';
    
    if (picture && avatarImg) {
        avatarImg.src = picture;
        avatarImg.style.display = 'block';
        if (avatarInitials) avatarInitials.style.display = 'none';
    } else if (avatarInitials && userState.name) {
        const initials = userState.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        avatarInitials.textContent = initials;
        if (avatarImg) avatarImg.style.display = 'none';
    }
}

function updateDropdown() {
    const dropdownAvatarImg = document.getElementById('dropdown-avatar-img');
    const dropdownAvatarInitials = document.getElementById('dropdown-avatar-initials');
    const dropdownName  = document.getElementById('dropdown-name');
    const dropdownEmail = document.getElementById('dropdown-email');
    
    // ✅ AJOUT : Gestion photo dans le dropdown
    const picture = localStorage.getItem('learner_picture') || '';
    
    if (picture && dropdownAvatarImg) {
        dropdownAvatarImg.src = picture;
        dropdownAvatarImg.style.display = 'block';
        if (dropdownAvatarInitials) dropdownAvatarInitials.style.display = 'none';
    } else if (userState.name) {
        const initials = userState.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        if (dropdownAvatarInitials) dropdownAvatarInitials.textContent = initials;
        if (dropdownAvatarImg) dropdownAvatarImg.style.display = 'none';
    }
    
    if (dropdownName) dropdownName.textContent = userState.name || '--';
    if (dropdownEmail) dropdownEmail.textContent = userState.email || '--';
}

// ============================================
// PROFILE DROPDOWN
// ============================================

function initProfileDropdown() {
    profileTrigger  = document.getElementById('profile-trigger');
    profileDropdown = document.getElementById('profile-dropdown');
    
    if (!profileTrigger || !profileDropdown) return;
    
    profileTrigger.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleDropdown();
    });
    
    profileDropdown.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            handleDropdownAction(this.getAttribute('data-action'));
        });
    });
    
    document.addEventListener('click', function(e) {
        if (profileDropdown.classList.contains('show') && 
            !profileDropdown.contains(e.target) && 
            !profileTrigger.contains(e.target)) {
            closeDropdown();
        }
    });
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && profileDropdown.classList.contains('show')) {
            closeDropdown();
        }
    });
}

function toggleDropdown() {
    profileDropdown.classList.contains('show') ? closeDropdown() : openDropdown();
}
function openDropdown()  { profileDropdown.classList.add('show');    profileTrigger.classList.add('active'); }
function closeDropdown() { profileDropdown.classList.remove('show'); profileTrigger.classList.remove('active'); }

function handleDropdownAction(action) {
    closeDropdown();
    switch(action) {
        case 'profile':  showNotification('Redirecting to My Profile...'); break;
        case 'settings': showNotification('Redirecting to Settings...'); break;
        case 'logout':   logout(); break;
    }
}

async function logout() {
    try {
        await fetch(`${API_BASE}/api/logout/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ learner_id: userState.learnerId })
        });
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        localStorage.removeItem('learner_id');
        localStorage.removeItem('learner_name');
        localStorage.removeItem('learner_email');
        localStorage.removeItem('learner_cefr_level');
        localStorage.removeItem('learner_progress');
        localStorage.removeItem('learner_picture');
        localStorage.removeItem('currentSubunitId');
        // Rediriger vers login sur Django :8000
        window.location.href = 'http://localhost:8000/login/';
    }
}

// ============================================
// UTILITIES
// ============================================

function toggleUnit(header) {
    const unitCard = header.parentElement;
    if (unitCard.classList.contains('locked')) return;

    const isOpen = unitCard.classList.contains('open');

    document.querySelectorAll('.unit-card').forEach(card => {
        card.classList.remove('open');
        const content = card.querySelector('.unit-content');
        if (content) {
            content.style.maxHeight = '0';
            content.style.overflowY = 'hidden';
            content.style.overflowX = 'hidden';
            content.style.padding   = '0 24px';
        }
    });

    if (!isOpen) {
        const content = unitCard.querySelector('.unit-content');
        if (!content) return;
        unitCard.classList.add('open');
        content.style.maxHeight = '400px';
        content.style.overflowY = 'auto';
        content.style.overflowX = 'hidden';
        content.style.padding   = '0 24px 24px 24px';
    }
}

function animateCards() {
    const cards = document.querySelectorAll('.stat-card, .unit-card');
    cards.forEach((card, index) => {
        card.style.opacity   = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity    = '1';
            card.style.transform  = 'translateY(0)';
        }, index * 100);
    });
}

function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.innerHTML = `<i class="fas fa-info-circle"></i><span>${message}</span>`;
    document.body.appendChild(notification);
    setTimeout(() => notification.classList.add('show'), 10);
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}