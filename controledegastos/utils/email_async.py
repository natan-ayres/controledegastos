import threading
from django.core.mail import send_mail

class EmailThread(threading.Thread):
    def __init__(self, assunto, mensagem, remetente, destinatarios, fail_silently=False):
        self.assunto = assunto
        self.mensagem = mensagem
        self.remetente = remetente
        self.destinatarios = destinatarios
        self.fail_silently = fail_silently
        threading.Thread.__init__(self)

    def run(self):
        send_mail(
            self.assunto,
            self.mensagem,
            self.remetente,
            self.destinatarios,
            fail_silently=self.fail_silently,
        )