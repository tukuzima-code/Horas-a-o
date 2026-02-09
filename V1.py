import streamlit as st
import pandas as pd
from astral import LocationInfo
from astral.sun import sun
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
import plotly.graph_objects as go
import ephem
from timezonefinder import TimezoneFinder
import pytz

st.set_page_config(page_title="Luz y Luna Pro", layout="centered")

def get_moon_phase(date):
    m = ephem.Moon(date)
    nn = ephem.next_new_moon(date)
    np = ephem.next_full_moon(date)
    phase = m.phase / 100
    if np < nn:
        if phase < 0.1: return "🌑 Nueva"
        if phase < 0.4: return "🌒 Creciente"
        if phase < 0.6: return "🌓 C. Creciente"
        return "🌕 Llena"
    else:
        if phase > 0.9: return "🌕 Llena"
        if phase > 0.4: return "🌗 C. Menguante"
        return "🌑 Nueva"

st.title("☀️ Mi Agenda Solar Personal")

cp = st.text_input("Introduce CP o Ciudad", "Madrid")
geolocator = Nominatim(user_agent="solar_app_v2")
tf = TimezoneFinder()

location = geolocator.geocode(cp)

if location:
    lat, lon = location.latitude, location.longitude
    tz_name = tf.timezone_at(lng=lon, lat=lat)
    local_tz = pytz.timezone(tz_name)
    
    city = LocationInfo("Personal", "Region", tz_name, lat, lon)
    
    # --- INFO DE HOY ---
    ahora = datetime.now(local_tz)
    semana_actual = ahora.isocalendar()[1]
    s_hoy = sun(city.observer, date=ahora, tzinfo=local_tz)
    
    st.subheader(f"📍 {location.address}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Amanecer", s_hoy['sunrise'].strftime('%H:%M'))
    c2.metric("Atardecer", s_hoy['sunset'].strftime('%H:%M'))
    c3.metric("Semana Actual", semana_actual)

    # --- DATOS ANUALES ---
    data = []
    año_actual = ahora.year
    # Empezamos el primer lunes del año
    fecha_it = datetime(año_actual, 1, 1, tzinfo=local_tz)
    
    for i in range(1, 53):
        # Calculamos el medio de la semana para la muestra
        dia_muestra = fecha_it + timedelta(weeks=i-1)
        try:
            s_dia = sun(city.observer, date=dia_muestra, tzinfo=local_tz)
            am = s_dia['sunrise'].hour + s_dia['sunrise'].minute / 60
            at = s_dia['sunset'].hour + s_dia['sunset'].minute / 60
            
            data.append({
                "Semana": i,
                "Amanecer": am,
                "Atardecer": at,
                "Texto_A": s_dia['sunrise'].strftime('%H:%M'),
                "Texto_At": s_dia['sunset'].strftime('%H:%M'),
                "Luna": get_moon_phase(dia_muestra)
            })
        except: continue

    df = pd.DataFrame(data)

    # --- GRÁFICO ---
    fig = go.Figure()

    # Barras de luz
    fig.add_trace(go.Bar(
        x=df["Semana"],
        y=df["Atardecer"] - df["Amanecer"],
        base=df["Amanecer"],
        marker_color='rgb(255, 210, 50)',
        name='Horas de Luz',
        customdata=df[["Texto_A", "Texto_At", "Luna"]],
        hovertemplate="<b>Semana %{x}</b><br>Amanecer: %{customdata[0]}<br>Atardecer: %{customdata[1]}<br>Luna: %{customdata[2]}<extra></extra>"
    ))

    # LÍNEA ROJA (Semana actual)
    fig.add_vline(x=semana_actual, line_width=3, line_dash="dash", line_color="red")
    fig.add_annotation(x=semana_actual, y=23, text="Hoy", showarrow=False, font=dict(color="red"))

    fig.update_layout(
        template="plotly_dark",
        yaxis=dict(title="Hora del día", range=[0, 24], dtick=2),
        xaxis=dict(title="Semanas del Año", tickmode='linear', dtick=5),
        height=500,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Nota: La línea roja indica la semana en la que te encuentras ahora.")
else:
    st.info("Introduce una ubicación para generar tu mapa solar.")
