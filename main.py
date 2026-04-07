import sys
import os
import threading
import keyboard
import winsound
import time
import logging

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QLineEdit, QCheckBox, QStackedWidget, QFrame,
                             QScrollArea, QGridLayout, QSizePolicy, QFileDialog,
                             QGraphicsDropShadowEffect)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile, QWebEnginePage, QWebEngineScript
from PyQt5.QtCore import QUrl, pyqtSignal, QObject, Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QIcon, QCursor, QColor, QPixmap

from config import load_config, save_config
from db import init_db, log_history, get_recent_history
from audio_recorder import record_audio, list_microphones
from stt_engine import STTEngine
from intent_parser import parse_intent
from yt_music_handler import YTMusicHandler

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class WorkerSignals(QObject):
    update_status = pyqtSignal(str, bool)
    set_last_query = pyqtSignal(str)
    play_url = pyqtSignal(str)
    show_options = pyqtSignal(list)
    refresh_history = pyqtSignal()

# ================================
# ESTILOS NATIVOS MODERNOS (QSS)
# ================================
MODERN_STYLE = """
* {
    font-family: "Inter", "Segoe UI", sans-serif;
    color: #EAEAEA;
    border: none;
}

QMainWindow, QWidget#main_bg {
    background-color: #0F0F0F;
}

QStackedWidget, QScrollArea, QScrollArea > QWidget {
    background: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #0F0F0F;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #555555;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* SIDEBAR */
QFrame#sidebar {
    background-color: #000000;
}
QPushButton.nav_btn {
    background-color: transparent;
    color: #A7A7A7;
    text-align: left;
    padding: 12px 18px;
    font-size: 15px;
    font-weight: 600;
    border-radius: 6px;
}
QPushButton.nav_btn:hover {
    color: #FFFFFF;
}
QPushButton.nav_btn_active {
    background-color: #282828;
    color: #FFFFFF;
    text-align: left;
    padding: 12px 18px;
    font-size: 15px;
    font-weight: 600;
    border-radius: 6px;
}

/* DASHBOARD CARDS */
QFrame.history_card {
    background-color: rgba(24, 24, 24, 220); /* Semi-transparente para glassmorphism */
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 15px;
}
QFrame.history_card:hover {
    background-color: rgba(40, 40, 40, 240);
    border: 1px solid rgba(29, 185, 84, 150); /* Borde verde sutil al pasar el mouse */
}
QLabel.card_title {
    font-size: 16px;
    font-weight: bold;
    color: #FFFFFF;
}
QLabel.card_subtitle {
    font-size: 13px;
    color: #A7A7A7;
}

/* SETTINGS ELEMENTS */
QComboBox, QLineEdit {
    background-color: #121212;
    color: #FFFFFF;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 10px;
}
QComboBox::drop-down { border: none; width: 0px; }
QComboBox QAbstractItemView {
    background-color: #181818;
    border: 1px solid #333333;
    selection-background-color: #1DB954;
}
QPushButton.action_btn {
    background-color: #1DB954;
    color: #000000;
    font-weight: bold;
    border-radius: 20px;
    padding: 12px 24px;
}
QPushButton.action_btn:hover {
    background-color: #1ED760;
}
QPushButton.action_secondary {
    background-color: #2A2A2A;
    color: #FFFFFF;
    font-weight: bold;
    border-radius: 20px;
    padding: 12px 24px;
}
QPushButton.action_secondary:hover {
    background-color: #3A3A3A;
}

QCheckBox {
    spacing: 12px;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 10px; /* Circular checkbox */
    border: 2px solid #555555;
    background: #181818;
}
QCheckBox::indicator:checked {
    background: #1DB954;
    border: 2px solid #1DB954;
}
"""

# ================================
# WIDGET PERSONALIZADO PARA CARDS
# ================================
class ClickableCard(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.setProperty("class", "history_card")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        # Tamaño fijo un poco más grande para evitar recortes de texto
        self.setFixedSize(280, 120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "card_title")
        lbl_title.setWordWrap(True)
        layout.addWidget(lbl_title)
        
        lbl_subtitle = QLabel(subtitle)
        lbl_subtitle.setProperty("class", "card_subtitle")
        layout.addWidget(lbl_subtitle)
        layout.addStretch()

        # Efecto de Sombra (Shadow Effect)
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(self.shadow)
        
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

# ================================
# NAVEGADOR SILENCIOSO (Sin Diálogos)
# ================================
class SilentWebPage(QWebEnginePage):
    def javascriptConfirm(self, url, msg):
        return True # Auto-confirmar (Permitir salir del sitio o diálogos)
    
    def javascriptAlert(self, url, msg):
        pass # Mutear alertas de JS
    
    def javascriptPrompt(self, url, msg, default):
        return False, "" # Ignorar prompts
    
    def featurePermissionRequested(self, url, feature):
        # Auto-denegar notificaciones pero permitir otros (Media, etc)
        if feature == QWebEnginePage.Notifications:
            self.setFeaturePermission(url, feature, QWebEnginePage.PermissionDeniedByUser)
        else:
            self.setFeaturePermission(url, feature, QWebEnginePage.PermissionGrantedByUser)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # Opcional: Silenciar mensajes de consola internos de Chromium
        pass

# ================================
# APLICACIÓN PRINCIPAL
# ================================
class VoiceMusicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice YT Music")
        self.resize(1050, 680) # Tamaño optimizado
        
        icon_path = os.path.join(os.path.dirname(__file__), "Ado _ Chando fanart♡.jpeg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.setStyleSheet(MODERN_STYLE)
        
        self.config = load_config()
        self.is_listening = False
        self.stt = None
        self.ytm = YTMusicHandler()
        self.signals = WorkerSignals()
        
        self.signals.update_status.connect(self.on_update_status)
        self.signals.set_last_query.connect(self.on_set_last_query)
        self.signals.play_url.connect(self.on_play_url)
        self.signals.show_options.connect(self.on_show_options)
        self.signals.refresh_history.connect(self.load_history_cards)
        
        init_db()
        self.setup_ui()
        # Darle un pequeño tiempo al layout para calcular el tamaño real antes de poner el fondo
        QTimer.singleShot(50, self.apply_background)
        self.history_items = [] # Cache para responsividad
        self.load_history_cards()
        
        threading.Thread(target=self.init_stt_bg, daemon=True).start()
        
        hotkey = self.config.get("hotkey", "f8")
        try:
            keyboard.add_hotkey(hotkey, self.on_hotkey_pressed)
        except: pass

    def init_stt_bg(self):
        self.signals.update_status.emit("Cargando cerebro IA...", False)
        self.stt = STTEngine(model_size=self.config.get("model_size", "base"))
        self.signals.update_status.emit("🎤 Esperando comando", False)

    # ================= UI SETUP =================
    def setup_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("main_bg")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- SIDEBAR LATERAL ---
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(15, 30, 15, 20)
        side_layout.setSpacing(10)
        
        title = QLabel("VoiceMusic")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: white; margin-bottom: 20px; font-weight: 800; padding-left: 10px;")
        side_layout.addWidget(title)
        
        self.nav_home = QPushButton("🏠 Inicio")
        self.nav_player = QPushButton("🎵 Reproductor")
        self.nav_settings = QPushButton("⚙️ Configuración")
        
        self.nav_home.setProperty("class", "nav_btn_active")
        self.nav_player.setProperty("class", "nav_btn")
        self.nav_settings.setProperty("class", "nav_btn")
        
        side_layout.addWidget(self.nav_home)
        side_layout.addWidget(self.nav_player)
        side_layout.addWidget(self.nav_settings)
        
        side_layout.addStretch()
        
        # Mini State in sidebar
        self.side_status = QLabel("Listo")
        self.side_status.setStyleSheet("color: #1DB954; font-weight: bold; padding: 10px;")
        self.side_status.setWordWrap(True)
        side_layout.addWidget(self.side_status)
        
        main_layout.addWidget(sidebar)
        
        # --- AREA CENTRAL (Páginas) ---
        # Contenedor para que el fondo sea solo de la parte derecha
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Label para fondo con escalado de alta calidad solo en la derecha
        self.bg_label = QLabel(self.right_container)
        
        self.stack = QStackedWidget()
        self.right_layout.addWidget(self.stack)
        
        main_layout.addWidget(self.right_container, 1)
        
        self.setup_dashboard()
        self.setup_player()
        self.setup_settings()
        
        # Conectar navegación
        self.nav_home.clicked.connect(lambda: self.switch_page(0))
        self.nav_player.clicked.connect(lambda: self.switch_page(1))
        self.nav_settings.clicked.connect(lambda: self.switch_page(2))

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        
        # Actualizar clases de botones
        btns = [self.nav_home, self.nav_player, self.nav_settings]
        for i, btn in enumerate(btns):
            btn.setProperty("class", "nav_btn_active" if i == index else "nav_btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # =============== DASHBOARD (Page 0) ===============
    def setup_dashboard(self):
        dash_scroll = QScrollArea()
        dash_scroll.setWidgetResizable(True)
        dash_widget = QWidget()
        dash_scroll.setWidget(dash_widget)
        
        layout = QVBoxLayout(dash_widget)
        layout.setContentsMargins(40, 50, 40, 40)
        layout.setSpacing(30)
        
        # Hero Section
        hero_layout = QVBoxLayout()
        self.hero_status = QLabel("🎤 Esperando comando")
        self.hero_status.setFont(QFont("Segoe UI", 32, QFont.Bold))
        self.hero_status.setStyleSheet("color: white;")
        hero_layout.addWidget(self.hero_status)
        
        self.hero_sub = QLabel(f"Presiona [{self.config.get('hotkey', 'f8').upper()}] para hablar o usa los botones.")
        self.hero_sub.setFont(QFont("Segoe UI", 16))
        self.hero_sub.setStyleSheet("color: #A7A7A7;")
        hero_layout.addWidget(self.hero_sub)
        
        # Fast Actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(15)
        
        btn_listen = QPushButton("🎤 Escuchar Ahora")
        btn_listen.setProperty("class", "action_btn")
        btn_listen.setCursor(QCursor(Qt.PointingHandCursor))
        btn_listen.clicked.connect(self.trigger_manual_listen)
        actions_layout.addWidget(btn_listen)
        
        btn_open_player = QPushButton("🎵 Ver Reproductor")
        btn_open_player.setProperty("class", "action_secondary")
        btn_open_player.setCursor(QCursor(Qt.PointingHandCursor))
        btn_open_player.clicked.connect(lambda: self.switch_page(1))
        actions_layout.addWidget(btn_open_player)
        
        actions_layout.addStretch()
        hero_layout.addLayout(actions_layout)
        layout.addLayout(hero_layout)
        
        # Búsquedas Recientes / Historial dinámico
        history_lbl = QLabel("Búsquedas Recientes")
        history_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(history_lbl)
        
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(20)
        layout.addLayout(self.cards_layout)
        
        layout.addStretch()
        self.stack.addWidget(dash_scroll)

    def load_history_cards(self):
        self.history_items = get_recent_history(limit=8)
        self.update_cards_grid()

    def update_cards_grid(self):
        # Limpiar layout
        for i in reversed(range(self.cards_layout.count())): 
            widget = self.cards_layout.itemAt(i).widget()
            if widget: widget.setParent(None)
                
        if not self.history_items:
            no_data = QLabel("Todavía no hay canciones recientes.")
            no_data.setStyleSheet("color: #777777;")
            self.cards_layout.addWidget(no_data, 0, 0)
            return

        # Calcular columnas según el ancho disponible (Card width 280 + spacing 20)
        available_width = self.width() - 240 - 100 
        col_width = 300 
        cols = max(1, available_width // col_width)
        
        # Limitar a máximo 2 filas para mantener limpieza
        max_visible = cols * 2
        visible_items = self.history_items[:max_visible]

        row = 0
        col = 0
        for item in visible_items:
            query, url, stamp = item
            card = ClickableCard(query.title(), "YT Music")
            card.clicked.connect(lambda u=url, q=query: self.on_play_url(u, q))
            
            # Qt.AlignTop para que no se estiren verticalmente
            self.cards_layout.addWidget(card, row, col, Qt.AlignTop)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    # =============== REPRODUCTOR (Page 1) ===============
    def setup_player(self):
        player_widget = QWidget()
        layout = QVBoxLayout(player_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Crear perfil de navegador persistente
        self.browser_profile = QWebEngineProfile("yt_music_data", self)
        
        # 2. Obligar a guardar cookies permanentemente en una carpeta local
        cache_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "browser_data")
        self.browser_profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        self.browser_profile.setPersistentStoragePath(cache_dir)
        self.browser_profile.setCachePath(cache_dir)
        
        # 3. Spoofing (Falsificar) el User-Agent para que Google permita el inicio de sesión
        # TRUCO: Los User-Agents de Android son a menudo los que mejor funcionan para loguearse en apps de escritorio.
        user_agent = "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
        self.browser_profile.setHttpUserAgent(user_agent)
        
        # Inyectar el lenguaje para que Google no desconfíe
        self.browser_profile.setHttpAcceptLanguage("es-ES,es;q=0.9,en;q=0.8")
        
        settings = self.browser_profile.settings()
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        
        # 4. Inyectar script para matar diálogos y onbeforeunload a nivel DOM (Doble protección)
        script_code = """
        // Hacer que no parezca un navegador automatizado
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        
        window.alert = function() { console.log("Alert bloqueado"); };
        window.confirm = function() { return true; };
        window.prompt = function() { return null; };
        window.addEventListener('beforeunload', function(e) { 
            e.stopImmediatePropagation(); 
        }, true);
        """
        script = QWebEngineScript()
        script.setSourceCode(script_code)
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(True)
        self.browser_profile.scripts().insert(script)
        
        # 5. Iniciar navegador pasándole el perfil persistente customizado
        self.browser = QWebEngineView()
        
        # Clase personalizada que mata los diálogos de JS (Evita el "Are you sure you want to leave?")
        self.custom_page = SilentWebPage(self.browser_profile, self.browser)
        self.browser.setPage(self.custom_page)
        
        # Configuraciones globales adicionales
        self.browser.settings().setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        
        self.browser.setUrl(QUrl("https://music.youtube.com"))
        
        layout.addWidget(self.browser)
        self.stack.addWidget(player_widget)

    # =============== CONFIGURACIÓN (Page 2) ===============
    def setup_settings(self):
        set_scroll = QScrollArea()
        set_scroll.setWidgetResizable(True)
        set_widget = QWidget()
        set_scroll.setWidget(set_widget)
        
        layout = QVBoxLayout(set_widget)
        layout.setContentsMargins(40, 50, 40, 40)
        layout.setSpacing(25)
        
        title = QLabel("Configuración")
        title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        layout.addWidget(title)
        
        # Micrófono
        mic_lbl = QLabel("Micrófono de entrada:")
        mic_lbl.setStyleSheet("color: #A7A7A7;")
        layout.addWidget(mic_lbl)
        
        self.mic_combo = QComboBox()
        self.mic_combo.setFixedWidth(400)
        self.mics = list_microphones()
        for i, name in self.mics:
            self.mic_combo.addItem(name, i)
        saved_mic = self.config.get("mic_index")
        if saved_mic is not None:
            idx = self.mic_combo.findData(saved_mic)
            if idx >= 0: self.mic_combo.setCurrentIndex(idx)
        self.mic_combo.currentIndexChanged.connect(self.save_settings)
        layout.addWidget(self.mic_combo)
        
        # Hotkey
        hk_lbl = QLabel("Tecla de acceso rápido (Hotkey):")
        hk_lbl.setStyleSheet("color: #A7A7A7; margin-top: 15px;")
        layout.addWidget(hk_lbl)
        
        hk_layout = QHBoxLayout()
        self.hk_input = QLineEdit(self.config.get("hotkey", "f8"))
        self.hk_input.setFixedWidth(250)
        hk_layout.addWidget(self.hk_input)
        
        save_hk_btn = QPushButton("Actualizar Tecla")
        save_hk_btn.setProperty("class", "action_secondary")
        save_hk_btn.clicked.connect(self.save_hotkey)
        hk_layout.addWidget(save_hk_btn)
        hk_layout.addStretch()
        layout.addLayout(hk_layout)
        
        # Autoplay
        self.autoplay_chk = QCheckBox("Reproducir automáticamente el primer resultado")
        self.autoplay_chk.setFont(QFont("Segoe UI", 12))
        self.autoplay_chk.setChecked(self.config.get("auto_play", True))
        self.autoplay_chk.stateChanged.connect(self.save_settings)
        layout.addWidget(self.autoplay_chk)

        # Personalización de Fondo
        bg_lbl = QLabel("Fondo de pantalla:")
        bg_lbl.setStyleSheet("color: #A7A7A7; margin-top: 15px;")
        layout.addWidget(bg_lbl)
        
        bg_layout = QHBoxLayout()
        btn_choose_bg = QPushButton("Seleccionar Imagen")
        btn_choose_bg.setProperty("class", "action_secondary")
        btn_choose_bg.clicked.connect(self.choose_background_image)
        bg_layout.addWidget(btn_choose_bg)
        
        btn_remove_bg = QPushButton("Quitar Fondo")
        btn_remove_bg.setProperty("class", "action_secondary")
        btn_remove_bg.clicked.connect(self.remove_background_image)
        bg_layout.addWidget(btn_remove_bg)
        bg_layout.addStretch()
        layout.addLayout(bg_layout)

        layout.addStretch()
        self.stack.addWidget(set_scroll)

    # ====================================================

    def on_update_status(self, text, is_error):
        # Actualiza el dashboard y la barra lateral
        self.hero_status.setText(text)
        self.side_status.setText(text)
        if is_error:
            self.hero_status.setStyleSheet("color: #FF4444;")
            self.side_status.setStyleSheet("color: #FF4444;")
            self.play_beep("error")
        else:
            self.hero_status.setStyleSheet("color: white;")
            self.side_status.setStyleSheet("color: #1DB954;")
            
    def on_set_last_query(self, text):
        pass # Podríamos ponerlo temporalmente en el status
        
    def on_play_url(self, url, query=None):
        self.browser.page().runJavaScript("window.onbeforeunload = null;")
        self.browser.setUrl(QUrl(url))
        
        # Guardar en el historial si viene de un click en Card
        if query:
            log_history("Manual Click", query, url, True)
            
        # Pequeño delay de 200ms para asegurar que el DB termine de escribir antes de leer
        QTimer.singleShot(200, lambda: self.signals.refresh_history.emit())
        
        # Ir a la página del Player
        self.switch_page(1)
        
    def on_show_options(self, results):
        # Cambiar el titulo a Opciones
        self.hero_status.setText("Varias coincidencias")
        self.hero_sub.setText("Hemos encontrado esto. Clickeá una para reproducir:")
        
        # Usaremos el contenedor de cartas para inyectarlas directamente acá
        for i in reversed(range(self.cards_layout.count())): 
            widget = self.cards_layout.itemAt(i).widget()
            if widget: widget.setParent(None)
            
        row, col = 0, 0
        for res in results:
            title = res.get('title', '')
            artist_list = res.get('artists')
            artist = artist_list[0].get('name', '') if artist_list else 'Playlist'
            
            card = ClickableCard(f"🎵 {title}", artist)
            card.clicked.connect(lambda item=res, t=title: self.on_play_url(self.ytm.get_url(item), t))
            self.cards_layout.addWidget(card, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        self.switch_page(0)

    def save_settings(self):
        idx = self.mic_combo.currentIndex()
        if idx >= 0:
            self.config["mic_index"] = self.mic_combo.itemData(idx)
        self.config["auto_play"] = self.autoplay_chk.isChecked()
        save_config(self.config)
        self.apply_background()
        self.hero_sub.setText(f"Presiona [{self.config.get('hotkey', 'f8').upper()}] para hablar o usa los botones.")

    def apply_background(self):
        bg_path = self.config.get("background_image")
        if bg_path and os.path.exists(bg_path):
            self.update_background_pixmap()
        else:
            self.bg_label.clear()
            self.centralWidget().setStyleSheet("QWidget#main_bg { background-color: #0F0F0F; }")

    def update_background_pixmap(self):
        bg_path = self.config.get("background_image")
        if not bg_path or not os.path.exists(bg_path): return
        
        pixmap = QPixmap(bg_path)
        if pixmap.isNull(): return

        # Lógica de "Aspect Ratio Fill" (Cover) referenciada al contenedor derecho
        s = self.right_container.size()
        if s.isEmpty(): return # Evitar crash si es demasiado chico
        
        scaled_pixmap = pixmap.scaled(s, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        # Recortar al centro
        x = (scaled_pixmap.width() - s.width()) // 2
        y = (scaled_pixmap.height() - s.height()) // 2
        final_pixmap = scaled_pixmap.copy(x, y, s.width(), s.height())
        
        self.bg_label.setPixmap(final_pixmap)
        self.bg_label.setGeometry(0, 0, s.width(), s.height())
        self.bg_label.lower()
        self.centralWidget().setStyleSheet("QWidget#main_bg { background-color: #0F0F0F; }")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'bg_label'):
            self.update_background_pixmap()
        if hasattr(self, 'cards_layout'):
            self.update_cards_grid()

    def choose_background_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen de Fondo", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            self.config["background_image"] = file_path
            self.save_settings()

    def remove_background_image(self):
        self.config["background_image"] = None
        self.save_settings()
        
    def save_hotkey(self):
        old_hk = self.config.get("hotkey", "f8")
        try: keyboard.remove_hotkey(old_hk)
        except: pass
        self.config["hotkey"] = self.hk_input.text()
        self.save_settings()
        try: keyboard.add_hotkey(self.config["hotkey"], self.on_hotkey_pressed)
        except: pass

    def trigger_manual_listen(self):
        if not self.is_listening and self.stt:
            threading.Thread(target=self.process_voice_command, daemon=True).start()
            
    def play_beep(self, beep_type="start"):
        def _beep():
            if beep_type == "start": winsound.Beep(1000, 150)
            elif beep_type == "end": winsound.Beep(800, 150)
            elif beep_type == "error": winsound.Beep(400, 300)
            elif beep_type == "success":
                winsound.Beep(600, 100); time.sleep(0.05); winsound.Beep(800, 150)
        threading.Thread(target=_beep, daemon=True).start()

    def on_hotkey_pressed(self):
        if self.is_listening or not self.stt: return
        threading.Thread(target=self.process_voice_command, daemon=True).start()
        
    def process_voice_command(self):
        self.is_listening = True
        try:
            self.signals.update_status.emit("Escuchando...", False)
            self.play_beep("start")
            
            mic_idx = self.config.get("mic_index")
            max_t = self.config.get("max_listen_time", 6)
            
            audio_file = record_audio(max_duration=max_t, device_index=mic_idx)
            self.play_beep("end")
            
            if not audio_file:
                self.signals.update_status.emit("Error de micrófono", True)
                return
                
            self.signals.update_status.emit("Procesando Voz...", False)
            text, conf = self.stt.transcribe(audio_file)
            
            if not text:
                self.signals.update_status.emit("No se detectó voz", True)
                self.play_beep("error")
                return
                
            if conf < 0.5:
                self.signals.update_status.emit(f"Baja confianza:\n'{text}'", True)
                self.play_beep("error")
                return
                
            self.signals.update_status.emit(f"Analizando...", False)
            query, is_playlist = parse_intent(text)
            self.signals.set_last_query.emit(query)
            
            if not query or len(query) < 2:
                self.signals.update_status.emit("No entendí el pedido.", True)
                self.play_beep("error")
                return
            
            tipo = "playlist" if is_playlist else "canción"
            self.signals.update_status.emit(f"Buscando {tipo}...", False)
            auto_play = self.config.get("auto_play", True)
            
            search_response = self.ytm.search_and_process(query, is_playlist=is_playlist)
            
            results = search_response.get("results")
            if not results:
                self.signals.update_status.emit("No se encontró nada en YT", True)
                log_history(text, query, "", False)
                return
                
            best_res = results[0]
            url = self.ytm.get_url(best_res)
            # USAR EL NOMBRE REAL DE LA CANCIÓN DEVUELTO POR YOUTUBE
            actual_title = best_res.get('title', 'Audio')
            
            if auto_play:
                self.signals.update_status.emit(f"Reproduciendo: {actual_title}", False)
                self.play_beep("success")
                log_history(text, actual_title, url, True)
                self.signals.play_url.emit(url)
            else:
                self.signals.update_status.emit("Elegí una opción.", False)
                self.signals.show_options.emit(results)
                log_history(text, query, "", True)
                
        except Exception as e:
            logging.error(f"Error: {e}")
            self.signals.update_status.emit("Error interno", True)
        finally:
            self.is_listening = False
            try:
                if os.path.exists("temp.wav"): os.remove("temp.wav")
            except: pass

if __name__ == "__main__":
    import ctypes
    try:
        myappid = u'myvoiceapp.ytmusic.version1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except: pass
        
    app = QApplication(sys.argv)
    window = VoiceMusicApp()
    window.show()
    sys.exit(app.exec())
