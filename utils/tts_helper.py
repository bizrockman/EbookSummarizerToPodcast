import os
from slugify import slugify

from openai import OpenAI
from pydub import AudioSegment


def split_text_into_segments(text, max_length=4096):
    segments = []
    current_segment = ""

    for sentence in text.split('. '):
        if len(current_segment) + len(sentence) + 1 <= max_length:
            current_segment += sentence + ". "
        else:
            segments.append(current_segment.strip())
            current_segment = sentence + ". "

    if current_segment:
        segments.append(current_segment.strip())

    return segments


def combine_audio_files(audio_files, output_file):
    combined_audio = AudioSegment.empty()
    bitrate = 128

    for file in audio_files:
        audio_segment = AudioSegment.from_mp3(file)
        bitrate = audio_segment.frame_rate
        combined_audio += audio_segment

    combined_audio.export(output_file, format="mp3", bitrate=f"{bitrate}k")


def get_speech_from_text(title, content, voice):
    audiofiles_dir = "audiofiles"

    if isinstance(content, list):
        content = " ".join(content)
    elif not isinstance(content, str):
        raise TypeError("Content must be a string or a list of strings")

    segments = split_text_into_segments(title + "\n\n" + content)

    client = OpenAI()
    audio_files = []

    for i, segment in enumerate(segments):
        speech_file_path = os.path.join(audiofiles_dir, f"speech_part_{i}.mp3")
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            speed=1.15,
            input=segment
        )
        response.stream_to_file(speech_file_path)

        audio_files.append(speech_file_path)
        print(speech_file_path)

    title = slugify(title, separator="_")
    output_file = os.path.join(audiofiles_dir, f"{title}_speech.mp3")
    combine_audio_files(audio_files, output_file)
    print(output_file)
    # Temporäre Dateien löschen
    for file in audio_files:
        os.remove(file)

    return output_file


def generate_podcast(summaries, podcast_filename, voice="onyx"):
    audiofiles_dir = "audiofiles"
    if not os.path.exists(audiofiles_dir):
        os.makedirs(audiofiles_dir)

    audio_files = []
    total_cost = 0
    for title, content, cost in summaries:
        filename = get_speech_from_text(title, content, voice)
        audio_files.append(filename)
        segment_cost = 0.000030 * len(content)
        total_cost += segment_cost

    podcast_filename = slugify(podcast_filename, separator="_").capitalize()
    final_output_file = os.path.join(audiofiles_dir, podcast_filename + ".mp3")
    combine_audio_files(audio_files, final_output_file)

    # Temporäre Dateien löschen
    for file in audio_files:
        os.remove(file)

    return {'output_file': final_output_file, 'cost': total_cost}
