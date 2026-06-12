import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Bitácora de Laboratorio", layout="wide", page_icon="🧪")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

NOMBRES = ['Carlos Villalobos', 'Diego Abarca', 'Isidora Moscoso']

def load_data(worksheet=None):
    try:
        # Se lee la hoja (por defecto intentamos leer la primera hoja)
        # En la vida real, si la hoja está en blanco, podría lanzar error al no tener columnas
        if worksheet:
            df = conn.read(worksheet=worksheet, usecols=[0, 1, 2], ttl=0)
        else:
            df = conn.read(usecols=[0, 1, 2], ttl=0)
        df = df.dropna(how="all") # Limpiar filas totalmente vacías
        
        # Verificar si las columnas son las esperadas
        if df.empty or list(df.columns) != ["Fecha", "Nombre", "Trabajo"]:
             df = pd.DataFrame(columns=["Fecha", "Nombre", "Trabajo"])
             
        return df
    except Exception as e:
        # Si la hoja está completamente vacía o no existe, devolvemos un df vacío
        return pd.DataFrame(columns=["Fecha", "Nombre", "Trabajo"])

st.title("🧪 Bitácora de Tareas de Laboratorio")

tab1, tab2 = st.tabs(["📝 Ingreso de Tareas", "📊 Dashboard de Administrador"])

with tab1:
    st.header("Registrar Nueva Tarea")
    with st.form("task_form"):
        fecha = st.date_input("Fecha", date.today())
        nombre = st.selectbox("Nombre del Integrante", NOMBRES)
        trabajo = st.text_area("Descripción del Trabajo")
        submitted = st.form_submit_button("Guardar Tarea")

        if submitted:
            if not nombre or not trabajo:
                st.error("Por favor, completa todos los campos.")
            else:
                new_data = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Nombre": nombre,
                    "Trabajo": trabajo
                }])
                
                existing_data = load_data(worksheet=nombre)
                updated_data = pd.concat([existing_data, new_data], ignore_index=True)
                
                try:
                    # Actualiza la hoja con los nuevos datos
                    conn.update(worksheet=nombre, data=updated_data)
                    st.success("¡Tarea guardada exitosamente!")
                    st.cache_data.clear() # Limpia el caché para la próxima lectura
                except Exception as e:
                    st.error(f"Error al guardar en Google Sheets: {e}")
                    st.info("Asegúrate de que tus credenciales en .streamlit/secrets.toml sean correctas y tengas permisos de escritura.")

with tab2:
    st.header("Dashboard de Administrador")
    
    password = st.text_input("Contraseña de Administrador", type="password")
    
    # Contraseña hardcodeada simple para proteger esta sección
    ADMIN_PASSWORD = "admin" 
    
    if password == ADMIN_PASSWORD:
        st.success("Acceso concedido.")
        
        all_data = []
        for n in NOMBRES:
            all_data.append(load_data(worksheet=n))
        data = pd.concat(all_data, ignore_index=True)
        
        if data.empty:
            st.info("No hay tareas registradas aún.")
        else:
            st.subheader("Filtrar Tareas")
            integrante_seleccionado = st.selectbox("Seleccionar Integrante", ["Todos"] + NOMBRES)
            
            if integrante_seleccionado == "Todos":
                filtered_data = data
            else:
                filtered_data = data[data["Nombre"] == integrante_seleccionado]
                
            st.dataframe(filtered_data, use_container_width=True)
            
            st.subheader("Resumen de Tareas por Integrante")
            # Cuenta cuántas tareas tiene cada integrante
            conteo = data["Nombre"].value_counts().reset_index()
            conteo.columns = ["Nombre", "Cantidad de Tareas"]
            st.bar_chart(conteo.set_index("Nombre"))
            
    elif password:
        st.error("Contraseña incorrecta.")
