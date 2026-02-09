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

st.set_page_config(page_title="Luz Solar Pro", layout="centered")

@st.cache_data(show_spinner=False)
def obtener_ubicacion(cp):
    try:
        geolocator = Nominatim(user_agent="solar_app_v5_2026")
        return geolocator.geocode(cp, timeout=10)
    except:
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
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' 
    elif d < 172: return 'rgb(144, 238, 144)' 
    elif d < 264: return 'rgb(255, 165, 0)'   
    else: return 'rgb(210, 105, 30)'           

st.title("☀️ Agenda Solar Estacional")

vista = st.radio("Resolución:", ["Días", "Semanas", "Meses"], horizontal=True)
cp_input = st.text_input("Introduce CP o Ciudad", "Madrid, España")

location = obtener_ubicacion(cp_input)

if location:
    lat, lon = location.latitude, location.longitude
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=lon, lat=lat) or "UTC"
    local_tz = pytz.timezone(tz_name)
    city = LocationInfo("P", "R", tz_name, lat, lon)
    ahora = datetime.now(local_tz)

    st.success(f"📍 {location.address.split(',')[0]}")
    
    s_hoy = sun(city.observer, date=ahora, tzinfo=local_tz)
    c1, c2, c3 = st.columns(3)
    c1.metric("Amanecer", s_hoy['sunrise'].strftime('%H:%M'))
    c2.metric("Atardecer", s_hoy['sunset'].strftime('%H:%M'))
    c3.metric("Luna", get_moon_phase(ahora))

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
            
            if vista == "Días": x_val = i + 1
            elif vista == "Semanas": x_val = dia_m.isocalendar()[1]
            else: x_val = dia_m.month

            data.append({
                "X": x_val, "Amanecer": am, "Duracion": at - am,
                "Texto_A": s_dia['sunrise'].strftime('%H:%M'),
                "Texto_At": s_dia['sunset'].strftime('%H:%M'),
                "Luna": get_moon_phase(dia_m), "Color": get_season_color(i)
            })
        except: continue

    if data:
        df = pd.DataFrame(data)
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df["X"], 
            y=df["Duracion"], 
            base=df["Amanecer"],
            marker_color=df["Color"],
            customdata=df[["Texto_A", "Texto_At", "Luna"]],
            hovertemplate="<b>%{x}</b><br>☀️ %{customdata[0]}<br>🌅 %{customdata[1]}<br>🌙 %{customdata[2]}<extra></extra>"
        ))

        hoy_x = ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month)
        fig.add_vline(x=hoy_x, line_width=2, line_color="red")

        fig.update_layout(
            template="plotly_dark",
            dragmode="pan",
            height=500,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            yaxis=dict(title="Hora", range=[0, 24], dtick=2, fixedrange=True),
            xaxis=dict(title=vista)
        )

        st.plotly_chart(fig, use_container_width=True, config={
            'scrollZoom': True, 
            'displayModeBar': True,
            'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
            'displaylogo': False
        })
    else:
        st.info("Cargando datos...")
else:
    st.warning("Introduce una ubicación.")
    
