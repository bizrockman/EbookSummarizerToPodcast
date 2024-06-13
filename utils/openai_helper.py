import os
import openai

def check_openai_api_key_exist():
    if 'OPENAI_API_KEY' not in os.environ:
        st.error('Please provide your OpenAI API key in the sidebar.')
        st.stop()


def is_api_key_valid(api_key):
    import openai
    openai.api_key = api_key
    try:
        openai.Model.list()
    except openai.error.AuthenticationError as e:
        return False
    else:
        return True