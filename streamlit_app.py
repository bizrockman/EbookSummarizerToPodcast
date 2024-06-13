import os
import time
import base64
from dotenv import load_dotenv
import streamlit as st

from utils.ebook_helper import extract_chapter_content
from utils.summarizer import summarize
from utils.translator import translate_content
from utils.streamlit_helper import escape_markdown, draw_sidebar, draw_epub_loader
from utils.tts_helper import get_speech_from_text, generate_podcast
from langchain_community.callbacks.openai_info import get_openai_token_cost_for_model


def display_chapter_selection(toc):
    st.header("Kapitel Auswahl")

    if 'select_all' not in st.session_state:
        st.session_state.select_all = None

    if st.button("Alle auswählen"):
        for i in range(len(toc)):
            st.session_state[f'checkbox_{i}'] = True

    if st.button("Alle abwählen"):
        for i in range(len(toc)):
            st.session_state[f'checkbox_{i}'] = False

    st.subheader(st.session_state.book_title)
    selected_chapters = []
    seen_pages = set()

    for i, (chapter_title, chapter_href) in enumerate(toc):
        page = chapter_href.split('#')[0]  # Extrahiere den Seitenpfad ohne Anker
        if page in seen_pages:
            continue  # Überspringe Kapitel, die bereits berücksichtigt wurden
        seen_pages.add(page)

        if f'checkbox_{i}' not in st.session_state:
            if 'selected_chapters' in st.session_state and (i, chapter_title, chapter_href) in st.session_state.selected_chapters:
                st.session_state[f'checkbox_{i}'] = True
            else:
                st.session_state[f'checkbox_{i}'] = False

        checked = st.session_state[f'checkbox_{i}']

        if st.checkbox(chapter_title, value=checked, key=f'checkbox_{i}'):
            selected_chapters.append((i, chapter_title, chapter_href))

    return selected_chapters


def draw_main_app():
    st.title("ePub Zusammenfassung und Übersetzung")

    # try:
    draw_epub_loader()

    st.session_state.summarization_done = False
    book = st.session_state.book
    toc = st.session_state.toc
    book_title = st.session_state.book_title

    chapter_selection_container = st.empty()

    if 'button_clicked' in st.session_state and st.session_state.button_clicked and toc:
        st.session_state.button_clicked = False
        if len(st.session_state.selected_chapters) == 0:
            st.error("Keine Kapitel ausgewählt")
            return

        progress_bar = st.progress(0)
        log = st.empty()
        total_chapters = len(st.session_state.selected_chapters)

        all_summaries = []
        all_summary_costs = 0
        all_translation_costs = 0
        final_summaries = []
        final_translated_summaries = []

        with st.spinner("Fasse Kapitel zusammen..."):
            for i, (j, chapter_title, chapter_href) in enumerate(st.session_state.selected_chapters):
                progress = (i + 1) / total_chapters
                progress_bar.progress(progress)
                log.write(f"Verarbeite Kapitel ({i + 1}/{total_chapters}): " + chapter_title)
                chapter_content = extract_chapter_content(book, chapter_href)

                summary_data = summarize(chapter_content, model_name=st.session_state.model_name,
                                         summary_length=st.session_state.summary_length_value)
                summaries = summary_data['summaries']
                final_summary = summary_data['final_summary']
                input_tokens = summary_data['input_tokens']
                output_tokens = summary_data['output_tokens']
                input_cost = get_openai_token_cost_for_model(st.session_state.model_name, input_tokens,
                                                             is_completion=False)
                output_cost = get_openai_token_cost_for_model(st.session_state.model_name, output_tokens,
                                                              is_completion=True)
                cost = input_cost + output_cost

                all_summary_costs += cost
                all_summaries.extend(summaries)
                final_summaries.append((chapter_title, final_summary, cost))
        st.session_state.summarization_done = True

        if st.session_state.translate:
            progress_bar.progress(0)
            with st.spinner("Übersetze Kapitel..."):
                for i, (chapter_title, final_summary, summary_cost) in enumerate(final_summaries):
                    progress = (i + 1) / total_chapters
                    progress_bar.progress(progress)
                    log.write(f"Verarbeite Kapitel ({i + 1}/{total_chapters}): " + chapter_title)

                    translation_data = translate_content(final_summary,
                                                         target_language=st.session_state.target_language)
                    translations = translation_data['translations']
                    translation_input_tokens = translation_data['input_tokens']
                    translation_output_tokens = translation_data['output_tokens']
                    input_cost = get_openai_token_cost_for_model(st.session_state.model_name, translation_input_tokens,
                                                                 is_completion=False)
                    output_cost = get_openai_token_cost_for_model(st.session_state.model_name,
                                                                  translation_output_tokens,
                                                                  is_completion=True)
                    all_translation_costs += input_cost + output_cost

                    translated_chapter_title_data = translate_content([chapter_title],
                                                                      target_language=st.session_state.target_language)
                    translated_chapter_title = translated_chapter_title_data['translations']
                    translation_input_tokens = translated_chapter_title_data['input_tokens']
                    translation_output_tokens = translated_chapter_title_data['output_tokens']
                    input_cost = get_openai_token_cost_for_model(st.session_state.model_name, translation_input_tokens,
                                                                 is_completion=False)
                    output_cost = get_openai_token_cost_for_model(st.session_state.model_name,
                                                                  translation_output_tokens,
                                                                  is_completion=True)
                    cost = input_cost + output_cost
                    all_translation_costs += cost

                    final_translated_summaries.append((translated_chapter_title, translations, cost))
            st.session_state.translation_done = True

        if 'voice' in st.session_state and 'podcast' in st.session_state and st.session_state.podcast:
            with st.spinner("Erzeuge Podcast..."):
                voice = st.session_state.voice
                podcast_data = generate_podcast(final_translated_summaries if st.session_state.translate
                                           else final_summaries, podcast_filename=st.session_state.book_title,
                                                voice=voice.lower())
            st.audio(podcast_data['output_file'])
            with open(podcast_data['output_file'], "rb") as file:
                file_bytes = file.read()
                b64 = base64.b64encode(file_bytes).decode()

            href = (f'<a href="data:file/mp3;base64,{b64}" '
                    f'download="{st.session_state.book_title}.mp3">Download Podcast</a>')
            st.markdown(href, unsafe_allow_html=True)

        st.markdown(escape_markdown(f"Zusammenfassung - Gesamtkosten: {all_summary_costs:.2f} USD"))
        if st.session_state.translate:
            st.markdown(escape_markdown(f"Übersetzung - Gesamtkosten: {all_translation_costs:.2f} USD"))
        if 'voice' in st.session_state and 'podcast' in st.session_state and st.session_state.podcast:
            st.markdown(escape_markdown(f"Podcast - Gesamtkosten: {podcast_data['cost']:.2f} USD"))

        st.subheader(st.session_state.book_title)
        if st.session_state.translate:
            for translated_chapter_title, translation, cost in final_translated_summaries:
                st.markdown(escape_markdown(translated_chapter_title))
                st.markdown(escape_markdown(translation))
        else:
            for chapter_title, final_summary, cost in final_summaries:
                st.markdown(escape_markdown(chapter_title))
                st.markdown(escape_markdown(final_summary))

        with st.expander("Zwischenschritte", expanded=False):
            st.markdown(escape_markdown("\n\n".join(all_summaries)))
    else:
        if toc:
            with chapter_selection_container.container():
                if 'toc' in st.session_state:
                    selected_chapters = display_chapter_selection(st.session_state.toc)
                    st.session_state.selected_chapters = selected_chapters
            st.session_state.chapter_select_clicked = False

    if st.button("Erstellen"):
        st.session_state.button_clicked = True
        chapter_selection_container.empty()
        st.rerun()

    if 'summarization_done' in st.session_state and st.session_state.summarization_done:
        if st.button("Kapitelauswahl"):
            st.session_state.chapter_select_clicked = True
            st.rerun()


def main():
    load_dotenv()
    # Making Sidebar and Main Area Container that can be set to empty before showing other pages
    draw_sidebar()
    draw_main_app()


if __name__ == '__main__':
    main()
