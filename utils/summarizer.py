import time
from datetime import datetime
from utils.disk_cache import cache_with_disk
import numpy as np

from langchain_core.prompts import PromptTemplate
from langchain.docstore.document import Document
from langchain.chains.summarize.chain import load_summarize_chain
from langchain_community.callbacks.openai_info import OpenAICallbackHandler

import matplotlib.pyplot as plt

from utils.langchain_helper import get_chat_llm, get_llm_model_provider
from utils.text_helper import get_chunks_text
from utils.network_helper import get_topics
from utils.nlp_helper import get_similarity_matrix


def parse_title_summary_results(results):
    out = []
    for e in results:
        e = e.replace('\n', '')
        if '|' in e:
            processed = {'title': e.split('|')[0],
                         'summary': e.split('|')[1][1:]
                         }
        elif ':' in e:
            processed = {'title': e.split(':')[0],
                         'summary': e.split(':')[1][1:]
                         }
        elif '-' in e:
            processed = {'title': e.split('-')[0],
                         'summary': e.split('-')[1][1:]
                         }
        else:
            processed = {'title': '',
                         'summary': e
                         }
        out.append(processed)
    return out


@cache_with_disk()
def _summarize_stage_1(chunks_text, model_name=None):
    print(f'Start time: {datetime.now()}')

    # Prompt to get title and summary for each chunk
    map_prompt_template = """Firstly, give the following text an informative title. Then, on a new line, write a 75-100 
    word summary of the following text:
    
  {text}

  Return your answer in the following format:
  Title | Summary...
  e.g. 
  Why Artificial Intelligence is Good | AI can make humans more productive by automating many repetitive processes.

  TITLE AND CONCISE SUMMARY:"""

    map_prompt = PromptTemplate(template=map_prompt_template, input_variables=["text"])

    # Define the LLMs
    map_llm = get_chat_llm(model_name=model_name)
    map_llm_chain = map_prompt | map_llm
    map_llm_chain_input = [{'text': t} for t in chunks_text]
    # Run the input through the LLM chain (works in parallel)
    try:
        map_llm_chain_results = map_llm_chain.batch(map_llm_chain_input)
    except Exception as e:
        print(e)
        print("Try single threaded")
        map_llm_chain_results = []
        for llm_chain_input in map_llm_chain_input:
            time.sleep(0.5)
            result = map_llm_chain.invoke(llm_chain_input)
            map_llm_chain_results.append(result)

    stage_1_outputs = parse_title_summary_results([e.content for e in map_llm_chain_results])
    stage_1_input_tokens = sum([e.response_metadata.get("token_usage").get("prompt_tokens") for e in map_llm_chain_results])
    stage_1_output_tokens = sum([e.response_metadata.get("token_usage").get("completion_tokens") for e in map_llm_chain_results])

    return {
        'stage_1_outputs': stage_1_outputs,
        'stage_1_input_tokens': stage_1_input_tokens,
        'stage_1_output_tokens': stage_1_output_tokens
    }


@cache_with_disk()
def _summarize_stage_2(stage_1_outputs, topics, model_name, summary_num_words=250):
    print(f'Stage 2 start time {datetime.now()}')

    # Prompt that passes in all the titles of a topic, and asks for an overall title of the topic
    title_prompt_template = """Write an informative title that summarizes each of the following groups of titles. Make sure that the titles capture as much information as possible, 
  and are different from each other:
  {text}

  Return your answer in a numbered list, with new line separating each title: 
  1. Title 1
  2. Title 2
  3. Title 3

  TITLES:
  """

    map_prompt_template = """Write a 75-100 word summary of the following text. Do not start your answer with the text:
    {text}

    CONCISE SUMMARY:"""

    combine_prompt_template = 'Write a ' + str(summary_num_words) + """-word summary of the following, removing 
    irrelevant information. Do not start your answer with the text. 
  {text}
  """ + str(summary_num_words) + """-WORD SUMMARY:"""

    title_prompt = PromptTemplate(template=title_prompt_template, input_variables=["text"])
    map_prompt = PromptTemplate(template=map_prompt_template, input_variables=["text"])
    combine_prompt = PromptTemplate(template=combine_prompt_template, input_variables=["text"])

    topics_data = []
    for c in topics:
        topic_data = {
            'summaries': [stage_1_outputs[chunk_id]['summary'] for chunk_id in c],
            'titles': [stage_1_outputs[chunk_id]['title'] for chunk_id in c]
        }
        topic_data['summaries_concat'] = ' '.join(topic_data['summaries'])
        topic_data['titles_concat'] = ', '.join(topic_data['titles'])
        topics_data.append(topic_data)

    # Get a list of each community's summaries (concatenated)
    topics_summary_concat = [c['summaries_concat'] for c in topics_data]
    topics_titles_concat = [c['titles_concat'] for c in topics_data]

    # Concat into one long string to do the topic title creation
    topics_titles_concat_all = ''''''
    for i, c in enumerate(topics_titles_concat):
        topics_titles_concat_all += f'''{i + 1}. {c}
    '''

    print('topics_titles_concat_all', topics_titles_concat_all)

    title_llm = get_chat_llm(model_name=model_name)
    title_llm_chain = title_prompt | title_llm
    title_llm_chain_input = [{'text': topics_titles_concat_all}]
    print("Running Title LLM chain")
    title_llm_chain_results = title_llm_chain.batch(title_llm_chain_input)

    # Split by new line
    titles = title_llm_chain_results[0].content.split('\n')
    # Remove any empty titles
    titles = [t for t in titles if t != '']
    # Remove spaces at start or end of each title
    titles = [t.strip() for t in titles]
    print(titles)
    map_llm = get_chat_llm(model_name=model_name)
    reduce_llm = get_chat_llm(model_name=model_name, max_tokens=4000)

    # Run the map-reduce chain
    docs = [Document(page_content=t) for t in topics_summary_concat]

    print("Running Summarize chain")
    chain = load_summarize_chain(chain_type="map_reduce", map_prompt=map_prompt, combine_prompt=combine_prompt,
                                 return_intermediate_steps=True,
                                 llm=map_llm, reduce_llm=reduce_llm)

    if get_llm_model_provider() == "openai":
        openai_callback = [OpenAICallbackHandler()]
    else:
        openai_callback = None

    output = chain({"input_documents": docs}, return_only_outputs=True, callbacks=openai_callback)
    summaries = output['intermediate_steps']
    stage_2_outputs = [{'title': t, 'summary': s} for t, s in zip(titles, summaries)]
    final_summary = output['output_text']

    # Return: stage_1_outputs (title and summary), stage_2_outputs (title and summary), final_summary, chunk_allocations
    out = {
        'stage_2_outputs': stage_2_outputs,
        'final_summary': final_summary,

    }

    if get_llm_model_provider() == "openai":
        openai_callback = openai_callback[0]
        out['stage_2_input_tokens'] = openai_callback.prompt_tokens
        out['stage_2_output_tokens'] = openai_callback.completion_tokens

    print(f'Stage 2 done time {datetime.now()}')

    return out


def summarize(text, model_name, summary_length=250):
    output_tokens = 0
    input_tokens = 0

    chunks_text = get_chunks_text(text, MIN_WORDS=20, MAX_WORDS=80, CHUNK_LENGTH=5, STRIDE=1)
    # Run Stage 1 Summarizing
    stage_1_summary = _summarize_stage_1(chunks_text, model_name=model_name)
    print(f'Stage 1 done time {datetime.now()}')
    stage_1_outputs = stage_1_summary['stage_1_outputs']
    output_tokens += stage_1_summary['stage_1_output_tokens']
    input_tokens += stage_1_summary['stage_1_input_tokens']
    print(stage_1_outputs)

    # Split the titles and summaries
    stage_1_summaries = [e['summary'] for e in stage_1_outputs]
    stage_1_titles = [e['title'] for e in stage_1_outputs]

    summary_similarity_matrix = get_similarity_matrix(stage_1_summaries)

    # Draw a heatmap with the summary_similarity_matrix
    plt.figure()
    # Color scheme blues
    plt.imshow(summary_similarity_matrix, cmap='Blues')
    # plt.show()

    num_1_chunks = len(stage_1_summaries)
    num_topics = min(int(num_1_chunks / 4), 8)
    topics_out = get_topics(summary_similarity_matrix, num_topics=num_topics, bonus_constant=0.2)
    chunk_topics = topics_out['chunk_topics']
    topics = topics_out['topics']

    plt.figure(figsize=(10, 4))
    plt.imshow(np.array(chunk_topics).reshape(1, -1), cmap='tab20')
    # Draw vertical black lines for every 1 of the x-axis
    for i in range(1, len(chunk_topics)):
        plt.axvline(x=i - 0.5, color='black', linewidth=0.5)
    # plt.show()

    print(topics)

    out = _summarize_stage_2(stage_1_outputs, topics, model_name=model_name, summary_num_words=summary_length)
    stage_2_outputs = out['stage_2_outputs']
    output_tokens += out['stage_2_output_tokens']
    input_tokens += out['stage_2_input_tokens']
    stage_2_titles = [e['title'] for e in stage_2_outputs]
    stage_2_summaries = [e['summary'] for e in stage_2_outputs]

    return {
        'titles': stage_2_titles,
        'summaries': stage_2_summaries,
        'final_summary': out['final_summary'],
        'input_tokens': input_tokens,
        'output_tokens': output_tokens
    }
