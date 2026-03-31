#!/usr/bin/env python
# main.py — MoodRipple entry point

import os
import sys

# Suppress TensorFlow noise before any imports
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

# ── CRITICAL: import TensorFlow BEFORE PyQt5 ──────────────────────────────────
# On Windows, PyQt5 loads DLLs (Qt multimedia etc.) that conflict with TF's
# native runtime when TF is imported afterwards.  Importing TF first lets its
# DLLs initialise cleanly, and PyQt5 coexists fine after that.
try:
    import tensorflow as _tf  # noqa: F401
    print(f"[main] TensorFlow {_tf.__version__} pre-loaded OK.", flush=True)
except Exception as _e:
    print(f"[main] TF pre-load failed: {_e}", flush=True)

# Ensure working directory is always the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon

from ui.auth_window import AuthWindow
from ui.window import MainWindow
from ui.loading_screen import LoadingScreen


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MoodRipple")
    app.setOrganizationName("FYP")

    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Keep a reference so GC doesn't collect windows
    _state = {}

    def _launch_main(user: dict, remember: bool):
        _state["auth"].hide()

        loader = LoadingScreen()
        loader.show()
        _state["loader"] = loader

        def _build():
            loader.set_status("Building interface…")
            QApplication.processEvents()

            win = MainWindow(user=user)

            loader.set_status("Almost ready…")
            QApplication.processEvents()

            win.logged_out.connect(lambda: _on_logout(win))
            win.show()
            _state["main"] = win

            loader.close()
            _state.pop("loader", None)

        # Delay by 60 ms so the loader has time to paint before heavy work starts
        QTimer.singleShot(60, _build)

    def _on_logout(win: MainWindow):
        win.close()
        _state.pop("main", None)
        auth = AuthWindow()
        auth.logged_in.connect(lambda u, r: _launch_main(u, r))
        auth.show()
        _state["auth"] = auth

    auth = AuthWindow()
    auth.logged_in.connect(lambda u, r: _launch_main(u, r))
    auth.show()
    _state["auth"] = auth

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
