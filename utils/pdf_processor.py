import PyPDF2
import os
from typing import List, Dict
import re

class PDFProcessor:
    def __init__(self):
        # Tamaño máximo de cada fragmento de texto
        self.chunk_size = 1000
        # Número de palabras que se solapan entre fragmentos
        self.chunk_overlap = 200
    
    def process_pdf(self, file_path: str) -> List[Dict]:
        """
        Procesa un archivo PDF y devuelve fragmentos de texto con metadatos
        """
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extraer texto de todas las páginas del PDF
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text:
                        full_text += f"\n--- Página {page_num + 1} ---\n{text}"
                
                # Limpiar el texto extraído
                full_text = self._clean_text(full_text)
                
                # Dividir el texto en fragmentos
                chunks = self._create_chunks(full_text, os.path.basename(file_path))
                
                return chunks
                
        except Exception as e:
            raise Exception(f"Error al procesar el PDF: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Limpia y normaliza el texto extraído
        """
        # Elimina espacios en blanco adicionales
        text = re.sub(r'\s+', ' ', text)
        
        # Elimina caracteres especiales innecesarios pero conserva la puntuación relevante
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\"\'\n]', '', text)
        
        # Corrige problemas comunes en extracción desde PDF
        text = text.replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _create_chunks(self, text: str, document_name: str) -> List[Dict]:
        """
        Divide el texto en fragmentos con solapamiento para conservar el contexto
        """
        chunks = []
        sentences = text.split('. ')  # División básica por oraciones

        current_chunk = ""
        chunk_id = 0
        
        for sentence in sentences:
            # Si aún cabe la oración en el fragmento, se añade
            if len(current_chunk) + len(sentence) < self.chunk_size:
                current_chunk += sentence + ". "
            else:
                # Guarda el fragmento anterior si existe
                if current_chunk.strip():
                    chunks.append({
                        'id': f"{document_name}_{chunk_id}",
                        'content': current_chunk.strip(),
                        'document': document_name,
                        'chunk_index': chunk_id
                    })
                    chunk_id += 1
                
                # Inicia nuevo fragmento con solapamiento de palabras
                overlap_words = current_chunk.split()[-self.chunk_overlap // 30:]
                current_chunk = " ".join(overlap_words) + " " + sentence + ". "
        
        # Añade el último fragmento si existe
        if current_chunk.strip():
            chunks.append({
                'id': f"{document_name}_{chunk_id}",
                'content': current_chunk.strip(),
                'document': document_name,
                'chunk_index': chunk_id
            })
        
        return chunks
