import numpy as np

from scipy.spatial.distance import cosine

from langchain_openai import OpenAIEmbeddings
from utils.disk_cache import cache_with_disk


@cache_with_disk()
def get_embeddings(text):
    openai_embed = OpenAIEmbeddings()
    summary_embeds = np.array(openai_embed.embed_documents(text))
    return summary_embeds


def get_similarity_matrix(summaries):
    length = len(summaries)
    summary_embeds = np.array(get_embeddings(summaries))
    # title_embeds = np.array(openai_embed.embed_documents(stage_1_titles))

    # Get similarity matrix between the embeddings of the chunk summaries
    summary_similarity_matrix = np.zeros((length, length))
    summary_similarity_matrix[:] = np.nan

    for row in range(length):
        for col in range(row, length):
            # Calculate cosine similarity between the two vectors
            similarity = 1 - cosine(summary_embeds[row], summary_embeds[col])
            summary_similarity_matrix[row, col] = similarity
            summary_similarity_matrix[col, row] = similarity

    return summary_similarity_matrix
