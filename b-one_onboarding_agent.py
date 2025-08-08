import streamlit as st
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime

@st.cache_resource
def autenticar_y_obtener_servicio_drive():
    """Autentica usando la Cuenta de Servicio desde los secretos de Streamlit."""
    try:
        creds_json = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"Error de autenticación con la Cuenta de Servicio: {e}")
        return None

@st.cache_data
def obtener_contenido_documentos(_servicio_drive, ids_documentos):
    if not _servicio_drive:
        return None
    contexto_completo = ""
    try:
        with st.spinner("Accediendo a Google Drive..."):
            for doc_id in ids_documentos:
                request = _servicio_drive.files().export_media(fileId=doc_id, mimeType="text/plain")
                contenido_bytes = request.execute()
                contenido_texto = contenido_bytes.decode('utf-8')
                contexto_completo += f"\n--- INICIO: {doc_id} ---\n{contenido_texto}\n--- FIN: {doc_id} ---\n"
        st.success("¡Documentos listos!")
        return contexto_completo
    except HttpError as error:
        st.error(f"Error al acceder a un documento: {error}. ¿Compartiste el doc con el email del robot?")
        return None

def registrar_pregunta_sin_respuesta(pregunta):
    """Añade la pregunta a un archivo de registro."""
    with open("log_preguntas.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - {pregunta}\n")

st.set_page_config(page_title="Agente de Onboarding B-One", page_icon="🤖")
st.title("¡Bienvenido/a a la empresa!")
st.markdown("### ¡Hola, soy B-One! 🤖\nTu agente de onboarding personal. ¡Pregúntame lo que necesites!")
st.divider()

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    DOCUMENT_IDS = st.secrets["DOCUMENT_IDS"]
    servicio_drive = autenticar_y_obtener_servicio_drive()
    contexto_docs = obtener_
