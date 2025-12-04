"""
RUSSINT - Manual Entry UI (Streamlit)
Aplikacja do ręcznego dodawania postów i przeglądania zebranych danych.
Zaprojektowana z myślą o analizie relacji i sieci dezinformacji.
"""

import streamlit as st
import json
import uuid
from datetime import datetime
from pathlib import Path
import pandas as pd

# Ścieżki
BASE_DIR = Path(__file__).parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
MANUAL_DIR = RAW_DIR / "manual"
FACEBOOK_DIR = RAW_DIR / "facebook"
ENTITIES_FILE = RAW_DIR / "graph_nodes.json"
RELATIONSHIPS_FILE = RAW_DIR / "graph_edges.json"

# Upewnij się, że katalogi istnieją
MANUAL_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="RUSSINT - Manual Entry",
    page_icon="📝",
    layout="wide"
)


def load_entities():
    """Wczytuje listę znanych podmiotów."""
    if ENTITIES_FILE.exists():
        with open(ENTITIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_entities(entities):
    """Zapisuje listę podmiotów."""
    with open(ENTITIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)


def get_entity_by_name(name, entities):
    """Znajdź podmiot po nazwie."""
    for e in entities:
        if e['name'].lower() == name.lower():
            return e
    return None


def load_relationships():
    """Wczytuje listę relacji."""
    if RELATIONSHIPS_FILE.exists():
        with open(RELATIONSHIPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_relationships(relationships):
    """Zapisuje listę relacji."""
    with open(RELATIONSHIPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(relationships, f, ensure_ascii=False, indent=2)


def create_entity(name, handle=None, platform="facebook", entity_type="page"):
    """Tworzy nowy podmiot."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "handle": handle or name,
        "platform": platform,
        "entity_type": entity_type,
        "url": f"https://www.facebook.com/{handle or name}" if platform == "facebook" else None,
        "category": None,
        "threat_level": None,
        "first_seen": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat()
    }


# Inicjalizacja session_state
if 'posts' not in st.session_state:
    st.session_state.posts = []
if 'profile_name' not in st.session_state:
    st.session_state.profile_name = ""
if 'profile_url' not in st.session_state:
    st.session_state.profile_url = ""
if 'entities' not in st.session_state:
    st.session_state.entities = load_entities()


def load_all_posts():
    """Wczytuje wszystkie posty z plików JSON (manual + facebook)."""
    all_posts = []
    
    # Wczytaj pliki z folderu manual
    for json_file in MANUAL_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                source = data.get('name', json_file.stem)
                for idx, post in enumerate(data.get('posts', [])):
                    post['_source'] = source
                    post['_file'] = str(json_file)  # Pełna ścieżka do edycji
                    post['_file_name'] = json_file.name
                    post['_post_index'] = idx
                    post['_type'] = 'manual'
                    all_posts.append(post)
        except Exception as e:
            st.warning(f"Błąd wczytywania {json_file.name}: {e}")
    
    # Wczytaj pliki z folderu facebook
    for json_file in FACEBOOK_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                source = data.get('handle', data.get('name', json_file.stem))
                for idx, post in enumerate(data.get('posts', [])):
                    post['_source'] = source
                    post['_file'] = str(json_file)  # Pełna ścieżka do edycji
                    post['_file_name'] = json_file.name
                    post['_post_index'] = idx
                    post['_type'] = 'scraped'
                    all_posts.append(post)
        except Exception as e:
            st.warning(f"Błąd wczytywania {json_file.name}: {e}")
    
    return all_posts


def update_post_in_file(file_path, post_index, updated_fields):
    """Aktualizuje post w pliku JSON."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'posts' in data and post_index < len(data['posts']):
            # Aktualizuj pola (bez metadanych wewnętrznych)
            for key, value in updated_fields.items():
                if not key.startswith('_'):
                    data['posts'][post_index][key] = value
            
            data['posts'][post_index]['updated_at'] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
    except Exception as e:
        st.error(f"Błąd aktualizacji: {e}")
        return False


def save_session():
    """Zapisuje aktualną sesję do pliku JSON."""
    if not st.session_state.posts:
        st.warning("Brak postów do zapisania!")
        return None
    
    profile_name = st.session_state.profile_name or "unknown"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"manual_{profile_name}_{timestamp}.json"
    output_path = MANUAL_DIR / filename
    
    data = {
        "name": st.session_state.profile_name,
        "url": st.session_state.profile_url,
        "scraped_at": datetime.now().isoformat(),
        "type": "manual_entry",
        "posts": st.session_state.posts
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_path


# ===== SIDEBAR =====
st.sidebar.title("📝 RUSSINT")
st.sidebar.markdown("### Manual Entry")

page = st.sidebar.radio(
    "Nawigacja",
    ["➕ Dodaj post", "📋 Przegląd postów", "👥 Podmioty", "🕸️ Relacje", "📁 Sesja"]
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Posty w sesji:** {len(st.session_state.posts)}")
st.sidebar.markdown(f"**Podmioty:** {len(st.session_state.entities)}")


# ===== STRONA: DODAJ POST =====
if page == "➕ Dodaj post":
    st.title("➕ Dodaj nowy post")
    
    # Lista znanych podmiotów do autouzupełniania
    entity_names = [e['name'] for e in st.session_state.entities]
    
    with st.form("add_post_form"):
        st.markdown("### 📌 Podstawowe informacje")
        
        col1, col2 = st.columns(2)
        
        with col1:
            post_url = st.text_input(
                "🔗 Link do posta (URL)",
                placeholder="https://www.facebook.com/.../posts/..."
            )
            
            post_date = st.text_input(
                "📅 Data posta",
                placeholder="np. 2025-11-24 lub '2 godz.' lub '3 tyg.'"
            )
            
            # Autor z możliwością wyboru z listy lub wpisania nowego
            author_option = st.selectbox(
                "👤 Autor (publikujący)",
                options=["-- Wpisz nowego --"] + entity_names,
                help="Kto opublikował/udostępnił ten post"
            )
            
            if author_option == "-- Wpisz nowego --":
                author = st.text_input("Nowy autor:", placeholder="Nazwa autora")
            else:
                author = author_option
        
        with col2:
            platform = st.selectbox(
                "🌐 Platforma",
                ["facebook", "telegram", "twitter", "vk", "youtube", "tiktok", "other"]
            )
            
            post_type = st.selectbox(
                "📝 Typ posta",
                ["original", "repost", "share", "quote"],
                help="original = własna treść, repost/share = udostępnienie cudzego"
            )
        
        # === SEKCJA REPOST ===
        st.markdown("---")
        st.markdown("### 🔄 Repost / Udostępnienie")
        
        is_repost = post_type in ["repost", "share", "quote"]
        
        if is_repost:
            col1, col2 = st.columns(2)
            
            with col1:
                original_author_option = st.selectbox(
                    "👤 Autor ORYGINALNEGO posta",
                    options=["-- Wpisz nowego --"] + entity_names,
                    help="Kto jest autorem oryginalnej treści"
                )
                
                if original_author_option == "-- Wpisz nowego --":
                    original_author = st.text_input(
                        "Nowy autor oryginału:",
                        placeholder="Nazwa oryginalnego autora"
                    )
                else:
                    original_author = original_author_option
            
            with col2:
                original_url = st.text_input(
                    "🔗 Link do oryginalnego posta",
                    placeholder="URL oryginalnego posta (jeśli dostępny)"
                )
                
                original_platform = st.selectbox(
                    "🌐 Platforma oryginału",
                    ["facebook", "telegram", "twitter", "vk", "youtube", "tiktok", "other"],
                    key="orig_platform"
                )
        else:
            original_author = None
            original_url = None
            original_platform = None
        
        # === SEKCJA LINKI ZEWNĘTRZNE ===
        st.markdown("---")
        st.markdown("### 🌐 Linki zewnętrzne")
        
        col1, col2 = st.columns(2)
        with col1:
            external_url = st.text_input(
                "Link zawarty w poście",
                placeholder="Link do artykułu, video, strony zewnętrznej"
            )
        with col2:
            external_description = st.text_input(
                "Opis linku",
                placeholder="np. 'Artykuł z sputniknews.com'"
            )
        
        # === TREŚĆ ===
        st.markdown("---")
        st.markdown("### 📝 Treść")
        
        text = st.text_area(
            "Treść posta",
            height=200,
            placeholder="Wklej tutaj pełną treść posta..."
        )
        
        # === MEDIA ===
        st.markdown("---")
        st.markdown("### 🖼️ Media")
        
        images = st.text_area(
            "Linki do zdjęć (jeden na linię)",
            placeholder="https://example.com/image1.jpg",
            height=80
        )
        
        videos = st.text_area(
            "Linki do video (jeden na linię)",
            placeholder="https://youtube.com/...",
            height=80
        )
        
        # === KLASYFIKACJA ===
        st.markdown("---")
        st.markdown("### 🏷️ Klasyfikacja")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            topics = st.text_input(
                "Tematy/Tagi",
                placeholder="wojna, dezinformacja, NATO (oddzielone przecinkiem)"
            )
        with col2:
            sentiment = st.selectbox(
                "Wydźwięk",
                ["neutral", "positive", "negative", "inflammatory"]
            )
        with col3:
            narrative = st.text_input(
                "Narracja",
                placeholder="np. 'NATO aggression', 'biolabs'"
            )
        
        # === NOTATKI ===
        notes = st.text_area(
            "📝 Notatki analityka",
            placeholder="Dodatkowe obserwacje, kontekst...",
            height=80
        )
        
        # === PRZYCISKI ===
        st.markdown("---")
        
        col_submit, col_clear = st.columns([1, 1])
        with col_submit:
            submitted = st.form_submit_button("✅ Dodaj post", use_container_width=True)
        with col_clear:
            clear = st.form_submit_button("🗑️ Wyczyść formularz", use_container_width=True)
        
        if submitted:
            if not text.strip():
                st.error("Treść posta jest wymagana!")
            elif not author:
                st.error("Autor jest wymagany!")
            else:
                # Przetwórz listy
                image_list = [img.strip() for img in images.split('\n') if img.strip()] if images else []
                video_list = [vid.strip() for vid in videos.split('\n') if vid.strip()] if videos else []
                topic_list = [t.strip() for t in topics.split(',') if t.strip()] if topics else []
                
                # Dodaj nowych autorów do listy podmiotów
                if author and author not in entity_names:
                    new_entity = create_entity(author, platform=platform)
                    st.session_state.entities.append(new_entity)
                    save_entities(st.session_state.entities)
                
                if is_repost and original_author and original_author not in entity_names:
                    new_entity = create_entity(original_author, platform=original_platform or platform)
                    st.session_state.entities.append(new_entity)
                    save_entities(st.session_state.entities)
                
                # Znajdź ID autorów
                author_entity = get_entity_by_name(author, st.session_state.entities)
                original_author_entity = get_entity_by_name(original_author, st.session_state.entities) if original_author else None
                
                # Utwórz obiekt posta
                post_obj = {
                    "id": str(uuid.uuid4()),
                    "platform": platform,
                    "url": post_url if post_url else None,
                    "text": text.strip(),
                    "date": post_date if post_date else None,
                    
                    # Autorstwo
                    "author": author,
                    "author_id": author_entity['id'] if author_entity else None,
                    
                    # Repost
                    "is_repost": is_repost,
                    "post_type": post_type,
                    "original_author": original_author if is_repost else None,
                    "original_author_id": original_author_entity['id'] if original_author_entity else None,
                    "original_url": original_url if is_repost else None,
                    "original_platform": original_platform if is_repost else None,
                    
                    # Linki zewnętrzne
                    "external_url": external_url if external_url else None,
                    "external_description": external_description if external_description else None,
                    
                    # Media
                    "images": image_list,
                    "videos": video_list,
                    
                    # Klasyfikacja
                    "topics": topic_list,
                    "sentiment": sentiment,
                    "narrative": narrative if narrative else None,
                    
                    # Metadane
                    "notes": notes if notes else None,
                    "collected_at": datetime.now().isoformat(),
                    "collection_method": "manual",
                }
                
                st.session_state.posts.append(post_obj)
                st.success(f"✅ Post dodany! (łącznie: {len(st.session_state.posts)})")
                
                if is_repost:
                    st.info(f"📊 Relacja: **{author}** → repostuje → **{original_author}**")
                
                st.rerun()


# ===== STRONA: PRZEGLĄD POSTÓW =====
elif page == "📋 Przegląd postów":
    st.title("📋 Przegląd postów")
    
    tab1, tab2 = st.tabs(["📌 Aktualna sesja", "📂 Wszystkie zebrane"])
    
    # --- Tab 1: Aktualna sesja ---
    with tab1:
        if not st.session_state.posts:
            st.info("Brak postów w aktualnej sesji. Przejdź do '➕ Dodaj post'.")
        else:
            st.markdown(f"**Liczba postów:** {len(st.session_state.posts)}")
            
            for i, post in enumerate(st.session_state.posts):
                repost_badge = "🔄 " if post.get('is_repost') else ""
                with st.expander(f"{repost_badge}Post #{i+1} | {post.get('date', 'brak daty')} | {post.get('author', 'N/A')[:30]}"):
                    
                    # Tryb edycji
                    edit_key = f"edit_mode_{i}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False
                    
                    col_view, col_actions = st.columns([3, 1])
                    
                    with col_actions:
                        if st.button("✏️ Edytuj", key=f"edit_btn_{i}"):
                            st.session_state[edit_key] = not st.session_state[edit_key]
                            st.rerun()
                        if st.button("🗑️ Usuń", key=f"delete_{i}"):
                            st.session_state.posts.pop(i)
                            st.rerun()
                    
                    with col_view:
                        if not st.session_state[edit_key]:
                            # TRYB PODGLĄDU
                            st.markdown(f"**Platforma:** {post.get('platform', 'N/A')}")
                            st.markdown(f"**Data:** {post.get('date', 'N/A')}")
                            st.markdown(f"**Autor:** {post.get('author', 'N/A')}")
                            
                            if post.get('is_repost'):
                                st.markdown(f"🔄 **REPOST od:** {post.get('original_author', 'N/A')}")
                                if post.get('original_url'):
                                    st.markdown(f"**Oryginalny post:** [{post['original_url'][:40]}...]({post['original_url']})")
                            
                            if post.get('url'):
                                st.markdown(f"**Link:** [{post['url'][:50]}...]({post['url']})")
                            if post.get('external_url'):
                                st.markdown(f"**Link zewnętrzny:** [{post['external_url'][:50]}...]({post['external_url']})")
                            
                            # Klasyfikacja
                            st.markdown("---")
                            st.markdown("**🏷️ Klasyfikacja:**")
                            topics_str = ', '.join(post.get('topics', [])) if post.get('topics') else '-'
                            st.markdown(f"- Tematy: `{topics_str}`")
                            st.markdown(f"- Wydźwięk: `{post.get('sentiment', '-')}`")
                            st.markdown(f"- Narracja: `{post.get('narrative', '-')}`")
                            
                            st.markdown("---")
                            st.markdown("**Treść:**")
                            st.text(post.get('text', '')[:500] + ('...' if len(post.get('text', '')) > 500 else ''))
                        
                        else:
                            # TRYB EDYCJI
                            st.markdown("### ✏️ Tryb edycji")
                            
                            # Podstawowe pola
                            new_date = st.text_input("Data", value=post.get('date', ''), key=f"ed_date_{i}")
                            new_url = st.text_input("URL posta", value=post.get('url', ''), key=f"ed_url_{i}")
                            
                            # Klasyfikacja
                            st.markdown("**🏷️ Klasyfikacja:**")
                            col_c1, col_c2, col_c3 = st.columns(3)
                            
                            with col_c1:
                                current_topics = ', '.join(post.get('topics', [])) if post.get('topics') else ''
                                new_topics = st.text_input(
                                    "Tematy/Tagi",
                                    value=current_topics,
                                    key=f"ed_topics_{i}",
                                    help="Oddziel przecinkiem"
                                )
                            
                            with col_c2:
                                sentiment_options = ["neutral", "positive", "negative", "inflammatory"]
                                current_sentiment = post.get('sentiment', 'neutral')
                                sentiment_idx = sentiment_options.index(current_sentiment) if current_sentiment in sentiment_options else 0
                                new_sentiment = st.selectbox(
                                    "Wydźwięk",
                                    sentiment_options,
                                    index=sentiment_idx,
                                    key=f"ed_sentiment_{i}"
                                )
                            
                            with col_c3:
                                new_narrative = st.text_input(
                                    "Narracja",
                                    value=post.get('narrative', '') or '',
                                    key=f"ed_narrative_{i}"
                                )
                            
                            # Repost
                            st.markdown("**🔄 Repost:**")
                            post_type_options = ["original", "repost", "share", "quote"]
                            current_post_type = post.get('post_type', 'original')
                            post_type_idx = post_type_options.index(current_post_type) if current_post_type in post_type_options else 0
                            new_post_type = st.selectbox(
                                "Typ posta",
                                post_type_options,
                                index=post_type_idx,
                                key=f"ed_posttype_{i}"
                            )
                            
                            if new_post_type in ["repost", "share", "quote"]:
                                new_original_author = st.text_input(
                                    "Autor oryginału",
                                    value=post.get('original_author', '') or '',
                                    key=f"ed_origauthor_{i}"
                                )
                                new_original_url = st.text_input(
                                    "URL oryginału",
                                    value=post.get('original_url', '') or '',
                                    key=f"ed_origurl_{i}"
                                )
                            else:
                                new_original_author = None
                                new_original_url = None
                            
                            # Notatki
                            new_notes = st.text_area(
                                "Notatki analityka",
                                value=post.get('notes', '') or '',
                                key=f"ed_notes_{i}"
                            )
                            
                            # Przyciski zapisu
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.button("💾 Zapisz zmiany", key=f"save_{i}", use_container_width=True):
                                    # Aktualizuj post
                                    st.session_state.posts[i]['date'] = new_date if new_date else None
                                    st.session_state.posts[i]['url'] = new_url if new_url else None
                                    st.session_state.posts[i]['topics'] = [t.strip() for t in new_topics.split(',') if t.strip()] if new_topics else []
                                    st.session_state.posts[i]['sentiment'] = new_sentiment
                                    st.session_state.posts[i]['narrative'] = new_narrative if new_narrative else None
                                    st.session_state.posts[i]['post_type'] = new_post_type
                                    st.session_state.posts[i]['is_repost'] = new_post_type in ["repost", "share", "quote"]
                                    st.session_state.posts[i]['original_author'] = new_original_author
                                    st.session_state.posts[i]['original_url'] = new_original_url
                                    st.session_state.posts[i]['notes'] = new_notes if new_notes else None
                                    st.session_state.posts[i]['updated_at'] = datetime.now().isoformat()
                                    
                                    st.session_state[edit_key] = False
                                    st.success("✅ Zapisano!")
                                    st.rerun()
                            
                            with col_cancel:
                                if st.button("❌ Anuluj", key=f"cancel_{i}", use_container_width=True):
                                    st.session_state[edit_key] = False
                                    st.rerun()
    
    # --- Tab 2: Wszystkie zebrane ---
    with tab2:
        all_posts = load_all_posts()
        
        if not all_posts:
            st.info("Brak zebranych postów w systemie.")
        else:
            # Filtry
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                sources = list(set(p.get('_source', 'Unknown') for p in all_posts))
                selected_source = st.selectbox("Źródło", ["Wszystkie"] + sources)
            with col2:
                types = list(set(p.get('_type', 'Unknown') for p in all_posts))
                selected_type = st.selectbox("Typ", ["Wszystkie"] + types)
            with col3:
                repost_filter = st.selectbox("Reposty", ["Wszystkie", "Tylko reposty", "Tylko oryginalne"])
            with col4:
                search_text = st.text_input("🔍 Szukaj w treści")
            
            # Filtr klasyfikacji
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                classify_filter = st.selectbox(
                    "Status klasyfikacji",
                    ["Wszystkie", "Nieklasyfikowane", "Sklasyfikowane"]
                )
            with col_f2:
                sentiment_filter = st.selectbox(
                    "Wydźwięk",
                    ["Wszystkie", "neutral", "positive", "negative", "inflammatory"]
                )
            
            # Filtrowanie
            filtered = all_posts
            if selected_source != "Wszystkie":
                filtered = [p for p in filtered if p.get('_source') == selected_source]
            if selected_type != "Wszystkie":
                filtered = [p for p in filtered if p.get('_type') == selected_type]
            if repost_filter == "Tylko reposty":
                filtered = [p for p in filtered if p.get('is_repost')]
            elif repost_filter == "Tylko oryginalne":
                filtered = [p for p in filtered if not p.get('is_repost')]
            if classify_filter == "Nieklasyfikowane":
                filtered = [p for p in filtered if not p.get('topics') and not p.get('narrative')]
            elif classify_filter == "Sklasyfikowane":
                filtered = [p for p in filtered if p.get('topics') or p.get('narrative')]
            if sentiment_filter != "Wszystkie":
                filtered = [p for p in filtered if p.get('sentiment') == sentiment_filter]
            if search_text:
                filtered = [p for p in filtered if search_text.lower() in p.get('text', '').lower()]
            
            st.markdown(f"**Wyniki:** {len(filtered)} postów")
            
            # Wyświetlanie
            for i, post in enumerate(filtered[:50]):  # Limit 50
                repost_badge = "🔄 " if post.get('is_repost') else ""
                classified_badge = "🏷️ " if post.get('topics') or post.get('narrative') else "⚪ "
                unique_key = f"all_{post.get('_file_name', '')}_{post.get('_post_index', i)}_{i}"
                
                with st.expander(f"{classified_badge}{repost_badge}{post.get('_source', 'N/A')} | {post.get('date', 'brak daty')} | {post.get('text', '')[:50]}..."):
                    
                    # Tryb edycji
                    edit_key_all = f"edit_mode_all_{unique_key}"
                    if edit_key_all not in st.session_state:
                        st.session_state[edit_key_all] = False
                    
                    col_view, col_actions = st.columns([3, 1])
                    
                    with col_actions:
                        if st.button("✏️ Edytuj klasyfikację", key=f"edit_all_{unique_key}"):
                            st.session_state[edit_key_all] = not st.session_state[edit_key_all]
                            st.rerun()
                    
                    with col_view:
                        st.markdown(f"**Źródło:** {post.get('_source', 'N/A')} ({post.get('_type', 'N/A')})")
                        st.markdown(f"**Plik:** `{post.get('_file_name', 'N/A')}`")
                        st.markdown(f"**Data:** {post.get('date', 'N/A')}")
                        st.markdown(f"**Autor:** {post.get('author', 'N/A')}")
                        
                        if post.get('is_repost'):
                            st.markdown(f"🔄 **REPOST od:** {post.get('original_author', 'N/A')}")
                        
                        if post.get('url'):
                            st.markdown(f"**Link:** [Otwórz]({post['url']})")
                        
                        # Klasyfikacja - podgląd
                        st.markdown("---")
                        st.markdown("**🏷️ Klasyfikacja:**")
                        topics_str = ', '.join(post.get('topics', [])) if post.get('topics') else '-'
                        st.markdown(f"- Tematy: `{topics_str}`")
                        st.markdown(f"- Wydźwięk: `{post.get('sentiment', '-')}`")
                        st.markdown(f"- Narracja: `{post.get('narrative', '-')}`")
                        
                        st.markdown("---")
                        st.markdown("**Treść:**")
                        st.text(post.get('text', '')[:1000])
                        
                        if post.get('images'):
                            st.markdown("**Zdjęcia:**")
                            for img in post['images'][:3]:
                                st.markdown(f"- [{img[:50]}...]({img})")
                    
                    # PANEL EDYCJI
                    if st.session_state[edit_key_all]:
                        st.markdown("---")
                        st.markdown("### ✏️ Edycja klasyfikacji")
                        
                        col_e1, col_e2, col_e3 = st.columns(3)
                        
                        with col_e1:
                            current_topics = ', '.join(post.get('topics', [])) if post.get('topics') else ''
                            new_topics_all = st.text_input(
                                "Tematy/Tagi",
                                value=current_topics,
                                key=f"ed_all_topics_{unique_key}",
                                help="Oddziel przecinkiem"
                            )
                        
                        with col_e2:
                            sentiment_opts = ["neutral", "positive", "negative", "inflammatory"]
                            curr_sent = post.get('sentiment', 'neutral')
                            sent_idx = sentiment_opts.index(curr_sent) if curr_sent in sentiment_opts else 0
                            new_sentiment_all = st.selectbox(
                                "Wydźwięk",
                                sentiment_opts,
                                index=sent_idx,
                                key=f"ed_all_sentiment_{unique_key}"
                            )
                        
                        with col_e3:
                            new_narrative_all = st.text_input(
                                "Narracja",
                                value=post.get('narrative', '') or '',
                                key=f"ed_all_narrative_{unique_key}"
                            )
                        
                        # Repost
                        col_r1, col_r2 = st.columns(2)
                        with col_r1:
                            pt_opts = ["original", "repost", "share", "quote"]
                            curr_pt = post.get('post_type', 'original')
                            pt_idx = pt_opts.index(curr_pt) if curr_pt in pt_opts else 0
                            new_pt_all = st.selectbox(
                                "Typ posta",
                                pt_opts,
                                index=pt_idx,
                                key=f"ed_all_pt_{unique_key}"
                            )
                        
                        with col_r2:
                            if new_pt_all in ["repost", "share", "quote"]:
                                new_orig_auth_all = st.text_input(
                                    "Autor oryginału",
                                    value=post.get('original_author', '') or '',
                                    key=f"ed_all_origauth_{unique_key}"
                                )
                            else:
                                new_orig_auth_all = None
                        
                        new_notes_all = st.text_area(
                            "Notatki analityka",
                            value=post.get('notes', '') or '',
                            key=f"ed_all_notes_{unique_key}",
                            height=80
                        )
                        
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            if st.button("💾 Zapisz zmiany", key=f"save_all_{unique_key}", use_container_width=True):
                                updated_fields = {
                                    'topics': [t.strip() for t in new_topics_all.split(',') if t.strip()] if new_topics_all else [],
                                    'sentiment': new_sentiment_all,
                                    'narrative': new_narrative_all if new_narrative_all else None,
                                    'post_type': new_pt_all,
                                    'is_repost': new_pt_all in ["repost", "share", "quote"],
                                    'original_author': new_orig_auth_all,
                                    'notes': new_notes_all if new_notes_all else None
                                }
                                
                                file_path = post.get('_file')
                                post_index = post.get('_post_index', 0)
                                
                                if update_post_in_file(file_path, post_index, updated_fields):
                                    st.session_state[edit_key_all] = False
                                    st.success("✅ Zapisano do pliku!")
                                    st.rerun()
                        
                        with col_s2:
                            if st.button("❌ Anuluj", key=f"cancel_all_{unique_key}", use_container_width=True):
                                st.session_state[edit_key_all] = False
                                st.rerun()


# ===== STRONA: PODMIOTY =====
elif page == "👥 Podmioty":
    st.title("👥 Zarządzanie podmiotami")
    
    tab1, tab2 = st.tabs(["📋 Lista podmiotów", "➕ Dodaj podmiot"])
    
    with tab1:
        if not st.session_state.entities:
            st.info("Brak zarejestrowanych podmiotów.")
        else:
            # Filtry
            col1, col2 = st.columns(2)
            with col1:
                platforms = list(set(e.get('platform', 'unknown') for e in st.session_state.entities))
                filter_platform = st.selectbox("Platforma", ["Wszystkie"] + platforms)
            with col2:
                types = list(set(e.get('entity_type', 'unknown') for e in st.session_state.entities))
                filter_type = st.selectbox("Typ", ["Wszystkie"] + types)
            
            filtered_entities = st.session_state.entities
            if filter_platform != "Wszystkie":
                filtered_entities = [e for e in filtered_entities if e.get('platform') == filter_platform]
            if filter_type != "Wszystkie":
                filtered_entities = [e for e in filtered_entities if e.get('entity_type') == filter_type]
            
            st.markdown(f"**Liczba:** {len(filtered_entities)}")
            
            # Tabela
            df_data = []
            for e in filtered_entities:
                df_data.append({
                    "Nazwa": e.get('name', 'N/A'),
                    "Handle": e.get('handle', 'N/A'),
                    "Platforma": e.get('platform', 'N/A'),
                    "Typ": e.get('entity_type', 'N/A'),
                    "Kategoria": e.get('category', '-'),
                    "Threat": e.get('threat_level', '-')
                })
            
            if df_data:
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            
            # Szczegóły
            st.markdown("---")
            selected_entity = st.selectbox(
                "Wybierz podmiot do edycji",
                options=[e['name'] for e in filtered_entities]
            )
            
            if selected_entity:
                entity = get_entity_by_name(selected_entity, st.session_state.entities)
                if entity:
                    col1, col2 = st.columns(2)
                    with col1:
                        new_category = st.selectbox(
                            "Kategoria",
                            ["", "pro-kremlin", "alternative_media", "political", "activist", "bot_network", "state_media", "unknown"],
                            index=0 if not entity.get('category') else ["", "pro-kremlin", "alternative_media", "political", "activist", "bot_network", "state_media", "unknown"].index(entity.get('category', ''))
                        )
                    with col2:
                        new_threat = st.selectbox(
                            "Poziom zagrożenia",
                            ["", "low", "medium", "high", "critical"],
                            index=0 if not entity.get('threat_level') else ["", "low", "medium", "high", "critical"].index(entity.get('threat_level', ''))
                        )
                    
                    if st.button("💾 Zapisz zmiany"):
                        entity['category'] = new_category if new_category else None
                        entity['threat_level'] = new_threat if new_threat else None
                        entity['updated_at'] = datetime.now().isoformat()
                        save_entities(st.session_state.entities)
                        st.success("Zapisano!")
                        st.rerun()
    
    with tab2:
        with st.form("add_entity_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Nazwa", placeholder="Braterstwa Ludzi Wolnych")
                new_handle = st.text_input("Handle/Slug", placeholder="BraterstwaLudziWolnych")
                new_platform = st.selectbox("Platforma", ["facebook", "telegram", "twitter", "vk", "youtube", "tiktok", "other"])
            
            with col2:
                new_type = st.selectbox("Typ", ["page", "person", "organization", "group", "channel", "bot", "unknown"])
                new_url = st.text_input("URL profilu", placeholder="https://...")
                new_category = st.selectbox("Kategoria", ["", "pro-kremlin", "alternative_media", "political", "activist", "bot_network", "state_media", "unknown"])
            
            new_notes = st.text_area("Notatki", placeholder="Dodatkowe informacje...")
            
            if st.form_submit_button("➕ Dodaj podmiot", use_container_width=True):
                if not new_name:
                    st.error("Nazwa jest wymagana!")
                else:
                    new_entity = {
                        "id": str(uuid.uuid4()),
                        "name": new_name,
                        "handle": new_handle if new_handle else new_name,
                        "platform": new_platform,
                        "entity_type": new_type,
                        "url": new_url if new_url else None,
                        "category": new_category if new_category else None,
                        "threat_level": None,
                        "notes": new_notes if new_notes else None,
                        "first_seen": datetime.now().isoformat(),
                        "created_at": datetime.now().isoformat()
                    }
                    st.session_state.entities.append(new_entity)
                    save_entities(st.session_state.entities)
                    st.success(f"Dodano podmiot: {new_name}")
                    st.rerun()


# ===== STRONA: RELACJE =====
elif page == "🕸️ Relacje":
    st.title("🕸️ Analiza relacji")
    
    # Zbierz relacje z postów
    all_posts = load_all_posts() + st.session_state.posts
    
    relationships = []
    for post in all_posts:
        if post.get('is_repost') and post.get('author') and post.get('original_author'):
            relationships.append({
                "source": post['author'],
                "target": post['original_author'],
                "type": "REPOSTS",
                "post_date": post.get('date', 'N/A'),
                "platform": post.get('platform', 'N/A')
            })
    
    if not relationships:
        st.info("Brak zarejestrowanych relacji. Dodaj posty z repostami, aby zobaczyć sieć.")
    else:
        st.markdown(f"**Znaleziono {len(relationships)} relacji repostowania**")
        
        # Agregacja
        from collections import Counter
        relation_counts = Counter((r['source'], r['target']) for r in relationships)
        
        st.markdown("### 📊 Podsumowanie relacji")
        
        df_rel = []
        for (source, target), count in relation_counts.most_common(20):
            df_rel.append({
                "Źródło (repostuje)": source,
                "Cel (oryginalny autor)": target,
                "Liczba repostów": count
            })
        
        if df_rel:
            st.dataframe(pd.DataFrame(df_rel), use_container_width=True)
        
        # Eksport do Gephi
        st.markdown("---")
        st.markdown("### 📤 Eksport")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Nodes
            nodes = set()
            for r in relationships:
                nodes.add(r['source'])
                nodes.add(r['target'])
            
            nodes_csv = "Id,Label,Type\n"
            for node in nodes:
                entity = get_entity_by_name(node, st.session_state.entities)
                node_type = entity.get('entity_type', 'unknown') if entity else 'unknown'
                nodes_csv += f"{node},{node},{node_type}\n"
            
            st.download_button(
                "⬇️ Nodes (CSV dla Gephi)",
                data=nodes_csv,
                file_name="russint_nodes.csv",
                mime="text/csv"
            )
        
        with col2:
            # Edges
            edges_csv = "Source,Target,Type,Weight\n"
            for (source, target), count in relation_counts.items():
                edges_csv += f"{source},{target},REPOSTS,{count}\n"
            
            st.download_button(
                "⬇️ Edges (CSV dla Gephi)",
                data=edges_csv,
                file_name="russint_edges.csv",
                mime="text/csv"
            )


# ===== STRONA: SESJA =====
elif page == "📁 Sesja":
    st.title("📁 Zarządzanie sesją")
    
    st.markdown("### Konfiguracja profilu")
    
    col1, col2 = st.columns(2)
    with col1:
        new_profile_name = st.text_input(
            "Nazwa profilu",
            value=st.session_state.profile_name,
            placeholder="np. BraterstwaLudziWolnych"
        )
        if new_profile_name != st.session_state.profile_name:
            st.session_state.profile_name = new_profile_name
    
    with col2:
        new_profile_url = st.text_input(
            "URL profilu",
            value=st.session_state.profile_url,
            placeholder="https://www.facebook.com/..."
        )
        if new_profile_url != st.session_state.profile_url:
            st.session_state.profile_url = new_profile_url
    
    st.markdown("---")
    st.markdown("### Akcje")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Zapisz sesję", use_container_width=True):
            if not st.session_state.profile_name:
                st.error("Podaj nazwę profilu przed zapisaniem!")
            else:
                output_path = save_session()
                if output_path:
                    st.success(f"✅ Zapisano do: `{output_path.name}`")
                    # Wyczyść sesję po zapisaniu
                    st.session_state.posts = []
    
    with col2:
        if st.button("🗑️ Wyczyść sesję", use_container_width=True):
            st.session_state.posts = []
            st.success("Sesja wyczyszczona!")
            st.rerun()
    
    with col3:
        if st.button("📥 Eksport JSON", use_container_width=True):
            if st.session_state.posts:
                data = {
                    "name": st.session_state.profile_name,
                    "url": st.session_state.profile_url,
                    "posts": st.session_state.posts
                }
                st.download_button(
                    label="⬇️ Pobierz JSON",
                    data=json.dumps(data, ensure_ascii=False, indent=2),
                    file_name=f"export_{st.session_state.profile_name}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
            else:
                st.warning("Brak postów do eksportu!")
    
    st.markdown("---")
    st.markdown("### Podsumowanie sesji")
    
    if st.session_state.posts:
        st.markdown(f"- **Posty:** {len(st.session_state.posts)}")
        st.markdown(f"- **Profil:** {st.session_state.profile_name or 'nie ustawiony'}")
        
        # Tabela podglądowa
        df_data = []
        for p in st.session_state.posts:
            df_data.append({
                "Data": p.get('date', 'N/A'),
                "Autor": p.get('author', 'N/A'),
                "Treść (początek)": p.get('text', '')[:80] + "..."
            })
        
        if df_data:
            st.dataframe(pd.DataFrame(df_data), use_container_width=True)
    else:
        st.info("Sesja jest pusta.")


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("*RUSSINT v0.1*")
