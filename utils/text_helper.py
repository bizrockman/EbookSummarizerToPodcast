import pandas as pd


def create_sentences(segments, MIN_WORDS, MAX_WORDS):
    # Combine the non-sentences together
    sentences = []

    is_new_sentence = True
    sentence_length = 0
    sentence_num = 0
    sentence_segments = []

    for i in range(len(segments)):
        if is_new_sentence == True:
            is_new_sentence = False
        # Append the segment
        sentence_segments.append(segments[i])
        segment_words = segments[i].split(' ')
        sentence_length += len(segment_words)

        # If exceed MAX_WORDS, then stop at the end of the segment
        # Only consider it a sentence if the length is at least MIN_WORDS
        if (sentence_length >= MIN_WORDS and segments[i][-1] == '.') or sentence_length >= MAX_WORDS:
            sentence = ' '.join(sentence_segments)
            sentences.append({
                'sentence_num': sentence_num,
                'text': sentence,
                'sentence_length': sentence_length
            })
            # Reset
            is_new_sentence = True
            sentence_length = 0
            sentence_segments = []
            sentence_num += 1

    return sentences


def create_chunks(sentences, CHUNK_LENGTH, STRIDE):
    sentences_df = pd.DataFrame(sentences)

    chunks = []
    for i in range(0, len(sentences_df), (CHUNK_LENGTH - STRIDE)):
        chunk = sentences_df.iloc[i:i + CHUNK_LENGTH]
        chunk_text = ' '.join(chunk['text'].tolist())

        chunks.append({
            'start_sentence_num': chunk['sentence_num'].iloc[0],
            'end_sentence_num': chunk['sentence_num'].iloc[-1],
            'text': chunk_text,
            'num_words': len(chunk_text.split(' '))
        })

    chunks_df = pd.DataFrame(chunks)
    return chunks_df.to_dict('records')


def get_chunks_text(text, MIN_WORDS=20, MAX_WORDS=80, CHUNK_LENGTH=5, STRIDE=1):
    segments = text.split('.')
    segments = [segment + '.' for segment in segments]
    segments = [segment.split(',') for segment in segments]
    segments = [item for sublist in segments for item in sublist]

    sentences = create_sentences(segments, MIN_WORDS=MIN_WORDS, MAX_WORDS=MAX_WORDS)
    chunks = create_chunks(sentences, CHUNK_LENGTH=CHUNK_LENGTH, STRIDE=STRIDE)
    chunks_text = [chunk['text'] for chunk in chunks]
    return chunks_text
