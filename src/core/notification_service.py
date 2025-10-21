from PySide6.QtCore import QObject, Signal

class _NotificationService(QObject):
    """Serviço de notificação interno que usa o padrão Singleton."""
    _instance = None

    # Sinal que carrega a mensagem (str) e o tipo (str: 'success', 'info', 'warning', 'error')
    show_notification_signal = Signal(str, str)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = _NotificationService()
        return cls._instance

    def show(self, message: str, notification_type: str = 'success'):
        """Emite o sinal para mostrar a notificação."""
        self.show_notification_signal.emit(message, notification_type)

# Interface pública para o serviço
NotificationService = _NotificationService.get_instance()
