from dotenv import load_dotenv
import warnings

from utils.ebook_helper import load_epub, extract_toc, extract_chapter_content, display_toc
from utils.summarizer import summarize
from utils.translator import translate_content
from utils.tts_helper import get_speech_from_text

from langchain_community.callbacks.openai_info import get_openai_token_cost_for_model

warnings.filterwarnings("ignore", category=FutureWarning, module='ebooklib')


def main():
    load_dotenv()
    # Beispielnutzung
    # model_name = 'gpt-4o'
    model_name = 'gpt-3.5-turbo'
    summary_length = 250
    file_path = 'Blitzscaling.epub'
    book = load_epub(file_path)
    toc = extract_toc(book)

    print("Inhaltsverzeichnis:")
    display_toc(toc)

    if toc:
        chapter_title, chapter_href = toc[6]
        print(f"\nInhalt von '{chapter_title}':")
        chapter_content = extract_chapter_content(book, chapter_href)
        print(chapter_content[:1000])  # Nur die ersten 1000 Zeichen anzeigen

        summary_data = summarize(chapter_content, model_name=model_name, summary_length=summary_length)
        summaries = summary_data['summaries']
        input_tokens = summary_data['input_tokens']
        output_tokens = summary_data['output_tokens']
        input_cost = get_openai_token_cost_for_model(model_name, input_tokens, is_completion=False)
        output_cost = get_openai_token_cost_for_model(model_name, output_tokens, is_completion=True)
        cost = input_cost + output_cost
        print(f"Zusammenfassung Kapitel '{chapter_title}' - Kosten: {cost} USD")
        print(summary_data['final_summary'])
        exit()
        translation_data = translate_content(summaries)
        translations = translation_data['translations']
        translation_input_tokens = translation_data['input_tokens']
        translation_output_tokens = translation_data['output_tokens']
        input_cost = get_openai_token_cost_for_model(model_name, translation_input_tokens, is_completion=False)
        output_cost = get_openai_token_cost_for_model(model_name, translation_output_tokens, is_completion=True)
        cost = input_cost + output_cost
        translated_chapter_title_data = translate_content(chapter_title)
        translated_chapter_title = translated_chapter_title_data['translations']
        translation_input_tokens = translated_chapter_title_data['input_tokens']
        translation_output_tokens = translated_chapter_title_data['output_tokens']
        input_cost = get_openai_token_cost_for_model(model_name, translation_input_tokens, is_completion=False)
        output_cost = get_openai_token_cost_for_model(model_name, translation_output_tokens, is_completion=True)
        cost += input_cost + output_cost
        print(f"Übersetzung der Zusammenfassung - Kosten: {cost} USD")

        #combine all text in stage_3_translation in a final translated summary
        translated_final_summary = "\n\n".join(translations)
        translated_chapter = "".join(translated_chapter_title)
        translated_final_summary_w_title = f"{translated_chapter}\n\n{translated_final_summary}"

        print(translated_final_summary_w_title)
        # get_speech_from_text(translated_final_summary_w_title)


if __name__ == '__main__':
    main()
