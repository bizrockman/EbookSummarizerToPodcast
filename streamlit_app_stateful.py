import streamlit as st

from dotenv import load_dotenv


# Funktion zur Anzeige der Hauptseite
def show_main_page():
    st.title("Hauptseite")
    if st.button("Signup"):
        st.session_state.page = 'signup'
    if st.button("Login"):
        st.session_state.page = 'login'
    if st.button("Tokens kaufen"):
        st.session_state.page = 'buy_tokens'


# Funktion zur Anzeige der Signup-Seite
def show_signup_page():
    st.title("Signup Seite")
    # Hier können Signup-Formulare und Logik hinzugefügt werden
    if st.button("Zurück zur Hauptseite"):
        st.session_state.page = 'main'


# Funktion zur Anzeige der Login-Seite
def show_login_page():
    st.title("Login Seite")
    # Hier können Login-Formulare und Logik hinzugefügt werden
    if st.button("Zurück zur Hauptseite"):
        st.session_state.page = 'main'


# Funktion zur Anzeige der Token-Kauf-Seite
def show_buy_tokens_page():
    st.title("Tokens kaufen")
    # Hier kann die Logik für den Token-Kauf hinzugefügt werden
    if st.button("Zurück zur Hauptseite"):
        st.session_state.page = 'main'


# Hauptlogik der Anwendung
def main():
    load_dotenv()
    # Initialisierung des Seitenzustands
    if 'page' not in st.session_state:
        st.session_state.page = 'main'

    # Anzeige der entsprechenden Seite basierend auf dem aktuellen Zustand
    if st.session_state.page == 'main':
        show_main_page()
    elif st.session_state.page == 'signup':
        show_signup_page()
    elif st.session_state.page == 'login':
        show_login_page()
    elif st.session_state.page == 'buy_tokens':
        show_buy_tokens_page()


if __name__ == "__main__":
    main()
