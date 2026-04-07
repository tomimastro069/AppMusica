# 🎵 Voice YT Music - Dashboard Moderno Controlado por Voz

¡Bienvenido a **Voice YT Music**! Esta es una aplicación de escritorio premium diseñada para transformar tu experiencia con YouTube Music mediante comandos de voz y una interfaz minimalista.

![Demo](Ado%20_%20Chando%20fanart%E2%99%A1.jpeg)

## ✨ Características Principales
- **🎙️ Control por Voz**: Utiliza IA (Faster-Whisper) para buscar y reproducir música simplemente hablando.
- **🏠 Dashboard Inteligente**: Inicio con historial de búsquedas recientes y acceso rápido.
- **🎵 Reproductor Integrado**: Navegador embebido optimizado para YouTube Music que mantiene tu sesión iniciada.
- **⚙️ Altamente Configurable**: Cambia la tecla de acceso rápido (hotkey), elige tu micrófono y activa/desactiva la reproducción automática.
- **🌙 Estética Premium**: Tema oscuro con diseño moderno, bordes redondeados y micro-animaciones.

---

## 🚀 Guía de Instalación

Sigue estos pasos para poner la aplicación en marcha en tu PC (Windows):

### 1. Requisitos Previos
Asegúrate de tener instalado:
- **Python 3.10 o superior**: [Descargar aquí](https://www.python.org/downloads/)
- **FFmpeg**: Necesario para el procesamiento de audio. (Puedes instalarlo vía `choco install ffmpeg` o descargando el binario y agregándolo al PATH).

### 2. Instalación de Dependencias
Abre una terminal en la carpeta del proyecto y ejecuta:
```bash
pip install -r requirements.txt
```
> [!NOTE]
> La primera vez que inicies la app, se descargará el modelo de Whisper (aprox. 150MB para el modelo base). Esto solo sucede una vez.

### 3. Crear Acceso Directo (Opcional pero recomendado)
Para abrir la app con un icono bonito desde tu escritorio sin que aparezca la consola negra de Windows:
```bash
python crear_acceso_directo.py
```
Esto creará un acceso directo llamado **Voice YT Music** en tu escritorio usando el icono de la aplicación.

---

## 🎮 Cómo usar la App

1. **Inicia la aplicación**: Ejecuta el acceso directo creado o usa `python main.py`.
2. **Primer Inicio**: Ve a la pestaña **🎵 Reproductor** e inicia sesión en tu cuenta de YouTube Music para tener tus playlists y recomendaciones (la sesión se guardará automáticamente).
3. **Comandos de Voz**:
   - Presiona la tecla **F8** (puedes cambiarla en Configuración).
   - Di algo como: *"Reproduce algo de Ado"* o *"Busca la playlist de Lo-fi"*.
   - La app buscará, registrará en tu historial y reproducirá el mejor resultado.
4. **Historial**: En el **Inicio**, verás tus búsquedas pasadas. Haz clic en cualquier tarjeta para volver a escucharla al instante.

---

## 🔧 Configuración
En la pestaña de **Configuración** podrás:
- Seleccionar qué **micrófono** usar.
- Cambiar la **Hotkey** para activar el reconocimiento de voz.
- Activar el **Autoplay**: Si está activado, la app reproduce el primer resultado automáticamente. Si está desactivado, te mostrará opciones para elegir.

---

## 🛠️ Tecnologías Usadas
- **Core**: Python & PyQt5 (Desktop UI)
- **Engine STT**: Faster-Whisper (OpenAI Whisper optimizado)
- **Reproductor**: QWebEngine (Chromium)
- **Estilos**: Custom QSS (Vanilla CSS para Qt)
- **Base de Datos**: SQLite (Historial persistente)

---

> [!TIP]
> Si la app no te escucha bien, verifica en Configuración que el micrófono seleccionado sea el correcto y que no haya demasiado ruido de fondo.
