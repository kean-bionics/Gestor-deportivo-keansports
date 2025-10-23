import streamlit as st
import pandas as pd
import numpy as np
import os
import io
from PIL import Image
from datetime import datetime, timedelta

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
RANKING_REQUIRED_COLUMNS = ['Posicion', 'Atleta', 'Categoria', 'Oros', 'Platas', 'Bronces', 'Puntos']

# Archivo 6: Readiness
READINESS_FILE = 'readiness_data.xlsx'
READINESS_REQUIRED_COLUMNS = ['Atleta', 'Fecha', 'Sueño', 'Molestias', 'Disposicion']

# RUTA DEL LOGO
LOGO_PATH = 'logo.png' 


# --- 2. FUNCIONES DE CARGA DE DATOS (CON CACHÉ) ---

@st.cache_data(ttl=3600) 
def load_data():
    """Carga los datos de los atletas. Si no existe, lo crea."""
    df = pd.DataFrame()
    excel_exists = os.path.exists(EXCEL_FILE)
    status_message = None
    
    if excel_exists:
        try:
            df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
            
            df.columns = df.columns.str.strip() 
            
            missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                status_message = f"El archivo Excel de atletas existe, pero faltan columnas: {', '.join(missing_cols)}. Se añadirán vacías."
                for col in missing_cols:
                    df[col] = None
                    
        except Exception as e:
            status_message = f"Error al leer el archivo Excel de atletas ({e}). Se creará un archivo nuevo de ejemplo."
            excel_exists = False

    if not excel_exists or df.empty:
        status_message = f"Creando el archivo '{EXCEL_FILE}' de ejemplo con la estructura inicial."
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
        status_message += " Archivo creado con éxito."
        
    if 'Última_Fecha' in df.columns:
        df['Última_Fecha'] = pd.to_datetime(df['Última_Fecha'], errors='coerce') 

    # Quitamos la columna temporal si existe para no interferir con la lógica de guardado
    if 'Nueva_Prueba' in df.columns:
        df = df.drop(columns=['Nueva_Prueba'])
    
    return df, status_message 

@st.cache_data(ttl=600)
def load_calendar_data():
    """Carga los datos del calendario desde el archivo Excel."""
    calendar_df = pd.DataFrame()
    excel_exists = os.path.exists(CALENDAR_FILE)
    
    if excel_exists:
        try:
            calendar_df = pd.read_excel(CALENDAR_FILE, engine='openpyxl')
            calendar_df.columns = calendar_df.columns.str.strip() 
            
            # --- SOLUCIÓN CLAVE: Convertir la columna Fecha a datetime.date ---
            if 'Fecha' in calendar_df.columns:
                calendar_df['Fecha'] = pd.to_datetime(calendar_df['Fecha'], errors='coerce').dt.date
            # -----------------------------------------------------------------

        except:
             excel_exists = False

    if not excel_exists or calendar_df.empty:
        # Crea un DataFrame de ejemplo si no existe o hubo error
        data = {
            'Evento': ['Prueba de RM (Sentadilla/PB)', 'Evaluación de Resistencia', 'Reunión de Equipo'],
            'Fecha': [datetime.now().date() + timedelta(days=30), datetime.now().date() + timedelta(days=60), datetime.now().date() + timedelta(days=10)],
            'Detalle': ['Test de 1RM', 'Test de Cooper o 5K', 'Revisión de Mes'],
            'Habilitado': ['Sí', 'Sí', 'No']
        }
        calendar_df = pd.DataFrame(data, columns=CALENDAR_REQUIRED_COLUMNS) 
        calendar_df['Fecha'] = pd.to_datetime(calendar_df['Fecha'], errors='coerce').dt.date # Se añade conversión al crear
        calendar_df.to_excel(CALENDAR_FILE, index=False, engine='openpyxl') 

    # Convertir a booleano antes de retornar
    if 'Habilitado' in calendar_df.columns:
        calendar_df['Habilitado'] = calendar_df['Habilitado'].astype(str).str.lower().str.strip() == 'sí'

    return calendar_df

@st.cache_data(ttl=3600)
def load_tests_data():
    """
    Carga la lista de pruebas activas.
    Retorna el DataFrame COMPLETO para edición y el mensaje de estado.
    """
    status_message = None
    
    if not os.path.exists(PRUEBAS_FILE):
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
        df_tests.columns = df_tests.columns.str.strip()
    except Exception as e:
        status_message = f"Error al cargar {PRUEBAS_FILE}: {e}"
        return pd.DataFrame(), status_message 

    df_tests['Visible'] = df_tests['Visible'].astype(str).str.lower().str.strip().apply(lambda x: True if x == 'sí' else False)
    
    # Retorna el DF completo (con la columna Visible booleana)
    return df_tests, status_message 

@st.cache_data(ttl=3600)
def load_perfil_data():
    """Carga los datos de perfil de los atletas desde el archivo Excel. Si no existe, lo crea."""
    df_perfil = pd.DataFrame()
    excel_exists = os.path.exists(PERFILES_FILE)
    status_message = None

    DEFAULT_PROFILE_DATA = {
        'Atleta': ['Tu Nombre', 'Juan Pérez', 'Ana Gómez'],
        'Edad': [30, 25, 22],
        'Fecha_Nacimiento': ['1994-01-01', '1999-05-10', '2002-01-20'],
        'Documento': ['999', '12345678', '87654321'],
        'Altura_cm': [180, 178, 165],
        'Posicion': ['Entrenador', 'Delantero', 'Defensora'],
        'Email': ['tu@mail.com', 'juan@mail.com', 'ana@mail.com']
    }
    REQUIRED_PROFILE_COLUMNS = list(DEFAULT_PROFILE_DATA.keys())
    
    if excel_exists:
        try:
            df_perfil = pd.read_excel(PERFILES_FILE, engine='openpyxl')
            df_perfil.columns = df_perfil.columns.str.strip()
        except:
             excel_exists = False

    if not excel_exists or df_perfil.empty:
        df_perfil = pd.DataFrame(DEFAULT_PROFILE_DATA, columns=REQUIRED_PROFILE_COLUMNS) 
        df_perfil.to_excel(PERFILES_FILE, index=False, engine='openpyxl') 
        status_message = f"Archivo '{PERFILES_FILE}' creado con éxito."

    return df_perfil, status_message

@st.cache_data(ttl=3600)
def load_ranking_data():
    """Carga los datos de ranking desde el archivo Excel. Si no existe, lo crea."""
    df_ranking = pd.DataFrame()
    excel_exists = os.path.exists(RANKING_FILE)
    status_message = None
    
    if excel_exists:
        try:
            df_ranking = pd.read_excel(RANKING_FILE, engine='openpyxl')
            df_ranking.columns = df_ranking.columns.str.strip() 
            
            missing_cols = [col for col in RANKING_REQUIRED_COLUMNS if col not in df_ranking.columns]
            if missing_cols:
                 status_message = f"ADVERTENCIA: El archivo '{RANKING_FILE}' no tiene las columnas requeridas: {', '.join(missing_cols)}. Favor de corregir el archivo."
                 df_ranking = pd.DataFrame(columns=RANKING_REQUIRED_COLUMNS) 
                 return df_ranking, status_message
            
        except:
             excel_exists = False

    if not excel_exists or df_ranking.empty:
        data = {
            'Posicion': [1, 2, 3, 4],
            'Atleta': ['Tu Nombre', 'Juan Pérez', 'Ana Gómez', 'Pedro Lopez'],
            'Categoria': ['Senior', 'Junior', 'Senior', 'Junior'],
            'Oros': [5, 2, 1, 0],
            'Platas': [2, 3, 0, 1],
            'Bronces': [1, 0, 1, 2],
            'Puntos': [500, 350, 200, 150]
        }
        df_ranking = pd.DataFrame(data, columns=RANKING_REQUIRED_COLUMNS) 
        df_ranking.to_excel(RANKING_FILE, index=False, engine='openpyxl')
        status_message = f"Archivo '{RANKING_FILE}' creado con éxito."

    return df_ranking, status_message

@st.cache_data(ttl=3600)
def load_readiness_data():
    """Carga los datos de bienestar/readiness desde el archivo Excel."""
    df_readiness = pd.DataFrame()
    excel_exists = os.path.exists(READINESS_FILE)
    status_message = None

    if excel_exists:
        try:
            df_readiness = pd.read_excel(READINESS_FILE, engine='openpyxl')
            df_readiness.columns = df_readiness.columns.str.strip()
            df_readiness['Fecha'] = pd.to_datetime(df_readiness['Fecha'], errors='coerce')
        except:
             excel_exists = False

    if not excel_exists or df_readiness.empty:
        data = {
            'Atleta': ['Juan Pérez', 'Juan Pérez', 'Ana Gómez'],
            'Fecha': [datetime.now().date() - timedelta(days=2), datetime.now().date() - timedelta(days=1), datetime.now().date() - timedelta(days=1)],
            'Sueño': [4, 3, 5],
            'Molestias': [2, 3, 1],
            'Disposicion': [5, 4, 5]
        }
        df_readiness = pd.DataFrame(data, columns=READINESS_REQUIRED_COLUMNS) 
        df_readiness['Fecha'] = pd.to_datetime(df_readiness['Fecha'], errors='coerce')
        df_readiness.to_excel(READINESS_FILE, index=False, engine='openpyxl') 
        status_message = f"Archivo '{READINESS_FILE}' creado con éxito."
    
    return df_readiness, status_message


# --- 3. CARGA DE DATOS AL INICIO DE LA APP Y MUESTREO DE TOASTS ---

df_atletas, initial_status = load_data() 
df_calendario_full = load_calendar_data() # Carga el DF completo para editar el calendario
df_calendario = df_calendario_full[df_calendario_full['Habilitado'] == True].copy() # Filtramos para mostrar al atleta
df_pruebas_full, tests_status = load_tests_data() 
df_pruebas = df_pruebas_full[df_pruebas_full['Visible'] == True].copy() 
df_perfiles, perfil_status = load_perfil_data() 
df_ranking, ranking_status = load_ranking_data()
df_readiness, readiness_status = load_readiness_data()


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

# Relación inversa RIR a Porcentaje de 1RM
RIR_TO_PERCENT = {
    0: (90, 100), 
    1: (87, 95),  
    2: (80, 87),  
    3: (70, 80),  
    4: (65, 75),  
}

def calcular_carga_por_rir(rm_value, rir):
    """Calcula el peso óptimo basado en RIR y el RM, tomando el punto medio del rango de porcentaje."""
    if rir not in RIR_TO_PERCENT or rm_value <= 0:
        return 0, 0
        
    min_perc, max_perc = RIR_TO_PERCENT[rir]
    mid_perc = (min_perc + max_perc) / 2
    
    peso = rm_value * (mid_perc / 100)
    return round(peso * 2) / 2, mid_perc

def descomponer_placas(peso_total, peso_barra):
    """Calcula las placas necesarias por lado para un peso total dado."""
    if peso_total <= peso_barra or peso_barra < 0:
        return "Barra Sola o Peso Inválido", {}

    peso_a_cargar = (peso_total - peso_barra) / 2
    placas_disponibles = [25.0, 20.0, 15.0, 10.0, 5.0, 2.5, 1.25, 0.5] 
    placas_por_lado = {}

    peso_restante = peso_a_cargar
    
    for placa in placas_disponibles:
        if peso_restante >= (placa - 0.01):
            cantidad = int(peso_restante // placa)
            if cantidad > 0:
                placas_por_lado[placa] = cantidad
                peso_restante -= (cantidad * placa)
            
            if peso_restante < 0.1: 
                peso_restante = 0
                break
    
    peso_cargado_total = peso_barra + (sum(p * c for p, c in placas_por_lado.items()) * 2)

    return peso_cargado_total, placas_por_lado

def save_main_data(df_edited):
    """Guarda el DataFrame editado de atletas en el archivo XLSX, forzando Última_Fecha al final."""
    try:
        # 1. Limpieza y preparación
        df_edited.columns = df_edited.columns.str.strip()
        df_edited = df_edited.dropna(subset=['Atleta', 'Contraseña'], how='any')

        # [CORRECCIÓN CLAVE]: Ya no necesitamos la lógica de Nueva_Prueba aquí.
        
        # Convertir a fecha compatible (solo la columna que se sabe que es fecha)
        if 'Última_Fecha' in df_edited.columns:
            df_edited['Última_Fecha'] = pd.to_datetime(df_edited['Última_Fecha'], errors='coerce').dt.date
        
        # 2. Reordenamiento CLAVE de columnas para dejar 'Última_Fecha' al final
        cols = df_edited.columns.tolist()
        if 'Última_Fecha' in cols:
            cols.remove('Última_Fecha')
            cols.append('Última_Fecha')
        
        # Guardar solo las columnas que tienen datos
        valid_cols = [col for col in cols if not pd.isna(df_edited[col]).all()]
        df_to_save = df_edited[valid_cols].copy()
        
        # 3. Sobrescribir el archivo Excel
        df_to_save.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        
        # 4. Limpiar la caché de los datos principales
        load_data.clear()
        
        return True
    except Exception as e:
        st.error(f"Error al guardar los datos de atletas: {e}")
        return False

def save_readiness_data(atleta, fecha, sueno, molestias, disposicion):
    """Añade una nueva fila al archivo readiness_data.xlsx, actualiza el archivo y el DataFrame global."""
    
    try:
        current_df, _ = load_readiness_data()
        if current_df.empty:
             current_df = pd.DataFrame(columns=READINESS_REQUIRED_COLUMNS)
    except Exception:
         current_df = pd.DataFrame(columns=READINESS_REQUIRED_COLUMNS)

    new_entry = {
        'Atleta': atleta, 
        'Fecha': pd.to_datetime(fecha), 
        'Sueño': sueno, 
        'Molestias': molestias, 
        'Disposicion': disposicion
    }
    
    new_df = pd.DataFrame([new_entry])
    
    df_updated = pd.concat([current_df, new_df], ignore_index=True)
    
    try:
        df_updated.to_excel(READINESS_FILE, index=False, engine='openpyxl')
        load_readiness_data.clear() 
        return load_readiness_data()[0], True
        
    except Exception as e:
        st.error(f"Error al guardar los datos de bienestar: {e}")
        return current_df, False
    
def save_tests_data(df_edited):
    """Guarda el DataFrame editado de pruebas activas en el archivo XLSX."""
    # 1. Aseguramos que la columna 'Visible' tenga 'Sí' o 'No' al guardar en Excel
    df_edited['Visible'] = df_edited['Visible'].apply(lambda x: 'Sí' if x else 'No')
    
    # Aseguramos que solo se guarden las columnas requeridas
    df_to_save = df_edited[['NombrePrueba', 'ColumnaRM', 'Visible']].copy()
    
    try:
        # 2. Sobrescribir el archivo Excel
        df_to_save.to_excel(PRUEBAS_FILE, index=False, engine='openpyxl')
        
        # 3. Limpiar la caché de las pruebas para que la calculadora se actualice
        load_tests_data.clear()
        
        return True
    except Exception as e:
        st.error(f"Error al guardar las pruebas: {e}")
        return False

def save_calendar_data(df_edited):
    """Guarda el DataFrame editado de calendario en el archivo XLSX."""
    # 1. Aseguramos que la columna 'Habilitado' tenga 'Sí' o 'No' al guardar en Excel
    df_edited['Habilitado'] = df_edited['Habilitado'].apply(lambda x: 'Sí' if x else 'No')
    df_edited_cleaned = df_edited.dropna(subset=['Evento', 'Fecha'], how='any') # Limpiar filas sin datos esenciales
    
    # 2. Aseguramos que solo se guardan las columnas requeridas
    df_to_save = df_edited_cleaned[['Evento', 'Fecha', 'Detalle', 'Habilitado']].copy()
    
    try:
        # 3. Sobrescribir el archivo Excel
        df_to_save.to_excel(CALENDAR_FILE, index=False, engine='openpyxl')
        
        # 4. Limpiar la caché del calendario para que se actualice
        load_calendar_data.clear()
        
        return True
    except Exception as e:
        st.error(f"Error al guardar el calendario: {e}")
        return False


# --- 5. INTERFAZ PRINCIPAL DE STREAMLIT ---

st.set_page_config(layout="wide", page_title="Gestión de Rendimiento Atleta")

# Muestra mensajes de estado críticos (CREACIÓN o ERROR)
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
        st.image(LOGO_PATH, width=120) 
    
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
            if st.button("Recargar Calendario", help="Recarga 'calendario_data.xlsx'."):
                load_calendar_data.clear()
                load_tests_data.clear()
                st.rerun()

        st.markdown("---")
        st.subheader("1. Gestión de Atletas y Marcas RM (Edición Directa)")
        st.warning("⚠️ **ATENCIÓN**: Para añadir **nuevas pruebas RM**, debes agregar la columna al archivo **atletas_data.xlsx** manualmente, subirlo a GitHub y luego hacer clic en 'Recargar Datos Atletas...'.")

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
        st.caption(f"**Edita la tabla directamente para añadir/quitar pruebas y marcar 'Visible' con el chulito. Puedes borrar filas haciendo clic en el número de fila.**")
        
        # --- TABLA EDITABLE DE PRUEBAS ---
        
        # 1. Widget de edición
        df_edited = st.data_editor(
            df_pruebas_full, # Usamos el DF COMPLETO
            num_rows="dynamic", # Permite añadir y eliminar filas
            column_config={
                "Visible": st.column_config.CheckboxColumn(
                    "Visible",
                    help="Marca para mostrar la prueba en la calculadora.",
                    default=False,
                ),
                "ColumnaRM": st.column_config.Column("ColumnaRM", help="Debe coincidir EXACTAMENTE con el nombre de columna en Datos de Atletas (Ej: Biceps_RM)"), 
                "NombrePrueba": st.column_config.Column("NombrePrueba"),
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
    
    # Manejo de error si el atleta no está en el DF después de la edición
    if atleta_actual not in df_atletas['Atleta'].values:
        st.error(f"El atleta '{atleta_actual}' no se encuentra en la base de datos. Por favor, contacta al entrenador o cierra sesión.")
        st.stop()
        
    datos_usuario = df_atletas[df_atletas['Atleta'] == atleta_actual].iloc[0]
    
    st.write(f"**Hola, {atleta_actual}. Selecciona un ejercicio para cargar tu RM registrado.**")

    # --- ENTRADA DE DATOS RM Y BARRA ---
    col_ejercicio, col_barra = st.columns([2, 1])

    with col_ejercicio:
        # Usamos el DF FILTRADO (df_pruebas)
        ejercicio_options = df_pruebas['NombrePrueba'].tolist() 
        
        if not ejercicio_options:
            st.warning("No hay pruebas visibles. El Entrenador debe configurar el archivo 'pruebas_activas.xlsx'.")
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
            
            # Buscar el valor de RM en el DataFrame de Atletas, incluso si es una columna nueva
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
    
    # Usar el peso del estimador RIR para la conversión, ya que es el cálculo más específico
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
    st.caption(f"Archivo de origen: **{CALENDAR_FILE}**")
    
    if rol_actual == 'Entrenador':
        st.subheader("Gestión de Cronograma (Vista Entrenador)")
        st.caption("⚠️ **Edita, añade o elimina filas directamente en la tabla. El 'chulito' en 'Habilitado' controla la visibilidad para los atletas.**")
        
        # Copiamos el DF completo (booleano) para la edición
        df_calendar_edit = df_calendario_full.copy()
        
        # Widget de edición para el calendario
        df_edited_calendar = st.data_editor(
            df_calendar_edit,
            num_rows="dynamic",
            column_config={
                # DEFINICIÓN EXPLÍCITA DEL TIPO DE COLUMNA DE FECHA
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
        
        # Botón de guardado
        if st.button("💾 Guardar Cambios en Calendario y Aplicar", type="primary", key="save_calendar_data_btn"):
            df_edited_cleaned = df_edited_calendar.dropna(subset=['Evento', 'Fecha'], how='any')

            if save_calendar_data(df_edited_cleaned):
                st.success("✅ Calendario actualizado y guardado con éxito. Recargando aplicación...")
                st.rerun()
            else:
                st.error("❌ No se pudieron guardar los cambios en el calendario.")
        
        st.markdown("---")
        st.subheader(f"Vista del Atleta")
        eventos_mostrar = df_calendario # Usamos el DF ya filtrado globalmente
        
    else:
        st.subheader(f"Próximos Eventos Habilitados para {atleta_actual}")
        eventos_mostrar = df_calendario
    
    # Muestra la versión filtrada/actualizada
    st.dataframe(eventos_mostrar, use_container_width=True)

# ----------------------------------------------------------------------------------
## PESTAÑA 4: PERFIL (Visible para todos)
# ----------------------------------------------------------------------------------
with PERFIL_TAB:
    st.header(f"👤 Perfil y Datos de Contacto de {atleta_actual}")
    st.caption(f"Archivo de origen: **{PERFILES_FILE}**")

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
        st.warning(f"No se encontró información de perfil para **{atleta_actual}** en el archivo {PERFILES_FILE}. Por favor, verifique el Excel.")

    if rol_actual == 'Entrenador':
        st.markdown("---")
        st.subheader("Gestión de Perfiles (Vista Entrenador)")
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
    st.caption(f"Archivo de origen: **{RANKING_FILE}**")
    
    st.dataframe(
        df_ranking, 
        use_container_width=True,
        column_config={
            "Posicion": st.column_config.NumberColumn("Posición", format="%d"),
            "Oros": st.column_config.NumberColumn("🥇 Oros", format="%d"),
            "Platas": st.column_config.NumberColumn("🥈 Platas", format="%d"),
            "Bronces": st.column_config.NumberColumn("🥉 Bronces", format="%d"),
            "Puntos": st.column_config.NumberColumn("Puntos", format="%d"),
        },
        height=35 * (len(df_ranking) + 1)
    )

    current_athlete_rank = df_ranking[df_ranking['Atleta'] == atleta_actual]
    if not current_athlete_rank.empty:
        rank_data = current_athlete_rank.iloc[0]
        st.markdown("---")
        st.subheader(f"Tu Posición Actual: {atleta_actual}")
        
        col_rank, col_points, col_medals = st.columns(3)
        
        col_rank.metric("Rango", f"#{int(rank_data['Posicion'])}")
        col_points.metric("Puntos Totales", f"{int(rank_data['Puntos'])} pts")
        
        medals_text = f"🥇 {int(rank_data['Oros'])} | 🥈 {int(rank_data['Platas'])} | 🥉 {int(rank_data['Bronces'])}"
        col_medals.markdown(f"**Medallas:** <div style='font-size: 1.5em;'>{medals_text}</div>", unsafe_allow_html=True)


# --- FIN DEL CÓDIGO ---
