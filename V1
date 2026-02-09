import streamlit as st
import pandas as pd
from astral import LocationInfo
from astral.sun import sun
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Configuración de la página para móvil
st.set_page_config(page_title="Luz Solar App", layout="centered")

st.title("☀️ Mi Agenda Solar")

# 1. Entrada de ubicación
cp = st.text_input("Introduce tu Código Postal o Ciudad", "Madrid")

geolocator = Nominatim(user_agent="solar_app_personal")
location = geolocator.geocode(cp)

if location:
    lat, lon = location.latitude, location.longitude
    st.caption(f"📍 Ubicación: {location.address}")
    
    # 2. Vista Diaria (Hoy)
    city = LocationInfo("Personal", "Region", "UTC", lat, lon)
    s = sun(city.observer, date=datetime.now())
    
    col1, col2 = st.columns(2)
    col1.metric("Amanecer", s['sunrise'].strftime('%H:%M'))
    col2.metric("Atardecer", s['sunset'].strftime('%H:%M'))

    # 3. Generar datos para el gráfico anual (Vista por semanas)
    st.divider()
    st.subheader("📊 Ciclo Solar Anual")
    
    data = []
    fecha_inicio = datetime(2026, 1, 1)
    
    for i in range(0, 365, 7): # Saltos de semana en semana
        dia = fecha_inicio + timedelta(days=i)
        s_dia = sun(city.observer, date=dia)
        
        # Convertir a horas decimales para el gráfico
        amanecer_dec = s_dia['sunrise'].hour + s_dia['sunrise'].minute / 60
        atardecer_dec = s_dia['sunset'].hour + s_dia['sunset'].minute / 60
        
        data.append({
            "Semana": dia.strftime("%V"),
            "Amanecer": amanecer_dec,
            "Atardecer": atardecer_dec,
            "Texto_A": s_dia['sunrise'].strftime('%H:%M'),
            "Texto_At": s_dia['sunset'].strftime('%H:%M')
        })

    df = pd.DataFrame(data)

    # 4. Gráfico de Barras Flotantes (Gantt-style)
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["Semana"],
        y=df["Atardecer"] - df["Amanecer"],
        base=df["Amanecer"],
        marker_color='gold',
        name='Horas de Luz',
        hovertemplate="Semana: %{x}<br>Amanecer: %{customdata[0]}<br>Atardecer: %{customdata[1]}",
        customdata=df[["Texto_A", "Texto_At"]]
    ))

    fig.update_layout(
        yaxis=dict(title="Hora del día (0-24h)", range=[0, 24], dtick=4),
        xaxis=dict(title="Semana del año"),
        height=400,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("No se encontró la ubicación. Prueba con 'Ciudad, País'.")
