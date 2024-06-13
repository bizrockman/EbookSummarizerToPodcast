from datetime import datetime
from collections.abc import Iterable
from utils.disk_cache import cache_with_disk

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate


@cache_with_disk()
def translate_content(content, target_language='de'):
    translation_prompt_template = """
    Translate the following text from English to German. Translate that it make a lot of sense in German, do not 
    approach it too literally.:    
    {text}    
    """

    translation_prompt = PromptTemplate(template=translation_prompt_template, input_variables=["text"])

    # Define the LLMs
    translate_llm = ChatOpenAI(temperature=0, model_name='gpt-4o')
    translate_llm_chain = translation_prompt | translate_llm

    if isinstance(content, str):
        translate_llm_chain_input = [{'text': content}]
    elif isinstance(content, Iterable):
        translate_llm_chain_input = [{'text': t} for t in content]
    else:
        raise TypeError("Content must be a string or an iterable of strings")

    # Run the input through the LLM chain (works in parallel)
    translate_llm_chain_results = translate_llm_chain.batch(translate_llm_chain_input)

    stage_translations = [e.content for e in translate_llm_chain_results]
    stage_translations = '\n'.join(stage_translations)

    translation_input_tokens = sum(
        [e.response_metadata.get("token_usage").get("prompt_tokens") for e in translate_llm_chain_results])
    translation_output_tokens = sum(
        [e.response_metadata.get("token_usage").get("completion_tokens") for e in translate_llm_chain_results])
    print(f'Translation done time {datetime.now()}')

    return {
        'translations': stage_translations,
        'input_tokens': translation_input_tokens,
        'output_tokens': translation_output_tokens
    }
