import os
import requests
import json
from typing import List, Dict, Tuple
from utils.embedding_manager import EmbeddingManager

class ChatManager:
    def __init__(self):
        # Cargar la clave de la API Groq desde las variables de entorno
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama3-8b-8192"  # Modelo gratuito disponible en Groq
    
    def get_response(self, query: str, embedding_manager: EmbeddingManager, language: str = 'es') -> Tuple[str, List[Dict]]:
        import re

        # Limpieza estricta del input
        query_clean = re.sub(r'[^\w\s]', '', query.strip().lower())  # elimina signos como ! . ?
        
        # Lista de saludos comunes
        saludos = ['hola', 'buenas', 'que tal', 'hey', 'saludos', 'como estas']

        if query_clean in saludos:
            return "¡Hola! ¿En qué tema del material educativo te gustaría que te ayude?", []

        """
        Generar una respuesta utilizando el modelo LLM basado en la consulta del usuario
        y los documentos recuperados más relevantes.
        """
        # Buscar documentos relevantes para la consulta
        relevant_docs = embedding_manager.search(query, k=5)
        
        # Si no se encuentra contexto relevante, devolver mensaje al usuario
        if not relevant_docs:
            return "No encontré información relevante en los documentos cargados. Por favor, sube material relacionado con tu pregunta.", []
        
        # Construir el contexto uniendo los fragmentos recuperados
        context = "\n\n".join([doc['content'] for doc in relevant_docs])
        
        # Construir el prompt para el modelo (solo en español)
        system_prompt = """Eres un asistente educativo especializado en ingeniería de sistemas. Tu trabajo es ayudar a estudiantes y profesores respondiendo preguntas basadas en el material educativo proporcionado.

Instrucciones:
- Responde únicamente basándote en el contexto proporcionado
- Si la información no está en el contexto, indícalo claramente
- Sé preciso y educativo en tus respuestas
- Usa ejemplos del material cuando sea apropiado
- Mantén un tono profesional pero amigable
- Responde en español"""
        
        user_prompt = f"""Contexto del material educativo:
{context}

Pregunta del estudiante/profesor: {query}

Por favor, proporciona una respuesta detallada basada únicamente en el material proporcionado."""
        
        # Llamar a la API de Groq
        try:
            response = self._call_groq_api(system_prompt, user_prompt)
            return response, relevant_docs
        except Exception as e:
            return f"Error al generar respuesta: {str(e)}. Verifica tu configuración de API.", relevant_docs
    
    def _call_groq_api(self, system_prompt: str, user_prompt: str) -> str:
        """
        Realizar la llamada HTTP a la API de Groq para obtener una respuesta generada
        """
        if not self.groq_api_key:
            raise Exception("GROQ_API_KEY no configurada")
        
        # Encabezados HTTP para autenticación
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        # Cuerpo de la solicitud con el prompt y configuración
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1,
            "stream": False
        }
        
        # Realizar la solicitud POST
        response = requests.post(self.groq_url, headers=headers, json=data)
        
        # Verificar errores en la respuesta
        if response.status_code != 200:
            raise Exception(f"Error en la llamada a la API: {response.status_code} - {response.text}")
        
        # Obtener y retornar la respuesta generada por el modelo
        result = response.json()
        return result['choices'][0]['message']['content']
