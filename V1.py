import streamlit as st
import pandas as pd
from astral import LocationInfo
from astral.sun import sun
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
import ephem
from timezonefinder import TimezoneFinder
import pytz
import random

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Luz Solar Pro", layout="wide")

def decimal_a_horas_mins(decimal_horas):
    horas = int(decimal_horas)
    minutos = int(round((decimal_horas - horas) * 60))
    if minutos == 60: horas += 1; minutos = 0
    return f"{horas}h {minutos}min"

@st.cache_data(show_spinner=False, ttl=600)
def buscar_ubicacion_total(texto):
    """Buscador multicanal: Intenta varios servicios si uno falla"""
    if not texto: return None
    
    # Lista de endpoints para máxima fiabilidad
    urls = [
        f"https://nominatim.openstreetmap.org/search?q={texto.strip()}&format=json&limit=1",
        f"https://nominatim.openstreetmap.org/search?q={texto.strip()},Spain&format=json&limit=1",
        f"https://nominatim.openstreetmap.org/search?postalcode={texto.strip()}&country=Spain&format=json&limit=1"
    ]
    
    for url in urls:
        try:
            headers = {'User-Agent': f'SolarApp_Project_{random.randint(1,9999)}'}
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return {
                        "lat": float(data[0]["lat"]),
                        "lon": float(data[0]["lon"]),
                        "name": data[0]["display_name"].split(',')[0]
                    }
        except:
            continue
    return None

def get_moon_phase_data(date):
    m = ephem.Moon(date); p = m.phase 
    icon = "🌑" if p < 5 else "🌙" if p < 45 else "🌓" if p < 55 else "🌔" if p < 95 else "🌕"
    return f"{icon} {int(p)}%"

def get_season_color(d):
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' 
    elif d < 172: return 'rgb(144, 238, 144)'         
    elif d < 264: return 'rgb(255, 165, 0)'           
    else: return 'rgb(210, 105, 30)'                  

# --- ESTADO DE SESIÓN ---
if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 39.664, -0.228
    st.session_state.dir = "Puerto de Sagunto"

st.title("☀️ Agenda Solar & Efemérides")

# --- BUSCADOR ---
entrada = st.text_input("📍 Introduce población o CP (Ej: Benifairo de les Valls, 46511, Valencia...)", 
                        placeholder="Escribe y pulsa Enter")

if entrada:
    with st.spinner('Consultando satélites...'):
        res = buscar_ubicacion_total(entrada)
        if res:
            st.session_state.lat, st.session_state.lon = res["lat"], res["lon"]
            st.session_state.dir = res["name"]
            st.toast(f"✅ Cargado: {res['name']}", icon="📍")
        else:
            st.error(f"❌ Error: No se pudo localizar '{entrada}'. Intenta con el Código Postal.")

# --- CÁLCULOS ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state.lon, lat=st.session_state.lat) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("L", "R", tz_name, st.session_state.lat, st.session_state.lon)
ahora = datetime.now(local_tz)

st.success(f"🌍 Ubicación activa: **{st.session_state.dir}**")

# --- MÉTRICAS ---
s1 = sun(city.observer, date=ahora, tzinfo=local_tz)
s2 = sun(city.observer, date=ahora + timedelta(days=1), tzinfo=local_tz)
dif = (s2['sunset'] - s2['sunrise']).total_seconds() - (s1['sunset'] - s1['sunrise']).total_seconds()

m1, m2, m3, m4 = st.columns(4)
m1.metric("🌅 Amanecer", s1['sunrise'].strftime('%H:%M'))
m2.metric("🌇 Atardecer", s1['sunset'].strftime('%H:%M'))
m3.metric("🌓 Luna", get_moon_phase_data(ahora))
m4.metric("⏱️ Cambio luz", f"{int(abs(dif)//60)}m {int(abs(dif)%60)}s", 
          delta="Ganando luz" if dif > 0 else "Perdiendo luz")

# --- GRÁFICO ---
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
for i in range(0, 366):
    dia_m = inicio_año + timedelta(days=i)
    if dia_m.year > ahora.year: break
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am_dt, at_dt = s_dia['sunrise'], s_dia['sunset']
        dur_dec = (at_dt - am_dt).total_seconds() / 3600
        data.append({
            "Día": i+1, "Am_dec": am_dt.hour + am_dt.minute/60, "Dur_dec": dur_dec, 
            "Dur_txt": decimal_a_horas_mins(dur_dec), "Am": am_dt.strftime('%H:%M'), 
            "At": at_dt.strftime('%H:%M'), "Fecha": dia_m.strftime("%d %b"),
            "Luna": get_moon_phase_data(dia_m), "Am_dt": am_dt, "At_dt": at_dt
        })
    except: continue

df = pd.DataFrame(data)
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["Día"], y=df["Dur_dec"], base=df["Am_dec"], 
    marker_color=[get_season_color(i) for i in df["Día"]],
    customdata=df[["Am", "At", "Fecha", "Luna", "Dur_txt"]],
    hovertemplate="<b>%{customdata[2]}</b><br>🌅 Salida: %{customdata[0]}<br>🌇 Puesta: %{customdata[1]}<br>⏱️ Duración: %{customdata[4]}<br>🌙 Luna: %{customdata[3]}<extra></extra>"
))

for est in [{"dia": 80, "icon": "🌱"}, {"dia": 172, "icon": "☀️"}, {"dia": 264, "icon": "🍂"}, {"dia": 355, "icon": "❄️"}]:
    fig.add_annotation(x=est["dia"], y=0, text=est["icon"], showarrow=False, font=dict(size=20), yshift=-30)

fig.add_vline(x=ahora.timetuple().tm_yday, line_width=2, line_color="red")
fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=20, b=60), showlegend=False,
    yaxis=dict(range=[0, 24], dtick=4, title="Horas"),
    xaxis=dict(tickmode='array', tickvals=[1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335],
               ticktext=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
               rangeslider=dict(visible=True, thickness=0.04)))
st.plotly_chart(fig, use_container_width=True)

# --- PANEL INFERIOR ---
st.markdown("---")
col_inf1, col_inf2, col_inf3 = st.columns(3)
d_l = df.loc[df['Dur_dec'].idxmax()]; d_c = df.loc[df['Dur_dec'].idxmin()]
a_a = df.loc[df['Am_dt'].dt.time == df['Am_dt'].dt.time.min()].iloc[0]
a_t = df.loc[df['At_dt'].dt.time == df['At_dt'].dt.time.max()].iloc[0]

with col_inf1:
    st.write(f"🔝 **Día más largo:** {d_l['Fecha']} ({d_l['Dur_txt']})")
    st.write(f"📉 **Día más corto:** {d_c['Fecha']} ({d_c['Dur_txt']})")
with col_inf2:
    st.write(f"🌅 **Amanece antes:** {a_a['Fecha']} ({a_a['Am']})")
    st.write(f"🌇 **Atardece tarde:** {a_t['Fecha']} ({a_t['At']})")
with col_inf3:
    m_m = datetime(ahora.year, 3, 31); dv = m_m - timedelta(days=(m_m.weekday() + 1) % 7)
    m_o = datetime(ahora.year, 10, 31); di = m_o - timedelta(days=(m_o.weekday() + 1) % 7)
    st.write(f"🕐 **Cambio Verano:** {dv.strftime('%d Mar')}")
    st.write(f"🕒 **Cambio Invierno:** {di.strftime('%d Oct')}")
    
