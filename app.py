import streamlit as st
from dotenv import load_dotenv
import os
load_dotenv()  # Carga variables de entorno desde un archivo .env

# Muestra por consola si se cargó correctamente la clave de API
print("✅ Clave cargada:", os.getenv("GROQ_API_KEY"))

import json
from datetime import datetime

# Importa clases propias del proyecto
from utils.pdf_processor import PDFProcessor
from utils.embedding_manager import EmbeddingManager
from utils.chat_manager import ChatManager
from utils.language_manager import LanguageManager

# Configuración de la página Streamlit
st.set_page_config(
    page_title="Asistente Educativo IA",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estado inicial de la sesión
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'processed_pdfs' not in st.session_state:
    st.session_state.processed_pdfs = []
if 'embedding_manager' not in st.session_state:
    st.session_state.embedding_manager = None

# Inicializa las clases necesarias y las guarda en caché
@st.cache_resource
def get_managers():
    pdf_processor = PDFProcessor()
    embedding_manager = EmbeddingManager()
    chat_manager = ChatManager()
    language_manager = LanguageManager()
    return pdf_processor, embedding_manager, chat_manager, language_manager

pdf_processor, embedding_manager, chat_manager, language_manager = get_managers()

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
                        file_path = f"data/uploaded_pdfs/{uploaded_file.name}"
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        # Procesa el PDF y genera embeddings
                        chunks = pdf_processor.process_pdf(file_path)
                        embedding_manager.add_documents(chunks, uploaded_file.name)

                        # Guarda los datos del archivo procesado
                        st.session_state.processed_pdfs.append({
                            'name': uploaded_file.name,
                            'chunks': len(chunks),
                            'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M")
                        })

                        st.success(f"✅ {uploaded_file.name} {lang['processed_successfully']}")
                    except Exception as e:
                        st.error(f"❌ {lang['error_processing']} {uploaded_file.name}: {str(e)}")

    # Muestra los PDFs procesados
    if st.session_state.processed_pdfs:
        st.subheader(lang['processed_pdfs'])
        for pdf in st.session_state.processed_pdfs:
            with st.expander(f"📄 {pdf['name']}"):
                st.write(f"**{lang['chunks']}:** {pdf['chunks']}")
                st.write(f"**{lang['processed_at']}:** {pdf['processed_at']}")
                if st.button(f"{lang['delete']} {pdf['name']}", key=f"delete_{pdf['name']}"):
                    embedding_manager.remove_document(pdf['name'])
                    st.session_state.processed_pdfs = [p for p in st.session_state.processed_pdfs if p['name'] != pdf['name']]
                    try:
                        os.remove(f"data/uploaded_pdfs/{pdf['name']}")
                    except:
                        pass
                    st.rerun()

    # Botón para limpiar todos los documentos y datos
    if st.session_state.processed_pdfs:
        if st.button(lang['clear_all'], type="secondary"):
            embedding_manager.clear_all()
            st.session_state.processed_pdfs = []
            st.session_state.chat_history = []
            try:
                import shutil
                shutil.rmtree("data/uploaded_pdfs")
                os.makedirs("data/uploaded_pdfs", exist_ok=True)
            except:
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
                    except Exception as e:
                        error_msg = f"{lang['error_generating']}: {str(e)}"
                        st.error(error_msg)
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": error_msg
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

    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if groq_api_key:
        st.success(f"✅ {lang['api_configured']}")
    else:
        st.error(f"❌ {lang['api_not_configured']}")
        st.info(lang['api_help'])

    # Botón para limpiar el historial del chat
    if st.session_state.chat_history:
        if st.button(lang['clear_chat'], type="secondary"):
            st.session_state.chat_history = []
            st.rerun()

# Pie de página
st.markdown("---")
st.markdown(f"*{lang['footer']}*")
