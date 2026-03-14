#!/usr/bin/env python
# main.py — MoodRipple entry point

import os
import sys

# Suppress TensorFlow noise before any imports
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

# Ensure working directory is always the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from ui.auth_window import AuthWindow
from ui.window import MainWindow


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
        win = MainWindow(user=user)
        win.logged_out.connect(lambda: _on_logout(win))
        win.show()
        _state["main"] = win

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
