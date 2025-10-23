import streamlit as st
import pandas as pd
import numpy as np
import os
import io
from PIL import Image

# --- 1. CONFIGURACIÓN INICIAL DE ARCHIVOS ---

# Archivo 1: Atletas y Marcas
EXCEL_FILE = 'atletas_data.xlsx' 
REQUIRED_COLUMNS = ['ID', 'Atleta', 'Contraseña', 'Rol', 'Sentadilla_RM', 'PressBanca_RM', 'PesoCorporal', 'Última_Fecha']

# Archivo 2: Calendario
CALENDAR_FILE = 'calendario_data.xlsx'
CALENDAR_REQUIRED_COLUMNS = ['Evento', 'Fecha', 'Detalle', 'Habilitado']

# Archivo 3: Pruebas Activas (Modularidad de la Calculadora)
PRUEBAS_FILE = 'pruebas_activas.xlsx'

# RUTA DEL LOGO
LOGO_PATH = 'logo.png' 


# --- 2. FUNCIONES DE CARGA DE DATOS (SIN LLAMADAS A ST.XYZ INTERNAS) ---

@st.cache_data(ttl=3600) 
def load_data():
    """Carga los datos de los atletas. Si no existe, lo crea."""
    df = pd.DataFrame()
    excel_exists = os.path.exists(EXCEL_FILE)
    status_message = None
    
    if excel_exists:
        try:
            df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
            
            missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                status_message = f"El archivo Excel de atletas existe, pero faltan columnas: {', '.join(missing_cols)}. Se añadirán vacías."
                for col in missing_cols:
                    df[col] = None
                    
            if not status_message:
                 status_message = "Datos de atletas cargados exitosamente."
            
        except Exception as e:
            status_message = f"Error al leer el archivo Excel de atletas ({e}). Se creará un archivo nuevo de ejemplo."
            excel_exists = False

    if not excel_exists or df.empty:
        # Crea un DataFrame de ejemplo
        status_message = f"Creando el archivo '{EXCEL_FILE}' de ejemplo con la estructura inicial..."
        data = {
            'ID': [1, 2, 3],
            'Atleta': ['Juan Pérez', 'Ana Gómez', 'Tu Nombre'],
            'Contraseña': ['1234', '5678', 'admin'], 
            'Rol': ['Atleta', 'Atleta', 'Entrenador'], 
            'Sentadilla_RM': [140.0, 95.0, 160.0],
            'PressBanca_RM': [100.0, 55.0, 115.0],
            'PesoCorporal': [80.0, 60.0, 90.0],
            'Última_Fecha': ['2023-10-15', '2023-10-10', '2023-10-12']
        }
        df = pd.DataFrame(data, columns=REQUIRED_COLUMNS) 
        
        df.to_excel(EXCEL_FILE, index=False, engine='openpyxl') 
        status_message = f"Archivo '{EXCEL_FILE}' creado con éxito."
        
    if 'Última_Fecha' in df.columns:
        df['Última_Fecha'] = pd.to_datetime(df['Última_Fecha'], errors='coerce') 

    return df, status_message 

@st.cache_data(ttl=600)
def load_calendar_data():
    """Carga los datos del calendario desde el archivo Excel. Si no existe, lo crea."""
    calendar_df = pd.DataFrame()
    excel_exists = os.path.exists(CALENDAR_FILE)
    
    if excel_exists:
        try:
            calendar_df = pd.read_excel(CALENDAR_FILE, engine='openpyxl')
        except:
             excel_exists = False

    if not excel_exists or calendar_df.empty:
        # Crea un DataFrame de ejemplo si no existe o hubo error
        data = {
            'Evento': ['Prueba de RM (Sentadilla/PB)', 'Evaluación de Resistencia', 'Reunión de Equipo'],
            'Fecha': ['2025-11-01', '2025-11-15', '2025-11-20'],
            'Detalle': ['Test de 1RM', 'Test de Cooper o 5K', 'Revisión de Mes'],
            'Habilitado': ['Sí', 'Sí', 'No']
        }
        calendar_df = pd.DataFrame(data, columns=CALENDAR_REQUIRED_COLUMNS) 
        calendar_df.to_excel(CALENDAR_FILE, index=False, engine='openpyxl') 

    if 'Habilitado' in calendar_df.columns:
        calendar_df['Habilitado'] = calendar_df['Habilitado'].astype(str).str.lower().str.strip() == 'sí'

    return calendar_df

@st.cache_data(ttl=3600)
def load_tests_data():
    """Carga la lista de pruebas activas para la calculadora."""
    status_message = None
    
    if not os.path.exists(PRUEBAS_FILE):
        # Crea archivo si no existe
        data = {
            'NombrePrueba': ['Sentadilla', 'Press Banca', 'Peso Muerto', 'Otro'],
            'ColumnaRM': ['Sentadilla_RM', 'PressBanca_RM', 'PesoMuerto_RM', 'N/A'],
            'Visible': ['Sí', 'Sí', 'No', 'Sí']
        }
        df_tests = pd.DataFrame(data)
        df_tests.to_excel(PRUEBAS_FILE, index=False, engine='openpyxl')
        status_message = f"Archivo '{PRUEBAS_FILE}' creado con éxito."
    
    try:
        df_tests = pd.read_excel(PRUEBAS_FILE, engine='openpyxl')
    except Exception as e:
        status_message = f"Error al cargar {PRUEBAS_FILE}: {e}"
        return pd.DataFrame(), status_message 

    df_tests['Visible'] = df_tests['Visible'].astype(str).str.lower().str.strip() == 'sí'
    
    return df_tests[df_tests['Visible'] == True], status_message


# --- 3. CARGA DE DATOS AL INICIO DE LA APP Y MUESTREO DE TOASTS ---

df_atletas, initial_status = load_data() 
df_calendario = load_calendar_data()
df_pruebas, tests_status = load_tests_data() 


# --- 4. FUNCIONES AUXILIARES ---

def check_login(username, password):
    """Verifica el usuario y contraseña contra el DataFrame."""
    user_row = df_atletas[df_atletas['Atleta'].str.lower() == username.lower()]
    
    if not user_row.empty:
        if user_row['Contraseña'].iloc[0] == password:
            return True, user_row['Rol'].iloc[0], user_row['Atleta'].iloc[0]
    return False, None, None

def login_form():
    """Muestra el formulario de inicio de sesión en el cuerpo principal de la app."""
    # NO se usa st.sidebar aquí
    with st.form("login_form"):
        username = st.text_input("Usuario (Nombre del Atleta)")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            success, rol, atleta_nombre = check_login(username, password)
            if success:
                st.session_state['logged_in'] = True
                st.session_state['rol'] = rol
                st.session_state['atleta_nombre'] = atleta_nombre
                st.success(f"Bienvenido, {atleta_nombre} ({rol})!")
                st.rerun() 
            else:
                st.error("Usuario o Contraseña incorrectos.")

def logout():
    """Cierra la sesión del usuario."""
    if 'logged_in' in st.session_state and st.session_state['logged_in']:
        st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.clear())
        st.sidebar.markdown(f"**Conectado como:** {st.session_state['atleta_nombre']}")
        st.sidebar.markdown(f"**Rol:** {st.session_state['rol']}")

def calcular_porcentaje_rm(rm_value, porcentaje):
    """Calcula el peso basado en un porcentaje del RM, redondeando a 0.5 kg."""
    if rm_value > 0 and 0 <= porcentaje <= 100:
        peso = rm_value * (porcentaje / 100)
        return round(peso * 2) / 2
    return 0


# --- 5. INTERFAZ PRINCIPAL DE STREAMLIT ---

st.set_page_config(layout="wide", page_title="Gestión de Rendimiento Atleta")

# Muestra los mensajes de estado inicial 
st.toast(initial_status, icon="📝")
if tests_status:
    st.toast(tests_status, icon="🛠️")

# Inicializar el estado de la sesión
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ----------------------------------------------------------------------
# --- PANTALLA DE ACCESO/BIENVENIDA (LOGO IZQUIERDA, TEXTO CENTRADO) ---
# ----------------------------------------------------------------------
if not st.session_state['logged_in']:
    
    # Fila Superior: Logo a la izquierda (1) y Espaciador (10)
    logo_col, spacer_col = st.columns([1, 10])
    with logo_col:
        st.image(LOGO_PATH, width=120) 
    
    st.markdown("---") 

    # Contenido Central: [Espaciador (1), Contenido (3), Espaciador (1)]
    col1, col2, col3 = st.columns([1, 3, 1]) 
    
    with col2: 
        
        # Título principal con color NARANJA y centrado forzado
        st.markdown(
            f"<h1 style='text-align: center; color: #FFA500;'>¡Bienvenido al Gestor de Rendimiento!</h1>", 
            unsafe_allow_html=True
        )
        
        # Subtítulo con color BLANCO y centrado forzado
        st.markdown(
            f"<p style='text-align: center; font-size: 1.2em; color: white;'>Tu plataforma para gestionar marcas personales, calcular cargas y organizar tu calendario deportivo.</p>", 
            unsafe_allow_html=True
        )
        
        st.info("Por favor, inicia sesión para acceder a la aplicación.")
        login_form()
        
    st.stop()
    
# ----------------------------------------------------------------------
# --- CONTENIDO DE LA APLICACIÓN (POST-LOGIN) ---
# ----------------------------------------------------------------------

st.title("💪 RM & Rendimiento Manager")
logout() 

# Mostrar logo en la sidebar después del login
if st.session_state['logged_in']:
    st.sidebar.image(LOGO_PATH, width=100)
    st.sidebar.markdown("---")

rol_actual = st.session_state['rol']
atleta_actual = st.session_state['atleta_nombre']

# Definir pestañas según el rol
if rol_actual == 'Entrenador':
    tab1, tab2, tab3 = st.tabs(["📊 Vista Entrenador (Datos)", "🧮 Calculadora de Carga", "📅 Calendario"])
else:
    tab2, tab3 = st.tabs(["🧮 Calculadora de Carga", "📅 Calendario"])

# ----------------------------------------------------------------------------------
## PESTAÑA 1: VISTA ENTRENADOR (Solo visible para Entrenador)
# ----------------------------------------------------------------------------------
if rol_actual == 'Entrenador':
    with tab1:
        st.header("Datos de Atletas y Marcas RM")
        st.subheader("Control Total (Vista del Entrenador)")
        
        # Botones de recarga
        col_recarga_atletas, col_recarga_pruebas = st.columns(2)
        with col_recarga_atletas:
            if st.button("Recargar Datos de Atletas", help="Recarga el archivo 'atletas_data.xlsx'."):
                load_data.clear()
                st.rerun() 
        with col_recarga_pruebas:
            if st.button("Recargar Pruebas / Calendario", help="Recarga 'pruebas_activas.xlsx' y 'calendario_data.xlsx'."):
                load_calendar_data.clear()
                load_tests_data.clear()
                st.rerun()

        st.markdown("---")
        st.caption(f"Archivo de origen: **{EXCEL_FILE}**")
        
        # Muestra la tabla de datos completa (sin la contraseña)
        df_mostrar = df_atletas.drop(columns=['Contraseña'], errors='ignore')
        st.dataframe(df_mostrar, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Gestión de Pruebas (Modularidad de la Calculadora)")
        st.caption(f"Edita el archivo **{PRUEBAS_FILE}** para habilitar o deshabilitar pruebas.")
        st.dataframe(df_pruebas, use_container_width=True)
    
# ----------------------------------------------------------------------------------
## PESTAÑA 2: CALCULADORA DE CARGA (Visible para todos)
# ----------------------------------------------------------------------------------
calc_tab = tab2 

with calc_tab:
    st.header("🧮 Calculadora de Carga por Porcentaje (%) de RM")
    
    datos_usuario = df_atletas[df_atletas['Atleta'] == atleta_actual].iloc[0]
    
    st.write(f"**Hola, {atleta_actual}. Selecciona un ejercicio para cargar tu RM registrado.**")

    ejercicio_options = df_pruebas['NombrePrueba'].tolist()
    
    if not ejercicio_options:
        st.warning("No hay pruebas visibles. El Entrenador debe configurar el archivo 'pruebas_activas.xlsx'.")
        rm_manual = st.number_input("RM actual (en kg):", min_value=0.0, value=0.0, step=5.0)
    else:
        ejercicio_default = st.selectbox(
            "Selecciona el Ejercicio:",
            options=ejercicio_options, 
            key='ejercicio_calc'
        )
        
        rm_inicial = 0.0
        columna_rm = None
        
        columna_rm_series = df_pruebas[df_pruebas['NombrePrueba'] == ejercicio_default]['ColumnaRM']
        if not columna_rm_series.empty:
            columna_rm = columna_rm_series.iloc[0]
        
        if columna_rm and columna_rm != 'N/A' and columna_rm in datos_usuario and pd.notna(datos_usuario.get(columna_rm)):
            rm_inicial = float(datos_usuario[columna_rm]) 
        
        rm_manual = st.number_input(
            f"RM actual para **{ejercicio_default}** (en kg):",
            min_value=0.0,
            value=rm_inicial,
            step=5.0
        )
    
    st.markdown("---")
    st.subheader("Pesos a utilizar según el porcentaje:")
    
    cols = st.columns(3)
    porcentajes = [60, 65, 70, 75, 80, 85, 90, 95, 100]
    
    for i, porcentaje in enumerate(porcentajes):
        peso = calcular_porcentaje_rm(rm_manual, porcentaje)
        cols[i % 3].metric(f"{porcentaje}% de RM", f"{peso} kg")

# ----------------------------------------------------------------------------------
## PESTAÑA 3: CALENDARIO (Visible para todos)
# ----------------------------------------------------------------------------------
calendar_tab = tab3

with calendar_tab:
    st.header("📅 Calendario de Pruebas y Actividades")
    st.caption(f"Archivo de origen: **{CALENDAR_FILE}**")
    
    # Filtrar el calendario basado en el rol
    if rol_actual == 'Entrenador':
        st.subheader("Vista Completa (Entrenador)")
        st.warning("Edita el archivo 'calendario_data.xlsx' para actualizar el calendario y usar 'Sí'/'No' en la columna 'Habilitado'.")
        eventos_mostrar = df_calendario
    else:
        st.subheader(f"Próximos Eventos Habilitados para {atleta_actual}")
        # El atleta solo ve los eventos marcados como True (Sí)
        eventos_mostrar = df_calendario[df_calendario['Habilitado'] == True].drop(columns=['Habilitado'], errors='ignore')
    
    st.dataframe(eventos_mostrar, use_container_width=True)

# --- FIN DEL CÓDIGO ---
