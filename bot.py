#!/usr/bin/env python3
"""
Bot Automático Completo - v5.0
Flujo: Buscar → Descargar → Publicar (todo automático)
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
COLA_VIDEOS = DATA_DIR / 'cola_videos.json'
LOG_FILE = DATA_DIR / 'log_ejecuciones.txt'

def log(msg, tipo='info'):
    iconos = {'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️'}
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linea = f"[{timestamp}] {iconos.get(tipo, 'ℹ️')} {msg}"
    print(linea)
    
    # Guardar log
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
# PASO 1: BUSCAR VIDEOS DE NOTICIAS
# =============================================================================

KEYWORDS = {
    'breaking': 10, 'urgent': 10, 'alert': 10, 'news': 8,
    'war': 10, 'guerra': 10, 'conflict': 10, 'ataque': 10,
    'ukraine': 10, 'ucrania': 10, 'gaza': 10, 'israel': 10,
    'iran': 10, 'trump': 8, 'biden': 8, 'putin': 8,
    'missile': 10, 'misil': 10, 'nuclear': 10,
    'live': 5, 'ahora': 5, 'ultima hora': 10,
}

def calcular_puntaje(titulo):
    t = titulo.lower()
    return sum(v for p, v in KEYWORDS.items() if p in t)

def buscar_videos_youtube():
    """Busca videos de noticias recientes en YouTube"""
    if not YOUTUBE_API_KEY:
        log("YOUTUBE_API_KEY no configurado", 'error')
        return []
    
    log("🔍 Buscando videos de noticias...", 'info')
    
    videos = []
    queries = [
        'breaking news live international',
        'world news today conflict war',
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
                
                # Solo noticias relevantes (puntaje >= 8)
                if puntaje >= 8:
                    videos.append({
                        'video_id': vid,
                        'titulo': titulo,
                        'url': f"https://youtube.com/watch?v={vid}",
                        'thumbnail': f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                        'canal': snip.get('channelTitle', 'Unknown'),
                        'descripcion': snip.get('description', '')[:300],
                        'publicado': snip.get('publishedAt', ''),
                        'puntaje': puntaje,
                        'encontrado_en': datetime.now().isoformat()
                    })
                    
        except Exception as e:
            log(f"Error buscando: {e}", 'error')
    
    # Ordenar por puntaje
    videos = sorted(videos, key=lambda x: x['puntaje'], reverse=True)
    
    # Eliminar duplicados
    vistos = set()
    unicos = []
    for v in videos:
        if v['video_id'] not in vistos:
            vistos.add(v['video_id'])
            unicos.append(v)
    
    log(f"✅ Encontrados {len(unicos)} videos nuevos relevantes", 'exito')
    return unicos[:3]  # Top 3

# =============================================================================
# PASO 2: DESCARGAR VIDEO
# =============================================================================

def descargar_video(video_info, output_dir):
    """Descarga video usando pytubefix"""
    try:
        from pytubefix import YouTube
        
        log(f"⬇️ Descargando: {video_info['titulo'][:50]}...", 'info')
        
        yt = YouTube(video_info['url'])
        
        # Metadatos completos
        metadatos = {
            'video_id': video_info['video_id'],
            'titulo': yt.title,
            'descripcion': yt.description or video_info['descripcion'],
            'canal': yt.author or video_info['canal'],
            'url': video_info['url'],
            'duracion_segundos': yt.length,
            'duracion_formateada': f"{yt.length // 60}:{yt.length % 60:02d}",
            'vistas': yt.views,
            'thumbnail_url': video_info['thumbnail'],
            'keywords': video_info.get('keywords', []),
            'puntaje_noticia': video_info['puntaje'],
            'fecha_descarga': datetime.now().isoformat(),
        }
        
        # Seleccionar calidad
        stream = yt.streams.get_highest_resolution()
        
        # Descargar
        safe_title = "".join([c for c in yt.title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        filename = f"{video_info['video_id']}_{safe_title[:40]}.mp4"
        output_path = Path(output_dir) / filename
        
        # Crear directorio
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        stream.download(output_path=str(output_path.parent), filename=filename)
        
        # Guardar metadatos
        meta_file = output_path.parent / f"{video_info['video_id']}_metadatos.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadatos, f, ensure_ascii=False, indent=2)
        
        file_size = output_path.stat().st_size
        log(f"✅ Descargado: {file_size/1024/1024:.1f} MB", 'exito')
        
        return {
            'video_path': str(output_path),
            'metadatos': metadatos
        }
        
    except Exception as e:
        log(f"❌ Error descargando: {e}", 'error')
        return None

# =============================================================================
# PASO 3: PUBLICAR EN FACEBOOK
# =============================================================================

def publicar_facebook(video_path, metadatos):
    """Publica video descargado en Facebook"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("Faltan credenciales Facebook", 'error')
        return None
    
    # Verificar duplicado
    historial_fb = cargar_json(HISTORIAL_FB, [])
    for pub in historial_fb:
        if pub.get('video_id') == metadatos['video_id']:
            log(f"⚠️ Ya publicado: {metadatos['video_id']}", 'advertencia')
            return None
    
    # Crear mensaje
    hashtags = "#BreakingNews #Noticias #Urgente"
    
    mensaje = f"""🔴 {metadatos['titulo']}

📺 {metadatos['canal']} | ⏱️ {metadatos['duracion_formateada']}
👁️ {metadatos['vistas']:,} vistas | 🎯 Relevancia: {metadatos['puntaje_noticia']}/100

{metadatos['descripcion'][:200]}

🔗 Original: {metadatos['url']}

{hashtags}

🤖 Publicado automáticamente"""

    try:
        log("📤 Subiendo a Facebook...", 'info')
        
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos"
        
        with open(video_path, 'rb') as video_file:
            files = {'file': ('video.mp4', video_file, 'video/mp4')}
            data = {
                'access_token': FB_ACCESS_TOKEN,
                'description': mensaje,
                'title': metadatos['titulo'][:255],
            }
            
            response = requests.post(url, files=files, data=data, timeout=300)
            response.raise_for_status()
            
            resultado = response.json()
            post_id = resultado.get('id')
            
            # Guardar en historial
            historial_fb.append({
                'video_id': metadatos['video_id'],
                'titulo': metadatos['titulo'],
                'post_id': post_id,
                'fecha': datetime.now().isoformat(),
                'url_facebook': f"https://facebook.com/{post_id}",
                'puntaje': metadatos['puntaje_noticia']
            })
            guardar_json(HISTORIAL_FB, historial_fb[-100:])  # Mantener últimos 100
            
            log(f"✅ Publicado: https://facebook.com/{post_id}", 'exito')
            return resultado
            
    except Exception as e:
        log(f"❌ Error publicando: {e}", 'error')
        return None

# =============================================================================
# FLUJO PRINCIPAL AUTOMÁTICO
# =============================================================================

def ejecutar_flujo_completo():
    """Ejecuta todo el flujo: Buscar → Descargar → Publicar"""
    
    print("\n" + "="*70)
    print("🤖 BOT AUTOMÁTICO DE NOTICIAS - v5.0")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    temp_dir = os.getenv('RUNNER_TEMP', '/tmp') + '/bot_noticias'
    
    # PASO 1: BUSCAR
    videos = buscar_videos_youtube()
    if not videos:
        log("⏹️ No hay videos nuevos para procesar", 'advertencia')
        return False
    
    # PASO 2 & 3: DESCARGAR Y PUBLICAR CADA VIDEO
    publicados = 0
    for video in videos:
        log(f"\n{'─'*50}", 'info')
        log(f"Procesando: {video['titulo'][:50]}...", 'info')
        
        # Descargar
        resultado = descargar_video(video, temp_dir)
        if not resultado:
            log("⏭️ Saltando (falló descarga)", 'advertencia')
            continue
        
        # Publicar
        post = publicar_facebook(resultado['video_path'], resultado['metadatos'])
        if post:
            publicados += 1
            
            # Guardar en historial de búsqueda (marcar como procesado)
            historial = cargar_json(HISTORIAL_BUSQUEDA, [])
            historial.append({
                'video_id': video['video_id'],
                'titulo': video['titulo'],
                'fecha_procesado': datetime.now().isoformat(),
                'publicado': True
            })
            guardar_json(HISTORIAL_BUSQUEDA, historial)
        
        # Pequeña pausa entre publicaciones
        time.sleep(5)
    
    # Resumen
    log(f"\n{'='*70}", 'info')
    log(f"📊 RESUMEN: {publicados}/{len(videos)} videos publicados", 'exito')
    log(f"{'='*70}", 'info')
    
    return publicados > 0

if __name__ == "__main__":
    try:
        exito = ejecutar_flujo_completo()
        sys.exit(0 if exito else 1)
    except Exception as e:
        log(f"💥 Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        sys.exit(1)
