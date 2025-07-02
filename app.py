'''Agente Chatbot Educativo IA'''
import os
import shutil
import json
from datetime import datetime
import streamlit as st

# Importa clases propias del proyecto
from utils.pdf_processor import PDFProcessor
from utils.embedding_manager import EmbeddingManager
from utils.chat_manager import ChatManager
from utils.language_manager import LanguageManager

# Intentar cargar la API key desde st.secrets si existe
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    print("✅ Clave cargada desde Streamlit secrets")
except st.runtime.secrets.StreamlitSecretNotFoundError:
    from dotenv import load_dotenv
    load_dotenv()
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    print("⚠️ Clave cargada desde archivo .env")
# Validación básica
if not groq_api_key:
    st.error(
        "❌ No se pudo cargar la clave GROQ_API_KEY."
        "Asegúrate de tener un archivo .env o secrets.toml configurado."
    )

# Configuración de la página Streamlit
st.set_page_config(
    page_title="Asistente Educativo IA",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar la apariencia del chat
st.markdown("""
<style>
    /* Reducir el padding general de la página */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
        max-width: 100%;
    }
    
    /* Contenedor principal sin overflow */
    .stApp {
        overflow: hidden;
    }
    
    /* Chat input siempre visible en la parte inferior */
    .stChatInputContainer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: var(--background-color);
        padding: 1rem;
        border-top: 2px solid var(--primary-color);
        z-index: 1000;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }
    
    /* Espacio inferior para que el último mensaje no quede oculto por la barra de entrada */
    .chat-messages {
        padding-bottom: 100px;
        max-height: calc(100vh - 200px);
        overflow-y: auto;
    }
    
    /* Mejor espaciado para los mensajes */
    .stChatMessage {
        margin-bottom: 1.5rem;
    }
    
    /* Scroll más suave */
    .chat-messages::-webkit-scrollbar {
        width: 6px;
    }
    
    .chat-messages::-webkit-scrollbar-track {
        background: var(--secondary-background-color);
        border-radius: 3px;
    }
    
    .chat-messages::-webkit-scrollbar-thumb {
        background: var(--text-color);
        border-radius: 3px;
        opacity: 0.5;
    }
    
    .chat-messages::-webkit-scrollbar-thumb:hover {
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

# Función para cargar PDFs procesados previamente
def load_existing_pdfs(embedding_manager_instance):
    """Cargar información de PDFs que ya fueron procesados anteriormente"""
    processed_pdfs = []

    # Directorio donde se guardan los PDFs
    pdf_dir = "data/uploaded_pdfs"

    if os.path.exists(pdf_dir):
        # Obtener lista de archivos PDF en el directorio
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]

        # Para cada archivo PDF encontrado, obtener información del embedding manager
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_file)
            if os.path.exists(pdf_path):
                # Obtener información del archivo
                file_stats = os.stat(pdf_path)
                processed_time = datetime.fromtimestamp(file_stats.st_mtime)

                # Contar chunks en el embedding manager para este documento
                chunks_count = len(
                    [doc for doc in embedding_manager_instance.documents
                        if doc.get('document') == pdf_file])

                if chunks_count > 0:  # Solo agregar si tiene chunks procesados
                    processed_pdfs.append({
                        'name': pdf_file,
                        'chunks': chunks_count,
                        'processed_at': processed_time.strftime("%Y-%m-%d %H:%M")
                    })

    return processed_pdfs

# Funciones para manejar la persistencia del historial de chat
def save_chat_history(history_data):
    """Guardar el historial de chat en un archivo"""
    try:
        chat_directory = "data/chat_history"
        os.makedirs(chat_directory, exist_ok=True)

        # Asegurar que history_data sea una lista válida
        if not isinstance(history_data, list):
            history_data = []

        # Crear nombre de archivo con timestamp solo si hay datos
        if len(history_data) > 0:
            timestamp = datetime.now().strftime("%Y%m%d")
            chat_file = os.path.join(chat_directory, f"chat_history_{timestamp}.json")

            with open(chat_file, 'w', encoding='utf-8') as file:
                json.dump(history_data, file, ensure_ascii=False, indent=2)

        # Siempre actualizar el archivo "último chat" (incluso si está vacío)
        latest_file = os.path.join(chat_directory, "latest_chat.json")
        with open(latest_file, 'w', encoding='utf-8') as file:
            json.dump(history_data, file, ensure_ascii=False, indent=2)

    except (IOError, OSError) as e:
        print(f"Error guardando historial de chat: {e}")

def load_chat_history():
    """Cargar el último historial de chat guardado"""
    try:
        chat_file = "data/chat_history/latest_chat.json"
        if os.path.exists(chat_file):
            with open(chat_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                # Verificar que sea una lista válida
                if isinstance(data, list):
                    return data
                else:
                    print("Archivo de historial inválido, devolviendo lista vacía")
                    return []
    except (IOError, OSError, json.JSONDecodeError) as e:
        print(f"Error cargando historial de chat: {e}")
        # Si hay error, eliminar el archivo corrupto
        try:
            chat_file = "data/chat_history/latest_chat.json"
            if os.path.exists(chat_file):
                os.remove(chat_file)
        except (FileNotFoundError, PermissionError, OSError):
            pass

    return []

def verify_and_clean_chat_state():
    """Verificar y limpiar el estado del chat si hay inconsistencias"""
    if 'chat_history' in st.session_state:
        # Si el historial en sesión no es una lista válida, limpiarlo
        if not isinstance(st.session_state.chat_history, list):
            st.session_state.chat_history = []
            save_chat_history(st.session_state.chat_history)

        # Si el historial está vacío pero existe el archivo, verificar consistencia
        if len(st.session_state.chat_history) == 0:
            chat_file = "data/chat_history/latest_chat.json"
            if os.path.exists(chat_file):
                try:
                    with open(chat_file, 'r', encoding='utf-8') as file:
                        file_data = json.load(file)
                        if isinstance(file_data, list) and len(file_data) > 0:
                            # Hay datos en el archivo pero no en la sesión, cargar del archivo
                            st.session_state.chat_history = file_data
                except (IOError, OSError, json.JSONDecodeError):
                    # Si hay error, eliminar el archivo corrupto
                    try:
                        os.remove(chat_file)
                    except (FileNotFoundError, PermissionError, OSError):
                        pass

def get_saved_chat_sessions():
    """Obtener lista de sesiones de chat guardadas"""
    chat_sessions = []
    chat_directory = "data/chat_history"

    if os.path.exists(chat_directory):
        for filename in os.listdir(chat_directory):
            if filename.startswith("chat_history_") and filename.endswith(".json"):
                try:
                    filepath = os.path.join(chat_directory, filename)
                    file_stats = os.stat(filepath)
                    created_time = datetime.fromtimestamp(file_stats.st_mtime)

                    # Cargar el archivo para contar mensajes
                    with open(filepath, 'r', encoding='utf-8') as file:
                        chat_data = json.load(file)
                        message_count = len(chat_data)

                    chat_sessions.append({
                        'filename': filename,
                        'date': created_time.strftime("%Y-%m-%d %H:%M"),
                        'messages': message_count
                    })
                except (IOError, OSError, json.JSONDecodeError):
                    continue

    return sorted(chat_sessions, key=lambda x: x['date'], reverse=True)

# Estado inicial de la sesión
if 'chat_history' not in st.session_state:
    # Cargar el último historial de chat guardado
    st.session_state.chat_history = load_chat_history()
if 'processed_pdfs' not in st.session_state:
    st.session_state.processed_pdfs = []
if 'embedding_manager' not in st.session_state:
    st.session_state.embedding_manager = None

# Verificar y limpiar inconsistencias en el estado del chat
verify_and_clean_chat_state()

@st.cache_resource
def get_managers(api_key):
    '''Inicializa las clases necesarias y las guarda en caché'''
    processor = PDFProcessor()
    embeddings = EmbeddingManager()
    chat = ChatManager(api_key=api_key)
    language = LanguageManager()
    return processor, embeddings, chat, language

pdf_processor, embedding_manager, chat_manager, language_manager = get_managers(groq_api_key)

# Cargar PDFs procesados previamente si la lista está vacía
if not st.session_state.processed_pdfs:
    st.session_state.processed_pdfs = load_existing_pdfs(embedding_manager)

# Fija el idioma directamente a español (ya no hay opción para elegir)
st.session_state.language = 'es'
lang = language_manager.get_text(st.session_state.language)

# Título principal
st.title(f"🎓 {lang['title']}")
st.markdown(f"*{lang['subtitle']}*")

# Sidebar para subir y gestionar archivos PDF
with st.sidebar:
    st.header(lang['pdf_management'])

    uploaded_files = st.file_uploader(
        lang['upload_pdfs'],
        type=['pdf'],
        accept_multiple_files=True,
        help=lang['upload_help']
    )

    # Procesamiento de archivos PDF subidos
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in [pdf['name'] for pdf in st.session_state.processed_pdfs]:
                with st.spinner(f"{lang['processing']} {uploaded_file.name}..."):
                    try:
                        # Guarda el archivo localmente
                        FILE_PATH = f"data/uploaded_pdfs/{uploaded_file.name}"
                        os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
                        with open(FILE_PATH, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        # Procesa el PDF y genera embeddings
                        chunks = pdf_processor.process_pdf(FILE_PATH)
                        embedding_manager.add_documents(chunks, uploaded_file.name)

                        # Guarda los datos del archivo procesado
                        st.session_state.processed_pdfs.append({
                            'name': uploaded_file.name,
                            'chunks': len(chunks),
                            'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M")
                        })

                        st.success(f"✅ {uploaded_file.name} {lang['processed_successfully']}")
                    except (IOError, OSError) as e:
                        st.error(f"❌ {lang['error_processing']} {uploaded_file.name}: {str(e)}")
                    except (ValueError, TypeError) as e:
                        st.error(f"❌ Error inesperado al procesar {uploaded_file.name}: {str(e)}")

    # Muestra los PDFs procesados en un expander colapsable
    if st.session_state.processed_pdfs:
        with st.expander(
            f"📁 {lang['processed_pdfs']} ({len(st.session_state.processed_pdfs)} archivos)",
            expanded=False):
            for pdf in st.session_state.processed_pdfs:
                with st.container():
                    col_info, col_action = st.columns([3, 1])

                    with col_info:
                        st.write(f"📄 **{pdf['name']}**")
                        CHUNKS_INFO = f"{lang['chunks']}: {pdf['chunks']}"
                        PROCESSED_INFO = f"{lang['processed_at']}: {pdf['processed_at']}"
                        st.caption(f"{CHUNKS_INFO} | {PROCESSED_INFO}")

                    with col_action:
                        if st.button(
                                "🗑️",
                                key=f"delete_{pdf['name']}",
                                help=f"Eliminar {pdf['name']}"):
                            embedding_manager.remove_document(pdf['name'])
                            st.session_state.processed_pdfs = [
                                p for p in st.session_state.processed_pdfs
                                    if p['name'] != pdf['name']]
                            try:
                                os.remove(f"data/uploaded_pdfs/{pdf['name']}")
                            except (FileNotFoundError, PermissionError):
                                # Archivo no encontrado o sin permisos, continuar sin error
                                pass
                            st.rerun()

                    st.divider()

    # Botón para limpiar todos los documentos y datos
    if st.session_state.processed_pdfs:
        st.markdown("---")  # Separador visual
        if st.button(lang['clear_all'], type="secondary", use_container_width=True):
            embedding_manager.clear_all()
            st.session_state.processed_pdfs = []
            st.session_state.chat_history = []

            # Limpiar todos los archivos de historial de chat
            try:
                CHAT_DIR = "data/chat_history"
                if os.path.exists(CHAT_DIR):
                    shutil.rmtree(CHAT_DIR)
                    os.makedirs(CHAT_DIR, exist_ok=True)
            except (FileNotFoundError, PermissionError, OSError):
                pass

            # Guardar el historial vacío (recrear el archivo latest_chat.json vacío)
            save_chat_history(st.session_state.chat_history)

            try:
                shutil.rmtree("data/uploaded_pdfs")
                os.makedirs("data/uploaded_pdfs", exist_ok=True)
            except (FileNotFoundError, PermissionError, OSError):
                # Error al limpiar archivos, continuar sin error crítico
                pass
            st.rerun()

    st.markdown("---")  # Separador antes de las conversaciones guardadas

    # Sección para gestionar conversaciones guardadas - colapsable
    saved_sessions = get_saved_chat_sessions()

    with st.expander(
            f"💬 Conversaciones Guardadas ({len(saved_sessions)} sesiones)", expanded=False):
        if saved_sessions:
            for session in saved_sessions[:5]:  # Mostrar solo las últimas 5
                with st.container():
                    st.write(f"📅 **{session['date']}** - {session['messages']} mensajes")
                    st.caption(f"Archivo: {session['filename']}")

                    col_load, col_delete = st.columns(2)

                    with col_load:
                        if st.button("📂 Cargar", key=f"load_{session['filename']}"):
                            try:
                                with open(
                                    f"data/chat_history/{session['filename']}", 'r',
                                    encoding='utf-8'
                                ) as f:
                                    loaded_history = json.load(f)
                                    st.session_state.chat_history = loaded_history
                                    save_chat_history(st.session_state.chat_history)  # Hacer backup
                                    st.success("✅ Conversación cargada")
                                    st.rerun()
                            except (IOError, OSError, json.JSONDecodeError) as e:
                                st.error(f"❌ Error cargando conversación: {e}")

                    with col_delete:
                        if st.button("🗑️ Eliminar", key=f"delete_session_{session['filename']}"):
                            try:
                                os.remove(f"data/chat_history/{session['filename']}")
                                st.success("✅ Conversación eliminada")
                                st.rerun()
                            except (FileNotFoundError, PermissionError) as e:
                                st.error(f"❌ Error eliminando conversación: {e}")

                    st.divider()
        else:
            st.info("No hay conversaciones guardadas aún")

# Sección principal: interfaz de chat
col1, col2 = st.columns([3, 1])

with col1:
    st.header(lang['chat_interface'])

    # Contenedor para el historial de chat con scroll independiente
    st.markdown('<div class="chat-messages">', unsafe_allow_html=True)

    if st.session_state.chat_history:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("sources"):
                    with st.expander(lang['sources']):
                        for source in message["sources"]:
                            document_info = (
                                f"📄 **{source['document']}** - "
                                f"{lang['relevance']}: {source['score']:.2f}"
                            )
                            st.write(document_info)
                            st.write(f"*{source['content'][:200]}...*")
    else:
        st.info("¡Hola! Sube algunos PDFs y comienza a hacer preguntas.")

    st.markdown('</div>', unsafe_allow_html=True)

    # Campo para ingresar pregunta - FIJO en la parte inferior
    if prompt := st.chat_input(lang['ask_question']):
        if not st.session_state.processed_pdfs:
            st.warning(lang['no_pdfs_warning'])
        else:
            # Agregar mensaje del usuario
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            save_chat_history(st.session_state.chat_history)

            # Generar respuesta del asistente
            with st.spinner(lang['generating_response']):
                try:
                    response, sources = chat_manager.get_response(
                        prompt,
                        embedding_manager,
                        st.session_state.language
                    )

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources
                    })

                    # Guardar automáticamente el historial de chat
                    save_chat_history(st.session_state.chat_history)

                    # Forzar actualización para mostrar la nueva respuesta
                    st.rerun()

                except (KeyError, ValueError) as e:
                    ERROR_MSG = f"{lang['error_generating']}: Error de datos - {str(e)}"
                    st.error(ERROR_MSG)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": ERROR_MSG
                    })
                    save_chat_history(st.session_state.chat_history)
                except (ConnectionError, TimeoutError) as e:
                    ERROR_MSG = f"{lang['error_generating']}: Error inesperado - {str(e)}"
                    st.error(ERROR_MSG)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": ERROR_MSG
                    })
                    save_chat_history(st.session_state.chat_history)

# Columna derecha: estadísticas y configuración
with col2:
    st.header(lang['statistics'])

    if st.session_state.processed_pdfs:
        total_chunks = sum(pdf['chunks'] for pdf in st.session_state.processed_pdfs)
        st.metric(lang['total_pdfs'], len(st.session_state.processed_pdfs))
        st.metric(lang['total_chunks'], total_chunks)
        st.metric(lang['total_conversations'], len(st.session_state.chat_history))
    else:
        st.info(lang['no_statistics'])

    st.header(lang['configuration'])

    if groq_api_key:
        st.success("✅ Clave de API configurada correctamente")
    else:
        st.error("❌ No se ha configurado la clave de API (ni en secrets.toml ni en .env)")

    # Botones para gestionar el chat
    if st.session_state.chat_history:
        # Crear dos columnas para los botones
        col_new, col_clear = st.columns(2)

        with col_new:
            if st.button("🆕 Nuevo Chat", type="primary"):
                # Guardar la conversación actual antes de empezar una nueva
                if len(st.session_state.chat_history) > 0:
                    save_chat_history(st.session_state.chat_history)

                # Limpiar el historial para empezar nuevo chat
                st.session_state.chat_history = []

                # Guardar el nuevo historial vacío
                save_chat_history(st.session_state.chat_history)

                st.success("✅ Nuevo chat iniciado")
                st.rerun()

        with col_clear:
            if st.button("🗑️ Limpiar Chat", type="secondary"):
                # Limpiar completamente el historial
                st.session_state.chat_history = []

                # Guardar el historial vacío en todos los archivos
                save_chat_history(st.session_state.chat_history)

                # También eliminar el archivo latest_chat.json para asegurar limpieza completa
                try:
                    LATEST_FILE = "data/chat_history/latest_chat.json"
                    if os.path.exists(LATEST_FILE):
                        os.remove(LATEST_FILE)
                except (FileNotFoundError, PermissionError):
                    pass

                # Mostrar mensaje de confirmación
                st.success("✅ Historial de chat limpiado completamente")
                st.rerun()
    else:
        # Si no hay historial, solo mostrar botón de nuevo chat (aunque no es necesario)
        st.info("💡 Comienza una nueva conversación escribiendo tu primera pregunta")

# Pie de página
st.markdown("---")
st.markdown(f"*{lang['footer']}*")
