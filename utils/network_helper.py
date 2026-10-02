import numpy as np
import networkx as nx
from utils.disk_cache import cache_with_disk


@cache_with_disk()
def get_topics(title_similarity, num_topics=8, bonus_constant=0.25, min_size=3):
    # Do not mutate a cached embedding matrix. Keep the legacy experiment bounded.
    title_similarity = np.array(title_similarity, dtype=float, copy=True)
    if title_similarity.ndim != 2 or title_similarity.shape[0] != title_similarity.shape[1]:
        raise ValueError("Expected square similarity matrix")
    size = len(title_similarity)
    if not size:
        return {'chunk_topics': [], 'topics': []}
    if size == 1:
        return {'chunk_topics': [0], 'topics': [[0]]}
    title_similarity = np.maximum(np.nan_to_num(title_similarity), 0)
    np.fill_diagonal(title_similarity, 0)
    proximity_bonus_arr = np.zeros_like(title_similarity)
    for row in range(proximity_bonus_arr.shape[0]):
        for col in range(proximity_bonus_arr.shape[1]):
            if row == col:
                proximity_bonus_arr[row, col] = 0
            else:
                proximity_bonus_arr[row, col] = 1 / (abs(row - col)) * bonus_constant

    title_similarity += proximity_bonus_arr

    title_nx_graph = nx.from_numpy_array(title_similarity)

    desired_num_topics = max(1, min(num_topics, size))
    # Store the accepted partitionings
    topics_title_accepted = []

    resolution = 0.85
    resolution_step = 0.01
    iterations = 40

    # Find the resolution that gives the desired number of topics
    topics_title = []
    if title_nx_graph.size(weight='weight') == 0:
        return {'chunk_topics': list(range(size)), 'topics': [[i] for i in range(size)]}
    best_partition, best_distance = None, float('inf')
    for _ in range(200):
        topics_title = nx.community.louvain_communities(title_nx_graph, weight='weight', resolution=resolution, seed=0)
        distance = abs(len(topics_title) - desired_num_topics)
        if distance < best_distance:
            best_partition, best_distance = topics_title, distance
        if distance == 0:
            break
        resolution += resolution_step
    topics_title = best_partition
    topic_sizes = [len(c) for c in topics_title]
    sizes_sd = np.std(topic_sizes)
    modularity = nx.community.modularity(title_nx_graph, topics_title, weight='weight', resolution=resolution)

    lowest_sd_iteration = 0
    # Set lowest sd to inf
    lowest_sd = float('inf')

    for i in range(iterations):
        topics_title = nx.community.louvain_communities(title_nx_graph, weight='weight', resolution=resolution, seed=i)
        modularity = nx.community.modularity(title_nx_graph, topics_title, weight='weight', resolution=resolution)

        # Check SD
        topic_sizes = [len(c) for c in topics_title]
        sizes_sd = np.std(topic_sizes)

        topics_title_accepted.append(topics_title)

        if sizes_sd < lowest_sd and min(topic_sizes) >= min_size:
            lowest_sd_iteration = i
            lowest_sd = sizes_sd

    # Set the chosen partitioning to be the one with highest modularity
    topics_title = topics_title_accepted[lowest_sd_iteration]
    print(f'Best SD: {lowest_sd}, Best iteration: {lowest_sd_iteration}')

    topic_id_means = [sum(e) / len(e) for e in topics_title]
    # Arrange title_topics in order of topic_id_means
    topics_title = [sorted(c) for _, c in sorted(zip(topic_id_means, topics_title), key=lambda pair: pair[0])]
    # Create an array denoting which topic each chunk belongs to
    chunk_topics = [None] * title_similarity.shape[0]
    for i, c in enumerate(topics_title):
        for j in c:
            chunk_topics[j] = i

    return {
        'chunk_topics': chunk_topics,
        'topics': topics_title
    }
