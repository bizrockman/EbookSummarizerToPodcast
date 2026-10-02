"""
DAO Pattern für LLM Dienste (Kapitelerkennung, Übersetzung)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

from api.config.settings import settings


class LLMDao(ABC):
    """Abstrakte Basis-Klasse für LLM DAOs"""
    
    @abstractmethod
    def detect_chapter_type(self, chapter_title: str, chapter_excerpt: str) -> Dict[str, Any]:
        """
        Erkennt ob ein Kapitel Hauptinhalt oder Zusatzmaterial ist
        
        Returns:
            Dict mit: {"type": "content|supplement", "confidence": float, "tokens": dict, "cost": float}
        """
        pass
    
    @abstractmethod
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Erkennt die Sprache des Textes
        
        Returns:
            Dict mit: {"language": str, "confidence": float, "tokens": dict, "cost": float}
        """
        pass
    
    @abstractmethod
    def translate_text(self, text: str, target_language: str) -> Dict[str, Any]:
        """
        Übersetzt Text in Zielsprache
        
        Returns:
            Dict mit: {"translated_text": str, "tokens": dict, "cost": float}
        """
        pass
    
    @abstractmethod
    def get_cost_per_token(self) -> Dict[str, float]:
        """Gibt Kosten pro Token zurück"""
        pass


class OpenAILLMDao(LLMDao):
    """OpenAI LLM Implementation"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.openai_default_model
        self.llm: BaseChatModel = ChatOpenAI(
            model_name=self.model_name,
            temperature=0 if self.model_name != "gpt-5" else 1,
            api_key=settings.openai_api_key
        )
        self.input_cost_per_1k = settings.openai_gpt4o_input_cost_per_1k
        self.output_cost_per_1k = settings.openai_gpt4o_output_cost_per_1k
    
    def detect_chapter_type(self, chapter_title: str, chapter_excerpt: str) -> Dict[str, Any]:
        """Erkennt Kapiteltyp mit OpenAI"""
        
        prompt_template = """
        Analysiere den folgenden Kapiteltitel und Textausschnitt eines Buches.
        Bestimme, ob es sich um Hauptinhalt (content) oder Zusatzmaterial (supplement) handelt.
        
        Zusatzmaterial umfasst: Danksagungen, Bibliographien,
        Index, "About the Author", Copyright-Seiten, etc.
        
        Hauptinhalt umfasst: Alle Kapitel, die zum eigentlichen Buch gehören, einschließlich
        Einleitungen, Vorwörtern und Anhängen, sofern sie Argumente, Begriffe oder Beispiele
        des Werkes erklären. Im Zweifel content; Titel allein genügt nicht zum Ausschluss.
        
        Kapiteltitel: {title}
        Textausschnitt: {excerpt}
        
        Antworte NUR mit "content" oder "supplement".
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["title", "excerpt"]
        )
        
        # Begrenze Excerpt auf 500 Zeichen
        excerpt = chapter_excerpt[:500] if len(chapter_excerpt) > 500 else chapter_excerpt
        
        chain = prompt | self.llm
        result = chain.invoke({"title": chapter_title, "excerpt": excerpt})
        
        chapter_type = result.content.strip().lower()
        if chapter_type not in ["content", "supplement"]:
            chapter_type = "content"  # Default zu content
        
        # Token-Nutzung und Kosten
        input_tokens = result.response_metadata.get("token_usage", {}).get("prompt_tokens", 0)
        output_tokens = result.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
        
        cost = (input_tokens / 1000 * self.input_cost_per_1k +
                output_tokens / 1000 * self.output_cost_per_1k)
        
        return {
            "type": chapter_type,
            "confidence": 1.0,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost": cost,
            "provider": "openai",
            "model": self.model_name
        }
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """Erkennt Sprache mit OpenAI"""
        
        prompt_template = """
        Erkenne die Sprache des folgenden Textes.
        Antworte NUR mit dem ISO 639-1 Code (z.B. 'en', 'de', 'fr', 'es').
        
        Text: {text}
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["text"]
        )
        
        # Begrenze Text auf 500 Zeichen
        text_sample = text[:500] if len(text) > 500 else text
        
        chain = prompt | self.llm
        result = chain.invoke({"text": text_sample})
        
        language = result.content.strip().lower()
        
        # Token-Nutzung und Kosten
        input_tokens = result.response_metadata.get("token_usage", {}).get("prompt_tokens", 0)
        output_tokens = result.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
        
        cost = (input_tokens / 1000 * self.input_cost_per_1k +
                output_tokens / 1000 * self.output_cost_per_1k)
        
        return {
            "language": language,
            "confidence": 1.0,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost": cost,
            "provider": "openai",
            "model": self.model_name
        }
    
    def translate_text(self, text: str, target_language: str) -> Dict[str, Any]:
        """Übersetzt Text mit OpenAI"""
        
        language_names = {
            "de": "German",
            "en": "English",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian",
            "pt": "Portuguese"
        }
        
        target_lang_name = language_names.get(target_language, target_language)
        
        prompt_template = """
        Translate the following text to {target_language}. 
        Make sure the translation is natural and makes sense in the target language,
        don't approach it too literally.
        
        Text: {text}
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["text", "target_language"]
        )
        
        chain = prompt | self.llm
        result = chain.invoke({"text": text, "target_language": target_lang_name})
        
        translated_text = result.content.strip()
        
        # Token-Nutzung und Kosten
        input_tokens = result.response_metadata.get("token_usage", {}).get("prompt_tokens", 0)
        output_tokens = result.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
        
        cost = (input_tokens / 1000 * self.input_cost_per_1k +
                output_tokens / 1000 * self.output_cost_per_1k)
        
        return {
            "translated_text": translated_text,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost": cost,
            "provider": "openai",
            "model": self.model_name
        }
    
    def get_cost_per_token(self) -> Dict[str, float]:
        return {
            "input_per_1k": self.input_cost_per_1k,
            "output_per_1k": self.output_cost_per_1k
        }


class GroqLLMDao(LLMDao):
    """Groq LLM Implementation"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.groq_default_model
        self.llm: BaseChatModel = ChatGroq(
            model_name=self.model_name,
            temperature=0,
            groq_api_key=settings.groq_api_key,
            groq_api_base=settings.groq_api_base
        )
        # Groq ist oft kostenlos oder sehr günstig
        self.input_cost_per_1k = 0.0
        self.output_cost_per_1k = 0.0
    
    def detect_chapter_type(self, chapter_title: str, chapter_excerpt: str) -> Dict[str, Any]:
        """Erkennt Kapiteltyp mit Groq - ähnliche Implementierung wie OpenAI"""
        # Implementation analog zu OpenAI
        prompt_template = """
        Analysiere den folgenden Kapiteltitel und Textausschnitt eines Buches.
        Bestimme, ob es sich um Hauptinhalt (content) oder Zusatzmaterial (supplement) handelt.
        
        Zusatzmaterial umfasst: Vorwörter, Einleitungen, Danksagungen, Anhänge, Bibliographien,
        Index, "About the Author", Copyright-Seiten, etc.
        
        Hauptinhalt umfasst: Alle Kapitel, die zum eigentlichen Buch gehören.
        
        Kapiteltitel: {title}
        Textausschnitt: {excerpt}
        
        Antworte NUR mit "content" oder "supplement".
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["title", "excerpt"]
        )
        
        excerpt = chapter_excerpt[:500] if len(chapter_excerpt) > 500 else chapter_excerpt
        
        chain = prompt | self.llm
        result = chain.invoke({"title": chapter_title, "excerpt": excerpt})
        
        chapter_type = result.content.strip().lower()
        if chapter_type not in ["content", "supplement"]:
            chapter_type = "content"
        
        input_tokens = result.response_metadata.get("token_usage", {}).get("prompt_tokens", 0)
        output_tokens = result.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
        
        cost = 0.0  # Groq oft kostenlos
        
        return {
            "type": chapter_type,
            "confidence": 1.0,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost": cost,
            "provider": "groq",
            "model": self.model_name
        }
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """Erkennt Sprache mit Groq"""
        # Implementation analog zu OpenAI
        prompt_template = """
        Erkenne die Sprache des folgenden Textes.
        Antworte NUR mit dem ISO 639-1 Code (z.B. 'en', 'de', 'fr', 'es').
        
        Text: {text}
        """
        
        prompt = PromptTemplate(template=prompt_template, input_variables=["text"])
        text_sample = text[:500] if len(text) > 500 else text
        
        chain = prompt | self.llm
        result = chain.invoke({"text": text_sample})
        
        language = result.content.strip().lower()
        
        input_tokens = result.response_metadata.get("token_usage", {}).get("prompt_tokens", 0)
        output_tokens = result.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
        
        return {
            "language": language,
            "confidence": 1.0,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost": 0.0,
            "provider": "groq",
            "model": self.model_name
        }
    
    def translate_text(self, text: str, target_language: str) -> Dict[str, Any]:
        """Übersetzt Text mit Groq"""
        # Implementation analog zu OpenAI
        language_names = {
            "de": "German",
            "en": "English",
            "fr": "French",
            "es": "Spanish"
        }
        
        target_lang_name = language_names.get(target_language, target_language)
        
        prompt_template = """
        Translate the following text to {target_language}. 
        Make sure the translation is natural and makes sense in the target language.
        
        Text: {text}
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["text", "target_language"]
        )
        
        chain = prompt | self.llm
        result = chain.invoke({"text": text, "target_language": target_lang_name})
        
        translated_text = result.content.strip()
        
        input_tokens = result.response_metadata.get("token_usage", {}).get("prompt_tokens", 0)
        output_tokens = result.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
        
        return {
            "translated_text": translated_text,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost": 0.0,
            "provider": "groq",
            "model": self.model_name
        }
    
    def get_cost_per_token(self) -> Dict[str, float]:
        return {
            "input_per_1k": self.input_cost_per_1k,
            "output_per_1k": self.output_cost_per_1k
        }


def get_llm_dao(provider: str = None) -> LLMDao:
    """Factory-Funktion für LLM DAO"""
    if not provider:
        provider = settings.llm_model_provider
    
    if provider == "openai":
        return OpenAILLMDao()
    elif provider == "groq":
        return GroqLLMDao()
    else:
        raise ValueError(f"Unbekannter LLM Provider: {provider}")

