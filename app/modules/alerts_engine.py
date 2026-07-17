import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AlertsEngine:
    """
    Universal Alerts Engine for formatting and sending notifications.
    Currently supports Telegram and Email (SMTP) via stubs.
    """
    
    def __init__(self, telegram_token: Optional[str] = None, email_config: Optional[Dict[str, Any]] = None):
        self.telegram_token = telegram_token
        self.email_config = email_config or {}
        
    def format_alert(self, level: str, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Formats the alert message with a timestamp, level, and optional context."""
        timestamp = datetime.now().isoformat()
        formatted_message = f"[{timestamp}] [{level.upper()}] {message}"
        if context:
            formatted_message += f"\nContext: {context}"
        return formatted_message

    def send_telegram(self, chat_id: str, message: str) -> bool:
        """Send a Telegram message via the real Bot API (app.modules.alerts)."""
        if not self.telegram_token:
            logger.error("Telegram token not configured.")
            return False
        from .alerts import TelegramAlert
        ok = TelegramAlert(self.telegram_token, chat_id).send(message)
        if not ok:
            logger.error(f"Telegram send to {chat_id} failed.")
        return ok

    def send_email(self, to_address: str, subject: str, body: str) -> bool:
        """Send an email via real SMTP (app.modules.alerts.EmailAlert).

        Requires email_config with: smtp_server, smtp_port, sender_email,
        sender_password.
        """
        cfg = self.email_config
        required = ("smtp_server", "smtp_port", "sender_email", "sender_password")
        if not cfg or any(k not in cfg for k in required):
            logger.error(f"Email configuration incomplete; need {required}.")
            return False
        try:
            port = int(cfg["smtp_port"])  # env/JSON configs supply strings
        except (TypeError, ValueError):
            logger.error(f"Invalid smtp_port: {cfg['smtp_port']!r}")
            return False
        from .alerts import EmailAlert
        ok = EmailAlert(
            cfg["smtp_server"], port,
            cfg["sender_email"], cfg["sender_password"],
        ).send(to_address, subject, body)
        if not ok:
            logger.error(f"Email send to {to_address} failed.")
        return ok
        
    def dispatch_alert(self, level: str, message: str, channels: List[str], target_info: Dict[str, str], context: Optional[Dict[str, Any]] = None):
        """
        Dispatches an alert to the specified channels.
        """
        formatted_message = self.format_alert(level, message, context)
        
        for channel in channels:
            if channel.lower() == 'telegram':
                chat_id = target_info.get('chat_id')
                if chat_id:
                    self.send_telegram(chat_id, formatted_message)
                else:
                    logger.error("chat_id not found in target_info for telegram alert")
            elif channel.lower() == 'email':
                email_address = target_info.get('email')
                if email_address:
                    subject = f"Alert: {level.upper()} Notification"
                    self.send_email(email_address, subject, formatted_message)
                else:
                    logger.error("email not found in target_info for email alert")
            else:
                logger.warning(f"Unknown alert channel: {channel}")
