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

def get_moon_phase(date):
    m = ephem.Moon(date)
    phase = m.phase / 100
    if phase < 0.1: return "🌑"
    if phase < 0.4: return "🌙"
    if phase < 0.6: return "🌓"
    if phase < 0.9: return "🌔"
    return "🌕"

def get_season_color(day_of_year):
    # Lógica de color según el día del año (aproximado para hemisferio norte)
    # Invierno: Azul, Primavera: Verde, Verano: Naranja/Oro, Otoño: Marrón
    if day_of_year < 80 or day_of_year > 355: return 'rgb(100, 149, 237)' # Azul invierno
    elif day_of_year < 172: return 'rgb(144, 238, 144)' # Verde primavera
    elif day_of_year < 264: return 'rgb(255, 165, 0)'   # Naranja verano
    else: return 'rgb(210, 105, 30)'                   # Marrón otoño

st.title("☀️ Agenda Solar Estacional")

vista = st.radio("Cambiar resolución:", ["Días", "Semanas", "Meses"], horizontal=True)

cp = st.text_input("Introduce CP o Ciudad", "Madrid")
geolocator = Nominatim(user_agent="solar_app_final")
tf = TimezoneFinder()

location = geolocator.geocode(cp)

if location:
    lat, lon = location.latitude, location.longitude
    tz_name = tf.timezone_at(lng=lon, lat=lat)
    local_tz = pytz.timezone(tz_name)
    city = LocationInfo("Personal", "Region", tz_name, lat, lon)
    ahora = datetime.now(local_tz)

    data = []
    año_actual = ahora.year
    inicio = datetime(año_actual, 1, 1, tzinfo=local_tz)
    
    pasos = {"Días": 1, "Semanas": 7, "Meses": 30}
    
    for i in range(0, 365, pasos[vista]):
        dia_m = inicio + timedelta(days=i)
        try:
            s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
            am = s_dia['sunrise'].hour + s_dia['sunrise'].minute / 60
            at = s_dia['sunset'].hour + s_dia['sunset'].minute / 60
            
            data.append({
                "X": i//pasos[vista] + 1 if vista != "Días" else i + 1,
                "Amanecer": am,
                "Atardecer": at,
                "Texto_A": s_dia['sunrise'].strftime('%H:%M'),
                "Texto_At": s_dia['sunset'].strftime('%H:%M'),
                "Luna": get_moon_phase(dia_m),
                "Color": get_season_color(i)
            })
        except: continue

    df = pd.DataFrame(data)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["X"],
        y=df["Atardecer"] - df["Amanecer"],
        base=df["Amanecer"],
        marker_color=df["Color"], # Aplicamos el color estacional
        name='Horas de Luz',
        customdata=df[["Texto_A", "Texto_At", "Luna"]],
        hovertemplate="<b>%{x}</b><br>☀️ Sale: %{customdata[0]}<br>🌅 Pone: %{customdata[1]}<br>🌙 Luna: %{customdata[2]}<extra></extra>"
    ))

    # Marcador de "Hoy"
    hoy_x = ahora.timetuple().tm_yday if vista == "Días" else ahora.isocalendar()[1]
    if vista != "Meses":
        fig.add_vline(x=hoy_x, line_width=2, line_color="red")

    fig.update_layout(
        template="plotly_dark",
        dragmode="pan",
        yaxis=dict(title="Hora (0-24h)", range=[0, 24], fixedrange=True, dtick=2),
        xaxis=dict(title=f"Eje de tiempo ({vista})", scrollzoom=True),
        height=550,
        margin=dict(l=0, r=0, t=20, b=0)
    )

    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True,
        'displayModeBar': True,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
        'displaylogo': False
    })
    
    st.caption("📱 Pellizca para zoom • Arrastra para mover • Pulsa la 'casita' para resetear.")
else:
    st.info("Introduce tu ubicación para generar la vista.")
