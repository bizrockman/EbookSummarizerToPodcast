"""
DAO Pattern für Text-to-Speech Dienste
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
import os
from openai import OpenAI
from pydub import AudioSegment
from slugify import slugify

from api.config.settings import settings


class TTSDao(ABC):
    """Abstrakte Basis-Klasse für TTS DAOs"""
    
    @abstractmethod
    def generate_speech(
        self,
        text: str,
        voice: str,
        output_file: str
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Generiere Sprache aus Text
        
        Returns:
            Tuple[str, float, Dict]: (Pfad zur Audio-Datei, Dauer in Sekunden, Kosten-Details)
        """
        pass
    
    @abstractmethod
    def get_cost_per_character(self) -> float:
        """Gibt die Kosten pro Zeichen zurück"""
        pass
    
    @abstractmethod
    def get_available_voices(self) -> list:
        """Gibt verfügbare Stimmen zurück"""
        pass


class OpenAITTSDao(TTSDao):
    """OpenAI TTS Implementation"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_tts_model
        self.cost_per_char = settings.openai_tts_cost_per_char
    
    def split_text_into_segments(self, text: str, max_length: int = 4096) -> list:
        """Teilt Text in Segmente auf"""
        segments = []
        current_segment = ""
        
        for sentence in text.split('. '):
            if len(current_segment) + len(sentence) + 1 <= max_length:
                current_segment += sentence + ". "
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence + ". "
        
        if current_segment:
            segments.append(current_segment.strip())
        
        return segments
    
    def generate_speech(
        self,
        text: str,
        voice: str = "alloy",
        output_file: str = None,
        progress_callback: callable = None
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Generiere Sprache mit OpenAI TTS
        
        Args:
            text: Text für TTS
            voice: Stimme
            output_file: Ausgabedatei
            progress_callback: Optional callback(current_chunk, total_chunks) für Progress-Updates
        """
        
        if not output_file:
            output_file = os.path.join(
                settings.audiofiles_dir,
                f"tts_{slugify(text[:30])}.mp3"
            )
        
        segments = self.split_text_into_segments(text)
        audio_files = []
        total_chars = len(text)
        total_chunks = len(segments)
        
        # Generiere Audio für jedes Segment
        for i, segment in enumerate(segments):
            temp_file = output_file.replace(".mp3", f"_part_{i}.mp3")
            
            response = self.client.audio.speech.create(
                model=self.model,
                voice=voice,
                speed=1.15,
                input=segment
            )
            
            response.stream_to_file(temp_file)
            audio_files.append(temp_file)
            
            # Progress Callback NACH erfolgreicher Generierung
            if progress_callback:
                progress_callback(i + 1, total_chunks)
        
        # Kombiniere Audio-Dateien
        if len(audio_files) > 1:
            combined_audio = AudioSegment.empty()
            for file in audio_files:
                audio_segment = AudioSegment.from_mp3(file)
                combined_audio += audio_segment
            
            combined_audio.export(output_file, format="mp3", bitrate="128k")
            
            # Lösche temporäre Dateien
            for file in audio_files:
                os.remove(file)
        else:
            # Nur eine Datei, keine Kombination nötig
            os.rename(audio_files[0], output_file)
        
        # Berechne Dauer
        audio = AudioSegment.from_mp3(output_file)
        duration_seconds = len(audio) / 1000.0
        
        # Berechne Kosten
        cost = total_chars * self.cost_per_char
        
        cost_details = {
            "characters": total_chars,
            "cost_per_char": self.cost_per_char,
            "total_cost_usd": cost,
            "provider": "openai",
            "model": self.model,
            "total_chunks": total_chunks  # Anzahl der TTS-Chunks
        }
        
        return output_file, duration_seconds, cost_details
    
    def get_cost_per_character(self) -> float:
        return self.cost_per_char
    
    def get_available_voices(self) -> list:
        return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


class ElevenLabsTTSDao(TTSDao):
    """ElevenLabs TTS Implementation (Platzhalter)"""
    
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        # TODO: Implementierung für ElevenLabs
    
    def generate_speech(
        self,
        text: str,
        voice: str,
        output_file: str = None
    ) -> Tuple[str, float, Dict[str, Any]]:
        raise NotImplementedError("ElevenLabs TTS noch nicht implementiert")
    
    def get_cost_per_character(self) -> float:
        # Beispielwert - muss angepasst werden
        return 0.00003
    
    def get_available_voices(self) -> list:
        return ["default"]


class LocalTTSDao(TTSDao):
    """Lokales TTS Modell Implementation (Platzhalter)"""
    
    def generate_speech(
        self,
        text: str,
        voice: str,
        output_file: str = None
    ) -> Tuple[str, float, Dict[str, Any]]:
        raise NotImplementedError("Lokales TTS noch nicht implementiert")
    
    def get_cost_per_character(self) -> float:
        return 0.0  # Lokal = keine Kosten
    
    def get_available_voices(self) -> list:
        return ["default"]


def get_tts_dao(provider: str = "openai") -> TTSDao:
    """Factory-Funktion für TTS DAO"""
    if provider == "openai":
        return OpenAITTSDao()
    elif provider == "elevenlabs":
        return ElevenLabsTTSDao()
    elif provider == "local":
        return LocalTTSDao()
    else:
        raise ValueError(f"Unbekannter TTS Provider: {provider}")

