#!/usr/bin/env python3
"""
Bot Automático Completo - v5.1 (yt-dlp edition)
Flujo: Buscar → Descargar → Publicar (todo automático)
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests

# Configuración desde secrets
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

# Rutas
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
# PASO 1: BUSCAR VIDEOS DE NOTICIAS
# =============================================================================

KEYWORDS = {
    'breaking': 10, 'urgent': 10, 'alert': 10, 'news': 8,
    'war': 10, 'guerra': 10, 'conflict': 10, 'conflicto': 10,
    'ukraine': 10, 'ucrania': 10, 'gaza': 10, 'israel': 10,
    'iran': 10, 'irán': 10, 'trump': 8, 'biden': 8, 'putin': 8,
    'missile': 10, 'misil': 10, 'attack': 10, 'ataque': 10,
    'live': 5, 'ahora': 5, 'ultima hora': 10, 'noticia': 8,
    'politica': 7, 'mundo': 6, 'internacional': 7,
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
                        'thumbnail': f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                        'canal': snip.get('channelTitle', 'Unknown'),
                        'descripcion': snip.get('description', '')[:300],
                        'publicado': snip.get('publishedAt', ''),
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
# PASO 2: DESCARGAR VIDEO CON YT-DLP
# =============================================================================

def descargar_video(video_info, output_dir):
    """Descarga video usando yt-dlp (más robusto contra bloqueos)"""
    try:
        import yt_dlp
        
        log(f"⬇️ Descargando: {video_info['titulo'][:50]}...", 'info')
        
        video_id = video_info['video_id']
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        output_template = str(output_path / f"{video_id}_%(title).50s.%(ext)s")
        
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Referer': 'https://www.youtube.com/',
            },
            'retries': 3,
            'fragment_retries': 3,
            'socket_timeout': 30,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_info['url'], download=False)
            
            metadatos = {
                'video_id': video_id,
                'titulo': info.get('title', video_info['titulo']),
                'descripcion': info.get('description', video_info['descripcion']),
                'canal': info.get('uploader', video_info['canal']),
                'url': video_info['url'],
                'duracion_segundos': info.get('duration', 0),
                'duracion_formateada': f"{info.get('duration', 0) // 60}:{info.get('duration', 0) % 60:02d}",
                'vistas': info.get('view_count', 0),
                'thumbnail_url': info.get('thumbnail', video_info['thumbnail']),
                'tags': info.get('tags', []),
                'puntaje_noticia': video_info['puntaje'],
                'fecha_descarga': datetime.now().isoformat(),
            }
            
            log(f"   Formato: {info.get('format', 'desconocido')}", 'info')
            ydl.download([video_info['url']])
            
            descargados = list(output_path.glob(f"{video_id}_*"))
            archivos_video = [f for f in descargados if f.suffix in ['.mp4', '.webm', '.mkv']]
            
            if not archivos_video:
                raise FileNotFoundError("No se encontró archivo de video descargado")
            
            video_file = archivos_video[0]
            file_size = video_file.stat().st_size
            
            meta_file = output_path / f"{video_id}_metadatos.json"
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(metadatos, f, ensure_ascii=False, indent=2)
            
            log(f"✅ Descargado: {file_size/1024/1024:.1f} MB", 'exito')
            
            return {
                'video_path': str(video_file),
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
    
    historial_fb = cargar_json(HISTORIAL_FB, [])
    for pub in historial_fb:
        if pub.get('video_id') == metadatos['video_id']:
            log(f"⚠️ Ya publicado: {metadatos['video_id']}", 'advertencia')
            return None
    
    hashtags = "#BreakingNews #Noticias #Urgente #Viral"
    
    mensaje = f"""🔴 {metadatos['titulo']}

📺 {metadatos['canal']} | ⏱️ {metadatos['duracion_formateada']}
👁️ {metadatos['vistas']:,} vistas | 🎯 Relevancia: {metadatos['puntaje_noticia']}/100

{metadatos['descripcion'][:200] if metadatos['descripcion'] else ''}

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
            
            historial_fb.append({
                'video_id': metadatos['video_id'],
                'titulo': metadatos['titulo'],
                'post_id': post_id,
                'fecha': datetime.now().isoformat(),
                'url_facebook': f"https://facebook.com/{post_id}",
                'puntaje': metadatos['puntaje_noticia']
            })
            guardar_json(HISTORIAL_FB, historial_fb[-100:])
            
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
    print("🤖 BOT AUTOMÁTICO DE NOTICIAS - v5.1 (yt-dlp)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    temp_dir = os.getenv('RUNNER_TEMP', '/tmp') + '/bot_noticias'
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    
    videos = buscar_videos_youtube()
    if not videos:
        log("⏹️ No hay videos nuevos para procesar", 'advertencia')
        return False
    
    publicados = 0
    for video in videos:
        log(f"\n{'─'*50}", 'info')
        log(f"Procesando: {video['titulo'][:50]}...", 'info')
        
        resultado = descargar_video(video, temp_dir)
        if not resultado:
            log("⏭️ Saltando (falló descarga)", 'advertencia')
            continue
        
        post = publicar_facebook(resultado['video_path'], resultado['metadatos'])
        if post:
            publicados += 1
            
            historial = cargar_json(HISTORIAL_BUSQUEDA, [])
            historial.append({
                'video_id': video['video_id'],
                'titulo': video['titulo'],
                'fecha_procesado': datetime.now().isoformat(),
                'publicado': True
            })
            guardar_json(HISTORIAL_BUSQUEDA, historial)
        
        time.sleep(5)
    
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
