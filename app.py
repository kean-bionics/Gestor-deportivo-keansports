import streamlit as st
import pandas as pd
import numpy as np
import os
import io
from PIL import Image
from datetime import datetime, timedelta, time

# --- 1. CONFIGURACIÓN INICIAL DE ARCHIVOS Y FUNCIONES DE CÁLCULO ---

# Archivo 1: Atletas y Marcas RM
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

# Archivo 7: Resultados de Pruebas Físicas (NUEVO)
TEST_RESULTS_FILE = 'test_results.xlsx'
# Columnas que pediste, más ID y Atleta para identificación
TEST_RESULTS_REQUIRED_COLUMNS = [
    'ID', 'Atleta', 'Fecha', '100m (s)', '400m (s)', '5k (min)', '10km (min)', 
    'Course Navette (max)', 'Salto Largo (cm)', 'Salto Alto (cm)', 
    'Dinamometria Izq (kg)', 'Dinamometria Der (kg)'
]

# RUTA DEL LOGO
LOGO_PATH = 'logo.png' 

# --- FUNCIONES DE CÁLCULO (MOVIDAS AL INICIO PARA EVITAR NAMEERROR) ---

def calculate_tmb_mifflin(peso_kg, altura_cm, edad_anos, sexo):
    """Calcula la Tasa Metabólica Basal (TMB) usando la fórmula de Mifflin-St Jeor."""
    if peso_kg <= 0 or altura_cm <= 0 or edad_anos <= 0:
        return 0
    if sexo == 'Hombre':
        tmb = (10 * peso_kg) + (6.25 * altura_cm) - (5 * edad_anos) + 5
    else: # Mujer
        tmb = (10 * peso_kg) + (6.25 * altura_cm) - (5 * edad_anos) - 161
    return round(tmb)

def calculate_and_sort_ranking(df):
    """Calcula los puntos y ordena el ranking por jerarquía de medallas (Oros > Platas > Bronces)."""
    
    for col in ['Oros', 'Platas', 'Bronces']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
    df['Puntos'] = (df['Oros'] * 10) + (df['Platas'] * 3) + (df['Bronces'] * 1)
    
    df_sorted = df.sort_values(
        by=['Oros', 'Platas', 'Bronces', 'Puntos'], 
        ascending=[False, False, False, False]
    ).copy()
    
    df_sorted['Posicion'] = np.arange(1, len(df_sorted) + 1)
    
    return df_sorted

# ----------------------------------------------------------------------------------


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
            
            if 'Fecha' in calendar_df.columns:
                calendar_df['Fecha'] = pd.to_datetime(calendar_df['Fecha'], errors='coerce').dt.date

        except:
             excel_exists = False

    if not excel_exists or calendar_df.empty:
        data = {
            'Evento': ['Prueba de RM (Sentadilla/PB)', 'Evaluación de Resistencia', 'Reunión de Equipo'],
            'Fecha': [datetime.now().date() + timedelta(days=30), datetime.now().date() + timedelta(days=60), datetime.now().date() + timedelta(days=10)],
            'Detalle': ['Test de 1RM', 'Test de Cooper o 5K', 'Revisión de Mes'],
            'Habilitado': ['Sí', 'Sí', 'No']
        }
        calendar_df = pd.DataFrame(data, columns=CALENDAR_REQUIRED_COLUMNS) 
        calendar_df['Fecha'] = pd.to_datetime(calendar_df['Fecha'], errors='coerce').dt.date
        calendar_df.to_excel(CALENDAR_FILE, index=False, engine='openpyxl') 

    if 'Habilitado' in calendar_df.columns:
        calendar_df['Habilitado'] = calendar_df['Habilitado'].astype(str).str.lower().str.strip() == 'sí'

    return calendar_df

@st.cache_data(ttl=3600)
def load_tests_data():
    """Carga la lista de pruebas activas."""
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
    
    return df_tests, status_message 

@st.cache_data(ttl=3600)
def load_perfil_data():
    """Carga los datos de perfil de los atletas desde el archivo Excel."""
    df_perfil = pd.DataFrame()
    excel_exists = os.path.exists(PERFILES_FILE)
    status_message = None

    DEFAULT_PROFILE_DATA = {
        'Atleta': ['Tu Nombre', 'Juan Pérez', 'Ana Gómez'],
        'Edad': [30, 25, 22],
        'Fecha_Nacimiento': ['1994-01-01', '1999-05-10', '2002-01-20'],
        'Documento': ['999', '12345678', '87654321'],
        'Altura_cm': [180, 178, 165],
        'Sexo': ['Hombre', 'Hombre', 'Mujer'],
        'Posicion': ['Entrenador', 'Delantero', 'Defensora'],
        'Email': ['tu@mail.com', 'juan@mail.com', 'ana@mail.com']
    }
    REQUIRED_PROFILE_COLUMNS = list(DEFAULT_PROFILE_DATA.keys())
    
    if excel_exists:
        try:
            df_perfil = pd.read_excel(PERFILES_FILE, engine='openpyxl')
            df_perfil.columns = df_perfil.columns.str.strip()
            
            if 'Sexo' not in df_perfil.columns:
                 df_perfil['Sexo'] = 'Hombre'
                 
        except:
             excel_exists = False

    if not excel_exists or df_perfil.empty:
        df_perfil = pd.DataFrame(DEFAULT_PROFILE_DATA, columns=REQUIRED_PROFILE_COLUMNS) 
        df_perfil.to_excel(PERFILES_FILE, index=False, engine='openpyxl') 
        status_message = f"Archivo '{PERFILES_FILE}' creado con éxito."

    return df_perfil, status_message

@st.cache_data(ttl=3600)
def load_ranking_data():
    """Carga los datos de ranking, los calcula, ordena y crea el archivo si no existe."""
    df_ranking = pd.DataFrame()
    status_message = None
    excel_exists = os.path.exists(RANKING_FILE)
    
    if excel_exists:
        try:
            df_ranking = pd.read_excel(RANKING_FILE, engine='openpyxl')
            df_ranking.columns = df_ranking.columns.str.strip() 
            
            missing_cols = [col for col in RANKING_REQUIRED_COLUMNS if col not in df_ranking.columns]
            if missing_cols:
                 status_message = f"ADVERTENCIA: El archivo '{RANKING_FILE}' no tiene las columnas requeridas: {', '.join(missing_cols)}. Favor de corregir el archivo."
                 full_ranking_cols = RANKING_REQUIRED_COLUMNS + ['Puntos'] 
                 df_ranking = pd.DataFrame(columns=full_ranking_cols) 
            
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
        }
        df_ranking = pd.DataFrame(data, columns=RANKING_REQUIRED_COLUMNS) 
        df_ranking.to_excel(RANKING_FILE, index=False, engine='openpyxl')
        status_message = f"Archivo '{RANKING_FILE}' creado con éxito."

    if not df_ranking.empty:
        df_ranking = calculate_and_sort_ranking(df_ranking)
        
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

@st.cache_data(ttl=3600)
def load_test_results_data():
    """Carga los datos de los resultados de pruebas físicas. Si no existe, lo crea."""
    df = pd.DataFrame()
    excel_exists = os.path.exists(TEST_RESULTS_FILE)
    status_message = None
    
    if excel_exists:
        try:
            df = pd.read_excel(TEST_RESULTS_FILE, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            # Asegurar que las columnas requeridas existan
            missing_cols = [col for col in TEST_RESULTS_REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                status_message = f"ADVERTENCIA: El archivo de pruebas físicas existe, pero faltan columnas: {', '.join(missing_cols)}. Se añadirán vacías."
                for col in missing_cols:
                    df[col] = None
                    
        except Exception as e:
            status_message = f"Error al leer el archivo Excel de pruebas físicas ({e}). Se creará un archivo nuevo de ejemplo."
            excel_exists = False

    if not excel_exists or df.empty or len(df.columns) < 3: 
        status_message = f"Creando el archivo '{TEST_RESULTS_FILE}' de ejemplo con la estructura inicial."
        data = {
            'ID': [1, 2, 3],
            'Atleta': ['Juan Pérez', 'Ana Gómez', 'Tu Nombre'],
            'Fecha': [datetime.now().date(), datetime.now().date() - timedelta(days=7), datetime.now().date() - timedelta(days=14)],
            '100m (s)': [11.5, 13.2, 11.0],
            '400m (s)': [55.0, 68.0, 52.0],
            '5k (min)': [22.0, 28.0, 20.0],
            '10km (min)': [48.0, 60.0, 42.0],
            'Course Navette (max)': [12, 9, 14],
            'Salto Largo (cm)': [250, 220, 270],
            'Salto Alto (cm)': [65, 55, 75],
            'Dinamometria Izq (kg)': [50, 35, 60],
            'Dinamometria Der (kg)': [55, 38, 65]
        }
        df = pd.DataFrame(data, columns=TEST_RESULTS_REQUIRED_COLUMNS)
        
        df.to_excel(TEST_RESULTS_FILE, index=False, engine='openpyxl')
        status_message += " Archivo creado con éxito."
        
    # Conversión de tipos de datos para columnas conocidas
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.date

    # Asegurar ID como entero
    df['ID'] = pd.to_numeric(df['ID'], errors='coerce').fillna(0).astype(int)
        
    return df, status_message


# --- 3. CARGA DE DATOS AL INICIO DE LA APP Y MUESTREO DE TOASTS ---

df_atletas, initial_status = load_data() 
df_calendario_full = load_calendar_data() 
df_calendario = df_calendario_full[df_calendario_full['Habilitado'] == True].copy() 
df_pruebas_full, tests_status = load_tests_data() 
df_pruebas = df_pruebas_full[df_pruebas_full['Visible'] == True].copy() 
df_perfiles, perfil_status = load_perfil_data() 
df_ranking, ranking_status = load_ranking_data()
df_readiness, readiness_status = load_readiness_data()
df_test_results_full, test_results_status = load_test_results_data() # NUEVA CARGA


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
if test_results_status and ('creado' in test_results_status.lower() or 'error' in test_results_status.lower() or 'adver' in test_results_status.lower()):
    st.toast(test_results_status, icon="🏃")


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

def save_ranking_data(df_edited):
    """Guarda el DataFrame editado del ranking, recalculando y ordenando primero."""
    
    # 1. Limpiar filas vacías
    df_cleaned = df_edited.dropna(subset=['Atleta'], how='any').copy()
    
    # 2. Calcular puntos y ordenar (la lógica clave)
    df_sorted = calculate_and_sort_ranking(df_cleaned)

    # 3. Guardar solo las columnas requeridas
    df_to_save = df_sorted[RANKING_REQUIRED_COLUMNS]
    
    try:
        df_to_save.to_excel(RANKING_FILE, index=False, engine='openpyxl')
        load_ranking_data.clear() 
        return True
    except Exception as e:
        st.error(f"Error al guardar el ranking: {e}")
        return False

def save_test_results_data(df_edited):
    """Guarda el DataFrame editado de resultados de pruebas físicas en el archivo XLSX."""
    
    try:
        # Limpieza y preparación (eliminar filas vacías y asegurar columnas)
        df_cleaned = df_edited.dropna(subset=['Atleta', 'Fecha'], how='any').copy()
        
        # 1. Asegurar que las nuevas filas tengan un ID
        max_id = df_cleaned['ID'].max() if 'ID' in df_cleaned.columns and not df_cleaned.empty else 0
        
        for index, row in df_cleaned.iterrows():
            if pd.isna(row.get('ID', 0)) or row.get('ID', 0) == 0:
                max_id += 1
                df_cleaned.loc[index, 'ID'] = max_id
        
        # 2. Convertir la Fecha antes de guardar
        if 'Fecha' in df_cleaned.columns:
            df_cleaned['Fecha'] = pd.to_datetime(df_cleaned['Fecha'], errors='coerce').dt.date
            
        # 3. Guardar todas las columnas que existen en el DF editado
        df_to_save = df_cleaned.copy()
        
        # 4. Sobrescribir el archivo Excel
        df_to_save.to_excel(TEST_RESULTS_FILE, index=False, engine='openpyxl')
        
        # 5. Limpiar la caché
        load_test_results_data.clear()
        
        return True
    except Exception as e:
        st.error(f"Error al guardar los resultados de pruebas: {e}")
        return False


# --- FUNCIONES ADICIONALES ---

def get_days_until(date_obj):
    """Calcula los días restantes hasta una fecha, o un gran número si ya pasó."""
    today = datetime.now().date()
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
        
    if pd.isna(date_obj) or date_obj is None:
        return 999
        
    delta = date_obj - today
    return delta.days

def highlight_imminent_events(df):
    """Aplica estilo de fondo a filas con eventos a menos de 5 días."""
    
    if 'Days_Until' not in df.columns:
        return pd.DataFrame('', index=df.index, columns=df.columns)
        
    mask = (df['Days_Until'] >= 0) & (df['Days_Until'] <= 5)
    
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    
    # Aplicar estilo: fondo verde claro de 'success'
    styles.loc[mask] = 'background-color: #d4edda; color: #155724; font-weight: bold;' 
    
    return styles

# --- FIN DE FUNCIONES AUXILIARES ---


# --- 5. INTERFAZ PRINCIPAL DE STREAMLIT ---

st.set_page_config(layout="wide", page_title="Gestión de Rendimiento Atleta")


# Inicializar el estado de la sesión
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ----------------------------------------------------------------------
# --- PANTALLA DE ACCESO/BIENVENIDA ---
# ----------------------------------------------------------------------
if not st.session_state['logged_in']:
    
    try:
        logo_img = Image.open(LOGO_PATH)
    except FileNotFoundError:
        logo_img = None
        
    logo_col, spacer_col = st.columns([1, 10])
    with logo_col:
        if logo_img:
            st.image(logo_img, width=120) 
        else:
            st.markdown("## 🏋️")
            
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

st.title("💪 GESTOR DEPORTIVO - HAPKIDO BETA V1.0")
logout() 

if st.session_state['logged_in']:
    try:
        logo_img = Image.open(LOGO_PATH)
        st.sidebar.image(logo_img, width=100)
    except FileNotFoundError:
        st.sidebar.markdown("## 🏋️ Logo")
        
    st.sidebar.markdown("---")

rol_actual = st.session_state['rol']
atleta_actual = st.session_state['atleta_nombre']

# Definición de pestañas (PRUEBAS_TAB es la nueva)
if rol_actual == 'Entrenador':
    tab1, tab2, PRUEBAS_TAB, CALENDAR_TAB, PERFIL_TAB, ACOND_TAB, GESTION_PESO_TAB, RECUPERACION_TAB, RANKING_TAB = st.tabs([
        "📊 Vista Entrenador (Datos)", 
        "🧮 Calculadora de Carga", 
        "🏋️ Pruebas Físicas", # NUEVA PESTAÑA
        "📅 Calendario", 
        "👤 Perfil", 
        "🏃 Acondicionamiento", 
        "⚖️ Gestión de Peso",
        "🌡️ Recuperación",
        "🏆 Ranking"
    ])
else:
    tab2, PRUEBAS_TAB, CALENDAR_TAB, PERFIL_TAB, ACOND_TAB, GESTION_PESO_TAB, RECUPERACION_TAB, RANKING_TAB = st.tabs([
        "🧮 Calculadora de Carga", 
        "🏋️ Pruebas Físicas", # NUEVA PESTAÑA
        "📅 Calendario", 
        "👤 Perfil", 
        "🏃 Acondicionamiento", 
        "⚖️ Gestión de Peso",
        "🌡️ Recuperación",
        "🏆 Ranking"
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
## PESTA 1: VISTA ENTRENADOR (Solo visible para Entrenador)
# ----------------------------------------------------------------------------------
if rol_actual == 'Entrenador':
    with tab1:
        st.header("Datos de Atletas y Marcas RM")
        st.subheader("Control Total (Vista del Entrenador)")
        
        # Botones de recarga
        col_recarga_atletas, col_recarga_pruebas = st.columns(2)
        with col_recarga_atletas:
            if st.button("Recargar Datos Atletas/Perfiles/Ranking", help="Recarga todos los archivos de datos dinámicos."):
                load_data.clear()
                load_perfil_data.clear()
                load_ranking_data.clear()
                load_test_results_data.clear() # Limpiamos la caché de las pruebas también
                st.rerun() 
        with col_recarga_pruebas:
            if st.button("Recargar Calendario/Pruebas Modulares", help="Recarga 'calendario_data.xlsx' y 'pruebas_activas.xlsx'."):
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
            df_pruebas_full,
            num_rows="dynamic",
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
## PESTAÑA 3: PRUEBAS FÍSICAS (NUEVA - Visible para todos)
# ----------------------------------------------------------------------------------
with PRUEBAS_TAB:
    st.header("🏋️ Historial y Gestión de Pruebas Físicas")
    st.caption(f"Archivo de origen: **{TEST_RESULTS_FILE}**. El Entrenador edita y carga todos los resultados.")

    if rol_actual == 'Entrenador':
        st.subheader("Gestión de Resultados (Vista Entrenador)")
        st.warning("⚠️ **ATENCIÓN**: El Entrenador puede ver, editar y añadir todos los resultados. Asegúrate de que las columnas de pruebas coincidan con el Excel que cargues, si añades más.")
        
        df_editor_tests = df_test_results_full.copy()
        
        # Configuración de columnas base para el editor
        test_col_config = {
            "ID": st.column_config.NumberColumn("ID", disabled=True),
            "Atleta": st.column_config.TextColumn("Atleta", help="Nombre del atleta (Debe coincidir con el login)", required=True),
            "Fecha": st.column_config.DateColumn("Fecha de Prueba", required=True),
            "100m (s)": st.column_config.NumberColumn("100m (segundos)", format="%.2f", step=0.01),
            "400m (s)": st.column_config.NumberColumn("400m (segundos)", format="%.1f", step=0.1),
            "5k (min)": st.column_config.NumberColumn("5k (minutos)", format="%.1f", step=0.1),
            "10km (min)": st.column_config.NumberColumn("10km (minutos)", format="%.1f", step=0.1),
            "Course Navette (max)": st.column_config.NumberColumn("Course Navette (nivel)", format="%d", step=1),
            "Salto Largo (cm)": st.column_config.NumberColumn("Salto Largo (cm)", format="%d", step=1),
            "Salto Alto (cm)": st.column_config.NumberColumn("Salto Alto (cm)", format="%d", step=1),
            "Dinamometria Izq (kg)": st.column_config.NumberColumn("Dinamo Izq (kg)", format="%d", step=1),
            "Dinamometria Der (kg)": st.column_config.NumberColumn("Dinamo Der (kg)", format="%d", step=1),
        }
        
        # Combinar columnas base con las columnas que realmente existen en el DF cargado
        # Esto permite que el usuario añada columnas en el Excel manualmente y que sigan saliendo
        editor_columns = {}
        for col in df_editor_tests.columns:
            editor_columns[col] = test_col_config.get(col, st.column_config.TextColumn(col)) # Si no existe en la config, usa TextColumn por defecto
        
        df_edited_tests = st.data_editor(
            df_editor_tests,
            num_rows="dynamic",
            column_config=editor_columns,
            use_container_width=True,
            key="test_results_data_editor"
        )
        
        if st.button("💾 Guardar Resultados de Pruebas y Aplicar", type="primary", key="save_test_results_btn"):
            if save_test_results_data(df_edited_tests):
                st.success("✅ Resultados de Pruebas actualizados y guardados con éxito. Recargando aplicación...")
                st.rerun()
            else:
                st.error("❌ No se pudieron guardar los datos de pruebas.")
                
        st.markdown("---")
        st.subheader("Vista Completa (Todos los Atletas)")
        df_display = df_test_results_full.sort_values(by=['Atleta', 'Fecha'], ascending=[True, False]).copy()
        
    else: # Vista Atleta
        st.subheader(f"Tus Resultados de Pruebas Físicas Históricas, {atleta_actual}")
        
        df_filtered = df_test_results_full[df_test_results_full['Atleta'] == atleta_actual].copy()
        df_display = df_filtered.sort_values(by='Fecha', ascending=False)
        
        if df_display.empty:
            st.info(f"No hay resultados de pruebas registrados para {atleta_actual} aún.")

    if not df_display.empty:
        # Excluir la columna ID para la visualización final si no es entrenador
        cols_to_display = [col for col in df_display.columns if col != 'ID']
        
        # Muestra la tabla (filtrada o completa)
        st.dataframe(
            df_display[cols_to_display],
            use_container_width=True,
            hide_index=True
        )

# ----------------------------------------------------------------------------------
## PESTAÑA 4: CALENDARIO (Visible para todos)
# ----------------------------------------------------------------------------------
with CALENDAR_TAB:
    st.header("📅 Calendario de Pruebas y Actividades")
    st.caption(f"Archivo de origen: **{CALENDAR_FILE}**")
    
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
## PESTAÑA 5: PERFIL (Visible para todos)
# ----------------------------------------------------------------------------------
with PERFIL_TAB:
    st.header(f"👤 Perfil y Datos de Contacto de {atleta_actual}")
    st.caption(f"Archivos de origen: Atletas y Perfiles")

    datos_perfil = df_perfiles[df_perfiles['Atleta'] == atleta_actual].iloc[0] if atleta_actual in df_perfiles['Atleta'].values else None
    datos_rm = df_atletas[df_atletas['Atleta'] == atleta_actual].iloc[0] if atleta_actual in df_atletas['Atleta'].values else None
    
    if datos_perfil is None:
        st.warning("No se encontró información de perfil (Altura, Edad, Sexo, etc.). Edita la hoja de Perfiles.")
        datos_perfil = pd.Series({'Edad': np.nan, 'Altura_cm': np.nan, 'Sexo': 'Hombre'})
    
    # --- MÓDULO 1: INFORMACIÓN PERSONAL ---
    st.subheader("Información Personal")
    
    col_personal_1, col_personal_2 = st.columns(2)
    
    for i, (key, value) in enumerate(datos_perfil.drop(labels=['Atleta', 'Sexo'], errors='ignore').items()):
        if key.lower() == 'fecha_nacimiento' and pd.notna(value):
            value_display = value.strftime('%Y-%m-%d') if isinstance(value, pd.Timestamp) else str(value)
        else:
            value_display = str(value) if pd.notna(value) else 'N/D'
            
        with col_personal_1 if i % 2 == 0 else col_personal_2:
            st.metric(label=key.replace('_', ' ').title(), value=value_display)
            
    st.markdown("---")
    st.subheader("Diagnóstico de Fuerza Relativa y Composición Corporal")
    
    # Extracción de valores seguros para cálculos
    peso_kg = float(datos_rm.get('PesoCorporal', 0)) if datos_rm is not None and pd.notna(datos_rm.get('PesoCorporal')) else 0
    sentadilla_rm = float(datos_rm.get('Sentadilla_RM', 0)) if datos_rm is not None and pd.notna(datos_rm.get('Sentadilla_RM')) else 0
    pressbanca_rm = float(datos_rm.get('PressBanca_RM', 0)) if datos_rm is not None and pd.notna(datos_rm.get('PressBanca_RM')) else 0
    altura_cm = float(datos_perfil.get('Altura_cm', 0)) if pd.notna(datos_perfil.get('Altura_cm')) else 0
    
    # Cálculo de IMC
    if peso_kg > 0 and altura_cm > 0:
        altura_m = altura_cm / 100
        imc = peso_kg / (altura_m ** 2)
        imc_display = f"{imc:.1f}"
    else:
        imc = 0
        imc_display = "N/D"

    # Cálculo de Fuerza Relativa
    rel_squat = round(sentadilla_rm / peso_kg, 2) if peso_kg > 0 and sentadilla_rm > 0 else 0
    rel_bench = round(pressbanca_rm / peso_kg, 2) if peso_kg > 0 and pressbanca_rm > 0 else 0
    ratio_sq_bp = round(sentadilla_rm / pressbanca_rm, 2) if pressbanca_rm > 0 and sentadilla_rm > 0 else 0

    col_metric_1, col_metric_2, col_metric_3 = st.columns(3)
    
    col_metric_1.metric("IMC (Índice de Masa Corporal)", imc_display, help="Peso (kg) / Altura (m)²")
    col_metric_2.metric("Fuerza Relativa (Squat)", f"{rel_squat:.2f}x BW", help="RM de Sentadilla / Peso Corporal. Ideal > 1.5x.")
    col_metric_3.metric("Ratio Squat:Bench", f"{ratio_sq_bp:.2f}:1", help="Relación Sentadilla a Press Banca. Ideal ~1.5:1 para balance.")

    st.markdown("---")
    st.subheader("Análisis de Desequilibrio")
    
    if ratio_sq_bp > 0:
        if ratio_sq_bp > 2.2:
            st.warning("⚠️ **Desequilibrio Notable:** El Press Banca es muy bajo en relación con la Sentadilla. Priorizar el empuje del tren superior.")
        elif ratio_sq_bp < 1.3:
             st.warning("⚠️ **Desequilibrio Notable:** La Sentadilla es muy baja en relación con el Press Banca. Priorizar la cadena posterior y el core.")
        else:
            st.success("✅ **Balance Óptimo:** Ratio Squat:Bench dentro del rango ideal (1.3:1 a 2.2:1).")
    else:
           st.info("Falta el registro de RM de Sentadilla o Press Banca para calcular el balance.")


    if rol_actual == 'Entrenador':
        st.markdown("---")
        st.subheader("Gestión de Perfiles (Vista Entrenador)")
        st.caption("Asegúrate de que la columna 'Atleta' en el Excel coincida exactamente con el nombre de usuario.")
        st.dataframe(df_perfiles, use_container_width=True)


# ----------------------------------------------------------------------------------
## PESTAÑA 6: ACONDICIONAMIENTO
# ----------------------------------------------------------------------------------
with ACOND_TAB:
    st.header("🏃 Calculadora de Desempeño y Acondicionamiento")
    
    datos_perfil = df_perfiles[df_perfiles['Atleta'] == atleta_actual]
    
    if not datos_perfil.empty:
        datos_perfil = datos_perfil.iloc[0]
        edad = pd.to_numeric(datos_perfil.get('Edad', 25), errors='coerce', downcast='integer')
        
        # Fórmula FC Máx: Tanaka (208 - 0.7 * edad)
        fc_max_estimada = round(208 - (0.7 * edad)) if not pd.isna(edad) and edad > 0 else "N/D"

        st.subheader("1. Frecuencia Cardíaca Máxima (FC Máx) y Zonas")
        
        col_edad, col_fc = st.columns([1, 1])
        with col_edad:
            st.metric("Edad Registrada (Aprox.)", f"{int(edad) if not pd.isna(edad) else 'N/D'} años")
            
        with col_fc:
            st.metric("FC Máx Estimada", f"**{fc_max_estimada} ppm** (Fórmula de Tanaka)")

        if not pd.isna(fc_max_estimada) and isinstance(fc_max_estimada, int):
            st.markdown("---")
            st.subheader("Visualización de Zonas de Entrenamiento")
            
            # --- LÓGICA DEL GRÁFICO (NUEVO) ---
            
            fc_max_int = int(fc_max_estimada)
            
            zonas_data = {
                "Zona": ["Zona 1: Muy Ligera", "Zona 2: Ligera", "Zona 3: Aeróbica", "Zona 4: Umbral", "Zona 5: Máxima"],
                "Mínimo (ppm)": [
                    round(fc_max_int * 0.50),
                    round(fc_max_int * 0.60),
                    round(fc_max_int * 0.70),
                    round(fc_max_int * 0.80),
                    round(fc_max_int * 0.90),
                ],
                "Máximo (ppm)": [
                    round(fc_max_int * 0.60),
                    round(fc_max_int * 0.70),
                    round(fc_max_int * 0.80),
                    round(fc_max_int * 0.90),
                    fc_max_int
                ]
            }
            df_zonas = pd.DataFrame(zonas_data)
            df_zonas.set_index('Zona', inplace=True)
            
            st.bar_chart(df_zonas, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Rangos Exactos de Entrenamiento (ppm)")
            
            col_z1, col_z2, col_z3 = st.columns(3)
            
            col_z1.metric("Zona 1 (50%-60%)", f"{df_zonas.loc['Zona 1: Muy Ligera']['Mínimo (ppm)']} - {df_zonas.loc['Zona 1: Muy Ligera']['Máximo (ppm)']} ppm")
            col_z1.metric("Zona 2 (60%-70%)", f"{df_zonas.loc['Zona 2: Ligera']['Mínimo (ppm)']} - {df_zonas.loc['Zona 2: Ligera']['Máximo (ppm)']} ppm")
            col_z2.metric("Zona 3 (70%-80%)", f"{df_zonas.loc['Zona 3: Aeróbica']['Mínimo (ppm)']} - {df_zonas.loc['Zona 3: Aeróbica']['Máximo (ppm)']} ppm")
            col_z2.metric("Zona 4 (80%-90%)", f"{df_zonas.loc['Zona 4: Umbral']['Mínimo (ppm)']} - {df_zonas.loc['Zona 4: Umbral']['Máximo (ppm)']} ppm")
            col_z3.metric("Zona 5 (90%-100%)", f"{df_zonas.loc['Zona 5: Máxima']['Mínimo (ppm)']} - {df_zonas.loc['Zona 5: Máxima']['Máximo (ppm)']} ppm")

            # --- Fin de la lógica del gráfico ---
        else:
            st.info("No se puede calcular la FC Máx. Asegúrate de que la columna 'Edad' esté registrada en tu perfil.")

    st.markdown("---")
    
    # --- MÓDULO 3: ESTIMACIÓN VAM Y RITMOS ---
    st.subheader("2. Estimador de Ritmo de Carrera (VAM)") # Cambiado a 2
    
    col_dist, col_min, col_sec = st.columns(3)

    with col_dist:
        test_dist = st.number_input("Distancia Total de la Prueba (metros):", min_value=100, value=2000, step=100, key='acond_dist')
    
    with col_min:
        test_minutes = st.number_input("Tiempo de Prueba: Minutos:", min_value=0, value=7, step=1, key='acond_min')
        
    with col_sec:
        test_seconds = st.number_input("Tiempo de Prueba: Segundos:", min_value=0, max_value=59, value=30, step=5, key='acond_sec')

    total_seconds = (test_minutes * 60) + test_seconds
    
    if total_seconds > 0 and test_dist > 0:
        v_ms = test_dist / total_seconds
        v_kmh = v_ms * 3.6
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.metric("VAM Estimada", f"**{v_kmh:.2f} km/h**")
        
        st.markdown("---")
        st.subheader("Ritmos de Carrera para Acondicionamiento:")
        
        ritmos = pd.DataFrame({
            '% VAM': [100, 95, 90, 85, 80],
            'Velocidad (km/h)': [v_kmh, v_kmh * 0.95, v_kmh * 0.90, v_kmh * 0.85, v_kmh * 0.80]
        })
        
        def kmh_to_min_km(kmh):
            if kmh == 0: return "N/D"
            min_per_km = 60 / kmh
            minutes = int(min_per_km)
            seconds = int((min_per_km - minutes) * 60)
            return f"{minutes}:{seconds:02d}"

        ritmos['Ritmo (min/km)'] = ritmos['Velocidad (km/h)'].apply(kmh_to_min_km)
        ritmos['Velocidad (km/h)'] = ritmos['Velocidad (km/h)'].round(2)
        
        st.dataframe(ritmos.set_index('% VAM'), use_container_width=True)
    else:
        st.info("Ingresa los datos de la prueba para calcular el VAM.")


# ----------------------------------------------------------------------------------
## PESTAÑA 7: GESTIÓN DE PESO (NUEVA PESTAÑA)
# ----------------------------------------------------------------------------------

with GESTION_PESO_TAB:
    st.header("⚖️ Gestión de Peso y Nutrición")
    
    datos_perfil = df_perfiles[df_perfiles['Atleta'] == atleta_actual].iloc[0] if atleta_actual in df_perfiles['Atleta'].values else None
    datos_rm = df_atletas[df_atletas['Atleta'] == atleta_actual].iloc[0] if atleta_actual in df_atletas['Atleta'].values else None

    peso_kg = datos_rm.get('PesoCorporal', 0) if datos_rm is not None else 0
    altura_cm = datos_perfil.get('Altura_cm', 0) if datos_perfil is not None else 0
    edad_anos = pd.to_numeric(datos_perfil.get('Edad', 0), errors='coerce', downcast='integer') if datos_perfil is not None else 0
    sexo = datos_perfil.get('Sexo', 'Hombre') if datos_perfil is not None else 'Hombre'


    st.subheader("1. Cálculo de Tasa Metabólica Basal (TMB)")
    
    col_peso, col_alt, col_edad_sexo = st.columns(3)
    
    with col_peso:
        peso_input = st.number_input(
            "Peso Corporal (kg):", 
            min_value=0.0, 
            value=float(peso_kg) if pd.notna(peso_kg) and peso_kg > 0 else 70.0, 
            step=0.5,
            key='gestion_peso_input' 
        )
    with col_alt:
        altura_input = st.number_input(
            "Altura (cm):", 
            min_value=0.0, 
            value=float(altura_cm) if pd.notna(altura_cm) and altura_cm > 0 else 175.0, 
            step=1.0,
            key='gestion_altura_input' 
        )
    with col_edad_sexo:
        edad_input = st.number_input(
            "Edad (años):", 
            min_value=1, 
            value=int(edad_anos) if pd.notna(edad_anos) and edad_anos > 0 else 25, 
            step=1,
            key='gestion_edad_input' 
        )
        sexo_input = st.selectbox("Sexo:", options=['Hombre', 'Mujer'], index=0 if sexo == 'Hombre' else 1, key='gestion_sexo_input')
        
    
    if peso_input > 0 and altura_input > 0 and edad_input > 0:
        tmb_calc = calculate_tmb_mifflin(peso_input, altura_input, edad_input, sexo_input)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.metric(
            "Tasa Metabólica Basal (TMB)", 
            f"**{tmb_calc} kcal/día** (Fórmula de Mifflin-St Jeor)"
        )

        st.markdown("---")
        st.subheader("2. Gasto Calórico Total y Objetivos")
        
        col_act, col_obj = st.columns(2)
        
        act_factors = {
            "Sedentario (poco o ningún ejercicio)": 1.2,
            "Ligero (ejercicio 1-3 días/sem)": 1.375,
            "Moderado (ejercicio 3-5 días/sem)": 1.55,
            "Alto (ejercicio 6-7 días/sem)": 1.725,
            "Muy Alto (entrenamientos 2 veces/día)": 1.9
        }
        
        with col_act:
            factor_label = st.selectbox(
                "Nivel de Actividad:",
                options=list(act_factors.keys()),
                key='gestion_act_input'
            )
            factor_actividad = act_factors[factor_label] 

        obj_factors = {
            "Mantenimiento": 0,
            "Definición (Bajar peso)": -500,
            "Volumen (Subir peso)": 500
        }
        
        with col_obj:
            objetivo_label = st.selectbox(
                "Objetivo de Peso:",
                options=list(obj_factors.keys()),
                key='gestion_obj_input'
            )
            objetivo_calorico = obj_factors[objetivo_label]
            
        get_calc = round(tmb_calc * factor_actividad) 
        calorias_objetivo = get_calc + objetivo_calorico

        st.metric(
            "Gasto Energético Total (GET)",
            f"{get_calc} kcal/día"
        )
        st.metric(
            "Objetivo Calórico Diario",
            f"**{calorias_objetivo} kcal/día**"
        )

        st.markdown("---")
        st.subheader("3. Hidratación Sugerida 💧")
        
        agua_litros = round(peso_input * 0.035, 1) 
        
        st.metric(
            "Agua Sugerida",
            f"**{agua_litros} Litros/día** (35 ml por kg de peso)"
        )
        
        st.caption("Ajustar este valor al alza en días de entrenamiento intenso o calor.")
        
    else:
        st.warning("Ingresa tu Peso, Altura y Edad en tu Perfil para calcular tus métricas nutricionales.")


# ----------------------------------------------------------------------------------
## PESTAÑA 8: RECUPERACIÓN (DIAGNÓSTICO DE SESIÓN)
# ----------------------------------------------------------------------------------

with RECUPERACION_TAB:
    st.header("🌡️ Protocolos de Recuperación y Movilidad")
    st.caption("Herramientas de diagnóstico y guía para optimizar tu estado físico.")
    st.markdown("---")

    # --- MÓDULO 1: DIAGNÓSTICO DE ESTADO SRD (EN VIVO) ---
    st.subheader("1. Diagnóstico de Recuperación de Sesión (SRD)")
    
    st.caption("Mueve los deslizadores para obtener una recomendación de intensidad instantánea.")

    col_sleep, col_pain, col_ready = st.columns(3)
    
    with col_sleep:
        sueno = st.slider("1. Calidad del Sueño:", min_value=1, max_value=5, value=4, help="1=Pésimo, 5=Excelente", key='session_sueno')
    
    with col_pain:
        molestias = st.slider("2. Nivel de Molestias/Dolor:", min_value=1, max_value=5, value=2, help="1=Ninguna, 5=Severa", key='session_molestias')
        
    with col_ready:
        disposicion = st.slider("3. Disposición para Entrenar:", min_value=1, max_value=5, value=4, help="1=Baja, 5=Alta", key='session_disposicion')
        
    # Cálculo de la Puntuación Media
    score = (sueno + (5 - molestias) + disposicion) / 3 
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if score >= 4.0:
        st.success(f"🟢 **SCORE SRD: {score:.1f}** (Óptimo)")
        st.markdown("**Recomendación:** Estás en estado óptimo. Sigue tu programación con intensidad.", unsafe_allow_html=True)
    elif score >= 3.0:
        st.warning(f"🟡 **SCORE SRD: {score:.1f}** (Adecuado)")
        st.markdown("**Recomendación:** Estado adecuado. Procede, pero respeta estrictamente los RIR/RPE y reduce el volumen si sientes fatiga.", unsafe_allow_html=True)
    else:
        st.error(f"🔴 **SCORE SRD: {score:.1f}** (Bajo)")
        st.markdown("**Recomendación:** **ALERTA DE FATIGA.** Considera reducir la carga (ej., trabajar con 5% menos de peso) y el volumen.", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- MÓDULO 2: PROTOCOLOS DE GUÍA (Información estática) ---
    st.subheader("2. Protocolos de Recuperación y Guía de Sueño")
    st.caption("Guías de referencia para mejorar tu estado actual.")
    
    col_crio, col_termo = st.columns(2)
    
    with col_crio:
        st.error("Protocolo de Baño de Hielo (Crioterapia)")
        st.markdown("""
        - **Objetivo:** Reducción de la inflamación muscular.
        - **Temperatura:** 10 °C - 15 °C
        - **Duración:** **10 minutos** (Máx 15 min).
        """)
        
    with col_termo:
        st.info("Pautas de Sueño Óptimo")
        st.markdown("""
        - **Duración Ideal:** **8 - 10 horas** por noche.
        - **Ambiente:** Oscuro, fresco y silencioso.
        - **Regla Digital:** Evitar pantallas 30 minutos antes de dormir.
        """)

    st.markdown("---")
    st.subheader("3. Movilidad y Áreas Focales")
    st.caption("Movilidad diaria para prevenir lesiones en áreas clave de combate.")
    
    st.success("""
    - **Movilidad Dinámica:** Realizar antes de cada entrenamiento para preparar las articulaciones. (Ej: Rotaciones de hombros, balanceos de piernas).
    - **Movilidad Estática:** Realizar *solo* después del entrenamiento o en días de descanso activo.
    - **Foco Principal:** **Caderas** (Flexores y Rotadores) y **Columna Torácica** (Rotación).
    """)


# ----------------------------------------------------------------------------------
## PESTAÑA 9: RANKING (Visible para todos)
# ----------------------------------------------------------------------------------
with RANKING_TAB:
    st.header("🏆 Ranking de Atletas")
    st.caption("Ordenado por: **Oros > Platas > Bronces**. (Oro=10, Plata=3, Bronce=1)")
    st.caption(f"Archivo de origen: **{RANKING_FILE}**")
    
    # --- Lógica de Podio Visual (TOP 3) ---
    if not df_ranking.empty:
        st.markdown("---")
        st.subheader("🥇 Top 3 Ranking Distrital") 

        df_top3 = df_ranking.head(3).copy()
        
        pos_1 = df_top3[df_top3['Posicion'] == 1].iloc[0] if len(df_top3) >= 1 else None
        pos_2 = df_top3[df_top3['Posicion'] == 2].iloc[0] if len(df_top3) >= 2 else None
        pos_3 = df_top3[df_top3['Posicion'] == 3].iloc[0] if len(df_top3) >= 3 else None

        col2, col1, col3 = st.columns([1, 1, 1])

        # POSICIÓN 2 (Plata)
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True) 
            if pos_2 is not None:
                st.info(f"**🥈 {pos_2['Atleta']}**")
                st.markdown(f"<h2 style='text-align: center; color: silver;'>2do Puesto</h2>", unsafe_allow_html=True) 
                
            else:
                 st.info("🥈 ---")

        # POSICIÓN 1 (Oro)
        with col1:
            if pos_1 is not None:
                st.success(f"**🥇 {pos_1['Atleta']}**")
                st.markdown(f"<h1 style='text-align: center; color: gold;'>1er Puesto</h1>", unsafe_allow_html=True)
            else:
                 st.success("🥇 ---")

        # POSICIÓN 3 (Bronce)
        with col3:
            st.markdown("<br><br><br>", unsafe_allow_html=True) 
            if pos_3 is not None:
                st.error(f"**🥉 {pos_3['Atleta']}**") 
                st.markdown(f"<h3 style='text-align: center; color: brown;'>3er Puesto</h3>", unsafe_allow_html=True) 
            else:
                 st.error("🥉 ---")
        
        st.markdown("<br>", unsafe_allow_html=True)

    # --- VISTA DE GESTIÓN (ENTRENADOR) ---
    if rol_actual == 'Entrenador':
        st.markdown("---")
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
    else:
        st.subheader("Clasificación Completa")

    # --- TABLA COMPLETA (Visible para todos) ---
    if df_ranking.empty:
        st.info("No hay datos de ranking para mostrar. El entrenador debe cargar el archivo.")
    else:
        cols_to_show = ['Posicion', 'Atleta', 'Categoria', 'Oros', 'Platas', 'Bronces']
        
        st.dataframe(
            df_ranking[cols_to_show], 
            use_container_width=True,
            column_config={
                "Posicion": st.column_config.NumberColumn("Posición", format="%d"),
                "Oros": st.column_config.NumberColumn("🥇 Oros", format="%d"),
                "Platas": st.column_config.NumberColumn("🥈 Platas", format="%d"),
                "Bronces": st.column_config.NumberColumn("🥉 Bronces", format="%d"),
            },
            height=35 * (len(df_ranking) + 1)
        )

        # Mostrar la posición del atleta actual de forma destacada
        current_athlete_rank = df_ranking[df_ranking['Atleta'] == atleta_actual]
        if not current_athlete_rank.empty:
            rank_data = current_athlete_rank.iloc[0]
            st.markdown("---")
            st.subheader(f"Tu Posición Actual: {atleta_actual}")
            
            col_rank, col_medals = st.columns(2)
            
            col_rank.metric("Rango", f"#{int(rank_data['Posicion'])}")
            
            medals_text = f"🥇 {int(rank_data['Oros'])} | 🥈 {int(rank_data['Platas'])} | 🥉 {int(rank_data['Bronces'])}"
            col_medals.markdown(f"**Medallas:** <div style='font-size: 1.5em;'>{medals_text}</div>", unsafe_allow_html=True)
