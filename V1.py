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

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Luz Solar Pro", layout="wide")

# --- FUNCIONES DE APOYO ---
def decimal_a_horas_mins(decimal_horas):
    """Convierte 9.4 a '9h 24min'"""
    horas = int(decimal_horas)
    minutos = int(round((decimal_horas - horas) * 60))
    if minutos == 60:
        horas += 1
        minutos = 0
    return f"{horas}h {minutos}min"

@st.cache_data(show_spinner=False, ttl=600)
def buscar_ubicacion(texto):
    """Buscador ultra-robusto que prioriza el texto directo del usuario"""
    if not texto: return None
    try:
        # Generamos un agente aleatorio para evitar bloqueos de la API
        n = random.randint(1000, 9999)
        geolocator = Nominatim(user_agent=f"solar_search_app_{n}")
        
        # Intento 1: Tal cual lo escribe el usuario (Mejor para nombres con tildes o en valenciano)
        location = geolocator.geocode(texto.strip(), timeout=10, language="es")
        
        # Intento 2: Si falla, añadir ", Spain" (Útil para códigos postales o nombres genéricos)
        if not location:
            location = geolocator.geocode(f"{texto.strip()}, Spain", timeout=10)
            
        return location
    except Exception as e:
        return None

def get_moon_phase_data(date):
    """Cálculo de fase lunar con icono y %"""
    m = ephem.Moon(date)
    p = m.phase 
    if p < 5: icon = "🌑"
    elif p < 45: icon = "🌙"
    elif p < 55: icon = "🌓"
    elif p < 95: icon = "🌔"
    else: icon = "🌕"
    return f"{icon} {int(p)}%"

def get_season_color(d):
    """Colores temáticos por día del año"""
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' # Invierno
    elif d < 172: return 'rgb(144, 238, 144)'         # Primavera
    elif d < 264: return 'rgb(255, 165, 0)'           # Verano
    else: return 'rgb(210, 105, 30)'                  # Otoño

# --- INICIALIZACIÓN DE SESIÓN ---
if 'lat' not in st.session_state:
    st.session_state['lat'], st.session_state['lon'] = 39.664, -0.228
    st.session_state['dir'] = "Puerto de Sagunto"

st.title("☀️ Agenda Solar & Efemérides")

# --- BUSCADOR ---
entrada = st.text_input("Introduce población o código postal", 
                        placeholder="Ej: Benifairó de les Valls, Sagunto, 46520...")

if entrada:
    res = buscar_ubicacion(entrada)
    if res:
        st.session_state['lat'], st.session_state['lon'] = res.latitude, res.longitude
        st.session_state['dir'] = res.address.split(',')[0]
    else:
        st.error(f"📍 No se ha encontrado '{entrada}'. Prueba a escribirlo de otra forma.")

# --- CÁLCULOS ASTRONÓMICOS ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state['lon'], lat=st.session_state['lat']) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("Lugar", "Región", tz_name, st.session_state['lat'], st.session_state['lon'])
ahora = datetime.now(local_tz)

st.info(f"📍 Datos para: **{st.session_state['dir']}**")

# --- MÉTRICAS DE HOY ---
s1 = sun(city.observer, date=ahora, tzinfo=local_tz)
s2 = sun(city.observer, date=ahora + timedelta(days=1), tzinfo=local_tz)
dur1 = (s1['sunset'] - s1['sunrise']).total_seconds()
dur2 = (s2['sunset'] - s2['sunrise']).total_seconds()
dif_seg = dur2 - dur1

m1, m2, m3, m4 = st.columns(4)
m1.metric("🌅 Amanecer", s1['sunrise'].strftime('%H:%M'))
m2.metric("🌇 Atardecer", s1['sunset'].strftime('%H:%M'))
m3.metric("🌓 Luna", get_moon_phase_data(ahora))
min_h, seg_h = int(abs(dif_seg)//60), int(abs(dif_seg)%60)
m4.metric("⏱️ Cambio luz", f"{min_h}m {seg_h}s", delta="Ganando luz" if dif_seg > 0 else "Perdiendo luz")

# --- GENERACIÓN DE DATOS ANUALES ---
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
for i in range(0, 366):
    dia_m = inicio_año + timedelta(days=i)
    if dia_m.year > ahora.year: break
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am_dt, at_dt = s_dia['sunrise'], s_dia['sunset']
        dur_decimal = (at_dt - am_dt).total_seconds() / 3600
        data.append({
            "Día": i+1, 
            "Am_dec": am_dt.hour + am_dt.minute/60, 
            "Dur_decimal": dur_decimal, 
            "Dur_texto": decimal_a_horas_mins(dur_decimal),
            "Amanece": am_dt.strftime('%H:%M'), 
            "Atardece": at_dt.strftime('%H:%M'), 
            "Fecha": dia_m.strftime("%d %b"),
            "Luna": get_moon_phase_data(dia_m),
            "Amanece_dt": am_dt,
            "Atardece_dt": at_dt
        })
    except: continue

df = pd.DataFrame(data)

# --- GRÁFICO INTERACTIVO ---
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["Día"], y=df["Dur_decimal"], base=df["Am_dec"], 
    marker_color=[get_season_color(i) for i in df["Día"]],
    customdata=df[["Amanece", "Atardece", "Fecha", "Luna", "Dur_texto"]],
    hovertemplate="""
    <b>%{customdata[2]}</b><br>
    🌅 Salida: %{customdata[0]}<br>
    🌇 Puesta: %{customdata[1]}<br>
    ⏱️ Duración: %{customdata[4]}<br>
    🌙 Luna: %{customdata[3]}
    <extra></extra>
    """
))

for est in [{"dia": 80, "icon": "🌱"}, {"dia": 172, "icon": "☀️"}, {"dia": 264, "icon": "🍂"}, {"dia": 355, "icon": "❄️"}]:
    fig.add_annotation(x=est["dia"], y=0, text=est["icon"], showarrow=False, font=dict(size=20), yshift=-30)

fig.add_vline(x=ahora.timetuple().tm_yday, line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", height=500, margin=dict(l=10, r=10, t=20, b=60), showlegend=False,
    yaxis=dict(range=[0, 24], dtick=4, title="Horas"),
    xaxis=dict(
        tickmode='array', tickvals=[1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335],
        ticktext=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
        rangeslider=dict(visible=True, thickness=0.04)
    )
)
st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- PANEL DE EFEMÉRIDES ---
st.markdown("### 📊 Efemérides del Año")
d_largo = df.loc[df['Dur_decimal'].idxmax()]
d_corto = df.loc[df['Dur_decimal'].idxmin()]
am_antes = df.loc[df['Amanece_dt'].dt.time == df['Amanece_dt'].dt.time.min()].iloc[0]
at_tarde = df.loc[df['Atardece_dt'].dt.time == df['Atardece_dt'].dt.time.max()].iloc[0]

m_marzo = datetime(ahora.year, 3, 31); dv = m_marzo - timedelta(days=(m_marzo.weekday() + 1) % 7)
m_oct = datetime(ahora.year, 10, 31); di = m_oct - timedelta(days=(m_oct.weekday() + 1) % 7)

f1, f2, f3 = st.columns(3)
with f1:
    st.write(f"🔝 **Día más largo:** {d_largo['Fecha']} — **{d_largo['Dur_texto']}**")
    st.write(f"📉 **Día más corto:** {d_corto['Fecha']} — **{d_corto['Dur_texto']}**")
with f2:
    st.write(f"🌅 **Amanece más pronto:** {am_antes['Fecha']} ({am_antes['Amanece']})")
    st.write(f"🌇 **Atardece más tarde:** {at_tarde['Fecha']} ({at_tarde['Atardece']})")
with f3:
    st.write(f"🕐 **Cambio Verano:** {dv.strftime('%d de marzo')}")
    st.write(f"🕒 **Cambio Invierno:** {di.strftime('%d de octubre')}")
