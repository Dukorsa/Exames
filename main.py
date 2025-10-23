import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from src.main_window import MainWindow
from src.core import database_manager as db
from src.core.theme import get_light_theme, apply_theme_to_stylesheet

def get_writable_data_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "data"
    return Path(__file__).resolve().parent / "data"

DATA_DIR = get_writable_data_dir()
LOG_FILE_PATH = DATA_DIR / "app.log"

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    STYLE_PATH = Path(sys._MEIPASS) / "assets" / "style.qss"
else:
    STYLE_PATH = Path(__file__).resolve().parent / "src" / "resources" / "styles" / "style.qss"

def setup_logging():
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE_PATH, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def load_stylesheet(path: Path) -> str:
    if not path.exists():
        logging.warning(f"Folha de estilos não encontrada em: {path}. Usando estilo padrão.")
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            qss_template = f.read()
        light_theme = get_light_theme()
        return apply_theme_to_stylesheet(qss_template, light_theme)
    except IOError as e:
        logging.error(f"Não foi possível ler a folha de estilos {path}: {e}")
        return ""

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setOrganizationName("GrupoNefron")
    app.setApplicationName("NefronApp Analisador")
    try:
        db.set_database_path(DATA_DIR)
        db.init_db()
        stylesheet = load_stylesheet(STYLE_PATH)
        if stylesheet:
            app.setStyleSheet(stylesheet)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"Ocorreu um erro fatal: {e}", exc_info=True)
        QMessageBox.critical(
            None,
            "Erro Crítico",
            f"Ocorreu um erro inesperado. Detalhes em:\n{LOG_FILE_PATH}"
        )
        sys.exit(1)

if __name__ == "__main__":
    setup_logging()
    main()