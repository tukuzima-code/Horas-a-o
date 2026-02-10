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

# --- FUNCIONES ---
@st.cache_data(show_spinner=False, ttl=300)
def buscar_lugar_robusto(texto):
    if not texto: return None
    try:
        user_agent = f"solar_app_{random.randint(1000, 9999)}_search"
        geolocator = Nominatim(user_agent=user_agent)
        return geolocator.geocode(texto, timeout=10, language="es")
    except: return None

def get_moon_phase(date):
    m = ephem.Moon(date)
    p = m.phase / 100
    if p < 0.1: return "🌑"
    elif p < 0.4: return "🌙"
    elif p < 0.6: return "🌓"
    elif p < 0.9: return "🌔"
    else: return "🌕"

# --- LÓGICA DE UBICACIÓN INTELIGENTE ---
if 'lat' not in st.session_state:
    # Intentamos pillar el GPS nada más entrar
    loc = get_geolocation()
    if loc:
        st.session_state['lat'] = loc['coords']['latitude']
        st.session_state['lon'] = loc['coords']['longitude']
        st.session_state['dir'] = "Mi ubicación"
    else:
        # Si falla o el usuario no da permiso, defecto: Sagunto
        st.session_state['lat'] = 39.664
        st.session_state['lon'] = -0.228
        st.session_state['dir'] = "Puerto de Sagunto"

st.title("☀️ Agenda Solar")

# --- BUSCADOR Y GPS (MANUAL) ---
col_gps, col_txt = st.columns([1, 3])

with col_gps:
    if st.button("📍 Forzar GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state['lat'] = loc['coords']['latitude']
            st.session_state['lon'] = loc['coords']['longitude']
            st.session_state['dir'] = "Ubicación GPS"
            st.rerun()

with col_txt:
    entrada = st.text_input("Cambiar ciudad o CP...", placeholder="Ej: Madrid", label_visibility="collapsed")
    if entrada:
        res = buscar_lugar_robusto(entrada)
        if res:
            st.session_state['lat'] = res.latitude
            st.session_state['lon'] = res.longitude
            st.session_state['dir'] = res.address.split(',')[0]
            st.rerun()

# --- CÁLCULOS ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state['lon'], lat=st.session_state['lat']) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, st.session_state['lat'], st.session_state['lon'])
ahora = datetime.now(local_tz)

st.success(f"📍 {st.session_state['dir']}")

# --- MÉTRICAS ---
s1 = sun(city.observer, date=ahora, tzinfo=local_tz)
s2 = sun(city.observer, date=ahora + timedelta(days=1), tzinfo=local_tz)
dur1 = (s1['sunset'] - s1['sunrise']).total_seconds()
dur2 = (s2['sunset'] - s2['sunrise']).total_seconds()
dif_seg = dur2 - dur1

st.markdown("---")
m1, m2, m3 = st.columns(3)
m1.metric("🌅 Amanecer", s1['sunrise'].strftime('%H:%M'))
m2.metric("🌇 Atardecer", s1['sunset'].strftime('%H:%M'))
m3.metric("🌓 Luna", get_moon_phase(ahora))

minutos, segundos = int(abs(dif_seg)//60), int(abs(dif_seg)%60)
st.metric(
    label="⏱️ Cambio de luz mañana", 
    value=f"{minutos}m {segundos}s", 
    delta="Ganando luz" if dif_seg > 0 else "Perdiendo luz"
)
st.markdown("---")

# --- GRÁFICO CON DEGRADADO ---
# Creamos un degradado que simula el cielo: azul oscuro -> naranja -> amarillo -> naranja -> azul oscuro
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
for i in range(0, 365):
    dia_m = inicio_año + timedelta(days=i)
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am = s_dia['sunrise'].hour + s_dia['sunrise'].minute/60
        at = s_dia['sunset'].hour + s_dia['sunset'].minute/60
        data.append({"Día": i+1, "Am": am, "Dur": at - am, "Fecha": dia_m.strftime("%d %b")})
    except: continue

df = pd.DataFrame(data)

fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["Día"], y=df["Dur"], base=df["Am"],
    marker=dict(
        color=df["Dur"],
        colorscale=[[0, '#1A237E'], [0.5, '#FF7043'], [1, '#FDD835']], # Azul -> Naranja -> Amarillo
        showscale=False
    ),
    hovertemplate="<b>%{customdata}</b><extra></extra>",
    customdata=df["Fecha"]
))

fig.add_vline(x=ahora.timetuple().tm_yday, line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10),
    yaxis=dict(range=[0, 24], dtick=4, title="Horas"),
    xaxis=dict(title="Día del año", rangeslider=dict(visible=True, thickness=0.05))
)

st.plotly_chart(fig, use_container_width=True)
