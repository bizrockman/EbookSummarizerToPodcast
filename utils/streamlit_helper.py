import os
import streamlit as st
from streamlit_extras.buy_me_a_coffee import button as coffee_button

from utils.ebook_helper import load_epub, extract_toc, extract_chapter_content, display_toc

def escape_markdown(text):
    # Escape Dollarzeichen und andere spezielle Markdown-Zeichen
    text = text.replace("$", "\$")
    # Ersetze \n durch zwei Leerzeichen gefolgt von \n für korrekte Markdown Zeilenumbrüche
    # text = text.replace("\n", "  \n  \n")
    return text


def load_and_process_epub(uploaded_file):
    try:
        upload_dir = "uploads"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_path = os.path.join(upload_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        book = load_epub(file_path)
        toc = extract_toc(book)
        file_name = uploaded_file.name
        book_title = uploaded_file.name.split(".")[0]
        return book, toc, book_title, file_name
    except Exception as e:
        st.error(f"Datei kann nicht eingelesen werden: {str(e)}")
        return None, None


def draw_epub_loader():
    if 'book' not in st.session_state or 'toc' not in st.session_state:
        st.session_state.book = None
        st.session_state.toc = None
        st.session_state.book_title = None

    if st.session_state.book is None and st.session_state.toc is None:
        uploaded_file = st.file_uploader("Lade ein ePub hoch", type="epub")
        if uploaded_file:
            st.session_state.book, st.session_state.toc, st.session_state.book_title, st.session_state.file_name = (
                load_and_process_epub(uploaded_file))
            st.rerun()
    else:
        if st.session_state.file_name is not None:
            st.markdown(f"**{st.session_state.file_name}**")
        if st.button("Andere Datei hochladen"):
            st.session_state.book = None
            st.session_state.toc = None
            st.session_state.book_title = None
            st.rerun()


def is_api_key_valid(api_key):
    from openai import OpenAI, AuthenticationError
    client = OpenAI(api_key=api_key)
    try:
        client.models.list()
    except AuthenticationError as e:
        return False
    else:
        return True


def draw_sidebar():
    api_key = st.sidebar.text_input('Your OpenAI API Key:', type='password', key='api_key')
    if api_key and is_api_key_valid(api_key):
        os.environ['OPENAI_API_KEY'] = api_key
        st.sidebar.success('API key successfully set.')
        st.session_state.api_key_valid = True
    else:
        st.sidebar.error('Invalid OpenAI API key. Please provide a valid key.')
        st.session_state.api_key_valid = False

    st.sidebar.title("Optionen")
    st.sidebar.selectbox(
        "Modell",
        ("gpt-4o", "gpt-3.5-turbo"),
        index=1,
        key="model_name"
    )

    summary_length = st.sidebar.radio(
        "Zusammenfassungslänge",
        ("knapp", "mittel", "lang"),
        index=1
    )
    summary_length_map = {"knapp": 100, "mittel": 200, "lang": 300}
    summary_length_value = summary_length_map[summary_length]
    st.session_state.summary_length_value = summary_length_value

    st.sidebar.checkbox("Übersetzung", key="translate")
    if st.session_state.translate:
        st.sidebar.selectbox(
            "Zielsprache",
            ("de", "fr", "en", "it", "es", "nl", "ru"),
            key="target_language",
            index=1
        )
    else:
        st.session_state.target_language = None

    st.sidebar.checkbox("Podcast", key="podcast")
    if st.session_state.podcast:
        st.sidebar.selectbox(
            "Wähle eine Stimme",
            ("Alloy", "Echo", "Fable", "Onyx", "Nova", "Shimmer"),
            key="voice"
        )
        # if voice:
        #    st.sidebar.audio(f"sample_{voice.lower()}.mp3")
    else:
        st.session_state.voice = None

    st.sidebar.divider()
    st.sidebar.text("Created by:")
    st.sidebar.write("Danny Gerst")
    st.sidebar.write("[LinkedIn](https://www.linkedin.com/in/dannygerst/)")
    st.sidebar.write("[Twitter](https://twitter.com/gerstdanny/)")
    st.sidebar.write("[Website](https://www.dannygerst.de/)")
    with st.sidebar:
        coffee_button(username="dannygerst", floating=False)

    if 'main' in st.session_state and st.session_state.main:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Signup"):
                st.session_state.page = 'signup'
        with col2:
            if st.button("Login"):
                st.session_state.page = 'login'
