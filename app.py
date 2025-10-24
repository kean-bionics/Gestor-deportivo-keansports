import streamlit as st
import pandas as pd
import numpy as np
import os
import io
from PIL import Image
from datetime import datetime, timedelta
# Importamos la librería necesaria para la conexión segura
from streamlit_gsheets import GSheetsConnection 
import json # Para manejar el JSON de las credenciales

# --- 1. CONFIGURACIÓN INICIAL DE ARCHIVOS ---

# Archivo 1: Atletas y Marcas
EXCEL_FILE = 'atletas_data.xlsx' 
REQUIRED_COLUMNS = ['ID', 'Atleta', 'Contraseña', 'Rol', 'Sentadilla_RM', 'PressBanca_RM', 'PesoCorporal', 'Última_Fecha']

# Archivo 2: Calendario
CALENDAR_FILE = 'calendario_data.xlsx'
CALENDAR_REQUIRED_COLUMNS = ['Evento', 'Fecha', 'Detalle', 'Habilitado']

# Archivo 3: Pruebas Activas (Modularidad de la Calculadora)
PRUEBAS_FILE = 'pruebas_activas.xlsx'

# Archivo 4: Perfiles de Atletas
PERFILES_FILE = 'perfiles.xlsx'

# Archivo 5: Ranking
RANKING_FILE = 'ranking.xlsx'
RANKING_REQUIRED_COLUMNS = ['Posicion', 'Atleta', 'Categoria', 'Oros', 'Platas', 'Bronces']

# Archivo 6: Readiness
READINESS_FILE = 'readiness_data.xlsx'
READINESS_REQUIRED_COLUMNS = ['Atleta', 'Fecha', 'Sueño', 'Molestias', 'Disposicion']

# RUTA DEL LOGO
LOGO_PATH = 'logo.png' 


# --- CONFIGURACIÓN DE GOOGLE SHEETS (CRÍTICO: TUS URLs PEGADAS) ---
GS_ATLETAS_URL = "https://docs.google.com/spreadsheets/d/1FB7RRgikMQIsTKmaSDU6yXDjkKp7tx4R/edit?usp=sharing&ouid=105993200479877589405&rtpof=true&sd=true"
GS_PERFILES_URL = "https://docs.google.com/spreadsheets/d/17PNuhgOP3QeE9ramQ06FfYdfTCFNdZks/edit?usp=sharing&ouid=105993200479877589405&rtpof=true&sd=true"
GS_RANKING_URL = "https://docs.google.com/spreadsheets/d/1K_ajXoEZv7d_ZbxUrabDpuktGfa_c817/edit?usp=sharing&ouid=105993200479877589405&rtpof=true&sd=true"
GS_READINESS_URL = "https://docs.google.com/spreadsheets/d/1R8Uaix9fMWzAScLdSyNbs_-mecvDYPMx/edit?usp=sharing&ouid=105993200479877589405&rtpof=true&sd=true"
GS_CALENDAR_URL = "https://docs.google.com/spreadsheets/d/1MLQER-HCr7V7549OD5b3zKdeEPSCm_mY/edit?usp=sharing&ouid=105993200479877589405&rtpof=true&sd=true" 
GS_TESTS_URL = "https://docs.google.com/spreadsheets/d/134DrZ0XPs0uPHKUpDQZC6Xbn9bZ8S25-/edit?usp=sharing&ouid=105993200479877589405&rtpof=true&sd=true"
# ------------------------------------------------


# --- FUNCIONES DE CÁLCULO (DEBES TENERLAS EN TU CÓDIGO) ---
# Si no tenías estas funciones, debes añadirlas a tu app.py o la calculadora fallará.
# Estas funciones son esenciales para la lógica de la Pestaña 2.

def calcular_porcentaje_rm(rm_value, porcentaje):
    """Calcula la carga al porcentaje dado del RM."""
    if rm_value <= 0: return 0.0
    return round(rm_value * (porcentaje / 100), 1)

def calcular_carga_por_rir(rm_value, rir_target):
    """Estima la carga basada en el RM y el RIR objetivo (basado en el RPE/RIR)."""
    if rm_value <= 0: return 0.0, 0.0
    
    # Tabla de pérdida de porcentaje típica por RIR (Ajustable)
    # RIR 4 (RPE 6) -> 70%
    # RIR 3 (RPE 7) -> 75%
    # RIR 2 (RPE 8) -> 80%
    # RIR 1 (RPE 9) -> 90%
    # RIR 0 (RPE 10) -> 100%
    
    perc_map = {
        4: 0.70,
        3: 0.75,
        2: 0.80,
        1: 0.90,
        0: 1.00
    }
    
    perc_sugerido = perc_map.get(rir_target, 0.75) # Default al 75% si no encuentra
    
    # Un RIR de 2-3 repeticiones se asocia típicamente con un 80-85% del 1RM
    # Ajustamos el porcentaje para el cálculo, buscando el peso que te permite hacer 'X' reps
    
    # Esta es una simplificación de la tabla de Epley/Brzycki:
    # Asumimos que quieres hacer N reps con ese RIR
    
    # El porcentaje de 1RM que se levanta en RIR 0 (fallo) es el 1RM.
    # El porcentaje de 1RM levantado al FALLO (RIR 0) con 5 repeticiones es típicamente ~85%
    
    # Si el atleta quiere 5 reps (target_reps=5) con RIR=2, eso es 7 reps en total antes del fallo.
    # Factor de porcentaje de 1RM (basado en el número total de repeticiones antes del fallo):
    # Total Reps = Reps Objetivo + RIR
    # Si Total Reps = 5 (RIR 0) -> 85%
    # Si Total Reps = 7 (RIR 2) -> 77.5%
    
    # Usaremos una aproximación simple basada en la pérdida de 2.5% por rep adicional
    reps_extra = 5 # Asumimos 5 repeticiones objetivo para el cálculo
    
    total_reps_antes_fallo = reps_extra + rir_target
    
    # Basado en la fórmula del RIR (ajustada para el factor 0.025/rep)
    if total_reps_antes_fallo >= 10:
        perc = 0.65
    elif total_reps_antes_fallo >= 8:
        perc = 0.725
    elif total_reps_antes_fallo >= 6:
        perc = 0.80
    elif total_reps_antes_fallo >= 4:
        perc = 0.875
    else: # Total Reps = 1
        perc = 0.95
        
    peso_calculado = rm_value * perc
    
    # Retornar el peso calculado y el porcentaje para fines informativos
    return round(peso_calculado, 1), round(perc * 100, 1)

def descomponer_placas(peso_requerido, peso_barra):
    """Descompone el peso requerido en placas por lado, asumiendo una barra fija."""
    if peso_requerido <= peso_barra:
        return "Peso < Barra", {}
    
    peso_neto = peso_requerido - peso_barra
    peso_por_lado = peso_neto / 2
    
    # Placas disponibles (de mayor a menor)
    placas_disp = [25, 20, 15, 10, 5, 2.5, 1.25, 0.5, 0.25]
    placas_por_lado = {}
    
    peso_restante = peso_por_lado
    
    for placa in placas_disp:
        if peso_restante >= placa:
            cantidad = int(peso_restante // placa)
            placas_por_lado[placa] = cantidad
            peso_restante -= cantidad * placa
            
    # Redondear el peso restante para evitar errores de coma flotante
    if round(peso_restante, 2) > 0.01:
        # Si aún queda peso por poner, puede ser un error en el cálculo o una placa pequeña no listada.
        pass
        
    return peso_requerido, placas_por_lado

def get_days_until(date_obj):
    """Calcula los días restantes hasta la fecha dada."""
    if pd.isna(date_obj):
        return 999 
    try:
        if isinstance(date_obj, str):
             date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
        elif isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        today = datetime.now().date()
        delta = (date_obj - today).days
        return delta
    except Exception:
        return 999

def highlight_imminent_events(df):
    """Aplica formato condicional a los eventos inminentes (0 a 5 días)."""
    days = df['Days_Until']
    is_imminent = (days >= 0) & (days <= 5)
    
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    
    styles.loc[is_imminent, :] = 'background-color: #f7a072; color: black;' # Naranja suave
    
    return styles

# --- FUNCIONES DE LOGIN (Deben estar en tu código) ---

def login_form():
    """Muestra el formulario de inicio de sesión."""
    with st.form("login_form"):
        st.subheader("Acceso")
        user = st.text_input("Usuario (Atleta o Entrenador):", key='login_user')
        password = st.text_input("Contraseña:", type='password', key='login_password')
        
        submitted = st.form_submit_button("Iniciar Sesión")
        
        if submitted:
            df = load_data()[0]
            if df.empty:
                st.error("No se pudo cargar la base de datos de atletas. Contacta al soporte.")
                return
            
            user_row = df[(df['Atleta'] == user) & (df['Contraseña'] == password)]
            
            if not user_row.empty:
                st.session_state['logged_in'] = True
                st.session_state['atleta_nombre'] = user_row['Atleta'].iloc[0]
                st.session_state['rol'] = user_row['Rol'].iloc[0]
                st.rerun()
            else:
                st.error("Usuario o Contraseña incorrectos.")

def logout():
    """Botón de cerrar sesión."""
    if st.session_state['logged_in']:
        if st.sidebar.button("Cerrar Sesión", type="secondary"):
            st.session_state['logged_in'] = False
            del st.session_state['atleta_nombre']
            del st.session_state['rol']
            st.rerun()


# --- FUNCIÓN DE CONEXIÓN A GOOGLE SHEETS (CACHEADA) ---
@st.cache_resource(ttl=3600)
def get_gsheets_connection():
    """Establece y cachea la conexión segura a Google Sheets."""
    try:
        # Aquí Streamlit usa las credenciales del secreto 'gservice_account'
        conn = st.connection("gsheets", type=GSheetsConnection) 
        return conn
    except Exception as e:
        st.error(f"Error crítico de conexión a Google Sheets. Revisa la configuración de Secrets: {e}")
        return None


# --- 2. FUNCIONES DE CARGA DE DATOS (MIGRADO A SHEETS) ---

@st.cache_data(ttl=300) # Carga más frecuente para datos principales
def load_data():
    """Carga los datos de los atletas desde Google Sheets."""
    conn = get_gsheets_connection()
    status_message = None
    
    if not conn:
        return pd.DataFrame(), "Error: No se pudo establecer la conexión con Google Sheets."

    try:
        df = conn.read(spreadsheet=GS_ATLETAS_URL, ttl=300)
        df.columns = df.columns.str.strip() 

        if df.empty or 'Atleta' not in df.columns:
             status_message = "ADVERTENCIA: La hoja de atletas está vacía o no tiene la columna 'Atleta'."
             df = pd.DataFrame(columns=df.columns if not df.empty else REQUIRED_COLUMNS) 
        
        if 'Última_Fecha' in df.columns:
            df['Última_Fecha'] = pd.to_datetime(df['Última_Fecha'], errors='coerce').dt.date
            
        return df, "Datos de atletas cargados de Google Sheets." 
        
    except Exception as e:
        return pd.DataFrame(), f"Error al cargar datos de Sheets: {e}"

@st.cache_data(ttl=600)
def load_calendar_data():
    """Carga los datos del calendario desde Google Sheets."""
    conn = get_gsheets_connection()
    if not conn: return pd.DataFrame(), "Error de conexión."
    
    try:
        calendar_df = conn.read(spreadsheet=GS_CALENDAR_URL, ttl=300)
        calendar_df.columns = calendar_df.columns.str.strip() 
        
        if 'Fecha' in calendar_df.columns:
            calendar_df['Fecha'] = pd.to_datetime(calendar_df['Fecha'], errors='coerce').dt.date

        if 'Habilitado' in calendar_df.columns:
            calendar_df['Habilitado'] = calendar_df['Habilitado'].astype(str).str.lower().str.strip() == 'sí'

        return calendar_df, None
    except Exception as e:
        return pd.DataFrame(), f"Error al cargar calendario de Sheets: {e}"

@st.cache_data(ttl=3600)
def load_tests_data():
    """Carga la lista de pruebas activas desde Google Sheets."""
    conn = get_gsheets_connection()
    status_message = None
    if not conn: return pd.DataFrame(), "Error de conexión."
    
    try:
        df_tests = conn.read(spreadsheet=GS_TESTS_URL, ttl=3600)
        df_tests.columns = df_tests.columns.str.strip()
        
        df_tests['Visible'] = df_tests['Visible'].astype(str).str.lower().str.strip().apply(lambda x: True if x == 'sí' else False)
        
        return df_tests, "Pruebas cargadas de Sheets."
    except Exception as e:
        return pd.DataFrame(), f"Error al cargar pruebas de Sheets: {e}"

@st.cache_data(ttl=3600)
def load_perfil_data():
    """Carga los datos de perfil de los atletas desde Google Sheets."""
    conn = get_gsheets_connection()
    status_message = None
    if not conn: return pd.DataFrame(), "Error de conexión."
    
    try:
        df_perfil = conn.read(spreadsheet=GS_PERFILES_URL, ttl=3600)
        df_perfil.columns = df_perfil.columns.str.strip()
        
        return df_perfil, "Perfiles cargados de Sheets."
    except Exception as e:
        return pd.DataFrame(), f"Error al cargar perfiles de Sheets: {e}"


# --- FUNCIÓN CLAVE PARA EL RANKING AUTOMATIZADO ---
def calculate_and_sort_ranking(df):
    """Calcula los puntos y ordena el ranking por jerarquía de medallas (Oros > Platas > Bronces)."""
    
    for col in ['Oros', 'Platas', 'Bronces']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
    # Calcular los puntos (Oro=10, Plata=3, Bronce=1)
    df['Puntos'] = (df['Oros'] * 10) + (df['Platas'] * 3) + (df['Bronces'] * 1)
    
    # Ordenación jerárquica: Oros (1ro) > Platas (2do) > Bronces (3ro) > Puntos (Desempate)
    df_sorted = df.sort_values(
        by=['Oros', 'Platas', 'Bronces', 'Puntos'], 
        ascending=[False, False, False, False]
    ).copy()
    
    df_sorted['Posicion'] = np.arange(1, len(df_sorted) + 1)
    
    return df_sorted
# -----------------------------------------------------

@st.cache_data(ttl=3600)
def load_ranking_data():
    """Carga los datos de ranking desde Google Sheets, los calcula y ordena."""
    conn = get_gsheets_connection()
    status_message = None
    if not conn: return pd.DataFrame(), "Error de conexión."

    try:
        df_ranking = conn.read(spreadsheet=GS_RANKING_URL, ttl=300)
        df_ranking.columns = df_ranking.columns.str.strip() 
        
        if df_ranking.empty:
             status_message = "ADVERTENCIA: La hoja de ranking está vacía."
             df_ranking = pd.DataFrame(columns=RANKING_REQUIRED_COLUMNS + ['Puntos']) 

        if not df_ranking.empty:
            df_ranking = calculate_and_sort_ranking(df_ranking)
        
        return df_ranking, "Ranking cargado de Sheets."
    except Exception as e:
        return pd.DataFrame(), f"Error al cargar ranking de Sheets: {e}"

@st.cache_data(ttl=3600)
def load_readiness_data():
    """Carga los datos de bienestar/readiness desde Google Sheets."""
    conn = get_gsheets_connection()
    status_message = None
    if not conn: return pd.DataFrame(), "Error de conexión."

    try:
        df_readiness = conn.read(spreadsheet=GS_READINESS_URL, ttl=300)
        df_readiness.columns = df_readiness.columns.str.strip()
        
        if df_readiness.empty:
             df_readiness = pd.DataFrame(columns=READINESS_REQUIRED_COLUMNS) 

        df_readiness['Fecha'] = pd.to_datetime(df_readiness['Fecha'], errors='coerce').dt.date
        
        return df_readiness, "Datos de bienestar cargados de Sheets."
    except Exception as e:
        return pd.DataFrame(), f"Error al cargar bienestar de Sheets: {e}"


# --- 3. CARGA DE DATOS AL INICIO DE LA APP Y MUESTREO DE TOASTS ---

df_atletas, initial_status = load_data() 
df_calendario_full, _ = load_calendar_data()
df_calendario = df_calendario_full[df_calendario_full['Habilitado'] == True].copy() 
df_pruebas_full, tests_status = load_tests_data() 
df_pruebas = df_pruebas_full[df_pruebas_full['Visible'] == True].copy() 
df_perfiles, perfil_status = load_perfil_data() 
df_ranking, ranking_status = load_ranking_data()
df_readiness, readiness_status = load_readiness_data()


# --- 4. FUNCIONES AUXILIARES DE GUARDADO (A SHEETS) ---

def save_main_data(df_edited):
    """Guarda el DataFrame editado de atletas SOBRE GOOGLE SHEETS."""
    conn = get_gsheets_connection()
    if not conn:
        st.error("No se pudo establecer la conexión segura para guardar.")
        return False
        
    try:
        df_edited.columns = df_edited.columns.str.strip()
        df_edited = df_edited.dropna(subset=['Atleta', 'Contraseña'], how='any')

        if 'Última_Fecha' in df_edited.columns:
            df_edited['Última_Fecha'] = pd.to_datetime(df_edited['Última_Fecha'], errors='coerce').dt.date
        
        cols = df_edited.columns.tolist()
        # Asegurarse que las columnas requeridas esten
        for col in REQUIRED_COLUMNS:
            if col not in cols:
                df_edited[col] = np.nan
        
        df_to_save = df_edited[cols].copy()
        
        # 1. Borrar todos los datos existentes en la hoja
        conn.clear(spreadsheet=GS_ATLETAS_URL)
        
        # 2. Escribir el nuevo DataFrame limpio a la hoja
        conn.write(df=df_to_save, spreadsheet=GS_ATLETAS_URL, headers=True) 
        
        load_data.clear()
        
        return True
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")
        return False

def save_readiness_data(atleta, fecha, sueno, molestias, disposicion):
    """Añade una nueva fila al archivo readiness_data.xlsx SOBRE GOOGLE SHEETS."""
    conn = get_gsheets_connection()
    if not conn:
        st.error("No se pudo establecer la conexión segura para guardar.")
        return False
        
    new_entry = {
        'Atleta': atleta, 
        'Fecha': pd.to_datetime(fecha).date(), 
        'Sueño': sueno, 
        'Molestias': molestias, 
        'Disposicion': disposicion
    }
    
    new_df = pd.DataFrame([new_entry])
    
    try:
        # Usa insert para añadir una nueva fila sin sobrescribir el resto
        conn.insert(df=new_df, spreadsheet=GS_READINESS_URL, headers=False) 
        load_readiness_data.clear() 
        return load_readiness_data()[0], True
        
    except Exception as e:
        st.error(f"Error al guardar el registro de bienestar en Sheets: {e}")
        return load_readiness_data()[0], False
    
def save_tests_data(df_edited):
    """Guarda el DataFrame editado de pruebas activas SOBRE GOOGLE SHEETS."""
    conn = get_gsheets_connection()
    if not conn:
        st.error("No se pudo establecer la conexión segura para guardar.")
        return False
        
    try:
        df_edited['Visible'] = df_edited['Visible'].apply(lambda x: 'Sí' if x else 'No')
        df_to_save = df_edited[['NombrePrueba', 'ColumnaRM', 'Visible']].copy()
        
        conn.clear(spreadsheet=GS_TESTS_URL)
        conn.write(df=df_to_save, spreadsheet=GS_TESTS_URL, headers=True)
        
        load_tests_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar las pruebas en Sheets: {e}")
        return False

def save_calendar_data(df_edited):
    """Guarda el DataFrame editado de calendario SOBRE GOOGLE SHEETS."""
    conn = get_gsheets_connection()
    if not conn:
        st.error("No se pudo establecer la conexión segura para guardar.")
        return False
        
    try:
        df_edited['Habilitado'] = df_edited['Habilitado'].apply(lambda x: 'Sí' if x else 'No')
        df_edited_cleaned = df_edited.dropna(subset=['Evento', 'Fecha'], how='any') 
        df_to_save = df_edited_cleaned[['Evento', 'Fecha', 'Detalle', 'Habilitado']].copy()
        
        conn.clear(spreadsheet=GS_CALENDAR_URL)
        conn.write(df=df_to_save, spreadsheet=GS_CALENDAR_URL, headers=True)
        
        load_calendar_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar el calendario en Sheets: {e}")
        return False

def save_ranking_data(df_edited):
    """Guarda el DataFrame editado del ranking, recalculando y ordenando primero."""
    conn = get_gsheets_connection()
    if not conn:
        st.error("No se pudo establecer la conexión segura para guardar.")
        return False

    try:
        df_cleaned = df_edited.dropna(subset=['Atleta'], how='any').copy()
        df_sorted = calculate_and_sort_ranking(df_cleaned)
        df_to_save = df_sorted[RANKING_REQUIRED_COLUMNS] 
        
        conn.clear(spreadsheet=GS_RANKING_URL)
        conn.write(df=df_to_save, spreadsheet=GS_RANKING_URL, headers=True)
        
        load_ranking_data.clear() 
        return True
    except Exception as e:
        st.error(f"Error al guardar el ranking en Sheets: {e}")
        return False


# --- 5. INTERFAZ PRINCIPAL DE STREAMLIT ---

st.set_page_config(layout="wide", page_title="Gestión de Rendimiento Atleta")

if initial_status and ('creado' in initial_status.lower() or 'error' in initial_status.lower() or 'adver' in initial_status.lower()):
    st.toast(initial_status, icon="📝")
if tests_status and ('creado' in tests_status.lower() or 'error' in tests_status.lower() or 'adver' in tests_status.lower()):
    st.toast(tests_status, icon="🛠️")
if perfil_status and ('creado' in perfil_status.lower() or 'error' in perfil_status.lower() or 'adver' in perfil_status.lower()):
    st.toast(perfil_status, icon="👤")
if ranking_status and ('creado' in ranking_status.lower() or 'error' in ranking_status.lower() or 'adver' in ranking_status.lower()):
    st.toast(ranking_status, icon="🏆")
if readiness_status and ('creado' in readiness_status.lower() or 'error' in readiness_status.lower() or 'adver' in readiness_status.lower()):
    st.toast(readiness_status, icon="🧘")


# Inicializar el estado de la sesión
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ----------------------------------------------------------------------
# --- PANTALLA DE ACCESO/BIENVENIDA ---
# ----------------------------------------------------------------------
if not st.session_state['logged_in']:
    
    logo_col, spacer_col = st.columns([1, 10])
    with logo_col:
        # Aquí se asume que 'logo.png' está en la carpeta raíz
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=120) 
        else:
            st.warning("No se encontró el archivo logo.png")
    
    st.markdown("---") 

    col1, col2, col3 = st.columns([1, 3, 1]) 
    
    with col2: 
        
        st.markdown(
            f"<h1 style='text-align: center; color: #FFA500;'>¡Bienvenido al Gestor de Rendimiento!</h1>", 
            unsafe_allow_html=True
        )
        
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

if st.session_state['logged_in']:
    # Asegúrate de que la ruta exista en Streamlit Cloud o usa un logo por defecto.
    if os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH, width=100)
    st.sidebar.markdown("---")

rol_actual = st.session_state['rol']
atleta_actual = st.session_state['atleta_nombre']

# Definición de pestañas
if rol_actual == 'Entrenador':
    tab1, tab2, CALENDAR_TAB, PERFIL_TAB, BIENESTAR_TAB, RANKING_TAB = st.tabs([
        "📊 Vista Entrenador (Datos)", "🧮 Calculadora de Carga", "📅 Calendario", "👤 Perfil", "🧘 Bienestar", "🏆 Ranking"
    ])
else:
    tab2, CALENDAR_TAB, PERFIL_TAB, BIENESTAR_TAB, RANKING_TAB = st.tabs([
        "🧮 Calculadora de Carga", "📅 Calendario", "👤 Perfil", "🧘 Bienestar", "🏆 Ranking"
    ])

# ----------------------------------------------------------------------------------
## NOTIFICACIÓN GLOBAL DE EVENTOS INMINENTES
# ----------------------------------------------------------------------------------

df_imminent = df_calendario.copy()
df_imminent['Days_Until'] = df_imminent['Fecha'].apply(get_days_until)
df_imminent = df_imminent[(df_imminent['Days_Until'] >= 0) & (df_imminent['Days_Until'] <= 5)]

if not df_imminent.empty:
    imminent_event = df_imminent.iloc[0]
    days = imminent_event['Days_Until']
    event_name = imminent_event['Evento']
    
    st.sidebar.warning(
        f"🚨 **¡Atención!** El evento **'{event_name}'** es en solo **{days} días**. ¡Revisa el calendario!"
    )
    st.toast(f"¡Evento Inminente! '{event_name}' en {days} días. ¡A revisarlo! ⏰", icon="⏰")

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
            if st.button("Recargar Datos Atletas/Perfiles/Ranking/Bienestar", help="Recarga todos los archivos de datos dinámicos."):
                load_data.clear()
                load_perfil_data.clear()
                load_ranking_data.clear()
                load_readiness_data.clear()
                st.rerun() 
        with col_recarga_pruebas:
            if st.button("Recargar Calendario/Pruebas", help="Recarga 'calendario_data.xlsx' y 'pruebas_activas.xlsx'."):
                load_calendar_data.clear()
                load_tests_data.clear()
                st.rerun()

        st.markdown("---")
        st.subheader("1. Gestión de Atletas y Marcas RM (Edición Directa)")
        st.warning("⚠️ **ATENCIÓN**: Para añadir **nuevas pruebas RM**, debes agregar la columna al archivo **atletas_data** en Google Sheets manualmente para que el código la reconozca.")

        df_editor_main = df_atletas.copy()
        
        # 1. Widget de edición para datos principales de atletas
        df_edited_main = st.data_editor(
            df_editor_main, 
            num_rows="dynamic",
            column_config={
                "ID": st.column_config.NumberColumn("ID", disabled=True), 
                "Atleta": st.column_config.TextColumn("Atleta", help="Nombre único del atleta y Usuario de Login", required=True),
                "Contraseña": st.column_config.TextColumn("Contraseña", required=True),
                "Rol": st.column_config.SelectboxColumn("Rol", options=['Atleta', 'Entrenador']),
                "Sentadilla_RM": st.column_config.NumberColumn("Sentadilla_RM (kg)", format="%.1f"),
                "PressBanca_RM": st.column_config.NumberColumn("PressBanca_RM (kg)", format="%.1f"),
                "PesoCorporal": st.column_config.NumberColumn("PesoCorporal (kg)", format="%.1f"),
                "Última_Fecha": st.column_config.DateColumn("Última_Fecha"),
            },
            use_container_width=True,
            key="main_data_editor"
        )
        
        # 2. Botón de guardado
        if st.button("💾 Guardar Cambios en Datos de Atletas y Aplicar", type="primary", key="save_main_data_btn"):
            if 'ID' in df_edited_main.columns:
                max_id = df_edited_main['ID'].dropna().max()
                if pd.isna(max_id): max_id = 0
                
                for index, row in df_edited_main.iterrows():
                    if pd.isna(row['ID']):
                        max_id += 1
                        df_edited_main.loc[index, 'ID'] = max_id
                        
            df_edited_cleaned_main = df_edited_main.dropna(subset=['Atleta', 'Contraseña'], how='any')

            if save_main_data(df_edited_cleaned_main):
                st.success("✅ Datos de Atletas actualizados y guardados con éxito. Recargando aplicación...")
                st.rerun()
            else:
                st.error("❌ No se pudieron guardar los datos de atletas.")

        st.markdown("---")
        st.subheader("2. Gestión de Pruebas (Modularidad de la Calculadora)")
        st.caption(f"**Edita la tabla directamente para añadir/quitar pruebas y marcar 'Visible' con el chulito.** La columna **ColumnaRM** debe coincidir exactamente con el encabezado en la hoja de Atletas.")
        
        # --- TABLA EDITABLE DE PRUEBAS ---
        
        # 1. Widget de edición
        df_edited = st.data_editor(
            df_pruebas_full,
            num_rows="dynamic",
            column_config={
                "Visible": st.column_config.CheckboxColumn(
                    "Visible",
                    help="Marca para mostrar la prueba en la calculadora.",
                    default=False,
                ),
                "ColumnaRM": st.column_config.TextColumn("ColumnaRM", help="Debe coincidir EXACTAMENTE con el nombre de columna en la Hoja de Atletas (Ej: Biceps_RM)"), 
                "NombrePrueba": st.column_config.TextColumn("NombrePrueba"),
            },
            use_container_width=True,
            key="tests_data_editor"
        )

        # 2. Botón de guardado
        if st.button("💾 Guardar Cambios en Pruebas Activas y Aplicar", type="secondary", key="save_tests_data_btn"):
            df_edited_cleaned = df_edited.dropna(subset=['NombrePrueba', 'ColumnaRM'], how='all')

            if save_tests_data(df_edited_cleaned):
                st.success("✅ Pruebas actualizadas y guardadas con éxito. Recargando aplicación...")
                st.rerun()
            else:
                st.error("❌ No se pudieron guardar los cambios.")
    
# ----------------------------------------------------------------------------------
## PESTAÑA 2: CALCULADORA DE CARGA (Visible para todos)
# ----------------------------------------------------------------------------------
calc_tab = tab2 

with calc_tab:
    st.header("🧮 Calculadora de Carga")
    
    if atleta_actual not in df_atletas['Atleta'].values:
        st.error(f"El atleta '{atleta_actual}' no se encuentra en la base de datos. Por favor, contacta al entrenador o cierra sesión.")
        st.stop()
        
    datos_usuario = df_atletas[df_atletas['Atleta'] == atleta_actual].iloc[0]
    
    st.write(f"**Hola, {atleta_actual}. Selecciona un ejercicio para cargar tu RM registrado.**")

    # --- ENTRADA DE DATOS RM Y BARRA ---
    col_ejercicio, col_barra = st.columns([2, 1])

    with col_ejercicio:
        ejercicio_options = df_pruebas['NombrePrueba'].tolist() 
        
        if not ejercicio_options:
            st.warning("No hay pruebas visibles. El Entrenador debe configurar el archivo 'pruebas_activas'.")
            rm_value = st.number_input("RM actual (en kg):", min_value=0.0, value=0.0, step=5.0)
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
            
            rm_value = st.number_input(
                f"RM actual para **{ejercicio_default}** (en kg):",
                min_value=0.0,
                value=rm_inicial,
                step=5.0
            )

    with col_barra:
        st.markdown(" ", unsafe_allow_html=True)
        peso_barra = st.number_input(
            "Peso de la Barra (kg):",
            min_value=0.0,
            value=20.0,
            step=2.5,
            key='peso_barra_input'
        )

    st.markdown("---")
    
    # --- MÓDULO 1: CÁLCULO DE CARGA DINÁMICA (%) ---
    st.subheader("1. Carga por Porcentaje (%) de RM (Slider Dinámico)")

    col_perc, col_metric = st.columns([2, 1])

    with col_perc:
        porcentaje_input = st.slider(
            "Selecciona el Porcentaje (%) de tu RM:",
            min_value=0,
            max_value=100,
            value=75,
            step=1,
            key='slider_perc'
        )
        peso_calculado_perc = calcular_porcentaje_rm(rm_value, porcentaje_input)

    with col_metric:
        st.metric(f"Peso Sugerido", f"**{peso_calculado_perc} kg**")
        st.caption(f"Al {porcentaje_input}%")
    
    # --- MÓDULO 2: CÁLCULO DE CARGA POR RIR Y REPETICIONES ---
    st.markdown("---")
    st.subheader("2. Estimador de Carga por RIR y Repeticiones")
    st.caption("Ingresa tu objetivo de repeticiones y esfuerzo (RIR) para obtener el peso ideal.")

    col_reps, col_rir, col_target = st.columns(3)
    
    with col_reps:
        reps_target = st.number_input("Repeticiones Objetivo (Reps):", min_value=1, max_value=20, value=5, step=1)
        
    with col_rir:
        rir_target = st.selectbox("Esfuerzo Deseado (RIR):", options=[4, 3, 2, 1, 0], index=2, key='rir_target_select')
    
    peso_calculado_rir, perc_sugerido = calcular_carga_por_rir(rm_value, rir_target)

    with col_target:
        st.markdown(" ", unsafe_allow_html=True) 
        st.metric("Peso Ideal", f"**{peso_calculado_rir} kg**")
        if peso_calculado_rir > 0:
             st.caption(f"Equivale aprox. al {perc_sugerido:.1f}% de RM")

    # --- Conversión de Placas ---
    st.markdown("---")
    st.subheader("Conversión de Placas")
    
    peso_conversion = peso_calculado_rir if peso_calculado_rir > 0 else peso_calculado_perc

    col_conversion, col_placas = st.columns([1, 1])
    
    with col_conversion:
        st.metric("Peso a Conversión", f"**{peso_conversion} kg**")
        st.caption("Usamos el Peso Ideal del Estimador RIR para la conversión.")

    peso_total_cargado, placas_por_lado = descomponer_placas(peso_conversion, peso_barra)
    
    with col_placas:
        if isinstance(peso_total_cargado, str):
            st.warning("Peso Requerido debe ser mayor que el Peso de la Barra.")
        else:
            st.markdown(f"**Carga por Lado ({peso_barra} kg de barra):**")
            placas_str = ""
            if placas_por_lado:
                for placa, cantidad in placas_por_lado.items():
                    placas_str += f"- **{placa} kg**: {cantidad} placa(s) ➡️ Total: {placa * cantidad} kg/lado\n"
                st.info(placas_str)
            else:
                st.success("No se requieren placas adicionales (Solo la barra).")
    
    st.markdown("---")

    # --- GUÍA VBT Y RPE/RIR PARA COMBATE ---

    col_rpe, col_vbt = st.columns(2)

    with col_rpe:
        st.subheader("Guía de Intensidad (RPE / RIR) 🥊")
        st.caption("Usa el RIR/RPE para el Estimador de Carga.")
        rpe_guide = pd.DataFrame({
            'RIR': [4, 3, 2, 1, 0],
            'RPE': [6, 7, 8, 9, 10],
            'Esfuerzo': ['Calentamiento / Técnica (Fácil)', 'Medio (Buena Velocidad)', 'Cerca del fallo (Lento)', 'Máximo posible (Muy Lento)', 'Fallo (Sin repeticiones extra)'],
            'Carga Sugerida': ['65% - 75%', '70% - 80%', '80% - 87%', '87% - 95%', '90% +']
        })
        st.table(rpe_guide.set_index('RIR'))

    with col_vbt:
        st.subheader("Guía de Velocidad (VBT) ⚡")
        st.caption("Maximiza la potencia en zonas de velocidad alta.")
        
        vbt_guide = pd.DataFrame({
            '% de 1RM Típico': ['90% - 95%', '80% - 85%', '60% - 70%', '40% - 50%'],
            'Intención': ['Fuerza Máxima', 'Fuerza-Velocidad', 'Velocidad-Fuerza', 'Técnica/Velocidad'],
            'Velocidad Objetivo (m/s)': ['0.30 - 0.45', '0.50 - 0.70', '0.75 - 1.00', '1.00 - 1.30']
        })
        st.table(vbt_guide.set_index('% de 1RM Típico'))
        
# ----------------------------------------------------------------------------------
## PESTAÑA 3: CALENDARIO (Visible para todos)
# ----------------------------------------------------------------------------------
with CALENDAR_TAB:
    st.header("📅 Calendario de Pruebas y Actividades")
    
    if rol_actual == 'Entrenador':
        st.subheader("Gestión de Cronograma (Vista Entrenador)")
        st.caption("⚠️ **Edita, añade o elimina filas directamente en la tabla. El 'chulito' en 'Habilitado' controla la visibilidad para los atletas.**")
        
        df_calendar_edit = df_calendario_full.copy()
        
        df_edited_calendar = st.data_editor(
            df_calendar_edit,
            num_rows="dynamic",
            column_config={
                "Fecha": st.column_config.DateColumn(
                    "Fecha", 
                    format="YYYY-MM-DD", 
                    required=True
                ),
                "Evento": st.column_config.TextColumn("Evento", required=True),
                "Habilitado": st.column_config.CheckboxColumn(
                    "Habilitado",
                    help="Marcar para que los atletas puedan ver el evento.",
                    default=True,
                )
            },
            use_container_width=True,
            key="calendar_data_editor"
        )
        
        if st.button("💾 Guardar Cambios en Calendario y Aplicar", type="primary", key="save_calendar_data_btn"):
            df_edited_cleaned = df_edited_calendar.dropna(subset=['Evento', 'Fecha'], how='any')

            if save_calendar_data(df_edited_cleaned):
                st.success("✅ Calendario actualizado y guardado con éxito. Recargando aplicación...")
                st.rerun()
            else:
                st.error("❌ No se pudieron guardar los cambios en el calendario.")
        
        st.markdown("---")
        st.subheader(f"Vista del Atleta")
        eventos_mostrar = df_calendario.copy()
        
    else:
        st.subheader(f"Próximos Eventos Habilitados para {atleta_actual}")
        eventos_mostrar = df_calendario.copy()
    
    # --- LÓGICA DE RESALTADO ---
    if not eventos_mostrar.empty:
        eventos_mostrar['Days_Until'] = eventos_mostrar['Fecha'].apply(get_days_until)
        
        st.dataframe(
            eventos_mostrar.style.apply(highlight_imminent_events, axis=None), 
            use_container_width=True
        )
        
    else:
        st.info("No hay eventos habilitados para mostrar.")

# ----------------------------------------------------------------------------------
## PESTAÑA 4: PERFIL (Visible para todos)
# ----------------------------------------------------------------------------------
with PERFIL_TAB:
    st.header(f"👤 Perfil y Datos de Contacto de {atleta_actual}")

    datos_perfil = df_perfiles[df_perfiles['Atleta'] == atleta_actual]

    if not datos_perfil.empty:
        perfil = datos_perfil.iloc[0].drop('Atleta', errors='ignore')

        st.subheader("Información Personal")
        
        cols = st.columns(2)
        
        for i, (key, value) in enumerate(perfil.items()):
            if key.lower() == 'fecha_nacimiento' and pd.notna(value):
                value_display = value.strftime('%Y-%m-%d') if isinstance(value, pd.Timestamp) else str(value)
            else:
                value_display = str(value)
                
            with cols[i % 2]:
                st.metric(label=key.replace('_', ' ').title(), value=value_display)

    else:
        st.warning(f"No se encontró información de perfil para **{atleta_actual}** en la base de datos.")

    if rol_actual == 'Entrenador':
        st.markdown("---")
        st.subheader("Datos Crudos de Perfiles (Vista Entrenador)")
        st.caption("Asegúrate de que la columna 'Atleta' en el Excel coincida exactamente con el nombre de usuario.")
        st.dataframe(df_perfiles, use_container_width=True)


# ----------------------------------------------------------------------------------
## PESTAÑA 5: BIENESTAR (NUEVA PESTAÑA)
# ----------------------------------------------------------------------------------
with BIENESTAR_TAB:
    st.header("🧘 Seguimiento de Bienestar y Disposición")
    st.caption("Registra tu estado subjetivo diario para optimizar tu entrenamiento.")

    st.subheader("Registro Diario")
    
    if 'df_readiness_display' not in st.session_state:
        st.session_state['df_readiness_display'] = df_readiness.copy()

    with st.form("readiness_form", clear_on_submit=True):
        fecha_registro = st.date_input("Fecha de Registro:", datetime.now().date())
        
        col_sleep, col_pain, col_ready = st.columns(3)
        
        with col_sleep:
            sueno = st.slider("1. Calidad del Sueño:", min_value=1, max_value=5, value=3, help="1=Pésimo, 5=Excelente")
        
        with col_pain:
            molestias = st.slider("2. Nivel de Molestias/Dolor:", min_value=1, max_value=5, value=1, help="1=Ninguna, 5=Severa")
            
        with col_ready:
            disposicion = st.slider("3. Disposición para Entrenar:", min_value=1, max_value=5, value=3, help="1=Baja, 5=Alta")
            
        submitted = st.form_submit_button("Guardar Registro Diario")
        
        if submitted:
            updated_df, success = save_readiness_data(atleta_actual, fecha_registro, sueno, molestias, disposicion)
            
            if success:
                st.success("¡Registro de bienestar guardado exitosamente! Actualizando historial...")
                st.session_state['df_readiness_display'] = updated_df
            

    st.markdown("---")
    st.subheader("Historial de Bienestar")

    df_atleta_readiness = st.session_state['df_readiness_display'][st.session_state['df_readiness_display']['Atleta'] == atleta_actual].sort_values(by='Fecha', ascending=False)
    
    if df_atleta_readiness.empty:
        st.info("No tienes registros de bienestar aún.")
    else:
        st.dataframe(
            df_atleta_readiness[['Fecha', 'Sueño', 'Molestias', 'Disposicion']].head(10), 
            use_container_width=True
        )
        
        if rol_actual == 'Entrenador':
            st.markdown("---")
            st.subheader("Datos Crudos (Vista Entrenador)")
            st.dataframe(st.session_state['df_readiness_display'], use_container_width=True)


# ----------------------------------------------------------------------------------
## PESTAÑA 6: RANKING (Visible para todos)
# ----------------------------------------------------------------------------------
with RANKING_TAB:
    st.header("🏆 Ranking de Atletas")
    st.caption("Ordenado por: **Oros > Platas > Bronces**. (Oro=10, Plata=3, Bronce=1)")
    
    if rol_actual == 'Entrenador':
        st.subheader("Gestión de Ranking (Edición Directa)")
        st.warning("⚠️ **Edita los valores de medallas y categorías. La Posición se recalculará automáticamente al guardar.**")
        
        df_edited_ranking = st.data_editor(
            df_ranking.drop(columns=['Puntos'], errors='ignore'),
            num_rows="dynamic",
            column_config={
                "Posicion": st.column_config.NumberColumn("Posición", disabled=True),
                "Atleta": st.column_config.TextColumn("Atleta", required=True),
                "Categoria": st.column_config.TextColumn("Categoría"),
                "Oros": st.column_config.NumberColumn("🥇 Oros"),
                "Platas": st.column_config.NumberColumn("🥈 Platas"),
                "Bronces": st.column_config.NumberColumn("🥉 Bronces"),
            },
            use_container_width=True,
            key="ranking_data_editor"
        )
        
        if st.button("💾 Guardar y Recalcular Ranking", type="primary", key="save_ranking_data_btn"):
            if save_ranking_data(df_edited_ranking):
                st.success("✅ Ranking recalculado, ordenado y guardado con éxito. Recargando aplicación...")
                st.rerun()
            else:
                st.error("❌ No se pudieron guardar los cambios en el ranking.")
        
        st.markdown("---")
        st.subheader("Clasificación Actual")

    st.dataframe(
        df_ranking.drop(columns=['Puntos'], errors='ignore'), 
        use_container_width=True,
        column_config={
            "Posicion": st.column_config.NumberColumn("Posición", format="%d"),
            "Oros": st.column_config.NumberColumn("🥇 Oros", format="%d"),
            "Platas": st.column_config.NumberColumn("🥈 Platas", format="%d"),
            "Bronces": st.column_config.NumberColumn("🥉 Bronces", format="%d"),
        },
        height=35 * (len(df_ranking) + 1)
    )

    current_athlete_rank = df_ranking[df_ranking['Atleta'] == atleta_actual]
    if not current_athlete_rank.empty:
        rank_data = current_athlete_rank.iloc[0]
        st.markdown("---")
        st.subheader(f"Tu Posición Actual: {atleta_actual}")
        
        col_rank, col_medals = st.columns(2)
        
        col_rank.metric("Rango", f"#{int(rank_data['Posicion'])}")
        
        medals_text = f"🥇 {int(rank_data['Oros'])} | 🥈 {int(rank_data['Platas'])} | 🥉 {int(rank_data['Bronces'])}"
        col_medals.markdown(f"**Medallas:** <div style='font-size: 1.5em;'>{medals_text}</div>", unsafe_allow_html=True)


# --- FIN DEL CÓDIGO ---
