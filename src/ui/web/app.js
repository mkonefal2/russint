const colors = {
    'Person': '#f778ba',      // Pink
    'Organization': '#58a6ff', // Blue
    'Event': '#d2a8ff',       // Purple
    'Post': '#7ee787',        // Green
    'Profile': '#ffa657',     // Orange
    'Site': '#00bcd4',        // Cyan
    'default': '#8b949e'      // Grey
};

let Graph = null;
let selectedNode = null;
let hoveredNode = null;
let hoveredLink = null;
let isEditing = false;
let highlightNodes = new Set();
let highlightLinks = new Set();

// Image cache for node symbols/logos
const nodeImageCache = new Map();

function loadNodeImage(node) {
    if (!node || !node.properties) return null;
    
    const nodeId = node.id;
    
    // Check cache first
    if (nodeImageCache.has(nodeId)) {
        return nodeImageCache.get(nodeId);
    }
    
    // Determine image path
    let imagePath = node.properties.image || node.properties.screenshot;
    
    // Auto-detect for symbol nodes
    if (!imagePath && nodeId && nodeId.startsWith('symbol-')) {
        imagePath = `data/evidence/symbols/${nodeId}.png`;
    }
    
    if (!imagePath) {
        nodeImageCache.set(nodeId, null);
        return null;
    }
    
    // Normalize path
    let src = imagePath.replace(/\\/g, '/');
    if (src.startsWith('data/')) {
        src = '/' + src;
    } else if (!src.startsWith('/')) {
        src = '/data/' + src;
    }
    
    // Create and cache image
    const img = new Image();
    img.src = src;
    img.crossOrigin = 'anonymous';
    
    // Store loading state
    const imgData = { img: img, loaded: false, failed: false };
    nodeImageCache.set(nodeId, imgData);
    
    img.onload = () => { imgData.loaded = true; };
    img.onerror = () => { imgData.failed = true; };
    
    return imgData;
}

async function init() {
    try {
        const response = await fetch('/api/graph');
        if (!response.ok) throw new Error(`Server returned ${response.status} ${response.statusText}`);
        const data = await response.json();
        
        // Map Page to Site
        if (data.nodes) {
            data.nodes.forEach(node => {
                if (node.group === 'Page') {
                    node.group = 'Site';
                }
            });
        }
        
        const container = document.getElementById('graph-container');
        
        Graph = ForceGraph()
            (container)
            .graphData(data)
            .backgroundColor('#0d1117')
            .nodeId('id')
            .nodeLabel('name')
            .nodeRelSize(6)
            // Spread nodes apart using built-in force config
            .d3AlphaDecay(0.02)
            .d3VelocityDecay(0.85)
            .warmupTicks(100)
            .cooldownTicks(200)
            .linkColor(link => {
                if (highlightLinks.size > 0 && !highlightLinks.has(link)) return 'rgba(88, 166, 255, 0.05)'; // Dimmed
                if (highlightLinks.size > 0 && highlightLinks.has(link)) return '#58a6ff'; // Highlighted - bright
                return link === hoveredLink ? '#ffffff' : 'rgba(88, 166, 255, 0.4)';
            })
            .linkWidth(link => {
                if (highlightLinks.size > 0 && !highlightLinks.has(link)) return 0.5; // Dimmed width
                if (highlightLinks.size > 0 && highlightLinks.has(link)) return 3; // Highlighted - thicker
                return link === hoveredLink ? 5 : 2;
            })
            .linkDirectionalParticles(link => {
                if (highlightLinks.size > 0 && !highlightLinks.has(link)) return 0; // No particles for dimmed
                if (highlightLinks.size > 0 && highlightLinks.has(link)) return 4; // More particles for highlighted
                return 2;
            })
            .linkDirectionalParticleWidth(3)
            .linkDirectionalParticleSpeed(0.005)
            .linkDirectionalParticleColor(() => '#58a6ff')
            .onLinkHover(link => {
                hoveredLink = link;
            })
            .onNodeHover(node => {
                hoveredNode = node;
                container.style.cursor = node ? 'pointer' : null;
            })
            .linkCanvasObjectMode(() => 'after')
            .linkCanvasObject((link, ctx) => {
                if (link === hoveredLink) {
                    const label = link.type;
                    const start = link.source;
                    const end = link.target;
                    const textPos = Object.assign({}, ...['x', 'y'].map(c => ({
                        [c]: start[c] + (end[c] - start[c]) / 2 
                    })));
                    
                    // Use same scaling as nodes: sqrt formula
                    const zoom = Graph ? Graph.zoom() : 1;
                    const dpr = window.devicePixelRatio || 1;
                    const globalScale = zoom * dpr;
                    
                    // Edge font = half of node font (baseFontSize 12 -> 6)
                    const baseFontSize = 6;
                    const fontSize = baseFontSize / Math.sqrt(globalScale);
                    ctx.font = `${fontSize}px Sans-Serif`;
                    const textWidth = ctx.measureText(label).width;
                    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.3);

                    ctx.save();
                    ctx.translate(textPos.x, textPos.y);
                    
                    const relLink = { x: end.x - start.x, y: end.y - start.y };
                    let textAngle = Math.atan2(relLink.y, relLink.x);
                    if (textAngle > Math.PI / 2) textAngle = -(Math.PI - textAngle);
                    if (textAngle < -Math.PI / 2) textAngle = -(-Math.PI - textAngle);
                    
                    ctx.rotate(textAngle);

                    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
                    ctx.fillRect(-bckgDimensions[0] / 2, -bckgDimensions[1] / 2, ...bckgDimensions);

                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = '#fff';
                    ctx.fillText(label, 0, 0);
                    
                    ctx.restore();
                }
            })
            .nodeCanvasObject((node, ctx, globalScale) => {
                const label = node.name;
                // Use sqrt scaling: text grows when zooming in, but not linearly
                const baseFontSize = 10;
                const fontSize = baseFontSize / Math.sqrt(globalScale);
                let color = colors[node.group] || colors['default'];
                
                // Dimming logic
                if (highlightNodes.size > 0 && !highlightNodes.has(node)) {
                    ctx.globalAlpha = 0.1;
                } else {
                    ctx.globalAlpha = 1;
                }
                
                const primaryGroups = ['Organization', 'Profile', 'Person', 'Site', 'Event', 'Channel'];
                const isPrimary = primaryGroups.includes(node.group);
                const isSelected = node === selectedNode;
                const isHovered = node === hoveredNode;
                const isHighlighted = highlightNodes.size > 0 && highlightNodes.has(node);
                
                // Show full card if primary, selected, hovered, OR highlighted in focus mode
                if (isPrimary || isSelected || isHovered || isHighlighted) {
                    ctx.font = `${fontSize}px 'Segoe UI', Sans-Serif`;
                    const textWidth = ctx.measureText(label).width;
                    const bckgDimensions = [textWidth + fontSize, fontSize * 1.4];

                    // Card background
                    ctx.fillStyle = 'rgba(22, 27, 34, 0.9)';
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 1 / globalScale;
                    
                    // Glow
                    if (isSelected) {
                        ctx.shadowColor = '#fff';
                        ctx.shadowBlur = 15;
                        ctx.strokeStyle = '#fff';
                    } else {
                        ctx.shadowColor = color;
                        ctx.shadowBlur = 5;
                    }
                    
                    ctx.beginPath();
                    if (ctx.roundRect) {
                        ctx.roundRect(
                            node.x - bckgDimensions[0] / 2, 
                            node.y - bckgDimensions[1] / 2, 
                            ...bckgDimensions, 
                            2 / globalScale
                        );
                    } else {
                        ctx.rect(
                            node.x - bckgDimensions[0] / 2, 
                            node.y - bckgDimensions[1] / 2, 
                            ...bckgDimensions
                        );
                    }
                    ctx.fill();
                    ctx.stroke();
                    
                    ctx.shadowBlur = 0;

                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = '#c9d1d9';
                    ctx.fillText(label, node.x, node.y);

                    node.__bckgDimensions = bckgDimensions; // Store for hit detection
                    
                    // Draw image below label when hovered (or selected/highlighted)
                    if ((isHovered || isSelected || isHighlighted) && node.properties && (node.properties.image || node.id.startsWith('symbol-'))) {
                        const imgData = loadNodeImage(node);
                        if (imgData && imgData.loaded && !imgData.failed) {
                            const maxImgSize = 60 / globalScale;
                            const aspectRatio = imgData.img.width / imgData.img.height;
                            let imgW, imgH;
                            if (aspectRatio > 1) {
                                imgW = maxImgSize;
                                imgH = maxImgSize / aspectRatio;
                            } else {
                                imgH = maxImgSize;
                                imgW = maxImgSize * aspectRatio;
                            }
                            const imgY = node.y + bckgDimensions[1] / 2 + 5 / globalScale;
                            
                            ctx.drawImage(
                                imgData.img,
                                node.x - imgW / 2,
                                imgY,
                                imgW,
                                imgH
                            );
                        }
                    }
                } else {
                    // Secondary nodes (Post, Event, etc.) - smaller Glowing Sphere
                    const radius = 2; // reduced size for non-primary nodes
                    
                    ctx.shadowColor = color;
                    ctx.shadowBlur = 6; // slightly reduced glow
                    
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
                    ctx.fillStyle = color;
                    ctx.fill();
                    
                    ctx.shadowBlur = 0;
                    
                    node.__bckgDimensions = null; // Reset so hit detection uses circle
                }
            })
            .nodePointerAreaPaint((node, color, ctx) => {
                ctx.fillStyle = color;
                const bckgDimensions = node.__bckgDimensions;
                if (bckgDimensions) {
                    // Use a simplified rectangle for hit detection
                    ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
                } else {
                    // Fallback - larger hit area for small nodes (radius 12 instead of 6)
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, 12, 0, 2 * Math.PI, false);
                    ctx.fill();
                }
            })
            .onNodeClick(node => {
                console.log("Clicked node:", node);
                if (node) {
                    // Visual feedback for debugging
                    showStatusBanner(`Selected: ${node.name}`, 'info');
                    
                    selectedNode = node;
                    isEditing = false; // Reset edit mode on new selection
                    
                    // Highlight logic
                    highlightNodes.clear();
                    highlightLinks.clear();
                    highlightNodes.add(node);
                    
                    // Find neighbors
                    const links = Graph.graphData().links;
                    links.forEach(link => {
                        if (link.source === node || link.target === node) {
                            highlightLinks.add(link);
                            highlightNodes.add(link.source);
                            highlightNodes.add(link.target);
                        }
                    });
                    
                    try {
                        updateDetails(node);
                        
                        // Auto-expand panel if collapsed
                        const detailsPanel = document.getElementById('details-container');
                        if (detailsPanel && detailsPanel.classList.contains('collapsed')) {
                            detailsPanel.classList.remove('collapsed');
                            // Restore a reasonable height if it was collapsed
                            if (detailsPanel.clientHeight < 100) {
                                detailsPanel.style.height = '300px';
                            }
                        }
                    } catch (e) {
                        console.error("Error updating details:", e);
                        alert("Error showing details: " + e.message);
                    }
                    
                    // Center
                    Graph.centerAt(node.x, node.y, 1000);
                    Graph.zoom(6, 2000);
                }
            })
            .onBackgroundClick(() => {
                clearSelection();
                highlightNodes.clear();
                highlightLinks.clear();
            });
        
        // Debug mouse events
        // document.addEventListener('mousemove', (e) => { ... });

        // Configure forces after graph is created for better spacing
        Graph.d3Force('charge').strength(-500);
        Graph.d3Force('link').distance(150);

        // --- Drag behavior improvements ---
        // Keep the dragged node fixed to the pointer while dragging
        // (avoid freezing *all* other nodes which can make the layout feel rigid)
        // NOTE: some builds of force-graph do not implement onNodeDragStart.
        // Use a lightweight start-detection inside onNodeDrag to avoid calling
        // a missing function which causes `TypeError: Graph.onNodeDragStart is not a function`.
        Graph.onNodeDrag((node) => {
            try {
                // If this is the first onNodeDrag call for this node, treat it as drag start
                if (!node.__isDragging) {
                    node.__isDragging = true;
                    // fix node at current position when dragging starts
                    node.fx = node.x;
                    node.fy = node.y;
                }

                // keep dragged node fixed to mouse coords while dragging
                node.fx = node.x;
                node.fy = node.y;
            } catch (e) {
                console.warn('onNodeDrag error', e);
            }
        });

        Graph.onNodeDragEnd((node) => {
            try {
                // release dragged node so simulation can continue
                node.fx = null;
                node.fy = null;
                // clear internal dragging flag
                if (node.__isDragging) node.__isDragging = false;
            } catch (e) {
                console.warn('onNodeDragEnd error', e);
            }
        });
            
        // Resize handling
        window.addEventListener('resize', () => {
            Graph.width(container.clientWidth);
            Graph.height(container.clientHeight);
        });

        // Escape key to exit focus mode
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                clearSelection();
                highlightNodes.clear();
                highlightLinks.clear();
            }
        });

    } catch (err) {
        console.error("Failed to init graph:", err);
        showStatusBanner('Failed to load graph data. Check console (F12) for details.');
    }
}

function showStatusBanner(message, level = 'error') {
    let el = document.getElementById('status-banner');
    if (!el) {
        el = document.createElement('div');
        el.id = 'status-banner';
        el.style.position = 'fixed';
        el.style.right = '12px';
        el.style.top = '12px';
        el.style.zIndex = '9999';
        el.style.padding = '10px 14px';
        el.style.borderRadius = '6px';
        el.style.fontSize = '13px';
        el.style.boxShadow = '0 4px 14px rgba(2,6,23,0.6)';
        el.style.color = '#fff';
        el.style.cursor = 'pointer';
        el.addEventListener('click', () => { el.style.display = 'none'; });
        document.body.appendChild(el);
    }
    el.style.display = 'block';
    el.style.background = level === 'error' ? 'rgba(220,50,47,0.95)' : 'rgba(50,120,200,0.95)';
    el.innerText = message;
}

function toggleEditMode() {
    if (!selectedNode) return;
    isEditing = !isEditing;
    updateDetails(selectedNode);
}

async function saveChanges() {
    if (!selectedNode) return;
    
    const inputs = document.querySelectorAll('.edit-input');
    const newProps = {};
    
    inputs.forEach(input => {
        const key = input.dataset.key;
        const value = input.value;
        newProps[key] = value;
        // Update local model
        selectedNode.properties[key] = value;
        if (key === 'name') selectedNode.name = value;
    });
    
    try {
        const response = await fetch('/api/update_node', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: selectedNode.id,
                properties: newProps
            })
        });
        
        if (!response.ok) throw new Error('Failed to save');
        
        isEditing = false;
        updateDetails(selectedNode);
        // Refresh graph to show name changes if any
        // Graph.refresh(); // ForceGraph doesn't have simple refresh, but data update works
        
    } catch (e) {
        alert("Error saving changes: " + e.message);
    }
}

function updateDetails(node) {
    const title = document.getElementById('details-title');
    const tbody = document.getElementById('details-body');
    const gallery = document.getElementById('details-gallery');
    const editBtn = document.getElementById('edit-btn');
    const saveBtn = document.getElementById('save-btn');
    
    if (!node) return;

    // Show controls
    if (editBtn) {
        editBtn.style.display = 'inline-block';
        editBtn.innerText = isEditing ? 'Cancel' : '✎ Edit';
    }
    if (saveBtn) {
        saveBtn.style.display = isEditing ? 'inline-block' : 'none';
    }

    title.innerText = `${node.group}: ${node.name}`;
    title.style.color = colors[node.group] || colors['default'];
    
    // Table
    let html = '';
    if (node.properties) {
        for (const [key, val] of Object.entries(node.properties)) {
            if (key === 'screenshot') continue; // Handle separately
            
            let displayVal = val;
            if (isEditing) {
                displayVal = `<input type="text" class="edit-input" data-key="${key}" value="${val ? val.replace(/"/g, '&quot;') : ''}" style="width: 100%; background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 4px;">`;
            } else {
                // Check if it's a URL
                if (typeof val === 'string' && (val.startsWith('http://') || val.startsWith('https://'))) {
                    displayVal = `<a href="${val}" target="_blank" style="color: #58a6ff; text-decoration: none;">${val}</a>`;
                }
            }
            
            html += `<tr><td class="prop-key">${key}</td><td class="prop-val">${displayVal}</td></tr>`;
        }
    } else {
        html = '<tr><td colspan="2">No properties available</td></tr>';
    }
    tbody.innerHTML = html;
    
    // Gallery - show screenshot or symbol image
    gallery.innerHTML = '';
    
    // Collect all image paths to display
    let imagePaths = [];
    
    // 1. Check for screenshot field
    if (node.properties && node.properties.screenshot) {
        imagePaths.push({ path: node.properties.screenshot, label: 'Screenshot' });
    }
    
    // 2. Check for image field (symbols/logos)
    if (node.properties && node.properties.image) {
        imagePaths.push({ path: node.properties.image, label: 'Symbol/Logo' });
    }
    
    // 3. Try to infer path from ID for Facebook posts
    if (node.id && node.id.startsWith('fb_')) {
        const parts = node.id.split('_');
        if (parts.length >= 3) {
            const handle = parts[1];
            imagePaths.push({ path: `data/evidence/facebook/${handle}/${node.id}.png`, label: 'Facebook Post' });
        }
    }

    // 3b. Try to infer path from URL (for nodes like post-001)
    if (node.properties && node.properties.url && node.properties.url.includes('facebook.com')) {
        try {
            // Example: https://www.facebook.com/BraterstwaLudziWolnych/posts/pfbid0...
            const url = node.properties.url;
            const match = url.match(/facebook\.com\/([^\/]+)\/posts\/([^\/?]+)/);
            if (match) {
                const handle = match[1];
                const postId = match[2];
                const filename = `fb_${handle}_${postId}.png`;
                imagePaths.push({ 
                    path: `data/evidence/facebook/${handle}/${filename}`, 
                    label: 'Facebook Screenshot (Inferred)' 
                });
            }
        } catch (e) {
            console.warn("Error parsing FB URL:", e);
        }
    }
    
    // 4. Try to infer symbol path from node ID
    if (node.id && node.id.startsWith('symbol-')) {
        // Try common extensions
        imagePaths.push({ path: `data/evidence/symbols/${node.id}.png`, label: 'Symbol' });
        imagePaths.push({ path: `data/evidence/symbols/${node.id}.jpg`, label: 'Symbol' });
    }

    if (imagePaths.length > 0) {
        let loadedAny = false;
        
        imagePaths.forEach((imgInfo, index) => {
            const img = document.createElement('img');
            
            let src = imgInfo.path;
            // Normalize path separators
            src = src.replace(/\\/g, '/');
            // Remove leading slash if present
            if (src.startsWith('/')) src = src.substring(1);
            
            // Try multiple possible static URL prefixes to be robust across
            // deployments (Streamlit Cloud, local with /app prefix, etc.).
            // We'll attempt each candidate in order and move to the next on error.
            const candidates = [];
            // common relative/absolute forms the app has used
            if (src.startsWith('data/')) {
                candidates.push('/app/static/' + src);
                candidates.push('/static/' + src);
                candidates.push('/' + src);
                candidates.push('/static/data/' + src.replace(/^data\//, ''));
                candidates.push('/src/ui/static/' + src);
                // Try raw GitHub as a last resort (public repo)
                try {
                        const ghUser = 'mkonefal2';
                        const ghRepo = 'russint';
                        const ghPath = src.replace(/^\//, '');
                        // Try multiple raw URL shapes: branch name and refs/heads/<branch>
                        const ghBranches = ['main', 'refs/heads/main'];
                        ghBranches.forEach(b => {
                            candidates.push(`https://raw.githubusercontent.com/${ghUser}/${ghRepo}/${b}/${ghPath}`);
                            // also try mirrored location under src/ui/static
                            candidates.push(`https://raw.githubusercontent.com/${ghUser}/${ghRepo}/${b}/src/ui/static/${ghPath}`);
                        });
                } catch (e) {
                    // ignore
                }
            } else {
                // other forms (already include data/ prefix sometimes)
                candidates.push('/app/static/data/' + src);
                candidates.push('/static/data/' + src);
                candidates.push('/' + src);
                candidates.push('/app/static/' + src);
                // try GitHub raw for non-standard src
                try {
                    const ghBase = 'https://raw.githubusercontent.com/mkonefal2/russint/main/';
                    const ghUser = 'mkonefal2';
                    const ghRepo = 'russint';
                    const ghPath2 = src.replace(/^\//, '');
                    const ghBranches2 = ['main', 'refs/heads/main'];
                    ghBranches2.forEach(b => {
                        candidates.push(`https://raw.githubusercontent.com/${ghUser}/${ghRepo}/${b}/${ghPath2}`);
                        candidates.push(`https://raw.githubusercontent.com/${ghUser}/${ghRepo}/${b}/src/ui/static/${ghPath2}`);
                    });
                } catch (e) {}
            }

            // Remove duplicates and normalize
            const seen = new Set();
            const urls = candidates.map(u => u.replace(/\\/g, '/')).filter(u => {
                if (seen.has(u)) return false; seen.add(u); return true;
            });

            // If this is a symbol path, add a local SVG placeholder as last resort
            // so the UI shows a clear placeholder instead of an empty box.
            if (src.includes('data/evidence/symbols')) {
                const placeholderCandidates = [
                    '/app/static/data/evidence/symbols/symbol-placeholder.svg',
                    '/static/data/evidence/symbols/symbol-placeholder.svg',
                    '/src/ui/static/data/evidence/symbols/symbol-placeholder.svg'
                ];
                placeholderCandidates.forEach(p => {
                    if (!seen.has(p)) {
                        urls.push(p);
                        seen.add(p);
                    }
                });
            }

            let attempt = 0;
            const tryNext = () => {
                if (attempt >= urls.length) {
                    // all attempts failed, keep last src for error message
                    img.dataset.tried = JSON.stringify(urls);
                    return;
                }
                const u = urls[attempt++];
                console.log('Trying image URL:', u);
                img.src = u;
            };

            img.className = 'gallery-img';
            img.style.marginBottom = '10px';
            img.onclick = () => window.open(img.src, '_blank');
            img.onload = () => {
                loadedAny = true;
            };
            img.onerror = () => {
                // try next candidate URL, or show the failing URL list when exhausted
                if (attempt < urls.length) {
                    tryNext();
                    return;
                }

                console.warn('Failed to load image (all candidates):', urls);
                img.style.display = 'none';
                const err = document.createElement('div');
                const last = urls.length ? urls[urls.length - 1] : img.src;
                err.innerHTML = `❌ Image not found:<br><a href="${last}" target="_blank" style="color:#ff6b6b;word-break:break-all;">${last}</a>`;
                err.style.color = '#ff6b6b';
                err.style.fontSize = '0.7rem';
                err.style.padding = '5px';
                err.style.border = '1px dashed #ff6b6b';
                wrapper.appendChild(err);
            };

            // start attempts
            tryNext();
            
            const wrapper = document.createElement('div');
            wrapper.style.marginBottom = '10px';
            
            const label = document.createElement('div');
            label.innerText = imgInfo.label;
            label.style.color = '#58a6ff';
            label.style.fontSize = '0.75rem';
            label.style.marginBottom = '3px';
            
            wrapper.appendChild(label);
            wrapper.appendChild(img);
            gallery.appendChild(wrapper);
        });
        
        const caption = document.createElement('div');
        caption.innerText = 'Click to enlarge';
        caption.style.color = '#555';
        caption.style.fontSize = '0.8rem';
        caption.style.marginTop = '5px';
        gallery.appendChild(caption);
    } else {
        gallery.innerHTML = '<div style="color: #555; font-size: 0.8rem;">No evidence available</div>';
    }
}

function clearSelection() {
    selectedNode = null;
    document.getElementById('details-title').innerText = 'Select a node';
    document.getElementById('details-title').style.color = '#58a6ff';
    document.getElementById('details-body').innerHTML = '<tr><td colspan="2" style="text-align:center; color:#555; padding: 20px;">Click on a node to view details</td></tr>';
    document.getElementById('details-gallery').innerHTML = '<div style="color: #555; font-size: 0.8rem;">No evidence selected</div>';
}

function resetZoom() {
    if (Graph) {
        Graph.zoomToFit(400);
    }
}

// Bottom Panel Logic
const detailsContainer = document.getElementById('details-container');
const resizeHandle = document.getElementById('resize-handle');
let isResizing = false;
let lastDownY = 0;

if (resizeHandle) {
    resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        lastDownY = e.clientY;
        document.body.style.cursor = 'ns-resize';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        // Calculate new height based on mouse position relative to window bottom
        // Panel is at bottom, so height = window.innerHeight - mouseY
        const newHeight = window.innerHeight - e.clientY;
        
        if (newHeight >= 60 && newHeight <= window.innerHeight * 0.8) {
            detailsContainer.style.height = `${newHeight}px`;
            
            if (newHeight > 70) {
                detailsContainer.classList.remove('collapsed');
            }
        }
    });

    document.addEventListener('mouseup', () => {
        isResizing = false;
        document.body.style.cursor = 'default';
    });
}

function toggleDetailsPanel() {
    const container = document.getElementById('details-container');
    container.classList.toggle('collapsed');
    
    if (!container.classList.contains('collapsed')) {
        // If expanding and height is small (collapsed state), restore default
        if (container.clientHeight <= 70) {
            container.style.height = '300px';
        }
    }
}

// Expose to global scope
window.toggleDetailsPanel = toggleDetailsPanel;

init();
