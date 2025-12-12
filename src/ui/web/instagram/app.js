/**
 * Social Media Manager - Frontend Application
 * Supports: Instagram (ig-*) and Facebook (fb-*)
 * + Graph Entities Management
 * Pure JS (no frameworks)
 */

const API_BASE = '/api/social';
const GRAPH_API = '/api/graph';

// ============================================
// STATE
// ============================================
const state = {
    // Posts state
    profiles: [],
    currentProfile: null,
    currentPlatform: null, // 'instagram' or 'facebook'
    posts: [],
    filteredPosts: [],
    currentPost: null,
    pendingUploads: [],
    viewMode: 'gallery', // 'gallery', 'detail', 'entities', 'entity-detail'
    contentTypeFilter: 'all', // 'all', 'post', 'story'
    mainView: 'posts', // 'posts' or 'entities'
    
    // Entities state
    entityTypes: {},
    relationshipTypes: [],
    entities: [],
    filteredEntities: [],
    currentEntity: null,
    entityTypeFilter: '',
    edges: []
};

// ============================================
// DOM ELEMENTS
// ============================================
const elements = {
    // View toggles
    viewToggleBtns: document.querySelectorAll('.view-toggle-btn'),
    sidebarPostsContent: document.getElementById('sidebar-posts-content'),
    sidebarEntitiesContent: document.getElementById('sidebar-entities-content'),
    
    // Posts elements
    profileSelect: document.getElementById('profile-select'),
    searchInput: document.getElementById('search-input'),
    sortSelect: document.getElementById('sort-select'),
    postCount: document.getElementById('post-count'),
    mediaCount: document.getElementById('media-count'),
    backBtn: document.getElementById('back-to-gallery-btn'),
    addPostBtn: document.getElementById('add-post-btn'),
    contentTypeBtns: document.querySelectorAll('.content-type-btn'),
    
    galleryView: document.getElementById('gallery-view'),
    galleryGrid: document.getElementById('gallery-grid'),
    
    detailView: document.getElementById('detail-view'),
    detailTitle: document.getElementById('detail-title'),
    savePostBtn: document.getElementById('save-post-btn'),
    deletePostBtn: document.getElementById('delete-post-btn'),
    
    // Entities elements
    entityTypeSelect: document.getElementById('entity-type-select'),
    entitySearchInput: document.getElementById('entity-search-input'),
    entityCount: document.getElementById('entity-count'),
    edgeCount: document.getElementById('edge-count'),
    addEntityBtn: document.getElementById('add-entity-btn'),
    addRelationshipBtn: document.getElementById('add-relationship-btn'),
    
    entitiesView: document.getElementById('entities-view'),
    entitiesGrid: document.getElementById('entities-grid'),
    
    // Graph view
    graphView: document.getElementById('graph-view'),
    graphIframe: document.getElementById('graph-iframe'),
    
    entityDetailView: document.getElementById('entity-detail-view'),
    entityDetailTitle: document.getElementById('entity-detail-title'),
    saveEntityBtn: document.getElementById('save-entity-btn'),
    deleteEntityBtn: document.getElementById('delete-entity-btn'),
    entityRelationsList: document.getElementById('entity-relations-list'),
    addRelationToEntityBtn: document.getElementById('add-relation-to-entity-btn'),
    
    // Entity form fields
    entityId: document.getElementById('entity-id'),
    entityType: document.getElementById('entity-type'),
    entityName: document.getElementById('entity-name'),
    entityDescription: document.getElementById('entity-description'),
    entityCountry: document.getElementById('entity-country'),
    entityFirstSeen: document.getElementById('entity-first-seen'),
    entityNotes: document.getElementById('entity-notes'),
    entityDynamicFields: document.getElementById('entity-dynamic-fields'),
    entityRawJson: document.getElementById('entity-raw-json'),
    
    // Media tabs
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    screenshotsGrid: document.getElementById('screenshots-grid'),
    carouselGrid: document.getElementById('carousel-grid'),
    
    // Upload
    uploadArea: document.getElementById('upload-area'),
    fileInput: document.getElementById('file-input'),
    uploadPreview: document.getElementById('upload-preview'),
    uploadBtn: document.getElementById('upload-btn'),
    
    // Form fields
    fieldUrl: document.getElementById('field-url'),
    fieldCaption: document.getElementById('field-caption'),
    fieldDate: document.getElementById('field-date'),
    fieldScraped: document.getElementById('field-scraped'),
    fieldHandle: document.getElementById('field-handle'),
    fieldRawJson: document.getElementById('field-raw-json'),
    openUrlBtn: document.getElementById('open-url-btn'),
    
    // Modals
    lightbox: document.getElementById('lightbox'),
    lightboxImg: document.getElementById('lightbox-img'),
    lightboxClose: document.getElementById('lightbox-close'),
    confirmModal: document.getElementById('confirm-modal'),
    confirmTitle: document.getElementById('confirm-title'),
    confirmMessage: document.getElementById('confirm-message'),
    confirmCancel: document.getElementById('confirm-cancel'),
    confirmOk: document.getElementById('confirm-ok'),
    createPostModal: document.getElementById('create-post-modal'),
    createPostForm: document.getElementById('create-post-form'),
    createPostCancel: document.getElementById('create-post-cancel'),
    newPostProfile: document.getElementById('new-post-profile'),
    newPostUrl: document.getElementById('new-post-url'),
    newPostCaption: document.getElementById('new-post-caption'),
    newPostDate: document.getElementById('new-post-date'),
    
    // Create entity modal
    createEntityModal: document.getElementById('create-entity-modal'),
    createEntityForm: document.getElementById('create-entity-form'),
    newEntityType: document.getElementById('new-entity-type'),
    newEntityName: document.getElementById('new-entity-name'),
    newEntityDescription: document.getElementById('new-entity-description'),
    newEntityCountry: document.getElementById('new-entity-country'),
    newEntityNotes: document.getElementById('new-entity-notes'),
    newEntityDynamicFields: document.getElementById('new-entity-dynamic-fields'),
    
    // Create relationship modal
    createRelationshipModal: document.getElementById('create-relationship-modal'),
    createRelationshipForm: document.getElementById('create-relationship-form'),
    relSource: document.getElementById('rel-source'),
    relType: document.getElementById('rel-type'),
    relTarget: document.getElementById('rel-target'),
    relDate: document.getElementById('rel-date'),
    relConfidence: document.getElementById('rel-confidence'),
    relEvidence: document.getElementById('rel-evidence'),
    
    // Scrape form
    scrapeForm: document.getElementById('scrape-form'),
    scrapeUrl: document.getElementById('scrape-url'),
    scrapeHandle: document.getElementById('scrape-handle'),
    
    // New profile form
    newProfileForm: document.getElementById('new-profile-form'),
    profilePlatform: document.getElementById('profile-platform'),
    profileHandle: document.getElementById('profile-handle'),
    
    // Modal tabs
    modalTabBtns: document.querySelectorAll('.modal-tab-btn'),
    modalTabContents: document.querySelectorAll('.modal-tab-content'),
    
    toastContainer: document.getElementById('toast-container')
};

// ============================================
// API CALLS
// ============================================
async function api(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (data) options.body = JSON.stringify(data);
    
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || `HTTP ${response.status}`);
    }
    return response.json();
}

async function loadProfiles() {
    try {
        const profiles = await api('/profiles');
        state.profiles = profiles;
        
        // Grupuj profile po platformie
        const grouped = {};
        profiles.forEach(p => {
            if (!grouped[p.platform]) grouped[p.platform] = [];
            grouped[p.platform].push(p);
        });
        
        // Render selecta z grupami
        let html = '';
        
        if (grouped.instagram && grouped.instagram.length > 0) {
            html += '<optgroup label="📷 Instagram">';
            grouped.instagram.forEach(p => {
                html += `<option value="${p.id}" data-platform="instagram">${p.name}</option>`;
            });
            html += '</optgroup>';
        }
        
        if (grouped.facebook && grouped.facebook.length > 0) {
            html += '<optgroup label="📘 Facebook">';
            grouped.facebook.forEach(p => {
                html += `<option value="${p.id}" data-platform="facebook">${p.name}</option>`;
            });
            html += '</optgroup>';
        }
        
        elements.profileSelect.innerHTML = html;
        
        // Populate create post profile dropdown too
        if (elements.newPostProfile) {
            elements.newPostProfile.innerHTML = '<option value="">Wybierz profil...</option>' + html;
        }
        
        if (profiles.length > 0) {
            state.currentProfile = profiles[0].id;
            state.currentPlatform = profiles[0].platform;
            await loadPosts();
        }
    } catch (err) {
        showToast('Błąd ładowania profili: ' + err.message, 'error');
    }
}

async function loadPosts() {
    if (!state.currentProfile) return;
    
    elements.galleryGrid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        const posts = await api(`/posts/${state.currentProfile}`);
        state.posts = posts;
        applyFilters();
        updateStats();
    } catch (err) {
        showToast('Błąd ładowania postów: ' + err.message, 'error');
        elements.galleryGrid.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Błąd ładowania</p></div>';
    }
}

async function loadPostDetail(postId) {
    try {
        const data = await api(`/post/${state.currentProfile}/${postId}`);
        state.currentPost = data;
        renderDetailView();
        switchView('detail');
    } catch (err) {
        showToast('Błąd ładowania posta: ' + err.message, 'error');
    }
}

async function savePost() {
    if (!state.currentPost) return;
    
    // Collect form data
    const metadata = JSON.parse(elements.fieldRawJson.value);
    metadata.url = elements.fieldUrl.value;
    metadata.post_url = elements.fieldUrl.value;
    metadata.text = elements.fieldCaption.value;
    metadata.caption = elements.fieldCaption.value;
    metadata.raw_text_preview = elements.fieldCaption.value;
    metadata.date_posted = elements.fieldDate.value;
    
    try {
        await api(`/post/${state.currentProfile}/${state.currentPost.id}`, 'PUT', { metadata });
        showToast('Zapisano zmiany!', 'success');
        // Reload to get fresh data
        await loadPostDetail(state.currentPost.id);
    } catch (err) {
        showToast('Błąd zapisu: ' + err.message, 'error');
    }
}

// ============================================
// GRAPH ENTITIES API
// ============================================
async function graphApi(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (data) options.body = JSON.stringify(data);
    
    const response = await fetch(`${GRAPH_API}${endpoint}`, options);
    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || `HTTP ${response.status}`);
    }
    return response.json();
}

// ============================================
// ADD POST TO GRAPH (Neo4j integration)
// ============================================

// Store pending post data for modal
let pendingPostData = null;

function addPostToNeo4j() {
    if (!state.currentPost) {
        showToast('Brak wybranego posta', 'error');
        return;
    }
    
    const post = state.currentPost;
    const platform = state.currentProfile?.startsWith('fb-') ? 'facebook' : 'instagram';
    
    // Generate ID for post node
    const postId = `post-${post.id}`;
    
    // Create post node data
    pendingPostData = {
        id: postId,
        entity_type: 'post',
        name: `Post: ${(post.metadata?.caption || post.id).substring(0, 50)}${(post.metadata?.caption || '').length > 50 ? '...' : ''}`,
        platform: platform,
        url: post.metadata?.url || '',
        description: post.metadata?.caption || '',
        date_posted: post.metadata?.timestamp || new Date().toISOString().split('T')[0],
        country: 'PL',
        notes: `Dodano z SM Manager. Profile: ${state.currentProfile}`
    };
    
    // Open modal
    openAddPostToGraphModal();
}

async function openAddPostToGraphModal() {
    const modal = document.getElementById('add-post-to-graph-modal');
    if (!modal) return;
    
    // Fill in preview
    document.getElementById('modal-post-name').textContent = pendingPostData.name;
    document.getElementById('modal-post-platform').innerHTML = `<i class="fab fa-${pendingPostData.platform}"></i> ${pendingPostData.platform}`;
    document.getElementById('modal-post-date').textContent = pendingPostData.date_posted;
    
    // Load entities for dropdown
    try {
        const nodes = await graphApi('/nodes');
        const entitySelect = document.getElementById('post-rel-entity');
        entitySelect.innerHTML = '<option value="">Wybierz encję...</option>';
        
        // Group by type
        const grouped = {};
        nodes.forEach(n => {
            const type = n.entity_type || 'other';
            if (!grouped[type]) grouped[type] = [];
            grouped[type].push(n);
        });
        
        // Add optgroups
        for (const [type, entities] of Object.entries(grouped)) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = type.charAt(0).toUpperCase() + type.slice(1);
            entities.forEach(e => {
                const opt = document.createElement('option');
                opt.value = e.id;
                opt.textContent = `${e.name} (${e.id})`;
                optgroup.appendChild(opt);
            });
            entitySelect.appendChild(optgroup);
        }
    } catch (err) {
        console.error('Error loading entities:', err);
    }
    
    // Reset options
    document.querySelector('input[name="add-option"][value="no-relation"]').checked = true;
    document.getElementById('relation-config').style.display = 'none';
    
    // Setup option card click handlers
    document.querySelectorAll('.option-card').forEach(card => {
        card.onclick = () => {
            const radio = card.querySelector('input[type="radio"]');
            radio.checked = true;
            
            const relationConfig = document.getElementById('relation-config');
            if (radio.value === 'with-relation') {
                relationConfig.style.display = 'block';
            } else {
                relationConfig.style.display = 'none';
            }
        };
    });
    
    modal.style.display = 'flex';
}

function closeAddPostToGraphModal() {
    const modal = document.getElementById('add-post-to-graph-modal');
    if (modal) modal.style.display = 'none';
    pendingPostData = null;
}

async function confirmAddPostToGraph() {
    if (!pendingPostData) {
        showToast('Brak danych posta', 'error');
        return;
    }
    
    const addWithRelation = document.querySelector('input[name="add-option"]:checked')?.value === 'with-relation';
    
    try {
        // First create the post node
        const result = await graphApi('/node', 'POST', pendingPostData);
        
        // If adding with relation
        if (addWithRelation) {
            const relType = document.getElementById('post-rel-type').value;
            const relDirection = document.getElementById('post-rel-direction').value;
            const entityId = document.getElementById('post-rel-entity').value;
            const evidence = document.getElementById('post-rel-evidence').value;
            
            if (!entityId) {
                showToast('Post dodany, ale nie wybrano encji dla relacji', 'warning');
            } else {
                // Create relationship
                const edgeData = {
                    source_id: relDirection === 'from-entity' ? entityId : pendingPostData.id,
                    target_id: relDirection === 'from-entity' ? pendingPostData.id : entityId,
                    relationship_type: relType,
                    evidence: evidence || `Dodano z SM Manager`,
                    confidence: 1.0,
                    date: pendingPostData.date_posted
                };
                
                await graphApi('/edge', 'POST', edgeData);
                showToast(`Post dodany do grafu z relacją ${relType}!`, 'success');
            }
        } else {
            showToast(`Post "${pendingPostData.name.substring(0, 30)}..." dodany do grafu!`, 'success');
        }
        
        closeAddPostToGraphModal();
        
        // Offer to switch to graph view
        if (confirm('Post dodany do grafu. Czy chcesz przejść do widoku Graf?')) {
            switchMainView('graph');
        }
        
        // Refresh entities if in that view
        if (state.viewMode === 'entities') {
            await loadEntities();
        }
    } catch (err) {
        console.error('Error adding post to graph:', err);
        showToast(`Błąd: ${err.message}`, 'error');
    }
}

async function syncToNeo4j() {
    showToast('Synchronizacja z Neo4j... może potrwać do 60s', 'info');
    
    const btn = document.getElementById('btn-sync-neo4j');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Synchronizuję...';
    }
    
    try {
        // Call sync API
        const response = await fetch('/api/graph/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('✅ Synchronizacja z Neo4j zakończona!', 'success');
            console.log('Neo4j sync output:', result.output);
            
            // Refresh graph iframe
            const graphIframe = document.getElementById('graph-iframe');
            if (graphIframe) {
                graphIframe.src = graphIframe.src;
            }
            
            // Refresh entities list
            await loadEntities();
        } else {
            showToast(`❌ Błąd: ${result.message || result.error}`, 'error');
            console.error('Neo4j sync error:', result);
        }
    } catch (err) {
        console.error('Error syncing to Neo4j:', err);
        showToast(`Błąd synchronizacji: ${err.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sync"></i> Sync Neo4j';
        }
    }
}

async function loadEntityTypes() {
    try {
        state.entityTypes = await graphApi('/entity-types');
        state.relationshipTypes = await graphApi('/relationship-types');
        
        // Populate entity type select
        if (elements.entityTypeSelect) {
            let html = '<option value="">Wszystkie typy</option>';
            for (const [type, config] of Object.entries(state.entityTypes)) {
                html += `<option value="${type}"><i class="${config.icon}"></i> ${config.label}</option>`;
            }
            elements.entityTypeSelect.innerHTML = html;
        }
        
        // Populate entity type in create form
        if (elements.newEntityType) {
            let html = '<option value="">Wybierz typ...</option>';
            for (const [type, config] of Object.entries(state.entityTypes)) {
                html += `<option value="${type}">${config.label}</option>`;
            }
            elements.newEntityType.innerHTML = html;
        }
        
        // Populate relationship type select
        if (elements.relType) {
            let html = '<option value="">Wybierz typ relacji...</option>';
            state.relationshipTypes.forEach(rt => {
                html += `<option value="${rt}">${rt}</option>`;
            });
            elements.relType.innerHTML = html;
        }
    } catch (err) {
        console.error('Error loading entity types:', err);
    }
}

async function loadEntities() {
    if (elements.entitiesGrid) {
        elements.entitiesGrid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    }
    
    try {
        let url = '/nodes';
        const params = new URLSearchParams();
        if (state.entityTypeFilter) params.append('type', state.entityTypeFilter);
        if (params.toString()) url += '?' + params.toString();
        
        state.entities = await graphApi(url);
        state.edges = await graphApi('/edges');
        
        applyEntityFilters();
        updateEntityStats();
    } catch (err) {
        showToast('Błąd ładowania encji: ' + err.message, 'error');
        if (elements.entitiesGrid) {
            elements.entitiesGrid.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Błąd ładowania</p></div>';
        }
    }
}

async function loadEntityDetail(entityId) {
    try {
        const entity = await graphApi(`/node/${entityId}`);
        const edges = await graphApi(`/node-edges/${entityId}`);
        
        state.currentEntity = { ...entity, edges };
        renderEntityDetailView();
        switchView('entity-detail');
    } catch (err) {
        showToast('Błąd ładowania encji: ' + err.message, 'error');
    }
}

async function saveEntity() {
    if (!state.currentEntity) return;
    
    const data = {
        name: elements.entityName.value,
        description: elements.entityDescription.value,
        country: elements.entityCountry.value,
        first_seen: elements.entityFirstSeen.value,
        notes: elements.entityNotes.value
    };
    
    try {
        await graphApi(`/node/${state.currentEntity.id}`, 'PUT', data);
        showToast('Encja zapisana!', 'success');
        await loadEntityDetail(state.currentEntity.id);
    } catch (err) {
        showToast('Błąd zapisu: ' + err.message, 'error');
    }
}

async function deleteEntity() {
    if (!state.currentEntity) return;
    
    try {
        const result = await graphApi(`/node/${state.currentEntity.id}`, 'DELETE');
        showToast(`Encja usunięta (${result.edges_removed} relacji usuniętych)`, 'success');
        switchView('entities');
        await loadEntities();
    } catch (err) {
        showToast('Błąd usuwania: ' + err.message, 'error');
    }
}

async function createEntity(data) {
    try {
        const result = await graphApi('/node', 'POST', data);
        showToast(`Utworzono encję: ${result.node.name}`, 'success');
        return result.node;
    } catch (err) {
        showToast('Błąd tworzenia encji: ' + err.message, 'error');
        throw err;
    }
}

async function createRelationship(data) {
    try {
        const result = await graphApi('/edge', 'POST', data);
        showToast(`Utworzono relację: ${data.relationship_type}`, 'success');
        return result.edge;
    } catch (err) {
        showToast('Błąd tworzenia relacji: ' + err.message, 'error');
        throw err;
    }
}

async function deleteEdge(edgeId) {
    try {
        await graphApi(`/edge/${edgeId}`, 'DELETE');
        showToast('Relacja usunięta', 'success');
        if (state.currentEntity) {
            await loadEntityDetail(state.currentEntity.id);
        }
    } catch (err) {
        showToast('Błąd usuwania relacji: ' + err.message, 'error');
    }
}

async function deletePost() {
    if (!state.currentPost) return;
    
    try {
        await api(`/post/${state.currentProfile}/${state.currentPost.id}`, 'DELETE');
        showToast('Post usunięty (przeniesiony do backupu)', 'success');
        switchView('gallery');
        await loadPosts();
    } catch (err) {
        showToast('Błąd usuwania: ' + err.message, 'error');
    }
}

async function deleteScreenshot(filename) {
    if (!state.currentPost) return;
    
    try {
        await api(`/screenshot/${state.currentProfile}/${state.currentPost.id}`, 'DELETE', { filename });
        showToast('Screenshot usunięty', 'success');
        await loadPostDetail(state.currentPost.id);
    } catch (err) {
        showToast('Błąd usuwania: ' + err.message, 'error');
    }
}

async function uploadFiles() {
    if (!state.currentPost || state.pendingUploads.length === 0) return;
    
    const formData = new FormData();
    state.pendingUploads.forEach(file => formData.append('files', file));
    
    try {
        const response = await fetch(
            `${API_BASE}/upload/${state.currentProfile}/${state.currentPost.id}`,
            { method: 'POST', body: formData }
        );
        
        if (!response.ok) throw new Error(await response.text());
        
        showToast(`Dodano ${state.pendingUploads.length} plik(ów)`, 'success');
        state.pendingUploads = [];
        elements.uploadPreview.innerHTML = '';
        elements.uploadBtn.style.display = 'none';
        await loadPostDetail(state.currentPost.id);
    } catch (err) {
        showToast('Błąd uploadu: ' + err.message, 'error');
    }
}

// ============================================
// RENDERING
// ============================================
function getEvidencePath() {
    // Determine the correct evidence path based on current platform and profile
    if (!state.currentProfile) return '';
    
    const profile = state.profiles.find(p => p.id === state.currentProfile);
    if (!profile) return '';
    
    const platform = profile.platform;
    const handle = profile.name;
    
    // FB nie używa podkatalogu, IG używa 'posts'
    if (platform === 'facebook') {
        return `/data/evidence/${platform}/${handle}`;
    } else {
        return `/data/evidence/${platform}/${handle}/posts`;
    }
}

function renderGallery() {
    if (state.filteredPosts.length === 0) {
        elements.galleryGrid.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-image"></i>
                <p>Brak postów do wyświetlenia</p>
            </div>
        `;
        return;
    }
    
    const evidencePath = getEvidencePath();
    
    elements.galleryGrid.innerHTML = state.filteredPosts.map(post => {
        const platformIcon = post.platform === 'facebook' ? 'fab fa-facebook' : 'fab fa-instagram';
        const platformClass = post.platform === 'facebook' ? 'platform-fb' : 'platform-ig';
        const typeIcon = post.contentType === 'story' ? 'fa-circle' : 'fa-image';
        
        return `
            <div class="post-card ${platformClass}" data-id="${post.id}">
                <div class="post-card-thumb">
                    ${post.thumbnail 
                        ? `<img src="${evidencePath}/${post.thumbnail}" alt="Thumb" loading="lazy">`
                        : '<i class="fas fa-image"></i>'
                    }
                    <span class="post-card-platform"><i class="${platformIcon}"></i></span>
                </div>
                <div class="post-card-info">
                    <div class="post-card-id" title="${post.id}">${post.id.length > 30 ? post.id.substring(0, 30) + '...' : post.id}</div>
                    <div class="post-card-date">${post.date || 'Brak daty'}</div>
                    <div class="post-card-badges">
                        ${post.screenshotCount > 0 ? `<span class="badge badge-media">${post.screenshotCount} 📷</span>` : ''}
                        ${post.imageCount > 0 ? `<span class="badge badge-carousel">${post.imageCount} 🎠</span>` : ''}
                        ${post.contentType === 'story' ? '<span class="badge badge-story">Story</span>' : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers
    document.querySelectorAll('.post-card').forEach(card => {
        card.addEventListener('click', () => loadPostDetail(card.dataset.id));
    });
}

function renderDetailView() {
    const post = state.currentPost;
    if (!post) return;
    
    const profile = state.profiles.find(p => p.id === state.currentProfile);
    const platform = profile ? profile.platform : 'instagram';
    const handle = profile ? profile.name : state.currentProfile;
    
    // FB nie używa podkatalogu, IG używa 'posts'
    let evidencePath;
    if (platform === 'facebook') {
        evidencePath = `/data/evidence/${platform}/${handle}`;
    } else {
        evidencePath = `/data/evidence/${platform}/${handle}/posts`;
    }
    const imagesPath = `/data/evidence/${platform}/${handle}/images`;
    
    elements.detailTitle.textContent = `Edycja: ${post.id}`;
    
    // Form fields - handle both IG and FB metadata formats
    const url = post.metadata.url || post.metadata.post_url || '';
    const caption = post.metadata.text || post.metadata.caption || post.metadata.raw_text_preview || '';
    const datePosted = post.metadata.date_posted || '';
    const scrapedAt = post.metadata.scraped_at || post.metadata.collected_at || '';
    const handleVal = post.metadata.handle || handle;
    
    elements.fieldUrl.value = url;
    elements.fieldCaption.value = caption;
    elements.fieldDate.value = datePosted;
    elements.fieldScraped.value = scrapedAt;
    elements.fieldHandle.value = handleVal;
    elements.fieldRawJson.value = JSON.stringify(post.metadata, null, 2);
    
    // Update URL button
    if (url) {
        elements.openUrlBtn.href = url;
        elements.openUrlBtn.style.display = 'flex';
    } else {
        elements.openUrlBtn.style.display = 'none';
    }
    
    // Screenshots
    if (post.screenshots && post.screenshots.length > 0) {
        elements.screenshotsGrid.innerHTML = post.screenshots.map(s => `
            <div class="media-item">
                <img src="${evidencePath}/${s}" 
                     alt="${s}" 
                     onclick="openLightbox(this.src)">
                <div class="media-item-actions">
                    <button class="btn btn-danger btn-small" onclick="confirmDeleteScreenshot('${s}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    } else {
        elements.screenshotsGrid.innerHTML = '<div class="empty-state"><i class="fas fa-camera"></i><p>Brak screenshotów</p></div>';
    }
    
    // Carousel images (mainly for Instagram)
    if (post.images && post.images.length > 0) {
        elements.carouselGrid.innerHTML = post.images.map(img => `
            <div class="media-item">
                <img src="${imagesPath}/${img}" 
                     alt="${img}" 
                     onclick="openLightbox(this.src)">
            </div>
        `).join('');
    } else {
        elements.carouselGrid.innerHTML = '<div class="empty-state"><i class="fas fa-images"></i><p>Brak obrazów karuzeli</p></div>';
    }
}

function updateStats() {
    elements.postCount.textContent = state.posts.length;
    const totalMedia = state.posts.reduce((sum, p) => sum + (p.screenshotCount || 0) + (p.imageCount || 0), 0);
    elements.mediaCount.textContent = totalMedia;
}

// ============================================
// ENTITY RENDERING
// ============================================
function getEntityIcon(entityType) {
    const icons = {
        'person': 'fas fa-user',
        'organization': 'fas fa-building',
        'event': 'fas fa-calendar-alt',
        'profile': 'fas fa-id-card',
        'post': 'fas fa-file-alt',
        'page': 'fas fa-globe',
        'media': 'fas fa-photo-video',
        'channel': 'fas fa-broadcast-tower',
        'group': 'fas fa-users'
    };
    return icons[entityType] || 'fas fa-question-circle';
}

function getEntityColor(entityType) {
    const colors = {
        'person': '#e74c3c',
        'organization': '#3498db',
        'event': '#9b59b6',
        'profile': '#1abc9c',
        'post': '#f39c12',
        'page': '#2ecc71',
        'media': '#e91e63',
        'channel': '#ff5722',
        'group': '#795548'
    };
    return colors[entityType] || '#95a5a6';
}

function renderEntitiesGallery() {
    if (!elements.entitiesGrid) return;
    
    if (state.filteredEntities.length === 0) {
        elements.entitiesGrid.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-database"></i>
                <p>Brak encji do wyświetlenia</p>
            </div>
        `;
        return;
    }
    
    elements.entitiesGrid.innerHTML = state.filteredEntities.map(entity => {
        const icon = getEntityIcon(entity.entity_type);
        const color = getEntityColor(entity.entity_type);
        const description = entity.description || entity.notes || '';
        const truncatedDesc = description.length > 100 ? description.substring(0, 100) + '...' : description;
        
        return `
            <div class="entity-card" data-id="${entity.id}">
                <div class="entity-card-icon" style="background: ${color}">
                    <i class="${icon}"></i>
                </div>
                <div class="entity-card-info">
                    <div class="entity-card-name">${entity.name}</div>
                    <div class="entity-card-type">
                        <span class="entity-type-badge" style="background: ${color}20; color: ${color}">
                            ${entity.entity_type}
                        </span>
                        ${entity.country ? `<span class="entity-country">${entity.country}</span>` : ''}
                    </div>
                    ${truncatedDesc ? `<div class="entity-card-desc">${truncatedDesc}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers
    document.querySelectorAll('.entity-card').forEach(card => {
        card.addEventListener('click', () => loadEntityDetail(card.dataset.id));
    });
}

function renderEntityDetailView() {
    const entity = state.currentEntity;
    if (!entity) return;
    
    if (elements.entityDetailTitle) {
        elements.entityDetailTitle.textContent = `Edycja: ${entity.name}`;
    }
    
    // Fill form fields
    if (elements.entityId) elements.entityId.value = entity.id;
    if (elements.entityType) elements.entityType.value = entity.entity_type;
    if (elements.entityName) elements.entityName.value = entity.name || '';
    if (elements.entityDescription) elements.entityDescription.value = entity.description || '';
    if (elements.entityCountry) elements.entityCountry.value = entity.country || '';
    if (elements.entityFirstSeen) elements.entityFirstSeen.value = entity.first_seen || '';
    if (elements.entityNotes) elements.entityNotes.value = entity.notes || '';
    
    // Dynamic fields based on entity type
    renderDynamicEntityFields(entity);
    
    // Raw JSON
    if (elements.entityRawJson) {
        elements.entityRawJson.value = JSON.stringify(entity, null, 2);
    }
    
    // Render relationships
    renderEntityRelations(entity.edges || []);
}

function renderDynamicEntityFields(entity) {
    if (!elements.entityDynamicFields) return;
    
    const type = entity.entity_type;
    let html = '';
    
    // Type-specific fields
    if (type === 'person') {
        html += `
            <div class="form-group">
                <label>Role</label>
                <input type="text" id="entity-roles" value="${(entity.roles || []).join(', ')}" 
                       placeholder="np. prelegent, aktywista">
            </div>
        `;
    } else if (type === 'organization') {
        html += `
            <div class="form-group">
                <label>Typ organizacji</label>
                <input type="text" id="entity-org-type" value="${entity.org_type || ''}" 
                       placeholder="np. NGO, partia, stowarzyszenie">
            </div>
        `;
    } else if (type === 'profile') {
        html += `
            <div class="form-group">
                <label>Platforma</label>
                <select id="entity-platform">
                    <option value="facebook" ${entity.platform === 'facebook' ? 'selected' : ''}>Facebook</option>
                    <option value="instagram" ${entity.platform === 'instagram' ? 'selected' : ''}>Instagram</option>
                    <option value="twitter" ${entity.platform === 'twitter' ? 'selected' : ''}>Twitter</option>
                    <option value="telegram" ${entity.platform === 'telegram' ? 'selected' : ''}>Telegram</option>
                    <option value="youtube" ${entity.platform === 'youtube' ? 'selected' : ''}>YouTube</option>
                </select>
            </div>
            <div class="form-group">
                <label>Handle</label>
                <input type="text" id="entity-handle" value="${entity.handle || ''}" placeholder="@handle">
            </div>
            <div class="form-group">
                <label>URL</label>
                <input type="url" id="entity-profile-url" value="${entity.url || ''}" placeholder="https://...">
            </div>
        `;
    } else if (type === 'event') {
        html += `
            <div class="form-group">
                <label>Data rozpoczęcia</label>
                <input type="date" id="entity-date-start" value="${entity.date_start || ''}">
            </div>
            <div class="form-group">
                <label>Data zakończenia</label>
                <input type="date" id="entity-date-end" value="${entity.date_end || ''}">
            </div>
            <div class="form-group">
                <label>Lokalizacja</label>
                <input type="text" id="entity-location" value="${entity.location || ''}" placeholder="Miasto, miejsce">
            </div>
        `;
    } else if (type === 'post') {
        html += `
            <div class="form-group">
                <label>Platforma</label>
                <select id="entity-platform">
                    <option value="facebook" ${entity.platform === 'facebook' ? 'selected' : ''}>Facebook</option>
                    <option value="instagram" ${entity.platform === 'instagram' ? 'selected' : ''}>Instagram</option>
                    <option value="twitter" ${entity.platform === 'twitter' ? 'selected' : ''}>Twitter</option>
                </select>
            </div>
            <div class="form-group">
                <label>URL posta</label>
                <input type="url" id="entity-post-url" value="${entity.url || ''}" placeholder="https://...">
            </div>
            <div class="form-group">
                <label>Data publikacji</label>
                <input type="date" id="entity-date-posted" value="${entity.date_posted || ''}">
            </div>
        `;
    } else if (type === 'page') {
        html += `
            <div class="form-group">
                <label>URL strony</label>
                <input type="url" id="entity-page-url" value="${entity.url || ''}" placeholder="https://...">
            </div>
        `;
    }
    
    elements.entityDynamicFields.innerHTML = html;
}

function renderEntityRelations(edges) {
    if (!elements.entityRelationsList) return;
    
    if (!edges || edges.length === 0) {
        elements.entityRelationsList.innerHTML = '<div class="empty-state-small">Brak powiązań</div>';
        return;
    }
    
    elements.entityRelationsList.innerHTML = edges.map(edge => {
        const isSource = edge.source_id === state.currentEntity.id;
        const otherName = isSource ? edge.target_name : edge.source_name;
        const otherId = isSource ? edge.target_id : edge.source_id;
        const direction = isSource ? '→' : '←';
        
        return `
            <div class="relation-item">
                <div class="relation-info">
                    <span class="relation-direction">${direction}</span>
                    <span class="relation-type">${edge.relationship_type}</span>
                    <span class="relation-target" data-id="${otherId}">${otherName || otherId}</span>
                    ${edge.confidence ? `<span class="relation-confidence">(${Math.round(edge.confidence * 100)}%)</span>` : ''}
                </div>
                <div class="relation-actions">
                    <button class="btn btn-small btn-danger" onclick="confirmDeleteEdge('${edge.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers for related entities
    document.querySelectorAll('.relation-target').forEach(el => {
        el.addEventListener('click', () => loadEntityDetail(el.dataset.id));
    });
}

function applyEntityFilters() {
    let entities = [...state.entities];
    
    // Entity type filter
    if (state.entityTypeFilter) {
        entities = entities.filter(e => e.entity_type === state.entityTypeFilter);
    }
    
    // Search filter
    const searchInput = elements.entitySearchInput;
    if (searchInput && searchInput.value) {
        const searchTerm = searchInput.value.toLowerCase();
        entities = entities.filter(e => 
            e.name.toLowerCase().includes(searchTerm) ||
            (e.description && e.description.toLowerCase().includes(searchTerm)) ||
            e.id.toLowerCase().includes(searchTerm)
        );
    }
    
    state.filteredEntities = entities;
    renderEntitiesGallery();
}

function updateEntityStats() {
    if (elements.entityCount) {
        elements.entityCount.textContent = state.entities.length;
    }
    if (elements.edgeCount) {
        elements.edgeCount.textContent = state.edges.length;
    }
}

function confirmDeleteEntity() {
    showConfirm(
        'Usuń encję',
        `Czy na pewno usunąć "${state.currentEntity?.name}"? Wszystkie powiązane relacje też zostaną usunięte.`,
        () => deleteEntity()
    );
}

function confirmDeleteEdge(edgeId) {
    showConfirm(
        'Usuń relację',
        'Czy na pewno usunąć tę relację?',
        () => deleteEdge(edgeId)
    );
}

// ============================================
// FILTERS & SORTING
// ============================================
function applyFilters() {
    let posts = [...state.posts];
    
    // Content type filter (all/post/story)
    if (state.contentTypeFilter !== 'all') {
        posts = posts.filter(p => p.contentType === state.contentTypeFilter);
    }
    
    // Search filter
    const searchTerm = elements.searchInput.value.toLowerCase();
    if (searchTerm) {
        posts = posts.filter(p => 
            p.id.toLowerCase().includes(searchTerm) ||
            (p.text && p.text.toLowerCase().includes(searchTerm))
        );
    }
    
    // Sorting
    const sortBy = elements.sortSelect.value;
    if (sortBy === 'newest') {
        posts.sort((a, b) => (b.scraped_at || '').localeCompare(a.scraped_at || ''));
    } else if (sortBy === 'oldest') {
        posts.sort((a, b) => (a.scraped_at || '').localeCompare(b.scraped_at || ''));
    } else {
        posts.sort((a, b) => a.id.localeCompare(b.id));
    }
    
    state.filteredPosts = posts;
    renderGallery();
}

// ============================================
// VIEW SWITCHING
// ============================================
function switchMainView(view) {
    state.mainView = view;
    
    // Update toggle buttons
    elements.viewToggleBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });
    
    // Show/hide sidebar content
    if (elements.sidebarPostsContent) {
        elements.sidebarPostsContent.style.display = view === 'posts' ? 'block' : 'none';
    }
    if (elements.sidebarEntitiesContent) {
        elements.sidebarEntitiesContent.style.display = view === 'entities' ? 'block' : 'none';
    }
    
    // Show/hide action buttons
    if (elements.addPostBtn) {
        elements.addPostBtn.style.display = view === 'posts' ? 'block' : 'none';
    }
    if (elements.addEntityBtn) {
        elements.addEntityBtn.style.display = view === 'entities' ? 'block' : 'none';
    }
    
    // Switch main view
    if (view === 'posts') {
        switchView('gallery');
    } else if (view === 'entities') {
        switchView('entities');
        // Load entities if not yet loaded
        if (state.entities.length === 0) {
            loadEntityTypes().then(() => loadEntities());
        }
    } else if (view === 'graph') {
        switchView('graph');
    }
}

function switchView(mode, pushState = true) {
    state.viewMode = mode;
    
    // Hide all views first
    if (elements.galleryView) elements.galleryView.style.display = 'none';
    if (elements.detailView) elements.detailView.style.display = 'none';
    if (elements.entitiesView) elements.entitiesView.style.display = 'none';
    if (elements.entityDetailView) elements.entityDetailView.style.display = 'none';
    if (elements.graphView) elements.graphView.style.display = 'none';
    elements.backBtn.style.display = 'none';
    
    if (mode === 'gallery') {
        elements.galleryView.style.display = 'flex';
        state.currentPost = null;
        
        // Update browser history
        if (pushState) {
            history.pushState({ view: 'gallery', profile: state.currentProfile }, '', `?profile=${state.currentProfile}`);
        }
    } else if (mode === 'detail') {
        elements.detailView.style.display = 'flex';
        elements.backBtn.style.display = 'block';
        
        // Update browser history
        if (pushState && state.currentPost) {
            history.pushState(
                { view: 'detail', profile: state.currentProfile, postId: state.currentPost.id }, 
                '', 
                `?profile=${state.currentProfile}&post=${state.currentPost.id}`
            );
        }
    } else if (mode === 'entities') {
        if (elements.entitiesView) elements.entitiesView.style.display = 'flex';
        state.currentEntity = null;
        
        // Update browser history
        if (pushState) {
            history.pushState({ view: 'entities' }, '', '?view=entities');
        }
    } else if (mode === 'entity-detail') {
        if (elements.entityDetailView) elements.entityDetailView.style.display = 'flex';
        elements.backBtn.style.display = 'block';
        
        // Update browser history
        if (pushState && state.currentEntity) {
            history.pushState(
                { view: 'entity-detail', entityId: state.currentEntity.id },
                '',
                `?view=entities&entity=${state.currentEntity.id}`
            );
        }
    } else if (mode === 'graph') {
        if (elements.graphView) {
            elements.graphView.style.display = 'flex';
            // Load kinetic viz from separate server (port 8082)
            if (elements.graphIframe && !elements.graphIframe.src.includes('localhost:8082')) {
                elements.graphIframe.src = 'http://localhost:8082/';
            }
        }
        
        // Update browser history
        if (pushState) {
            history.pushState({ view: 'graph' }, '', '?view=graph');
        }
    }
}

// ============================================
// TABS
// ============================================
function switchTab(tabName) {
    elements.tabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    elements.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

// ============================================
// UPLOAD HANDLING
// ============================================
function handleFiles(files) {
    state.pendingUploads = [...state.pendingUploads, ...Array.from(files)];
    renderUploadPreview();
}

function renderUploadPreview() {
    if (state.pendingUploads.length === 0) {
        elements.uploadPreview.innerHTML = '';
        elements.uploadBtn.style.display = 'none';
        return;
    }
    
    elements.uploadPreview.innerHTML = state.pendingUploads.map((file, idx) => `
        <div class="upload-preview-item">
            <img src="${URL.createObjectURL(file)}" alt="${file.name}">
            <button class="remove-btn" onclick="removePendingUpload(${idx})">&times;</button>
        </div>
    `).join('');
    
    elements.uploadBtn.style.display = 'block';
}

function removePendingUpload(idx) {
    state.pendingUploads.splice(idx, 1);
    renderUploadPreview();
}

// ============================================
// LIGHTBOX
// ============================================
function openLightbox(src) {
    elements.lightboxImg.src = src;
    elements.lightbox.style.display = 'flex';
}

function closeLightbox() {
    elements.lightbox.style.display = 'none';
    elements.lightboxImg.src = '';
}

// ============================================
// CONFIRM MODAL
// ============================================
let confirmCallback = null;

function showConfirm(title, message, callback) {
    elements.confirmTitle.textContent = title;
    elements.confirmMessage.textContent = message;
    confirmCallback = callback;
    elements.confirmModal.style.display = 'flex';
}

function closeConfirm() {
    elements.confirmModal.style.display = 'none';
    confirmCallback = null;
}

function confirmDeleteScreenshot(filename) {
    showConfirm(
        'Usuń screenshot',
        `Czy na pewno usunąć ${filename}? Plik zostanie przeniesiony do backupu.`,
        () => deleteScreenshot(filename)
    );
}

function confirmDeletePost() {
    showConfirm(
        'Usuń cały post',
        'Czy na pewno usunąć ten post wraz ze wszystkimi mediami? Pliki zostaną przeniesione do backupu.',
        () => deletePost()
    );
}

// ============================================
// CREATE POST MODAL
// ============================================
function openCreatePostModal() {
    if (elements.newPostProfile) {
        elements.newPostProfile.value = state.currentProfile || '';
    }
    if (elements.newPostUrl) elements.newPostUrl.value = '';
    if (elements.newPostCaption) elements.newPostCaption.value = '';
    if (elements.newPostDate) elements.newPostDate.value = new Date().toISOString().split('T')[0];
    
    // Reset scrape form
    if (elements.scrapeUrl) elements.scrapeUrl.value = '';
    if (elements.scrapeHandle) elements.scrapeHandle.value = '';
    
    // Reset profile form
    if (elements.profileHandle) elements.profileHandle.value = '';
    if (elements.profilePlatform) elements.profilePlatform.value = 'instagram';
    
    // Reset to first tab
    switchModalTab('manual');
    
    if (elements.createPostModal) {
        elements.createPostModal.style.display = 'flex';
    }
}

function closeCreatePostModal() {
    if (elements.createPostModal) {
        elements.createPostModal.style.display = 'none';
    }
}

function switchModalTab(tabName) {
    elements.modalTabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.modalTab === tabName);
    });
    elements.modalTabContents.forEach(content => {
        content.classList.toggle('active', content.id === `modal-tab-${tabName}`);
    });
}

async function handleCreatePost(e) {
    e.preventDefault();
    
    const profile = elements.newPostProfile.value;
    if (!profile) {
        showToast('Wybierz profil', 'error');
        return;
    }
    
    const data = {
        profile: profile,
        url: elements.newPostUrl.value,
        caption: elements.newPostCaption.value,
        date: elements.newPostDate.value
    };
    
    try {
        const result = await api('/post', 'POST', data);
        showToast(`Utworzono nowy wpis: ${result.post_id}`, 'success');
        closeCreatePostModal();
        
        // Reload posts if we're on the same profile
        if (state.currentProfile === profile) {
            await loadPosts();
        }
        
        // Optionally navigate to the new post
        if (result.post_id) {
            state.currentProfile = profile;
            elements.profileSelect.value = profile;
            await loadPosts();
            await loadPostDetail(result.post_id);
        }
    } catch (err) {
        showToast('Błąd tworzenia wpisu: ' + err.message, 'error');
    }
}

async function handleStartScrape(e) {
    e.preventDefault();
    
    const url = elements.scrapeUrl.value.trim();
    const handle = elements.scrapeHandle.value.trim();
    
    if (!url) {
        showToast('Podaj URL posta', 'error');
        return;
    }
    
    if (!handle) {
        showToast('Podaj nazwę profilu (@handle)', 'error');
        return;
    }
    
    try {
        const result = await api('/scrape', 'POST', {
            url: url,
            handle: handle
        });
        
        let msg = result.message || `Scraper uruchomiony dla posta`;
        if (result.new_profile) {
            msg += ` (nowy profil: @${result.handle})`;
        }
        showToast(msg, 'success');
        closeCreatePostModal();
        
        // If new profile was created, reload profiles
        if (result.new_profile) {
            await loadProfiles();
        }
        
        // Show info about checking console
        setTimeout(() => {
            showToast('Sprawdź konsolę serwera. Po zakończeniu odśwież galerię.', 'info');
        }, 1500);
        
    } catch (err) {
        showToast('Błąd scrapera: ' + err.message, 'error');
    }
}

async function handleCreateProfile(e) {
    e.preventDefault();
    
    const platform = elements.profilePlatform.value;
    const handle = elements.profileHandle.value.trim();
    
    if (!handle) {
        showToast('Podaj nazwę profilu', 'error');
        return;
    }
    
    try {
        const result = await api('/profile', 'POST', {
            platform: platform,
            handle: handle
        });
        
        showToast(`Utworzono profil: ${result.profile_id}`, 'success');
        closeCreatePostModal();
        
        // Reload profiles to include the new one
        await loadProfiles();
        
        // Select the new profile
        if (result.profile_id) {
            state.currentProfile = result.profile_id;
            elements.profileSelect.value = result.profile_id;
            await loadPosts();
        }
        
    } catch (err) {
        showToast('Błąd tworzenia profilu: ' + err.message, 'error');
    }
}

// ============================================
// ENTITY MODALS
// ============================================
function openCreateEntityModal() {
    if (elements.newEntityType) elements.newEntityType.value = '';
    if (elements.newEntityName) elements.newEntityName.value = '';
    if (elements.newEntityDescription) elements.newEntityDescription.value = '';
    if (elements.newEntityCountry) elements.newEntityCountry.value = 'PL';
    if (elements.newEntityNotes) elements.newEntityNotes.value = '';
    if (elements.newEntityDynamicFields) elements.newEntityDynamicFields.innerHTML = '';
    
    if (elements.createEntityModal) {
        elements.createEntityModal.style.display = 'flex';
    }
}

function closeCreateEntityModal() {
    if (elements.createEntityModal) {
        elements.createEntityModal.style.display = 'none';
    }
}

function openCreateRelationshipModal(preselectedSourceId = null) {
    // Populate source/target selects with all entities
    const options = state.entities.map(e => 
        `<option value="${e.id}">${e.name} (${e.entity_type})</option>`
    ).join('');
    
    if (elements.relSource) {
        elements.relSource.innerHTML = '<option value="">Wybierz źródło...</option>' + options;
        if (preselectedSourceId) {
            elements.relSource.value = preselectedSourceId;
        }
    }
    if (elements.relTarget) {
        elements.relTarget.innerHTML = '<option value="">Wybierz cel...</option>' + options;
    }
    if (elements.relDate) elements.relDate.value = new Date().toISOString().split('T')[0];
    if (elements.relConfidence) elements.relConfidence.value = '1.0';
    if (elements.relEvidence) elements.relEvidence.value = '';
    
    if (elements.createRelationshipModal) {
        elements.createRelationshipModal.style.display = 'flex';
    }
}

function closeCreateRelationshipModal() {
    if (elements.createRelationshipModal) {
        elements.createRelationshipModal.style.display = 'none';
    }
}

async function handleCreateEntity(e) {
    e.preventDefault();
    
    const entityType = elements.newEntityType?.value;
    const name = elements.newEntityName?.value?.trim();
    
    if (!entityType || !name) {
        showToast('Podaj typ i nazwę encji', 'error');
        return;
    }
    
    const data = {
        entity_type: entityType,
        name: name,
        description: elements.newEntityDescription?.value || '',
        country: elements.newEntityCountry?.value || '',
        notes: elements.newEntityNotes?.value || ''
    };
    
    try {
        const entity = await createEntity(data);
        closeCreateEntityModal();
        await loadEntities();
        
        // Navigate to new entity
        if (entity && entity.id) {
            await loadEntityDetail(entity.id);
        }
    } catch (err) {
        // Error already handled in createEntity
    }
}

async function handleCreateRelationship(e) {
    e.preventDefault();
    
    const sourceId = elements.relSource?.value;
    const targetId = elements.relTarget?.value;
    const relType = elements.relType?.value;
    
    if (!sourceId || !targetId || !relType) {
        showToast('Wypełnij wszystkie wymagane pola', 'error');
        return;
    }
    
    const sourceEntity = state.entities.find(e => e.id === sourceId);
    const targetEntity = state.entities.find(e => e.id === targetId);
    
    const data = {
        source_id: sourceId,
        source_name: sourceEntity?.name || sourceId,
        target_id: targetId,
        target_name: targetEntity?.name || targetId,
        relationship_type: relType,
        date: elements.relDate?.value || '',
        confidence: parseFloat(elements.relConfidence?.value) || 1.0,
        evidence: elements.relEvidence?.value || ''
    };
    
    try {
        await createRelationship(data);
        closeCreateRelationshipModal();
        
        // Reload current entity if viewing detail
        if (state.currentEntity) {
            await loadEntityDetail(state.currentEntity.id);
        }
        await loadEntities();
    } catch (err) {
        // Error already handled in createRelationship
    }
}

// ============================================
// TOAST NOTIFICATIONS
// ============================================
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================
// EVENT LISTENERS
// ============================================
function initEventListeners() {
    // Profile change
    elements.profileSelect.addEventListener('change', async (e) => {
        const selected = e.target.options[e.target.selectedIndex];
        state.currentProfile = e.target.value;
        state.currentPlatform = selected.dataset.platform || 'instagram';
        switchView('gallery');
        await loadPosts();
    });
    
    // Content type filter
    elements.contentTypeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.contentTypeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.contentTypeFilter = btn.dataset.type;
            applyFilters();
        });
    });
    
    // Search & Sort
    elements.searchInput.addEventListener('input', applyFilters);
    elements.sortSelect.addEventListener('change', applyFilters);
    
    // Back button
    elements.backBtn.addEventListener('click', () => {
        if (state.mainView === 'entities') {
            switchView('entities');
        } else {
            switchView('gallery');
        }
    });
    
    // Main view toggle (Posts / Entities)
    elements.viewToggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            switchMainView(btn.dataset.view);
        });
    });
    
    // Entity type filter
    if (elements.entityTypeSelect) {
        elements.entityTypeSelect.addEventListener('change', (e) => {
            state.entityTypeFilter = e.target.value;
            applyEntityFilters();
        });
    }
    
    // Entity search
    if (elements.entitySearchInput) {
        elements.entitySearchInput.addEventListener('input', applyEntityFilters);
    }
    
    // Add entity button
    if (elements.addEntityBtn) {
        elements.addEntityBtn.addEventListener('click', openCreateEntityModal);
    }
    
    // Add relationship button
    if (elements.addRelationshipBtn) {
        elements.addRelationshipBtn.addEventListener('click', openCreateRelationshipModal);
    }
    
    // Save entity button
    if (elements.saveEntityBtn) {
        elements.saveEntityBtn.addEventListener('click', saveEntity);
    }
    
    // Delete entity button
    if (elements.deleteEntityBtn) {
        elements.deleteEntityBtn.addEventListener('click', confirmDeleteEntity);
    }
    
    // Add relation to current entity
    if (elements.addRelationToEntityBtn) {
        elements.addRelationToEntityBtn.addEventListener('click', () => {
            openCreateRelationshipModal(state.currentEntity?.id);
        });
    }
    
    // Entity form and modal handlers
    if (elements.createEntityForm) {
        elements.createEntityForm.addEventListener('submit', handleCreateEntity);
    }
    if (elements.createEntityModal) {
        elements.createEntityModal.addEventListener('click', (e) => {
            if (e.target === elements.createEntityModal) closeCreateEntityModal();
        });
    }
    
    if (elements.createRelationshipForm) {
        elements.createRelationshipForm.addEventListener('submit', handleCreateRelationship);
    }
    if (elements.createRelationshipModal) {
        elements.createRelationshipModal.addEventListener('click', (e) => {
            if (e.target === elements.createRelationshipModal) closeCreateRelationshipModal();
        });
    }
    
    // Add post button
    if (elements.addPostBtn) {
        elements.addPostBtn.addEventListener('click', openCreatePostModal);
    }
    
    // Save button
    elements.savePostBtn.addEventListener('click', savePost);
    
    // Delete post button
    elements.deletePostBtn.addEventListener('click', confirmDeletePost);
    
    // Tabs
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
    
    // Upload area
    elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
    
    elements.uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.uploadArea.classList.add('dragover');
    });
    
    elements.uploadArea.addEventListener('dragleave', () => {
        elements.uploadArea.classList.remove('dragover');
    });
    
    elements.uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.uploadArea.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    elements.uploadBtn.addEventListener('click', uploadFiles);
    
    // Lightbox
    elements.lightboxClose.addEventListener('click', closeLightbox);
    elements.lightbox.addEventListener('click', (e) => {
        if (e.target === elements.lightbox) closeLightbox();
    });
    
    // Confirm modal
    elements.confirmCancel.addEventListener('click', closeConfirm);
    elements.confirmOk.addEventListener('click', () => {
        if (confirmCallback) confirmCallback();
        closeConfirm();
    });
    
    // Create post modal
    if (elements.createPostCancel) {
        elements.createPostCancel.addEventListener('click', closeCreatePostModal);
    }
    if (elements.createPostForm) {
        elements.createPostForm.addEventListener('submit', handleCreatePost);
    }
    if (elements.createPostModal) {
        elements.createPostModal.addEventListener('click', (e) => {
            if (e.target === elements.createPostModal) closeCreatePostModal();
        });
    }
    
    // Modal tab switching
    elements.modalTabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchModalTab(btn.dataset.modalTab));
    });
    
    // Scrape form
    if (elements.scrapeForm) {
        elements.scrapeForm.addEventListener('submit', handleStartScrape);
    }
    
    // New profile form
    if (elements.newProfileForm) {
        elements.newProfileForm.addEventListener('submit', handleCreateProfile);
    }
    
    // Neo4j integration buttons
    const btnAddToNeo4j = document.getElementById('btn-add-to-neo4j');
    if (btnAddToNeo4j) {
        btnAddToNeo4j.addEventListener('click', addPostToNeo4j);
    }
    
    const btnSyncNeo4j = document.getElementById('btn-sync-neo4j');
    if (btnSyncNeo4j) {
        btnSyncNeo4j.addEventListener('click', syncToNeo4j);
    }
    
    // Add post to graph modal - close on click outside
    const addPostModal = document.getElementById('add-post-to-graph-modal');
    if (addPostModal) {
        addPostModal.addEventListener('click', (e) => {
            if (e.target === addPostModal) closeAddPostToGraphModal();
        });
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeLightbox();
            closeConfirm();
            closeCreatePostModal();
            closeCreateEntityModal();
            closeCreateRelationshipModal();
            closeAddPostToGraphModal();
        }
    });
    
    // Browser back/forward button handling
    window.addEventListener('popstate', async (e) => {
        if (e.state) {
            if (e.state.view === 'gallery') {
                state.mainView = 'posts';
                if (e.state.profile && e.state.profile !== state.currentProfile) {
                    elements.profileSelect.value = e.state.profile;
                    await loadPosts(e.state.profile);
                }
                switchView('gallery', false);
            } else if (e.state.view === 'detail' && e.state.postId) {
                state.mainView = 'posts';
                if (e.state.profile && e.state.profile !== state.currentProfile) {
                    elements.profileSelect.value = e.state.profile;
                    await loadPosts(e.state.profile);
                }
                await loadPostDetail(e.state.postId);
                switchView('detail', false);
            } else if (e.state.view === 'entities') {
                state.mainView = 'entities';
                switchMainView('entities');
                switchView('entities', false);
            } else if (e.state.view === 'entity-detail' && e.state.entityId) {
                state.mainView = 'entities';
                switchMainView('entities');
                await loadEntityDetail(e.state.entityId);
                switchView('entity-detail', false);
            }
        } else {
            // Initial state - show gallery
            switchView('gallery', false);
        }
    });
}

// ============================================
// URL HANDLING
// ============================================
function parseUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        profile: params.get('profile'),
        postId: params.get('post'),
        view: params.get('view'),
        entityId: params.get('entity')
    };
}

// ============================================
// INIT
// ============================================
async function init() {
    initEventListeners();
    await loadProfiles();
    
    // Check URL for initial state
    const urlParams = parseUrlParams();
    
    // Check if we should load entities view
    if (urlParams.view === 'entities') {
        await loadEntityTypes();
        await loadEntities();
        switchMainView('entities');
        
        if (urlParams.entityId) {
            await loadEntityDetail(urlParams.entityId);
            switchView('entity-detail', false);
        }
    } else if (urlParams.profile && state.currentProfile === urlParams.profile) {
        if (urlParams.postId) {
            // URL contains post ID - load detail view
            await loadPostDetail(urlParams.postId);
            switchView('detail', false);
        }
    }
    
    // Set initial history state
    if (state.currentProfile && state.mainView === 'posts') {
        history.replaceState(
            { view: state.viewMode, profile: state.currentProfile, postId: state.currentPost?.id },
            '',
            window.location.search || `?profile=${state.currentProfile}`
        );
    }
}

// Make functions globally available for onclick handlers
window.openLightbox = openLightbox;
window.confirmDeleteScreenshot = confirmDeleteScreenshot;
window.removePendingUpload = removePendingUpload;
window.openCreatePostModal = openCreatePostModal;
window.closeCreatePostModal = closeCreatePostModal;
window.confirmDeleteEdge = confirmDeleteEdge;
window.openCreateEntityModal = openCreateEntityModal;
window.closeCreateEntityModal = closeCreateEntityModal;
window.openCreateRelationshipModal = openCreateRelationshipModal;
window.closeCreateRelationshipModal = closeCreateRelationshipModal;
window.closeAddPostToGraphModal = closeAddPostToGraphModal;
window.confirmAddPostToGraph = confirmAddPostToGraph;
window.addPostToNeo4j = addPostToNeo4j;
window.syncToNeo4j = syncToNeo4j;

// Graph functions
function refreshGraph() {
    if (elements.graphIframe) {
        // Force reload by resetting src
        elements.graphIframe.src = '';
        setTimeout(() => {
            elements.graphIframe.src = 'http://localhost:8082/';
        }, 100);
        showToast('Graf odświeżony', 'success');
    }
}
window.refreshGraph = refreshGraph;

// Graph search functions
let searchResults = [];

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function searchInGraph() {
    const searchInput = document.getElementById('graph-search-input');
    const searchQuery = searchInput?.value.trim();
    
    if (!searchQuery || searchQuery.length < 2) {
        showToast('Wprowadź co najmniej 2 znaki', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/graph/search?q=${encodeURIComponent(searchQuery)}`);
        if (!response.ok) throw new Error('Search failed');
        
        searchResults = await response.json();
        displaySearchResults(searchResults);
        
        if (searchResults.length === 0) {
            showToast('Nie znaleziono wyników', 'warning');
        } else {
            showToast(`Znaleziono ${searchResults.length} wyników`, 'success');
        }
    } catch (error) {
        console.error('Search error:', error);
        showToast('Błąd wyszukiwania', 'error');
    }
}
window.searchInGraph = searchInGraph;

function displaySearchResults(results) {
    const resultsContainer = document.getElementById('graph-search-results');
    const resultsList = document.getElementById('search-results-list');
    const clearBtn = document.getElementById('clear-search-btn');
    
    if (!resultsContainer || !resultsList) return;
    
    if (results.length === 0) {
        resultsContainer.style.display = 'none';
        clearBtn.style.display = 'none';
        return;
    }
    
    resultsContainer.style.display = 'block';
    clearBtn.style.display = 'inline-flex';
    
    resultsList.innerHTML = results.map(node => `
        <div class="search-result-item" onclick="highlightNodeInGraph('${node.id}')">
            <i class="${node.icon || 'fas fa-circle'}" style="color: ${node.color || '#888'}"></i>
            <div class="search-result-info">
                <div class="search-result-name">${escapeHtml(node.name)}</div>
                <div class="search-result-type">${node.entity_type || 'Unknown'}</div>
            </div>
        </div>
    `).join('');
}

function clearGraphSearch() {
    const searchInput = document.getElementById('graph-search-input');
    const resultsContainer = document.getElementById('graph-search-results');
    const clearBtn = document.getElementById('clear-search-btn');
    
    if (searchInput) searchInput.value = '';
    if (resultsContainer) resultsContainer.style.display = 'none';
    if (clearBtn) clearBtn.style.display = 'none';
    
    searchResults = [];
    
    // Clear highlight in iframe if possible
    try {
        const iframe = elements.graphIframe;
        if (iframe && iframe.contentWindow) {
            iframe.contentWindow.postMessage({ type: 'clearHighlight' }, '*');
        }
    } catch (e) {
        // Cross-origin iframe, can't access
    }
}
window.clearGraphSearch = clearGraphSearch;

function highlightNodeInGraph(nodeId) {
    // Send message to iframe to focus node (without isolating)
    try {
        const iframe = elements.graphIframe;
        if (iframe && iframe.contentWindow) {
            iframe.contentWindow.postMessage({ 
                type: 'focusNode', 
                nodeId: nodeId 
            }, '*');
            // showToast(`Podświetlono: ${nodeId}`, 'info');
        }
    } catch (e) {
        console.error('Cannot highlight node:', e);
        showToast('Nie można podświetlić węzła w grafie', 'error');
    }
}
window.highlightNodeInGraph = highlightNodeInGraph;

// Enable search on Enter key
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('graph-search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchInGraph();
            }
        });
    }
});

// Start app
init();
