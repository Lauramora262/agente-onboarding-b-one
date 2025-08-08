import streamlit as st
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- LÓGICA DEL PROGRAMA ---

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

# --- INTERFAZ DE LA APLICACIÓN WEB ---

st.set_page_config(page_title="Agente de Onboarding B-One", page_icon="🤖")
st.title("¡Bienvenido/a a la empresa!")
st.markdown("### ¡Hola, soy B-One! 🤖\nTu agente de onboarding personal. ¡Pregúntame lo que necesites!")
st.divider()

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    DOCUMENT_IDS = st.secrets["DOCUMENT_IDS"]
    servicio_drive = autenticar_y_obtener_servicio_drive()
    contexto_docs = obtener_contenido_documentos(servicio_drive, DOCUMENT_IDS)
except KeyError as e:
    st.error(f"Falta un secreto en la configuración de Streamlit. Revisa la clave: {e}")
    st.stop()

if contexto_docs:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error al configurar la API de Gemini: {e}")
        st.stop()

    pregunta_usuario = st.text_input("Haz tu pregunta aquí:", key="pregunta")

    if pregunta_usuario:
        prompt_final = f"""
        Eres "B-One", el colega robot más enrollado. Tu tono es informal, gamberro y positivo. Usa emojis. 😉
        Basa tus respuestas ÚNICAMENTE en la info de los documentos.
        Si no sabes la respuesta, di: "Uups, sobre eso no me han pasado el chivatazo. 😅"

        CONTEXTO:
        {contexto_docs}

        PREGUNTA:
        {pregunta_usuario}

        RESPUESTA DE B-ONE:
        """
        
        with st.spinner("B-One está buscando en sus archivos... 🧠"):
            response = model.generate_content(prompt_final)
            st.markdown(response.text)
