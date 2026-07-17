import smtplib
import urllib.request
import urllib.parse
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class TelegramAlert:
    """
    A class for sending alerts via Telegram using a bot.
    """
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send(self, message):
        """
        Sends a message to the specified Telegram chat.
        """
        data = urllib.parse.urlencode({
            'chat_id': self.chat_id,
            'text': message
        }).encode('utf-8')
        
        req = urllib.request.Request(self.api_url, data=data)
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('ok', False)
        except Exception as e:
            print(f"Error sending Telegram alert: {e}")
            return False


class EmailAlert:
    """
    A class for sending alerts via Email using SMTP.
    """
    def __init__(self, smtp_server, smtp_port, sender_email, sender_password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

    def send(self, recipient_email, subject, body):
        """
        Sends an email to the specified recipient.
        """
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            text = msg.as_string()
            server.sendmail(self.sender_email, recipient_email, text)
            server.quit()
            return True
        except Exception as e:
            print(f"Error sending Email alert: {e}")
            return False
