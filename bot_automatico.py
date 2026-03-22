#!/usr/bin/env python3
"""
Bot Automático - v6.0 MODO SOLO ENLACE
Busca noticias → Publica enlace con preview en Facebook
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests

# Configuración
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)

HISTORIAL_BUSQUEDA = DATA_DIR / 'historial_busquedas.json'
HISTORIAL_FB = DATA_DIR / 'historial_facebook.json'
LOG_FILE = DATA_DIR / 'log_ejecuciones.txt'

def log(msg, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️'}
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linea = f"[{timestamp}] {iconos.get(tipo, 'ℹ️')} {msg}"
    print(linea)
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(linea + '\n')

def cargar_json(ruta, default=None):
    default = default or []
    if ruta.exists():
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default.copy()

def guardar_json(ruta, datos):
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

# =============================================================================
# BUSCAR VIDEOS
# =============================================================================

KEYWORDS = {
    'breaking': 10, 'urgent': 10, 'alert': 10, 'news': 8,
    'war': 10, 'guerra': 10, 'conflict': 10, 'conflicto': 10,
    'ukraine': 10, 'ucrania': 10, 'gaza': 10, 'israel': 10,
    'iran': 10, 'irán': 10, 'trump': 8, 'biden': 8, 'putin': 8,
    'missile': 10, 'misil': 10, 'attack': 10, 'ataque': 10,
    'live': 5, 'ahora': 5, 'ultima hora': 10, 'noticia': 8,
}

def calcular_puntaje(titulo):
    t = titulo.lower()
    return sum(v for p, v in KEYWORDS.items() if p in t)

def buscar_videos_youtube():
    """Busca videos de noticias recientes"""
    if not YOUTUBE_API_KEY:
        log("YOUTUBE_API_KEY no configurado", 'error')
        return []
    
    log("🔍 Buscando videos de noticias...", 'info')
    
    videos = []
    queries = [
        'breaking news live international',
        'world news today war conflict',
        'israel gaza iran news live',
        'trump biden political news today',
        'urgent news alert now',
    ]
    
    historial = cargar_json(HISTORIAL_BUSQUEDA, [])
    videos_procesados = {v['video_id'] for v in historial}
    
    for query in queries:
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': 10,
                'key': YOUTUBE_API_KEY,
                'order': 'date',
                'publishedAfter': (datetime.now() - timedelta(hours=6)).isoformat("T") + "Z"
            }
            
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            
            if 'error' in data:
                log(f"API Error: {data['error'].get('message', 'Unknown')}", 'error')
                continue
            
            for item in data.get('items', []):
                vid = item['id'].get('videoId')
                if not vid or vid in videos_procesados:
                    continue
                
                snip = item['snippet']
                titulo = snip.get('title', '')
                puntaje = calcular_puntaje(titulo)
                
                if puntaje >= 6:
                    videos.append({
                        'video_id': vid,
                        'titulo': titulo,
                        'url': f"https://youtube.com/watch?v={vid}",
                        'thumbnail': f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg",
                        'canal': snip.get('channelTitle', 'Unknown'),
                        'descripcion': snip.get('description', '')[:300],
                        'publicado_yt': snip.get('publishedAt', ''),
                        'puntaje': puntaje,
                        'encontrado_en': datetime.now().isoformat()
                    })
                    
        except Exception as e:
            log(f"Error buscando: {e}", 'error')
    
    videos = sorted(videos, key=lambda x: x['puntaje'], reverse=True)
    vistos = set()
    unicos = []
    for v in videos:
        if v['video_id'] not in vistos:
            vistos.add(v['video_id'])
            unicos.append(v)
    
    log(f"✅ Encontrados {len(unicos)} videos nuevos relevantes", 'exito')
    return unicos[:3]

# =============================================================================
# PUBLICAR ENLACE EN FACEBOOK (con preview)
# =============================================================================

def publicar_enlace_facebook(video_info):
    """Publica enlace de YouTube (Facebook genera preview automático)"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("Faltan credenciales Facebook", 'error')
        return None
    
    # Verificar duplicado
    historial_fb = cargar_json(HISTORIAL_FB, [])
    for pub in historial_fb:
        if pub.get('video_id') == video_info['video_id']:
            log(f"⚠️ Ya publicado: {video_info['video_id']}", 'advertencia')
            return None
    
    # Calcular tiempo desde publicación
    tiempo_texto = "Reciente"
    try:
        pub_time = datetime.fromisoformat(video_info['publicado_yt'].replace('Z', '+00:00'))
        horas = (datetime.now(pub_time.tzinfo) - pub_time).total_seconds() / 3600
        if horas < 1:
            tiempo_texto = "🔴 Hace minutos"
        elif horas < 6:
            tiempo_texto = f"🔴 Hace {int(horas)} horas"
        else:
            tiempo_texto = f"Hace {int(horas)} horas"
    except:
        pass
    
    hashtags = "#BreakingNews #Noticias #Urgente #Viral #YouTube"
    
    mensaje = f"""🔴 {video_info['titulo']}

📺 {video_info['canal']} | ⏱️ {tiempo_texto}
🎯 Relevancia: {video_info['puntaje']}/100

{video_info['descripcion'][:200] if video_info['descripcion'] else ''}

🔗 Ver video completo en YouTube:
{video_info['url']}

{hashtags}

🤖 Publicado automáticamente"""

    try:
        log(f"📤 Publicando enlace: {video_info['titulo'][:50]}...", 'info')
        
        # Publicar como link (Facebook genera preview del video)
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
        
        data = {
            'access_token': FB_ACCESS_TOKEN,
            'message': mensaje,
            'link': video_info['url'],  # Facebook genera preview de YouTube
            'published': 'true'
        }
        
        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        resultado = response.json()
        post_id = resultado.get('id')
        
        # Guardar en historial
        historial_fb.append({
            'video_id': video_info['video_id'],
            'titulo': video_info['titulo'],
            'post_id': post_id,
            'fecha': datetime.now().isoformat(),
            'url_facebook': f"https://facebook.com/{post_id}",
            'url_youtube': video_info['url'],
            'puntaje': video_info['puntaje'],
            'tipo': 'enlace_con_preview'
        })
        guardar_json(HISTORIAL_FB, historial_fb[-100:])
        
        log(f"✅ Publicado: https://facebook.com/{post_id}", 'exito')
        return resultado
        
    except Exception as e:
        log(f"❌ Error publicando: {e}", 'error')
        return None

# =============================================================================
# FLUJO PRINCIPAL
# =============================================================================

def ejecutar_flujo():
    """Ejecuta: Buscar → Publicar enlaces"""
    
    print("\n" + "="*70)
    print("🤖 BOT AUTOMÁTICO DE NOTICIAS - v6.0 (Modo Enlace)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # PASO 1: BUSCAR
    videos = buscar_videos_youtube()
    if not videos:
        log("⏹️ No hay videos nuevos para procesar", 'advertencia')
        return False
    
    # PASO 2: PUBLICAR ENLACES
    publicados = 0
    for video in videos:
        log(f"\n{'─'*50}", 'info')
        log(f"Procesando: {video['titulo'][:50]}...", 'info')
        
        post = publicar_enlace_facebook(video)
        if post:
            publicados += 1
            
            # Guardar en historial de búsqueda
            historial = cargar_json(HISTORIAL_BUSQUEDA, [])
            historial.append({
                'video_id': video['video_id'],
                'titulo': video['titulo'],
                'fecha_procesado': datetime.now().isoformat(),
                'publicado': True,
                'modo': 'enlace'
            })
            guardar_json(HISTORIAL_BUSQUEDA, historial)
        
        time.sleep(3)  # Pausa entre publicaciones
    
    # Resumen
    log(f"\n{'='*70}", 'info')
    log(f"📊 RESUMEN: {publicados}/{len(videos)} enlaces publicados", 'exito')
    log(f"{'='*70}", 'info')
    
    return publicados > 0

if __name__ == "__main__":
    try:
        exito = ejecutar_flujo()
        sys.exit(0 if exito else 1)
    except Exception as e:
        log(f"💥 Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        sys.exit(1)
