import os
import pickle
import json
import re
from typing import List, Dict, Tuple
import streamlit as st
from collections import Counter
import math

class EmbeddingManager:
    def __init__(self):
        self.documents = []  # Lista para almacenar los documentos procesados
        self.embeddings_path = "data/vectorstore/documents.pkl"  # Ruta de almacenamiento
        
        # Crear carpeta si no existe
        os.makedirs(os.path.dirname(self.embeddings_path), exist_ok=True)
        
        # Cargar documentos previos si existen
        self._load_embeddings()
    
    def _load_embeddings(self):
        """Cargar documentos almacenados previamente desde disco"""
        try:
            if os.path.exists(self.embeddings_path):
                with open(self.embeddings_path, 'rb') as f:
                    self.documents = pickle.load(f)
        except Exception as e:
            print(f"Error al cargar documentos: {str(e)}")
            self.documents = []
    
    def _save_embeddings(self):
        """Guardar los documentos procesados en disco"""
        try:
            with open(self.embeddings_path, 'wb') as f:
                pickle.dump(self.documents, f)
        except Exception as e:
            print(f"Error al guardar documentos: {str(e)}")
    
    def _preprocess_text(self, text: str) -> List[str]:
        """Preprocesar texto: limpiar, dividir y eliminar palabras vacías"""
        # Convertir a minúsculas y eliminar caracteres especiales
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()

        # Lista de palabras vacías en español e inglés
        stop_words = { 'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'una', 'como', 'pero', 'sus', 'han', 'había', 'esto', 'fue', 'ser', 'está', 'hacer', 'más', 'muy', 'sobre', 'cada', 'hasta', 'tiene', 'pueden', 'todo', 'también', 'sin', 'otro', 'otros', 'otras', 'donde', 'cuando', 'cual', 'desde', 'entre', 'estas', 'estos', 'durante', 'parte', 'porque', 'después', 'antes', 'momento', 'través', 'tanto', 'menos', 'bien', 'ejemplo', 'general', 'así', 'ahora', 'luego', 'entonces', 'medio', 'forma', 'manera', 'mientras', 'mayor', 'mejor', 'mismo', 'nueva', 'nuevo', 'grandes', 'gran', 'diferentes', 'muchos', 'muchas', 'varios', 'varias', 'cualquier', 'algún', 'alguna', 'algunos', 'algunas', 'ningún', 'ninguna', 'ningunos', 'ningunas',
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'
        }

        # Eliminar palabras vacías
        words = [word for word in words if word not in stop_words and len(word) > 2]
        return words
    
    def _calculate_similarity(self, query_words: List[str], doc_words: List[str]) -> float:
        """Calcular similitud basada en TF-IDF entre consulta y documento"""
        if not query_words or not doc_words:
            return 0.0
        
        # Frecuencia de términos
        query_tf = Counter(query_words)
        doc_tf = Counter(doc_words)
        
        all_words = set(query_words + doc_words)
        
        # Producto punto (numerador del coseno)
        dot_product = sum(query_tf[word] * doc_tf[word] for word in all_words)
        
        # Magnitud de vectores
        query_magnitude = math.sqrt(sum(count**2 for count in query_tf.values()))
        doc_magnitude = math.sqrt(sum(count**2 for count in doc_tf.values()))
        
        if query_magnitude == 0 or doc_magnitude == 0:
            return 0.0
        
        similarity = dot_product / (query_magnitude * doc_magnitude)
        
        # Reforzar similitud si hay coincidencias exactas
        query_text = ' '.join(query_words)
        doc_text = ' '.join(doc_words)
        if query_text in doc_text:
            similarity += 0.3
        
        # Reforzar si hay muchas palabras en común
        common_words = set(query_words) & set(doc_words)
        if len(common_words) > 1:
            similarity += 0.1 * len(common_words)
        
        return min(similarity, 1.0)
    
    def add_documents(self, chunks: List[Dict], document_name: str):
        """Agregar nuevos fragmentos procesados a la base vectorial"""
        self.remove_document(document_name)  # Quitar duplicados si ya existía

        for chunk in chunks:
            chunk['processed_words'] = self._preprocess_text(chunk['content'])
            self.documents.append(chunk)
        
        self._save_embeddings()
    
    def remove_document(self, document_name: str):
        """Eliminar todos los fragmentos de un documento específico"""
        self.documents = [doc for doc in self.documents if doc['document'] != document_name]
        self._save_embeddings()
    
    def clear_all(self):
        """Eliminar toda la base de documentos y archivos guardados"""
        self.documents = []
        try:
            if os.path.exists(self.embeddings_path):
                os.remove(self.embeddings_path)
        except:
            pass
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Buscar fragmentos más similares según una consulta textual"""
        if not self.documents:
            return []
        
        query_words = self._preprocess_text(query)
        if not query_words:
            return []
        
        results = []
        for doc in self.documents:
            doc_words = doc.get('processed_words', [])
            if not doc_words:
                doc_words = self._preprocess_text(doc['content'])
                doc['processed_words'] = doc_words
            
            similarity = self._calculate_similarity(query_words, doc_words)
            if similarity > 0:
                result = doc.copy()
                result['score'] = similarity
                results.append(result)
        
        # Ordenar por similitud descendente y devolver los k mejores
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:k]
