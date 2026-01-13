import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.services.service_locator import ServiceLocator
from src.views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # サービスロケータ初期化
    locator = ServiceLocator.get_instance()
    locator.register_defaults()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
