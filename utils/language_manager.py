class LanguageManager:
    def __init__(self):
        # Diccionario de traducciones en español
        self.translations = {
            'es': {
                'title': 'Asistente Educativo IA',  # Título principal de la aplicación
                'subtitle': 'Chatbot inteligente para estudiantes y profesores de Ingeniería de Sistemas',  # Subtítulo de bienvenida
                'pdf_management': 'Gestión de PDFs',  # Título para la sección de carga de archivos
                'upload_pdfs': 'Subir archivos PDF',  # Etiqueta del botón para subir archivos
                'upload_help': 'Sube uno o más archivos PDF con material educativo',  # Ayuda sobre cómo subir los archivos
                'processing': 'Procesando',  # Texto mostrado mientras se procesa un archivo
                'processed_successfully': 'procesado exitosamente',  # Confirmación de que un PDF fue procesado
                'error_processing': 'Error procesando',  # Mensaje de error si ocurre un problema al cargar el PDF
                'processed_pdfs': 'PDFs Procesados',  # Título para mostrar los archivos ya cargados
                'chunks': 'Fragmentos',  # Número de fragmentos generados del PDF
                'processed_at': 'Procesado el',  # Fecha de procesamiento
                'delete': 'Eliminar',  # Botón para eliminar un archivo PDF cargado
                'clear_all': 'Limpiar Todo',  # Botón para eliminar todos los PDFs y el historial
                'chat_interface': 'Interfaz de Chat',  # Título de la sección del chatbot
                'sources': 'Fuentes',  # Fuentes utilizadas para responder la pregunta
                'relevance': 'Relevancia',  # Nivel de relevancia de un fragmento recuperado
                'ask_question': 'Haz tu pregunta sobre el material...',  # Texto de entrada del usuario
                'no_pdfs_warning': 'Por favor, sube al menos un archivo PDF antes de hacer preguntas.',  # Advertencia si no hay PDFs cargados
                'generating_response': 'Generando respuesta...',  # Texto mientras se genera una respuesta
                'error_generating': 'Error generando respuesta',  # Mensaje si falla la generación de respuesta
                'statistics': 'Estadísticas',  # Título de la sección de métricas
                'total_pdfs': 'Total PDFs',  # Cantidad total de PDFs procesados
                'total_chunks': 'Total Fragmentos',  # Total de fragmentos generados
                'total_conversations': 'Total Conversaciones',  # Total de preguntas realizadas
                'no_statistics': 'Sube PDFs para ver estadísticas',  # Texto si no hay datos para mostrar
                'configuration': 'Configuración',  # Sección para revisar el estado de configuración
                'api_configured': 'API Configurada',  # Mensaje si la clave de API está cargada correctamente
                'api_not_configured': 'API No Configurada',  # Mensaje si falta la clave de API
                'api_help': 'Configura GROQ_API_KEY como variable de entorno',  # Ayuda sobre cómo configurar la API
                'clear_chat': 'Limpiar Chat',  # Botón para limpiar el historial del chatbot
                'footer': 'Asistente Educativo IA - Desarrollado para estudiantes y profesores de Ingeniería de Sistemas'  # Mensaje de pie de página
            }
        }

    def get_text(self, language: str) -> dict:
        """
        Retorna los textos en español. Ignora otros idiomas.
        """
        return self.translations['es']

