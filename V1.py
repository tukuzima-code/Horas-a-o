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
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Luz Solar Pro", layout="centered")

# --- FUNCIONES ---
@st.cache_data(show_spinner=False, ttl=300)
def buscar_lugar_robusto(texto):
    if not texto: return None
    try:
        geolocator = Nominatim(user_agent="solar_app_v5")
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

def get_season_color(d):
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' 
    elif d < 172: return 'rgb(144, 238, 144)' 
    elif d < 264: return 'rgb(255, 165, 0)'   
    else: return 'rgb(210, 105, 30)'

# --- GESTIÓN DE ESTADO ---
if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 39.664, -0.228
    st.session_state.dir = "Puerto de Sagunto"
if 'graph_key' not in st.session_state:
    st.session_state.graph_key = 0

def reset_selection():
    st.session_state.graph_key += 1 # Al cambiar la clave, el gráfico se reinicia de cero

# --- INTERFAZ UBICACIÓN ---
st.title("☀️ Agenda Solar")
col_gps, col_txt = st.columns([1, 2])
with col_gps:
    if st.button("📍 GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state.lat, st.session_state.lon = loc['coords']['latitude'], loc['coords']['longitude']
            st.session_state.dir = "Ubicación GPS"
            reset_selection()
            st.rerun()

with col_txt:
    entrada = st.text_input("Buscar ciudad...", placeholder="Ej: Sagunto")
    if entrada:
        res = buscar_lugar_robusto(entrada)
        if res:
            st.session_state.lat, st.session_state.lon = res.latitude, res.longitude
            st.session_state.dir = res.address.split(',')[0]
            reset_selection()
            st.rerun()

tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state.lon, lat=st.session_state.lat) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, st.session_state.lat, st.session_state.lon)
ahora = datetime.now(local_tz)

st.success(f"📍 {st.session_state.dir}")

# --- DATOS DE HOY (SIEMPRE VISIBLES) ---
st.subheader("🗓️ Datos de Hoy")
s_hoy = sun(city.observer, date=ahora, tzinfo=local_tz)
s_man = sun(city.observer, date=ahora + timedelta(days=1), tzinfo=local_tz)
dif_seg = (s_man['sunset']-s_man['sunrise']).total_seconds() - (s_hoy['sunset']-s_hoy['sunrise']).total_seconds()

c1, c2, c3 = st.columns(3)
c1.metric("Amanecer", s_hoy['sunrise'].strftime('%H:%M'))
c2.metric("Atardecer", s_hoy['sunset'].strftime('%H:%M'))
minutos, segundos = int(abs(dif_seg)//60), int(abs(dif_seg)%60)
c3.metric("Mañana habrá", f"{minutos}m {segundos}s", 
          delta="Ganando luz" if dif_seg > 0 else "Perdiendo luz")

# --- GENERAR GRÁFICO ---
vista = st.radio("Escala:", ["Días", "Semanas", "Meses"], horizontal=True, on_change=reset_selection)
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
max_x = 366 if ahora.year % 4 == 0 else 365
pasos = {"Días": 1, "Semanas": 7, "Meses": 30}

for i in range(0, max_x, pasos[vista]):
    dia_m = inicio_año + timedelta(days=i)
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am, at = s_dia['sunrise'].hour + s_dia['sunrise'].minute/60, s_dia['sunset'].hour + s_dia['sunset'].minute/60
        x_val = i+1 if vista == "Días" else (dia_m.isocalendar()[1] if vista == "Semanas" else dia_m.month)
        data.append({
            "X": x_val, "Am": am, "Dur": at - am, 
            "L": dia_m.strftime("%d %b"), "Color": get_season_color(i), "Fecha": dia_m
        })
    except: continue
df = pd.DataFrame(data)

fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["X"], y=df["Dur"], base=df["Am"], 
    marker=dict(color=df["Color"]),
    customdata=df["L"], hovertemplate="<b>%{customdata}</b><extra></extra>"
))

hoy_x = ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month)
fig.add_vline(x=hoy_x, line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    yaxis=dict(range=[0, 24], fixedrange=True, dtick=2),
    xaxis=dict(range=[1, max_x if vista=="Días" else (53 if vista=="Semanas" else 12)], 
               fixedrange=True, rangeslider=dict(visible=True, thickness=0.08)),
    clickmode='event+select'
)

# El uso de la 'key' dinámica soluciona el retraso y permite el reset
event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key=f"sun_graph_{st.session_state.graph_key}")

# --- PANEL DE SELECCIÓN ---
if event_data and len(event_data.get("selection", {}).get("points", [])) > 0:
    idx = event_data["selection"]["points"][0]["point_index"]
    f_sel = df.iloc[idx]
    fecha_sel = f_sel['Fecha'].replace(tzinfo=local_tz)
    s_sel = sun(city.observer, date=fecha_sel, tzinfo=local_tz)
    
    st.markdown(f"### 🔍 Detalles del {fecha_sel.strftime('%d de %B')}")
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric("Amanecer", s_sel['sunrise'].strftime('%H:%M'))
    col_s2.metric("Atardecer", s_sel['sunset'].strftime('%H:%M'))
    col_s3.metric("Luna", get_moon_phase(fecha_sel))
    
    # El botón ahora sí funciona porque reinicia el gráfico
    if st.button("✖️ Cerrar selección"):
        reset_selection()
        st.rerun()
else:
    st.info("👆 Toca una barra en el gráfico para comparar.")
    
