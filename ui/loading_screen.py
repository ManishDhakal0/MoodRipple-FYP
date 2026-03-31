# ui/loading_screen.py
# Loading splash — frameless QWebEngineView showing web/loading.html

import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore    import Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWebChannel       import QWebChannel

from ui.bridge import AppBridge


class LoadingScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setFixedSize(460, 340)

        self._bridge  = AppBridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("bridge", self._bridge)

        self._view = QWebEngineView(self)
        self._view.page().setWebChannel(self._channel)
        self._view.settings().setAttribute(
            QWebEngineSettings.JavascriptEnabled, True)
        self._view.setContextMenuPolicy(Qt.NoContextMenu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        html_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "web", "loading.html")
        self._view.load(QUrl.fromLocalFile(html_path))

        self._center_on_screen()

    def set_status(self, text: str):
        self._bridge.loading_status.emit(text)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width()  // 2,
                geo.center().y() - self.height() // 2,
            )
