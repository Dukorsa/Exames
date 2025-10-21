import sys
import os
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from src.main_window import MainWindow
from src.core import database_manager as db

def get_app_root() -> Path:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).resolve().parent

def get_writable_data_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "data"
    else:
        return Path(__file__).resolve().parent / "data"

DATA_DIR = get_writable_data_dir()
LOG_FILE_PATH = DATA_DIR / "app.log"

APP_ROOT = get_app_root()
STYLE_PATH = APP_ROOT / "assets" / "style.qss"


def setup_logging():
    """Configura o sistema de logging para registrar em arquivo e no console."""
    DATA_DIR.mkdir(exist_ok=True, parents=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE_PATH, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Logger configurado.")


def load_stylesheet(path: Path) -> str:
    """Carrega a folha de estilos de um arquivo."""
    if not path.exists():
        logging.warning(f"Folha de estilos não encontrada em: {path}. Usando estilo padrão.")
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except IOError as e:
        logging.error(f"Não foi possível ler a folha de estilos {path}: {e}")
        return ""


def main():
    """Função principal que inicializa e executa a aplicação."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setOrganizationName("GrupoNefron")
    app.setApplicationName("NefronApp Analisador")

    try:
        db.set_database_path(DATA_DIR)
        
        logging.info("Garantindo a inicialização do banco de dados...")
        db.init_db()
        logging.info("Banco de dados inicializado com sucesso.")
        
        stylesheet = load_stylesheet(STYLE_PATH)
        if stylesheet:
            app.setStyleSheet(stylesheet)
            logging.info("Folha de estilos aplicada com sucesso.")
        else:
            logging.warning("Nenhuma folha de estilos foi aplicada.")

        logging.info("Instanciando a janela principal.")
        window = MainWindow()
        window.show()
        logging.info("Iniciando o loop de eventos da aplicação.")
        sys.exit(app.exec())

    except Exception as e:
        logging.critical(f"Ocorreu um erro fatal e a aplicação será encerrada: {e}", exc_info=True)
        try:
            DATA_DIR.mkdir(exist_ok=True, parents=True)
        except Exception as dir_e:
            print(f"Não foi possível criar o diretório de dados para o log de erro: {dir_e}")

        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setWindowTitle("Erro Crítico")
        error_box.setText("Ocorreu um erro inesperado e a aplicação não pode continuar.")
        error_box.setInformativeText(f"Detalhes do erro foram salvos em:\n{LOG_FILE_PATH}")
        error_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        error_box.exec()
        sys.exit(1)


if __name__ == "__main__":
    setup_logging()
    main()