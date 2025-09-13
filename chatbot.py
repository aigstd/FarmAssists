import streamlit as st
from openai import AzureOpenAI

# ==================== CONFIGURACIÓN ====================
# REEMPLAZA ESTAS VARIABLES CON TUS DATOS
ENDPOINT_URL = "https://gidoa-melknp6m-eastus2.openai.azure.com/"
API_KEY = "1UAACOGCIZo"  # 👈 REEMPLAZA CON TU API KEY
DEPLOYMENT_NAME = "gpt-4o"
SEARCH_ENDPOINT = "https://farmassistservicebasic.search.windows.net"
SEARCH_KEY = "QOzSeBPrWOU"  # 👈 REEMPLAZA CON TU SEARCH KEY

SEARCH_INDEX = ("skinprodindex")

# Configuración de la página
st.set_page_config(
    page_title="FarmAssist - Tu recomendador de parafarmacia",
    page_icon="💊",
    layout="wide"
)


class AzureChatbot:
    def __init__(self, endpoint, api_key, deployment, search_endpoint, search_key, search_index):
        """Inicializar el chatbot con autenticación por API Key"""
        try:
            self.client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version="2025-01-01-preview",
            )
            self.deployment = deployment
            self.search_endpoint = search_endpoint
            self.search_key = search_key
            self.search_index = search_index
            self.configured = True
        except Exception as e:
            st.error(f"Error al configurar el chatbot: {e}")
            self.configured = False

    def get_response(self, messages):
        """Obtener respuesta del modelo con Azure AI Search"""
        if not self.configured:
            return "Error: Chatbot no configurado correctamente"

        try:
            completion = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                max_tokens=1638,
                temperature=0.7,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
                stream=False,
                extra_body={
                    "data_sources": [{
                        "type": "azure_search",
                        "parameters": {
                            "endpoint": self.search_endpoint,
                            "index_name": self.search_index,
                            "semantic_configuration": "default",
                            "query_type": "vector_semantic_hybrid",
                            "in_scope": True,
                            "strictness": 3,
                            "top_n_documents": 5,
                            "authentication": {
                                "type": "api_key",
                                "key": self.search_key
                            },
                            "embedding_dependency": {
                                "type": "deployment_name",
                                "deployment_name": "text-embedding-ada-002"
                            }
                        }
                    }]
                }
            )

            content = completion.choices[0].message.content

            # Procesar referencias a documentos si existen
            if hasattr(completion.choices[0].message, 'context') and completion.choices[0].message.context:
                # Si hay contexto con documentos, procesarlos
                return self._process_document_references(content, completion.choices[0].message.context)

            return content

        except Exception as e:
            return f"Error al obtener respuesta: {e}"

    def _process_document_references(self, content, context):
        """Procesar referencias a documentos y convertirlas en enlaces"""
        try:
            import re

            # Buscar referencias como [doc1], [doc2], etc.
            doc_pattern = r'\[doc(\d+)\]'
            matches = re.findall(doc_pattern, content)

            if matches and 'citations' in context:
                # Reemplazar referencias con enlaces
                for match in matches:
                    doc_num = int(match) - 1  # Los índices suelen empezar en 0
                    if doc_num < len(context['citations']):
                        citation = context['citations'][doc_num]
                        if 'url' in citation:
                            link = f"[📄 Documento {match}]({citation['url']})"
                            content = content.replace(f"[doc{match}]", link)
                        elif 'filepath' in citation:
                            # Si solo hay filepath, mostrar el nombre del archivo
                            filename = citation['filepath'].split('/')[-1]
                            content = content.replace(f"[doc{match}]", f"**📄 {filename}**")

            return content

        except Exception as e:
            # Si hay error procesando, devolver contenido original
            return content


def main():
    # Header con logo y título
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <img src="https://github.com/user-attachments/assets/675fa551-a828-41cc-a36a-0b76bad38cd4" 
                 width="120" height="120" style="margin-bottom: 10px;">
            <h1 style="color: #2E86C1; margin: 10px 0 5px 0;">💊 FarmAssist</h1>
            <p style="color: #7D8A97; font-size: 18px; margin: 0;">Tu recomendador de productos de parafarmacia</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Verificar si las keys están configuradas
    if API_KEY == "KEY_EXAMPLE_REEMPLAZA" or SEARCH_KEY == "KEY_EXAMPLE_REEMPLAZA":
        st.error("⚠️ **¡Configura tus API Keys!**")
        st.markdown("""
        ### 🔧 Para usar el chatbot:
        1. Abre el archivo del chatbot
        2. Busca las variables `API_KEY` y `SEARCH_KEY`
        3. Reemplaza `KEY_EXAMPLE_REEMPLAZA` con tus claves reales
        4. Guarda el archivo y recarga la página

        ### 📋 Variables a configurar:
        - `API_KEY`: Tu clave de Azure OpenAI
        - `SEARCH_KEY`: Tu clave de Azure AI Search
        """)
        st.stop()

    # Inicializar el chatbot
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = AzureChatbot(
            ENDPOINT_URL, API_KEY, DEPLOYMENT_NAME,
            SEARCH_ENDPOINT, SEARCH_KEY, SEARCH_INDEX
        )

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'response_times' not in st.session_state:
        st.session_state.response_times = []

    # Sidebar con información
    with st.sidebar:
        st.header("ℹ️ Información")

        if st.session_state.chatbot.configured:
            st.success("🟢 FarmAssist configurado")
        else:
            st.error("🔴 Error en la configuración")

        st.markdown("### 🔧 Configuración:")
        st.code(f"""
Endpoint: {ENDPOINT_URL.split('//')[-1].split('.')[0]}...
Model: {DEPLOYMENT_NAME}
Search Index: {SEARCH_INDEX}
        """)

        st.markdown("---")

        if st.button("🗑️ Limpiar historial", use_container_width=True):
            st.session_state.messages = []
            st.session_state.response_times = []
            st.rerun()

        st.markdown("---")

        with st.expander("💡 Consejos de uso"):
            st.markdown("""
            - Pregunta sobre productos específicos
            - FarmAssist tiene acceso a tu catálogo
            - Puedes hacer preguntas de seguimiento
            - El contexto se mantiene durante la conversación

            **Ejemplos de preguntas:**
            - "¿Tienes champús para cabello graso?"
            - "¿Cuáles son los ingredientes del producto X?"
            - "Recomiéndame algo para piel seca"
            - "¿Qué productos tienes para el acné?"
            - "¿Hay contraindicaciones en este medicamento?"
            """)

        with st.expander("🔧 Configuración avanzada"):
            st.markdown("""
            ### Para habilitar enlaces a documentos:

            **1. En tu índice de Azure AI Search, asegúrate de tener:**
            - Campo `url`: URL directa al documento
            - Campo `filepath`: Ruta del archivo
            - Campo `title`: Título del documento

            **2. Ejemplo de documento en el índice:**
            """)
            st.code("""
{
    "id": "doc1",
    "content": "Contenido del documento...",
    "url": "https://example.com/documento1.pdf",
    "title": "Manual de productos",
    "filepath": "/docs/manual.pdf"
}
            """, language="json")
            st.markdown("""
            **3. Las referencias aparecerán como:**
            - `[doc1]` → Se convierte en enlace si hay campo 'url'
            - `[doc2]` → Se muestra como archivo si solo hay 'filepath'
            """)

            if st.button("🧪 Probar conexión a Azure Search"):
                st.info("Función de prueba - implementar si necesitas diagnosticar la conexión")

        # Estadísticas de la conversación
        if st.session_state.messages:
            st.markdown("### 📊 Estadísticas:")
            user_msgs = len([m for m in st.session_state.messages if m["role"] == "user"])
            assistant_msgs = len([m for m in st.session_state.messages if m["role"] == "assistant"])
            st.metric("Preguntas realizadas", user_msgs)
            st.metric("Respuestas de FarmAssist", assistant_msgs)

            # Estadísticas de tiempo de respuesta
            if st.session_state.response_times:
                avg_time = sum(st.session_state.response_times) / len(st.session_state.response_times)
                st.metric("⏱️ Tiempo promedio", f"{avg_time:.2f}s")

                # Tabla de tiempos de respuesta
                st.markdown("### ⏱️ Tiempos de respuesta:")

                # Crear DataFrame para la tabla
                import pandas as pd

                df_times = pd.DataFrame({
                    'Pregunta': [f"Pregunta {i + 1}" for i in range(len(st.session_state.response_times))],
                    'Tiempo (s)': [f"{time:.2f}" for time in st.session_state.response_times]
                })

                # Mostrar tabla scrollable
                st.dataframe(
                    df_times,
                    use_container_width=True,
                    height=200,  # Altura fija para scroll
                    hide_index=True
                )

    # Verificar si el chatbot está configurado
    if not st.session_state.chatbot.configured:
        st.error("⚠️ Error en la configuración del chatbot. Verifica tus API keys.")
        st.stop()

    # Mostrar historial de mensajes
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Mensaje de bienvenida si no hay mensajes
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown(
                "¡Hola! 👋 Soy **FarmAssist**, tu asistente especializado en productos de parafarmacia. ¿En qué puedo ayudarte hoy? 💊")

    # Input del usuario
    if prompt := st.chat_input("Escribe tu consulta aquí... 💬"):
        import time

        # Agregar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Obtener respuesta del asistente con medición de tiempo
        with st.chat_message("assistant"):
            with st.spinner("🔍 Buscando en el catálogo de parafarmacia..."):
                # Medir tiempo de inicio
                start_time = time.time()

                response = st.session_state.chatbot.get_response(st.session_state.messages)

                # Medir tiempo de fin y calcular duración
                end_time = time.time()
                response_time = end_time - start_time

                # Guardar tiempo de respuesta
                st.session_state.response_times.append(response_time)

                # Mostrar respuesta
                st.markdown(response)

                # Mostrar tiempo de respuesta actual
                st.caption(f"⏱️ Tiempo de respuesta: {response_time:.2f} segundos")

                # Mostrar información adicional si hay referencias
                if "[doc" in response:
                    with st.expander("📚 Información sobre las referencias"):
                        st.info("""
                        **Sobre las referencias [docX]:**

                        Las referencias como [doc1], [doc2], etc. indican que la información proviene 
                        de documentos específicos en tu catálogo de Azure AI Search.

                        **Para configurar enlaces a documentos:**
                        1. Asegúrate de que tus documentos en Azure AI Search tengan un campo 'url' o 'filepath'
                        2. FarmAssist intentará convertir automáticamente las referencias en enlaces clicables
                        3. Si no aparecen enlaces, revisa la configuración de tu índice de búsqueda
                        """)

                        # Mostrar botón para obtener más detalles
                        if st.button("🔍 Ver detalles técnicos"):
                            st.code(f"""
Endpoint de búsqueda: {SEARCH_ENDPOINT}
Índice: {SEARCH_INDEX}
Configuración: vector_semantic_hybrid
Documentos máximos: 5
                            """, language="yaml")

        # Agregar respuesta del asistente
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Scroll automático al último mensaje
        st.rerun()


if __name__ == "__main__":
    main()