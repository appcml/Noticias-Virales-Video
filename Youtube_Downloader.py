#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Downloader - Entry Point
Módulo principal de inicialización de la aplicación.
"""

import json
import os
import sys
from pathlib import Path

# Importaciones locales
from frames.root import Root, RUTA_BASE  # Nota: mayúsculas para clases/constantes
from frames.load_config import load_file, calcular_file
from frames.idiomas import Idiomas
from get_hash import (
    get_directory, 
    get_hash, 
    write_dict_hash_dir, 
    check_updates  # Corregido: cheack_updates → check_updates
)


def load_information(filepath: str = "information.json") -> dict:
    """
    Carga metadatos del proyecto desde archivo JSON.
    
    Args:
        filepath: Ruta al archivo de información
        
    Returns:
        Diccionario con metadatos del proyecto
        
    Raises:
        FileNotFoundError: Si no existe el archivo
        json.JSONDecodeError: Si el JSON es inválido
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)  # Mejor que literal_eval para JSON
    except FileNotFoundError:
        print(f"Error: No se encontró {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: JSON inválido en {filepath}: {e}")
        sys.exit(1)


def display_app_info(info: dict) -> None:
    """Muestra información de la aplicación formateada."""
    version = info.get("version", "desconocida")
    doc = info.get("doc", "Sin documentación")
    autor = info.get("autor", {})
    contribuidores = info.get("contribuidores", [])
    
    separador = "=" * 40
    
    print(f"\n{separador}")
    print(f"Versión del software -> {version}")
    print(f"{separador}")
    print(f"Documentación -> {doc}")
    print(f"{separador}")
    
    if contribuidores:
        print("Contribuidores:")
        for contrib in contribuidores:
            print(f"  Usuario: {contrib.get('usuario', 'N/A')}")
            print(f"  GitHub:  {contrib.get('github', 'N/A')}")
            print("-" * 40)
    
    print(f"Autor principal:")
    print(f"  Usuario: {autor.get('usuario', 'N/A')}")
    print(f"  GitHub:  {autor.get('github', 'N/A')}")
    print(f"{separador}\n")


def check_for_updates() -> bool:
    """
    Verifica si hay actualizaciones disponibles.
    
    Returns:
        True si hay actualización, False en caso contrario
    """
    print("Comprobando actualizaciones...")
    
    try:
        tree_dir = get_directory(debug=False)
        dict_hash_dir = get_hash(tree_dir)
        write_dict_hash_dir(dict_hash_dir)
        
        return check_updates()  # Nombre corregido
    except Exception as e:
        print(f"Advertencia: No se pudo verificar actualizaciones: {e}")
        return False


def setup_working_directory(ruta_config: str) -> None:
    """
    Configura el directorio de trabajo según la plataforma.
    
    Args:
        ruta_config: Ruta al archivo de configuración
    """
    if sys.platform == "win32":
        # Usar Path para manipulación segura de rutas
        path_obj = Path(ruta_config)
        nuevo_dir = path_obj.parent.parent  # Subir dos niveles
        try:
            os.chdir(nuevo_dir)
            print(f"Directorio cambiado a: {nuevo_dir}")
        except OSError as e:
            print(f"Error al cambiar directorio: {e}")


def initialize_gui(config_data: dict) -> None:
    """
    Inicializa la interfaz gráfica con la configuración cargada.
    
    Args:
        config_data: Diccionario con configuración de la GUI
    """
    try:
        idioma = Idiomas(config_data["lenguaje"])
        tamano = config_data["size"]
        color_fondo = config_data["color-background"]
        
        # Crear instancia de la clase Root (renombrada para evitar conflicto)
        app = Root(
            idioma=idioma,
            tamano_ventana=tamano,
            color_fondo=color_fondo
        )
        
        app.root.mainloop()
        
    except KeyError as e:
        print(f"Error: Configuración incompleta, falta clave: {e}")
        raise


def main() -> int:
    """
    Punto de entrada principal de la aplicación.
    
    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    # Cargar metadatos
    info = load_information()
    
    # Verificar actualizaciones
    if check_for_updates():
        print("¡Hay una nueva versión de este software disponible!")
    
    # Mostrar información
    display_app_info(info)
    
    try:
        # Calcular ruta de configuración
        ruta_config = calcular_file(RUTA_BASE, "config-GUI")
        print(f"Ruta de configuración: {ruta_config}")
        
        # Configurar directorio de trabajo
        setup_working_directory(ruta_config)
        
        # Cargar configuración
        config_data = load_file(ruta_config)
        print(f"Configuración cargada: {config_data}")
        
        # Iniciar GUI
        initialize_gui(config_data)
        
    except KeyboardInterrupt:
        print("\nSaliendo por interrupción del usuario...")
        return 0
        
    except Exception as e:
        print(f"\nError fatal: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
