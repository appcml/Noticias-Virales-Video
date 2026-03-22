import os
import json
from datetime import datetime
from pytubefix import YouTube

def get_download_directory():
    """Determina directorio de descarga según el entorno"""
    if os.getenv('GITHUB_ACTIONS') == 'true':
        temp_dir = os.getenv('RUNNER_TEMP', '/tmp')
        download_dir = os.path.join(temp_dir, 'youtube_downloads')
    else:
        download_dir = os.path.join(
            os.path.expanduser('~'), 
            'Downloads', 
            'YouTube_Downloader'
        )
    
    os.makedirs(download_dir, exist_ok=True)
    return download_dir

def descargar_video_con_metadatos(url, calidad='highest'):
    """
    Descarga video y guarda metadatos en archivo JSON
    """
    try:
        download_dir = get_download_directory()
        print(f"📁 Directorio: {download_dir}")
        
        yt = YouTube(url)
        
        print(f"🎬 Título: {yt.title}")
        print(f"👤 Canal: {yt.author}")
        print(f"⏱️  Duración: {yt.length} segundos")
        
        metadatos = {
            'titulo': yt.title,
            'descripcion': yt.description,
            'canal': yt.author,
            'url': url,
            'duracion_segundos': yt.length,
            'duracion_formateada': f"{yt.length // 60}:{yt.length % 60:02d}",
            'vistas': yt.views,
            'fecha_publicacion': str(yt.publish_date) if yt.publish_date else 'Desconocida',
            'video_id': yt.video_id,
            'thumbnail_url': yt.thumbnail_url,
            'keywords': yt.keywords if hasattr(yt, 'keywords') else [],
            'fecha_descarga': datetime.now().isoformat(),
            'calidad_descarga': calidad
        }
        
        metadata_file = os.path.join(download_dir, f"{yt.video_id}_metadatos.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadatos, f, ensure_ascii=False, indent=2)
        print(f"💾 Metadatos guardados: {metadata_file}")
        
        descripcion_file = os.path.join(download_dir, f"{yt.video_id}_descripcion.txt")
        with open(descripcion_file, 'w', encoding='utf-8') as f:
            f.write(f"TÍTULO: {yt.title}\n")
            f.write(f"CANAL: {yt.author}\n")
            f.write(f"URL: {url}\n")
            f.write(f"FECHA: {metadatos['fecha_publicacion']}\n")
            f.write(f"DURACIÓN: {metadatos['duracion_formateada']}\n")
            f.write("=" * 50 + "\n")
            f.write("DESCRIPCIÓN:\n")
            f.write("=" * 50 + "\n")
            f.write(yt.description or "Sin descripción")
        print(f"📝 Descripción guardada: {descripcion_file}")
        
        if calidad == 'highest':
            stream = yt.streams.get_highest_resolution()
        elif calidad == 'audio':
            stream = yt.streams.get_audio_only()
        else:
            stream = yt.streams.get_lowest_resolution()
        
        safe_title = "".join([c for c in yt.title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        video_filename = f"{yt.video_id}_{safe_title[:50]}.mp4"
        video_path = os.path.join(download_dir, video_filename)
        
        print(f"⬇️  Descargando video...")
        stream.download(output_path=download_dir, filename=video_filename)
        
        file_size = os.path.getsize(video_path)
        print(f"✅ Video guardado: {video_path}")
        print(f"📊 Tamaño: {file_size / 1024 / 1024:.2f} MB")
        
        return {
            'video_path': video_path,
            'metadata_path': metadata_file,
            'descripcion_path': descripcion_file,
            'video_id': yt.video_id,
            'titulo': yt.title,
            'tamaño_mb': file_size / 1024 / 1024
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Descargar video de YouTube con metadatos')
    parser.add_argument('--url', required=True, help='URL del video de YouTube')
    parser.add_argument('--calidad', default='highest', choices=['highest', 'lowest', 'audio'])
    args = parser.parse_args()
    
    resultado = descargar_video_con_metadatos(args.url, args.calidad)
    
    if resultado:
        print(f"\n{'='*60}")
        print("RESUMEN DE DESCARGA:")
        print(f"{'='*60}")
        print(f"Video: {resultado['video_path']}")
        print(f"Metadatos: {resultado['metadata_path']}")
        print(f"Descripción: {resultado['descripcion_path']}")
        print(f"Tamaño: {resultado['tamaño_mb']:.2f} MB")
        print(f"{'='*60}")
    else:
        print("La descarga falló")
        exit(1)
