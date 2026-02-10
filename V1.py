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
import random
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Luz Solar Pro", layout="centered")

# Función de búsqueda mejorada
@st.cache_data(show_spinner=False, ttl=300)
def buscar_lugar_robusto(texto):
    if not texto:
        return None
    try:
        # Generamos un User-Agent aleatorio para evitar bloqueos por IP
        user_agent = f"solar_app_{random.randint(1000, 9999)}_search"
        geolocator = Nominatim(user_agent=user_agent)
        # Forzamos la búsqueda en español/internacional
        return geolocator.geocode(texto, timeout=10, language="es")
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

st.title("☀️ Agenda Solar")

# Botón de emergencia
if st.button("🔄 Resetear App"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()

col_gps, col_txt = st.columns([1, 2])

with col_gps:
    st.write("")
    if st.button("📍 Usar GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state.lat = loc['coords']['latitude']
            st.session_state.lon = loc['coords']['longitude']
            st.session_state.modo = "gps"
        else:
            st.error("Permiso GPS denegado")

with col_txt:
    entrada = st.text_input("Ciudad o CP", placeholder="Ej: Madrid o 46511")
    if entrada:
        st.session_state.modo = "texto"
        st.session_state.busqueda = entrada

# LÓGICA DE UBICACIÓN FINAL
lat, lon, direccion = 40.41, -3.70, "Madrid (Por defecto)" # Valores de rescate

modo = st.session_state.get('modo', 'defecto')

if modo == "gps":
    lat, lon = st.session_state.lat, st.session_state.lon
    direccion = "Ubicación GPS"
elif modo == "texto":
    res = buscar_lugar_robusto(st.session_state.busqueda)
    if res:
        lat, lon = res.latitude, res.longitude
        direccion = res.address.split(',')[0]
    else:
        st.warning("⚠️ No encontrado. Mostrando Madrid por defecto.")
        lat, lon = 40.41, -3.70
else:
    # Intento inicial silencioso
    res = buscar_lugar_robusto("Madrid, España")
    if res:
        lat, lon = res.latitude, res.longitude
        direccion = "Madrid"

# --- PROCESAMIENTO Y GRÁFICO ---
if lat and lon:
    vista = st.radio("Ver por:", ["Días", "Semanas", "Meses"], horizontal=True)
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=lon, lat=lat) or "Europe/Madrid"
    local_tz = pytz.timezone(tz_name)
    city = LocationInfo("P", "R", tz_name, lat, lon)
    ahora = datetime.now(local_tz)

    st.success(f"📍 Mostrando: {direccion}")
    
    s_hoy = sun(city.observer, date=ahora, tzinfo=local_tz)
    c1, c2, c3 = st.columns(3)
    c1.metric("Amanecer", s_hoy['sunrise'].strftime('%H:%M'))
    c2.metric("Atardecer", s_hoy['sunset'].strftime('%H:%M'))
    c3.metric("Luna", get_moon_phase(ahora))

    data = []
    inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
    pasos = {"Días": 1, "Semanas": 7, "Meses": 30}
    meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    for i in range(0, 366, pasos[vista]):
        if i >= 365: break
        dia_m = inicio_año + timedelta(days=i)
        try:
            s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
            am = s_dia['sunrise'].hour + s_dia['sunrise'].minute / 60
            at = s_dia['sunset'].hour + s_dia['sunset'].minute / 60
            f_label = dia_m.strftime("%d %b")
            
            x_val = i+1 if vista == "Días" else (dia_m.isocalendar()[1] if vista == "Semanas" else dia_m.month)
            h_label = f"Día {x_val} ({f_label})" if vista=="Días" else (f"Semana {x_val} ({f_label})" if vista=="Semanas" else meses_nombres[x_val-1])

            data.append({
                "X": x_val, "Amanecer": am, "Dur": at - am,
                "T_A": s_dia['sunrise'].strftime('%H:%M'), "T_At": s_dia['sunset'].strftime('%H:%M'),
                "Luna": get_moon_phase(dia_m), "Color": get_season_color(i), "L": h_label
            })
        except: continue

    df = pd.DataFrame(data)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["X"], y=df["Dur"], base=df["Amanecer"], marker_color=df["Color"],
        customdata=df[["T_A", "T_At", "Luna", "L"]],
        hovertemplate="<b>%{customdata[3]}</b><br>☀️ Sale: %{customdata[0]}<br>🌅 Pone: %{customdata[1]}<br>🌙 %{customdata[2]}<extra></extra>"
    ))

    hoy_x = ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month)
    fig.add_vline(x=hoy_x, line_width=2, line_color="red")

    fig.update_layout(
        template="plotly_dark", dragmode="pan", height=500, margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False, yaxis=dict(title="Hora", range=[0, 24], dtick=2, fixedrange=True), xaxis=dict(title=vista)
    )

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})
    
