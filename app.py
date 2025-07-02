'''Agente Chatbot Educativo IA'''
import os
import shutil
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
    st.error("❌ No se pudo cargar la clave GROQ_API_KEY. Asegúrate de tener un archivo .env o secrets.toml configurado.")

# Configuración de la página Streamlit
st.set_page_config(
    page_title="Asistente Educativo IA",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Estado inicial de la sesión
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'processed_pdfs' not in st.session_state:
    st.session_state.processed_pdfs = []
if 'embedding_manager' not in st.session_state:
    st.session_state.embedding_manager = None

# Inicializa las clases necesarias y las guarda en caché
@st.cache_resource
def get_managers(api_key):
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

    # Muestra los PDFs procesados
    if st.session_state.processed_pdfs:
        st.subheader(lang['processed_pdfs'])
        for pdf in st.session_state.processed_pdfs:
            with st.expander(f"📄 {pdf['name']}"):
                st.write(f"**{lang['chunks']}:** {pdf['chunks']}")
                st.write(f"**{lang['processed_at']}:** {pdf['processed_at']}")
                if st.button(f"{lang['delete']} {pdf['name']}", key=f"delete_{pdf['name']}"):
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

    # Botón para limpiar todos los documentos y datos
    if st.session_state.processed_pdfs:
        if st.button(lang['clear_all'], type="secondary"):
            embedding_manager.clear_all()
            st.session_state.processed_pdfs = []
            st.session_state.chat_history = []
            try:
                shutil.rmtree("data/uploaded_pdfs")
                os.makedirs("data/uploaded_pdfs", exist_ok=True)
            except (FileNotFoundError, PermissionError, OSError):
                # Error al limpiar archivos, continuar sin error crítico
                pass
            st.rerun()

# Sección principal: interfaz de chat
col1, col2 = st.columns([3, 1])

with col1:
    st.header(lang['chat_interface'])

    # Muestra el historial del chat
    if st.session_state.chat_history:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("sources"):
                    with st.expander(lang['sources']):
                        for source in message["sources"]:
                            st.write(f"📄 **{source['document']}** - {lang['relevance']}: {source['score']:.2f}")
                            st.write(f"*{source['content'][:200]}...*")

    # Campo para ingresar pregunta
    if prompt := st.chat_input(lang['ask_question']):
        if not st.session_state.processed_pdfs:
            st.warning(lang['no_pdfs_warning'])
        else:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generación de respuesta por el asistente
            with st.chat_message("assistant"):
                with st.spinner(lang['generating_response']):
                    try:
                        response, sources = chat_manager.get_response(
                            prompt,
                            embedding_manager,
                            st.session_state.language
                        )

                        st.markdown(response)

                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": response,
                            "sources": sources
                        })

                        if sources:
                            with st.expander(lang['sources']):
                                for source in sources:
                                    st.write(f"📄 **{source['document']}** - {lang['relevance']}: {source['score']:.2f}")
                                    st.write(f"*{source['content'][:200]}...*")
                    except (KeyError, ValueError) as e:
                        ERROR_MSG = f"{lang['error_generating']}: Error de datos - {str(e)}"
                        st.error(ERROR_MSG)
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": ERROR_MSG
                        })
                    except (ConnectionError, TimeoutError) as e:
                        ERROR_MSG = f"{lang['error_generating']}: Error inesperado - {str(e)}"
                        st.error(ERROR_MSG)
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": ERROR_MSG
                        })

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



    # Botón para limpiar el historial del chat
    if st.session_state.chat_history:
        if st.button(lang['clear_chat'], type="secondary"):
            st.session_state.chat_history = []
            st.rerun()

# Pie de página
st.markdown("---")
st.markdown(f"*{lang['footer']}*")
