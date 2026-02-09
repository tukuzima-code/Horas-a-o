import streamlit as st
import pandas as pd
from astral import LocationInfo
from astral.sun import sun
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from datetime import datetime, timedelta
import plotly.graph_objects as go
import ephem
from timezonefinder import TimezoneFinder
import pytz
import time

st.set_page_config(page_title="Luz Solar Pro", layout="centered")

# FUNCIÓN DE UBICACIÓN REFORZADA
@st.cache_data(show_spinner=False)
def obtener_ubicacion(cp):
    # Intentamos con 3 User-Agents diferentes por si uno está bloqueado
    agentes = ["solar_app_user_1", "map_explorer_2026", "geo_viewer_xyz"]
    for agente in agentes:
        try:
            geolocator = Nominatim(user_agent=agente)
            # Añadimos una pequeña pausa para no saturar
            time.sleep(1) 
            return geolocator.geocode(cp, timeout=15)
        except:
            continue
    return None

def get_moon_phase(date):
    m = ephem.Moon(date)
    p = m.phase / 100
    if p < 0.1: return "🌑"
    elif p < 0.4: return "🌙"
    elif p < 0.6: return "🌓"
    elif p < 0.9: return "🌔"
    else: return "🌕"

def get_season_color(d):
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' # Azul
    elif d < 172: return 'rgb(144, 238, 144)' # Verde
    elif d < 264: return 'rgb(255, 165, 0)'   # Naranja
    else: return 'rgb(210, 105, 30)'           # Marrón

st.title("☀️ Agenda Solar Estacional")

# Selector de resolución
vista = st.radio("Resolución:", ["Días", "Semanas", "Meses"], horizontal=True)

# Entrada de ubicación (por defecto Madrid para que cargue algo)
cp_input = st.text_input("Introduce CP o Ciudad", "Madrid, España")

location = obtener_ubicacion(cp_input)

if location:
    lat, lon = location.latitude, location.longitude
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=lon, lat=lat)
    
    # Si no encuentra zona horaria, ponemos UTC por defecto
    if not tz_name: tz_name = "UTC"
    local_tz = pytz.timezone(tz_name)
    
    city = LocationInfo("P", "R", tz_name, lat, lon)
    ahora = datetime.now(local_tz)

    st.success(f"📍 Conectado a: {location.address.split(',')[0]}")
    
    s_hoy = sun(city.observer, date=ahora, tzinfo=local_tz)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Amanecer", s_hoy['sunrise'].strftime('%H:%M'))
    c2.metric("Atardecer", s_hoy['sunset'].strftime('%H:%M'))
    c3.metric("Luna", get_moon_phase(ahora))

    # --- DATOS ---
    data = []
    inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
    pasos = {"Días": 1, "Semanas": 7, "Meses": 30}
    
    for i in range(0, 366, pasos[vista]):
        if i >= 365: break
        dia_m = inicio_año + timedelta(days=i)
        try:
            s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
            am = s_dia['sunrise'].hour + s_dia['sunrise'].minute / 60
            at = s_dia['sunset'].hour + s_dia['sunset'].minute / 60
            
            x_val = i+1 if vista == "Días" else (dia_m.isocalendar()[1] if vista == "Semanas" else dia_m.month)

            data.append({
                "X": x_val, "Amanecer": am, "Atardecer": at,
                "Texto_A": s_dia['sunrise'].strftime('%H:%M'),
                "Texto_At": s_dia['sunset'].strftime('%H:%M'),
                "Luna": get_moon_phase(dia_m), "Color": get_season_color(i)
            })
        except: continue

    df = pd.DataFrame(data)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["X"], y=df["Atardecer"] - df["Amanecer"], base=df["Amanecer"],
        marker_color=df["Color"],
        customdata=df[["Texto_A", "Texto_At", "Luna"]],
        hovertemplate="<b>%{x}</b><br>☀️ %{customdata[0]}<br>🌅 %{customdata[1]}<br>🌙 %{customdata[2]}<extra></extra>"
    ))

    hoy_x = ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month)
    fig.add_vline(x=hoy_x, line_width=2, line_color="red")

    fig.update_layout(
        template="plotly_dark", dragmode="pan",
        yaxis=dict(title="Hora", range=[0, 24], fixedrange=True, dtick=2),
        xaxis=dict(title=vista, scrollzoom=True),
        height=500, margin=dict(l=0, r=0, t=10, b=0), showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True, 'displayModeBar': True,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'zoom2d'],
        'displaylogo': False
    })
else:
    st.error("❌ Error de conexión: Escribe la ciudad y el país (ej: 'Barcelona, España') o intenta recargar la página.")
    
