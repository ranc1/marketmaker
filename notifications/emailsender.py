import smtplib
from email.parser import Parser
import logging
from email.mime.text import MIMEText

GMAIL_SERVER = 'smtp.gmail.com'

# logger
log = logging.getLogger(__name__)


class EmailSender(object):
    def __init__(self, login, password):
        self.login = login
        self.password = password

    def send_email(self, email_template_file):
        with open(email_template_file) as fp:
            email = Parser().parse(fp)

        self.__send_email(email)

    def send_email_with_message(self, message, subject, from_address, to_address):
        email = MIMEText(message)
        email['Subject'] = subject
        email['From'] = from_address
        email['To'] = to_address

        self.__send_email(email)

    def __send_email(self, email):
        try:
            server = smtplib.SMTP_SSL(GMAIL_SERVER)
            server.ehlo()
            server.login(self.login, self.password)
            server.send_message(email)
            server.close()

            log.info("Email sent successfully.")
        except Exception as e:
            log.error("Failed to send email. Error: {}".format(e))
