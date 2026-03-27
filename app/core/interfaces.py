from abc import ABC, abstractmethod

class QueueProvider(ABC):
    @abstractmethod
    def send_message(self, payload: dict): pass
    @abstractmethod
    def receive_messages(self, max_number=1): pass
    @abstractmethod
    def delete_message(self, receipt_handle): pass