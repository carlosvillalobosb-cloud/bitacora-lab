import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Bitácora de Laboratorio", layout="wide", page_icon="🧪")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

NOMBRES = ['Carlos Villalobos', 'Diego Abarca', 'Isidora Moscoso']

def load_tareas_asignadas():
    try:
        df = conn.read(worksheet="Tareas_Asignadas", usecols=[0], ttl=0)
        df = df.dropna(how="all")
        if df.empty or list(df.columns) != ["Tarea"]:
            return []
        return df["Tarea"].tolist()
    except Exception:
        return []

def load_data(worksheet=None):
    try:
        # Se lee la hoja (por defecto intentamos leer la primera hoja)
        # En la vida real, si la hoja está en blanco, podría lanzar error al no tener columnas
        if worksheet:
            df = conn.read(worksheet=worksheet, usecols=[0, 1, 2, 3, 4], ttl=0)
        else:
            df = conn.read(usecols=[0, 1, 2, 3, 4], ttl=0)
        df = df.dropna(how="all") # Limpiar filas totalmente vacías
        
        # Verificar si las columnas son las esperadas
        if df.empty or list(df.columns) != ["Fecha", "Nombre", "Tarea Asignada", "Trabajo", "Horas"]:
             df = pd.DataFrame(columns=["Fecha", "Nombre", "Tarea Asignada", "Trabajo", "Horas"])
             
        return df
    except Exception as e:
        # Si la hoja está completamente vacía o no existe, devolvemos un df vacío
        return pd.DataFrame(columns=["Fecha", "Nombre", "Tarea Asignada", "Trabajo", "Horas"])

st.title("🧪 Bitácora de Tareas de Laboratorio")

tab1, tab2 = st.tabs(["📝 Ingreso de Tareas", "📊 Dashboard de Administrador"])

with tab1:
    st.header("Registrar Nueva Tarea")
    
    tareas_asignadas = load_tareas_asignadas()
    if not tareas_asignadas:
        tareas_asignadas = ["Sin tareas configuradas"]
        
    with st.form("task_form"):
        fecha = st.date_input("Fecha", date.today())
        nombre = st.selectbox("Nombre del Integrante", NOMBRES)
        tarea_asignada = st.selectbox("Tarea Asignada", tareas_asignadas)
        trabajo = st.text_area("Descripción del Trabajo")
        horas_dedicadas = st.number_input("Horas Dedicadas (ej: 1.5 = 1h 30m)", step=0.5, value=1.0)
        submitted = st.form_submit_button("Guardar Tarea")

        if submitted:
            if not nombre or not trabajo or tarea_asignada == "Sin tareas configuradas":
                st.error("Por favor, completa todos los campos y asegúrate de que haya tareas asignadas.")
            else:
                new_data = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Nombre": nombre,
                    "Tarea Asignada": tarea_asignada,
                    "Trabajo": trabajo,
                    "Horas": horas_dedicadas
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
            
            st.subheader("Distribución de Tareas Asignadas")
            if "Tarea Asignada" in data.columns and not data.empty:
                conteo_tareas = data["Tarea Asignada"].value_counts().reset_index()
                conteo_tareas.columns = ["Tarea", "Bloques Dedicados"]
                
                st.dataframe(conteo_tareas, hide_index=True, use_container_width=True)
                st.bar_chart(conteo_tareas.set_index("Tarea"))
            
            st.subheader("Gráfico de Línea de Tiempo de Esfuerzo")
            if "Horas" in data.columns and not data.empty:
                data["Horas"] = pd.to_numeric(data["Horas"], errors="coerce").fillna(0)
                
                # Opción para elegir el tipo de visualización
                tipo_agrupacion = st.radio("Mostrar gráficos por:", ["Nombres (Integrantes)", "Tareas Asignadas"], horizontal=True)
                
                columna_filtro = "Nombre" if tipo_agrupacion == "Nombres (Integrantes)" else "Tarea Asignada"
                
                if columna_filtro in data.columns:
                    opciones_unicas = data[columna_filtro].unique().tolist()
                else:
                    opciones_unicas = []

                # Multiselect para elegir qué elementos graficar
                seleccion = st.multiselect(
                    f"Selecciona {tipo_agrupacion}:",
                    options=opciones_unicas,
                    default=opciones_unicas
                )

                if not seleccion:
                    st.info("Selecciona al menos una opción para visualizar los gráficos.")
                else:
                    # Bucle for para crear un gráfico independiente para cada opción seleccionada
                    for item in seleccion:
                        # Título dinámico para el gráfico
                        st.caption(f"📈 **{tipo_agrupacion.split(' ')[0]}:** {item}")
                        
                        # Filtrar el DataFrame consolidado
                        df_filtrado = data[data[columna_filtro] == item]
                        
                        if not df_filtrado.empty:
                            # Agrupar por fecha y sumar horas para ese item específico
                            df_grafico = df_filtrado.groupby("Fecha")["Horas"].sum()
                            
                            # Dibujar el line chart
                            st.line_chart(df_grafico)
                        else:
                            st.write(f"No hay registros para {item}.")
                
        st.divider()
        st.subheader("Gestionar Tareas Asignadas")
        with st.form("nueva_tarea_form"):
            nueva_tarea = st.text_input("Nueva Tarea Asignada (Ej. Ensayos de tracción)")
            submit_tarea = st.form_submit_button("Agregar Tarea")
            if submit_tarea:
                if nueva_tarea:
                    tareas_actuales = load_tareas_asignadas()
                    if "Sin tareas configuradas" in tareas_actuales:
                        tareas_actuales.remove("Sin tareas configuradas")
                        
                    if nueva_tarea not in tareas_actuales:
                        tareas_actuales.append(nueva_tarea)
                        df_tareas = pd.DataFrame(tareas_actuales, columns=["Tarea"])
                        try:
                            conn.update(worksheet="Tareas_Asignadas", data=df_tareas)
                            st.success(f"Tarea '{nueva_tarea}' agregada exitosamente.")
                            st.cache_data.clear() # Limpia caché para que se refresque el selectbox
                            st.rerun() # Fuerza una recarga de la app
                        except Exception as e:
                            st.error(f"Error al guardar tarea: {e}")
                    else:
                        st.warning("La tarea ya existe.")
                else:
                    st.error("Por favor, escribe una tarea.")
            
    elif password:
        st.error("Contraseña incorrecta.")
