"""
RUSSINT - Dashboard
Aplikacja do przeglądania postów oraz edycji grafu wiedzy (węzły i relacje).
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
import shutil
import subprocess
import sys

# Konfiguracja strony musi być pierwsza
st.set_page_config(
    page_title="RUSSINT Dashboard",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# Ścieżki
BASE_DIR = Path(__file__).parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "facebook"
EVIDENCE_DIR = BASE_DIR / "data" / "evidence" / "facebook"
GRAPH_NODES_FILE = BASE_DIR / "data" / "raw" / "graph_nodes.json"
GRAPH_EDGES_FILE = BASE_DIR / "data" / "raw" / "graph_edges.json"
LOADER_SCRIPT = BASE_DIR / "scripts" / "load_to_neo4j.py"

# Custom CSS
st.markdown("""
<style>
    .post-card {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #333;
    }
    .post-header {
        color: #1877f2;
        font-weight: bold;
        font-size: 1.2em;
        margin-bottom: 10px;
    }
    .post-meta {
        color: #888;
        font-size: 0.9em;
        margin-bottom: 15px;
    }
    .post-text {
        color: #e0e0e0;
        line-height: 1.6;
        white-space: pre-wrap;
    }
    .external-link {
        background-color: #2d2d2d;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .stImage {
        border-radius: 10px;
        border: 1px solid #333;
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_available_profiles():
    """Pobiera listę dostępnych profili (katalogów z JSONami)."""
    profiles = []
    if RAW_DIR.exists():
        for folder in RAW_DIR.iterdir():
            if folder.is_dir() and list(folder.glob("*.json")):
                profiles.append(folder.name)
    return sorted(profiles)


def load_posts_for_profile(profile_name):
    """Wczytuje wszystkie posty dla danego profilu."""
    posts = []
    profile_dir = RAW_DIR / profile_name
    
    if not profile_dir.exists():
        return posts
    
    for json_file in sorted(profile_dir.glob("*.json"), reverse=True):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                post = json.load(f)
                post['_file'] = str(json_file)
                post['_file_name'] = json_file.name
                posts.append(post)
        except Exception as e:
            st.warning(f"Błąd wczytywania {json_file.name}: {e}")
    
    # Sortuj po dacie (jeśli dostępna)
    posts.sort(key=lambda x: x.get('collected_at', ''), reverse=True)
    return posts


def get_screenshot_path(post, profile_name):
    """Pobiera ścieżkę do screenshotu dla posta."""
    screenshot = post.get('screenshot')
    if not screenshot:
        return None
    
    # Jeśli screenshot zawiera pełną ścieżkę względną
    if screenshot.startswith('data/'):
        full_path = BASE_DIR / screenshot
        if full_path.exists():
            return full_path
    
    # Próbuj różnych lokalizacji (kompatybilność wsteczna)
    possible_paths = [
        EVIDENCE_DIR / profile_name / screenshot,
        EVIDENCE_DIR / profile_name / Path(screenshot).name,
        EVIDENCE_DIR / "screenshots" / screenshot,
        BASE_DIR / screenshot
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None


def format_date(date_str):
    """Formatuje datę do czytelnej formy."""
    if not date_str:
        return "Brak daty"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return date_str


def clean_text(text):
    """Czyści tekst z artefaktów."""
    if not text:
        return ""
    import re
    cleaned = re.sub(r'(?:\b[a-zA-Z0-9]\b\s+){5,}', '', text)
    return cleaned.strip()


def load_json_file(filepath):
    if not filepath.exists():
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Błąd wczytywania {filepath}: {e}")
        return []


def save_json_file(filepath, data):
    try:
        # Kopia zapasowa
        backup_path = filepath.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
        if filepath.exists():
            shutil.copy(filepath, backup_path)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        st.success(f"Zapisano zmiany w {filepath.name} (Kopia: {backup_path.name})")
        return True
    except Exception as e:
        st.error(f"Błąd zapisu {filepath}: {e}")
        return False


def run_neo4j_sync():
    """Uruchamia skrypt synchronizacji z Neo4j."""
    if not LOADER_SCRIPT.exists():
        st.error(f"Nie znaleziono skryptu loadera: {LOADER_SCRIPT}")
        return
    
    with st.spinner("⏳ Trwa synchronizacja z Neo4j..."):
        # Debug: Sprawdź zmienne środowiskowe
        if "NEO4J_PASSWORD" not in os.environ:
            st.warning("⚠️ Zmienna środowiskowa NEO4J_PASSWORD nie jest ustawiona w procesie Streamlit. Skrypt może nie mieć dostępu do bazy.")
        
        try:
            # Uruchomienie skryptu jako podproces z flagą -u (unbuffered)
            cmd = [sys.executable, "-u", str(LOADER_SCRIPT)]
            
            # Wymuś kodowanie UTF-8 dla środowiska podprocesu
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=BASE_DIR,
                encoding='utf-8',
                env=env
            )
            
            if result.returncode == 0:
                st.success("✅ Synchronizacja zakończona sukcesem!")
                with st.expander("📜 Logi synchronizacji", expanded=False):
                    st.code(result.stdout)
            else:
                st.error(f"❌ Błąd podczas synchronizacji! (Kod: {result.returncode})")
                with st.expander("📜 Szczegóły błędu", expanded=True):
                    st.markdown("**Komenda:**")
                    st.code(f"{' '.join(cmd)}")
                    st.markdown("**STDERR:**")
                    st.code(result.stderr if result.stderr else "Brak błędów w stderr")
                    st.markdown("**STDOUT:**")
                    st.code(result.stdout if result.stdout else "Brak outputu")
                    
        except Exception as e:
            st.error(f"Wystąpił błąd podczas uruchamiania skryptu: {e}")


# ==========================================
# VIEWS
# ==========================================

def render_post_viewer():
    st.header("📸 Post Viewer")
    
    # Sidebar controls specific to Post Viewer
    profiles = get_available_profiles()
    if not profiles:
        st.warning("Brak dostępnych profili. Uruchom najpierw scraper.")
        return

    selected_profile = st.sidebar.selectbox("📂 Wybierz profil", profiles, index=0)
    
    posts = load_posts_for_profile(selected_profile)
    st.sidebar.markdown(f"**Postów:** {len(posts)}")
    
    # Filtry
    st.sidebar.markdown("### 🔍 Filtry")
    search_query = st.sidebar.text_input("Szukaj w treści", "")
    has_external_link = st.sidebar.checkbox("Tylko z linkami zewnętrznymi", False)
    has_screenshot = st.sidebar.checkbox("Tylko ze screenshotami", False)
    
    filtered_posts = posts.copy()
    if search_query:
        filtered_posts = [p for p in filtered_posts 
                          if search_query.lower() in (p.get('raw_text_preview', '') or '').lower()]
    if has_external_link:
        filtered_posts = [p for p in filtered_posts if p.get('external_links')]
    if has_screenshot:
        filtered_posts = [p for p in filtered_posts if get_screenshot_path(p, selected_profile)]
    
    st.sidebar.markdown(f"**Wyświetlanych:** {len(filtered_posts)}")
    
    # Paginacja
    posts_per_page = st.sidebar.slider("Postów na stronę", 5, 50, 10)
    total_pages = max(1, (len(filtered_posts) + posts_per_page - 1) // posts_per_page)
    current_page = st.sidebar.number_input("Strona", min_value=1, max_value=total_pages, value=1)
    
    view_mode = st.sidebar.radio("Widok", ["📰 Pełny", "📋 Lista", "🖼️ Galeria"])
    
    # Render content
    st.markdown(f"Strona {current_page} z {total_pages} | Znaleziono {len(filtered_posts)} postów")
    
    start_idx = (current_page - 1) * posts_per_page
    end_idx = min(start_idx + posts_per_page, len(filtered_posts))
    page_posts = filtered_posts[start_idx:end_idx]
    
    if view_mode == "📰 Pełny":
        for idx, post in enumerate(page_posts):
            with st.container():
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown(f"### 📝 Post #{start_idx + idx + 1}")
                    collected = format_date(post.get('collected_at'))
                    st.markdown(f"**📅 Zebrano:** {collected}")
                    
                    post_url = post.get('post_url')
                    if post_url:
                        st.markdown(f"**🔗 Link:** [Otwórz na Facebook]({post_url})")
                    
                    external_links = post.get('external_links')
                    if external_links:
                        st.markdown("**📎 Linki zewnętrzne:**")
                        if isinstance(external_links, list):
                            for link in external_links:
                                st.markdown(f"- [{link}]({link})")
                        else:
                            st.markdown(f"- [{external_links}]({external_links})")
                    
                    text = post.get('raw_text_preview', '')
                    if text:
                        st.markdown("**📄 Treść:**")
                        cleaned = clean_text(text)
                        st.text_area("", cleaned, height=200, key=f"text_{post.get('id', idx)}", disabled=True)
                    
                    with st.expander("🔧 Szczegóły techniczne"):
                        st.code(f"ID: {post.get('id', 'N/A')}")
                        file_path = post.get('_file', '')
                        st.code(f"Plik: {post.get('_file_name', 'N/A')}")
                        
                        if file_path:
                            try:
                                abs_path = Path(file_path).absolute()
                                # Link do otwarcia pliku w VS Code
                                st.markdown(f"[📂 Otwórz JSON w VS Code](vscode://file/{abs_path})")
                            except Exception:
                                pass
                                
                        st.json(post)
                
                with col2:
                    screenshot_path = get_screenshot_path(post, selected_profile)
                    if screenshot_path:
                        st.markdown("**📸 Screenshot:**")
                        st.image(str(screenshot_path), use_container_width=True)
                        
                        # Przycisk do otwarcia w systemie (ułatwia kopiowanie)
                        if st.button("📂 Otwórz grafikę (Ctrl+C)", key=f"open_img_{post.get('id', idx)}"):
                            try:
                                if sys.platform == "win32":
                                    os.startfile(screenshot_path)
                                elif sys.platform == "darwin":
                                    subprocess.call(["open", str(screenshot_path)])
                                else:
                                    subprocess.call(["xdg-open", str(screenshot_path)])
                            except Exception as e:
                                st.error(f"Nie udało się otworzyć pliku: {e}")

                        # --- COPILOT CONTEXT HELPER ---
                        with st.expander("🤖 Copilot Context (Kopiuj do czatu)"):
                            copilot_prompt = f"""
Proszę o analizę tego posta.
Oto metadane z pliku JSON:
```json
{json.dumps(post, ensure_ascii=False, indent=2)}
```
Nazwa pliku screenshotu: `{screenshot_path.name}`
"""
                            st.code(copilot_prompt, language="markdown")
                            st.info("Skopiuj powyższy tekst i wklej go do czatu Copilot razem ze screenshotem.")
                        # ------------------------------
                    else:
                        st.info("Brak screenshotu")
                st.markdown("---")

    elif view_mode == "📋 Lista":
        for idx, post in enumerate(page_posts):
            with st.expander(f"📝 #{start_idx + idx + 1} | {format_date(post.get('collected_at'))} | {(post.get('raw_text_preview', '') or '')[:100]}..."):
                col1, col2 = st.columns([2, 1])
                with col1:
                    text = post.get('raw_text_preview', '')
                    if text:
                        st.markdown(clean_text(text))
                    post_url = post.get('post_url')
                    if post_url:
                        st.markdown(f"[🔗 Otwórz na Facebook]({post_url})")
                with col2:
                    screenshot_path = get_screenshot_path(post, selected_profile)
                    if screenshot_path:
                        st.image(str(screenshot_path), width=300)

    elif view_mode == "🖼️ Galeria":
        cols = st.columns(3)
        for idx, post in enumerate(page_posts):
            col_idx = idx % 3
            with cols[col_idx]:
                screenshot_path = get_screenshot_path(post, selected_profile)
                if screenshot_path:
                    st.image(str(screenshot_path), use_container_width=True)
                    st.caption(f"#{start_idx + idx + 1} | {format_date(post.get('collected_at'))}")
                    post_url = post.get('post_url')
                    if post_url:
                        st.markdown(f"[🔗 FB]({post_url})")
                else:
                    st.info(f"#{start_idx + idx + 1} - Brak screenshotu")


def render_graph_editor():
    st.header("🕸️ Graph Editor")
    st.info("Edytuj węzły (Nodes) i relacje (Edges). Zmiany są zapisywane do plików JSON w `data/raw/`.")
    
    tab_nodes, tab_edges = st.tabs(["🔵 Nodes (Węzły)", "🔗 Edges (Relacje)"])
    
    # --- NODES ---
    with tab_nodes:
        nodes_data = load_json_file(GRAPH_NODES_FILE)
        if nodes_data:
            df_nodes = pd.DataFrame(nodes_data)
            
            # Konfiguracja kolumn
            column_config = {
                "id": st.column_config.TextColumn("ID", disabled=True),
                "name": st.column_config.TextColumn("Nazwa"),
                "entity_type": st.column_config.SelectboxColumn(
                    "Typ",
                    options=["person", "organization", "event", "post", "page", "profile"],
                    required=True
                ),
                "description": st.column_config.TextColumn("Opis", width="large"),
                "url": st.column_config.LinkColumn("URL"),
            }
            
            st.markdown(f"**Liczba węzłów:** {len(nodes_data)}")
            
            edited_df_nodes = st.data_editor(
                df_nodes,
                column_config=column_config,
                num_rows="dynamic",
                key="editor_nodes",
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("💾 Zapisz zmiany (Nodes)", key="save_nodes"):
                # Konwersja z powrotem do listy słowników
                # Uwaga: st.data_editor zwraca DataFrame, trzeba obsłużyć NaN
                updated_nodes = edited_df_nodes.to_dict(orient="records")
                # Czyszczenie pustych wartości (NaN)
                cleaned_nodes = []
                for node in updated_nodes:
                    cleaned_node = {k: v for k, v in node.items() if pd.notna(v) and v != ""}
                    cleaned_nodes.append(cleaned_node)
                
                save_json_file(GRAPH_NODES_FILE, cleaned_nodes)
        else:
            st.warning("Brak danych węzłów.")

    # --- EDGES ---
    with tab_edges:
        edges_data = load_json_file(GRAPH_EDGES_FILE)
        if edges_data:
            df_edges = pd.DataFrame(edges_data)
            
            column_config_edges = {
                "id": st.column_config.TextColumn("ID", disabled=True),
                "source_id": st.column_config.TextColumn("Source ID", required=True),
                "target_id": st.column_config.TextColumn("Target ID", required=True),
                "relationship_type": st.column_config.SelectboxColumn(
                    "Typ Relacji",
                    options=[
                        "PUBLISHED", "LINKS_TO", "HAS_PROFILE", "ORGANIZES", 
                        "SPEAKER_AT", "HAS_WEBSITE", "AFFILIATED_WITH", 
                        "WORKS_AT", "FEATURED_ON", "SHARES", "AUTHORED_BY", "ANNOUNCES"
                    ],
                    required=True
                ),
                "confidence": st.column_config.NumberColumn("Pewność (0-1)", min_value=0.0, max_value=1.0, step=0.1),
                "evidence": st.column_config.TextColumn("Dowód", width="large"),
            }
            
            st.markdown(f"**Liczba relacji:** {len(edges_data)}")
            
            edited_df_edges = st.data_editor(
                df_edges,
                column_config=column_config_edges,
                num_rows="dynamic",
                key="editor_edges",
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("💾 Zapisz zmiany (Edges)", key="save_edges"):
                updated_edges = edited_df_edges.to_dict(orient="records")
                cleaned_edges = []
                for edge in updated_edges:
                    cleaned_edge = {k: v for k, v in edge.items() if pd.notna(v) and v != ""}
                    cleaned_edges.append(cleaned_edge)
                
                save_json_file(GRAPH_EDGES_FILE, cleaned_edges)
        else:
            st.warning("Brak danych relacji.")


# ==========================================
# MAIN APP
# ==========================================

st.sidebar.title("🕵️‍♂️ RUSSINT")
app_mode = st.sidebar.radio("Tryb", ["Post Viewer", "Graph Editor"])

st.sidebar.markdown("---")

# Neo4j Sync Button in Sidebar
st.sidebar.markdown("### 🔄 Neo4j Sync")
if st.sidebar.button("🚀 Załaduj do Neo4j"):
    run_neo4j_sync()

st.sidebar.markdown("---")

if app_mode == "Post Viewer":
    render_post_viewer()
elif app_mode == "Graph Editor":
    render_graph_editor()

# Footer
st.sidebar.markdown("v1.1 | Graph Editor Enabled")
