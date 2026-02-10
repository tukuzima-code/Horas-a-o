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
import math
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Luz Solar Pro", layout="centered")

# --- FUNCIONES ---
@st.cache_data(show_spinner=False, ttl=300)
def buscar_lugar_robusto(texto):
    if not texto: return None
    try:
        user_agent = f"solar_app_{random.randint(1000, 9999)}_search"
        geolocator = Nominatim(user_agent=user_agent)
        return geolocator.geocode(texto, timeout=10, language="es")
    except: return None

def get_moon_phase_data(date):
    m = ephem.Moon(date)
    p = m.phase 
    if p < 5: icon = "🌑"
    elif p < 45: icon = "🌙"
    elif p < 55: icon = "🌓"
    elif p < 95: icon = "🌔"
    else: icon = "🌕"
    return f"{icon} {int(p)}%"

def estimate_temp_mediterraneo(day_of_year, lat, is_max=True):
    """Estima temperatura media ajustada a climas más cálidos/costeros"""
    # El pico de calor suele ser a finales de Julio (día 200 aprox)
    cos_val = math.cos(2 * math.pi * (day_of_year - 205) / 365)
    
    if is_max:
        # Rango aprox Sagunto: 16°C (Ene) a 30°C (Ago)
        base, amp = 23, 7 
    else:
        # Rango aprox Sagunto: 7°C (Ene) a 21°C (Ago)
        base, amp = 14, 7
        
    return round(base + amp * cos_val, 1)

def get_season_color(d):
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' 
    elif d < 172: return 'rgb(144, 238, 144)' 
    elif d < 264: return 'rgb(255, 165, 0)'   
    else: return 'rgb(210, 105, 30)'

# --- ESTADO DE SESIÓN ---
if 'lat' not in st.session_state:
    st.session_state['lat'], st.session_state['lon'] = 39.664, -0.228
    st.session_state['dir'] = "Puerto de Sagunto"

st.title("☀️ Agenda Solar & Clima")

# --- BUSCADOR ---
col_gps, col_txt = st.columns([1, 3])
with col_gps:
    if st.button("📍 GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state['lat'], st.session_state['lon'] = loc['coords']['latitude'], loc['coords']['longitude']
            st.session_state['dir'] = "Ubicación GPS"; st.rerun()

with col_txt:
    entrada = st.text_input("Ciudad o CP", placeholder="Ej: Sagunto", label_visibility="collapsed")
    if entrada:
        res = buscar_lugar_robusto(entrada)
        if res:
            st.session_state['lat'], st.session_state['lon'] = res.latitude, res.longitude
            st.session_state['dir'] = res.address.split(',')[0]; st.rerun()

# --- CÁLCULOS ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state['lon'], lat=st.session_state['lat']) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, st.session_state['lat'], st.session_state['lon'])
ahora = datetime.now(local_tz)

st.success(f"📍 {st.session_state['dir']}")

# --- MÉTRICAS ---
s1 = sun(city.observer, date=ahora, tzinfo=local_tz)
t_max_hoy = estimate_temp_mediterraneo(ahora.timetuple().tm_yday, st.session_state['lat'], True)
t_min_hoy = estimate_temp_mediterraneo(ahora.timetuple().tm_yday, st.session_state['lat'], False)

st.markdown("---")
m1, m2, m3 = st.columns(3)
m1.metric("🌅 Amanecer", s1['sunrise'].strftime('%H:%M'))
m2.metric("🌇 Atardecer", s1['sunset'].strftime('%H:%M'))
m3.metric("🌓 Luna", get_moon_phase_data(ahora))

c_t1, c_t2 = st.columns(2)
c_t1.metric("🌡️ Máxima Media", f"{t_max_hoy}°C")
c_t2.metric("❄️ Mínima Media", f"{t_min_hoy}°C")
st.markdown("---")

# --- GRÁFICO ---
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
for i in range(0, 365, 2):
    dia_m = inicio_año + timedelta(days=i)
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am, at = s_dia['sunrise'].hour + s_dia['sunrise'].minute/60, s_dia['sunset'].hour + s_dia['sunset'].minute/60
        data.append({
            "Día": i, "Am": am, "Dur": at - am, 
            "T_A": s_dia['sunrise'].strftime('%H:%M'), "T_At": s_dia['sunset'].strftime('%H:%M'), 
            "L": dia_m.strftime("%d %b"), "Luna": get_moon_phase_data(dia_m),
            "Max": estimate_temp_mediterraneo(i, 0, True),
            "Min": estimate_temp_mediterraneo(i, 0, False),
            "Color": get_season_color(i)
        })
    except: continue

df = pd.DataFrame(data)
fig = go.Figure()

# Barras de Luz
fig.add_trace(go.Bar(
    x=df["Día"], y=df["Dur"], base=df["Am"], marker_color=df["Color"],
    customdata=df[["T_A", "T_At", "L", "Luna", "Max", "Min"]],
    hovertemplate="<b>%{customdata[2]}</b><br>☀️ %{customdata[0]} - %{customdata[1]}<br>🌙 %{customdata[3]}<br>🌡️ %{customdata[5]}° / %{customdata[4]}°C<extra></extra>"
))

# Línea roja hoy
fig.add_vline(x=ahora.timetuple().tm_yday, line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    yaxis=dict(range=[0, 24], dtick=4, title="Horas"),
    xaxis=dict(fixedrange=True, title="Evolución Anual")
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
