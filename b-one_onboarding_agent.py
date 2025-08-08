# --- Herramientas que vamos a necesitar ---
import os.path
import streamlit as st
import google.generativeai as genai
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- NO HAY CONFIGURACIÓN AQUÍ - TODO ESTÁ EN LOS SECRETOS ---

# --- LÓGICA DEL PROGRAMA (El motor del agente) ---

@st.cache_resource
def autenticar_y_obtener_servicio_drive():
    # Las credenciales se cargan desde los secretos de Streamlit
    # AJUSTE IMPORTANTE: Usamos "installed" para que coincida con tu archivo
    creds_json = {
        "installed": {
            "client_id": st.secrets["installed"]["client_id"],
            "project_id": st.secrets["installed"]["project_id"],
            "auth_uri": st.secrets["installed"]["auth_uri"],
            "token_uri": st.secrets["installed"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["installed"]["auth_provider_x509_cert_url"],
            "client_secret": st.secrets["installed"]["client_secret"],
            "redirect_uris": st.secrets["installed"]["redirect_uris"]
        }
    }
    
    with open("credentials.json", "w") as f:
        json.dump(creds_json, f)

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/drive.readonly"])
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Este flujo requiere una ejecución local la primera vez para generar token.json
            # Si en la nube da problemas, la solución es ejecutarlo localmente una vez
            # y subir el archivo token.json generado a GitHub.
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", ["https://www.googleapis.com/auth/drive.readonly"]
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            
    os.remove("credentials.json")
    
    return build("drive", "v3", credentials=creds)

@st.cache_data
def obtener_contenido_documentos(_servicio_drive, ids_documentos):
    contexto_completo = ""
    try:
        with st.spinner("Accediendo a Google Drive para leer los documentos..."):
            for doc_id in ids_documentos:
                request = _servicio_drive.files().export_media(fileId=doc_id, mimeType="text/plain")
                contenido_bytes = request.execute()
                contenido_texto = contenido_bytes.decode('utf-8')
                contexto_completo += f"\n--- INICIO DEL DOCUMENTO: {doc_id} ---\n"
                contexto_completo += contenido_texto
                contexto_completo += f"\n--- FIN DEL DOCUMENTO: {doc_id} ---\n"
        st.success("¡Documentos listos para la consulta!")
        return contexto_completo
    except HttpError as error:
        st.error(f"Error al acceder a un documento: {error}.")
        return None

# --- INTERFAZ DE LA APLICACIÓN WEB ---

st.set_page_config(page_title="Agente de Onboarding B-One", page_icon="🤖")

st.title("¡Bienvenido/a a la empresa!")
st.markdown("""
### ¡Hola, soy B-One! 🤖
    
Tu nuevo agente de onboarding personal.
**Adelante, ¡pregunta lo que necesites!**
""")
st.divider()

try:
    servicio = autenticar_y_obtener_servicio_drive()
    DOCUMENT_IDS = st.secrets["DOCUMENT_IDS"]
    contexto_docs = obtener_contenido_documentos(servicio, DOCUMENT_IDS)
except Exception as e:
    st.error(f"No se pudo iniciar sesión con Google. Revisa tus secretos. Error: {e}")
    st.stop()

if contexto_docs:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error al configurar la API de Gemini. Revisa tu GEMINI_API_KEY en los secretos. Error: {e}")
        st.stop()

    pregunta_usuario = st.text_input("Haz tu pregunta aquí:", key="pregunta", placeholder="Ej: ¿Cuáles son los horarios de la oficina?")

    if pregunta_usuario:
        prompt_final = f"""
        Eres "B-One", el colega robot más enrollado de la empresa. Tu tono es informal, gamberro y positivo. Usa emojis. 😉
        Basa tus respuestas ÚNICA Y EXCLUSIVAMENTE en la información de los documentos.
        Si no encuentras la respuesta, di algo como: "Uups, sobre eso no me han pasado el chivatazo. Mejor pregúntale a un humano. 😅"

        CONTEXTO:
        {contexto_docs}

        PREGUNTA:
        {pregunta_usuario}

        RESPUESTA DE B-ONE:
        """
        
        with st.spinner("B-One está buscando en sus archivos... 🧠"):
            response = model.generate_content(prompt_final)
            st.markdown(response.text)
