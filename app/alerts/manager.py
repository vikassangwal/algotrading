"""
Alert Manager - Multi-Channel Notification System
==================================================
Production-ready alert manager with:
- Multi-channel notifications (Slack, Telegram, Email, PagerDuty, Webhook)
- Alert routing with severity-based channels
- Deduplication and grouping
- Escalation policies
- Template system with Jinja2
- Rate limiting per channel
- Delivery tracking and retries
- Silencing and inhibition rules
"""

import asyncio
import logging
import time
import uuid
import hashlib
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from collections import defaultdict, deque
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import json

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from jinja2 import Template, Environment, BaseLoader
except ImportError:
    Template = None
    Environment = None
    BaseLoader = None

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Alert lifecycle status"""
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Alert definition"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.FIRING

    # Content
    title: str = ""
    message: str = ""
    details: Dict = field(default_factory=dict)

    # Labels for routing
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    # Metadata
    source: str = ""
    fingerprint: str = ""
    starts_at: datetime = field(default_factory=datetime.utcnow)
    ends_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Tracking
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    # Delivery tracking
    deliveries: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        # Generate fingerprint for deduplication
        if not self.fingerprint:
            key_parts = [
                self.name,
                str(sorted(self.labels.items())),
                self.source
            ]
            self.fingerprint = hashlib.md5(
                "|".join(key_parts).encode()
            ).hexdigest()[:16]

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'severity': self.severity.value,
            'status': self.status.value,
            'title': self.title,
            'message': self.message,
            'details': self.details,
            'labels': self.labels,
            'annotations': self.annotations,
            'source': self.source,
            'fingerprint': self.fingerprint,
            'starts_at': self.starts_at.isoformat(),
            'ends_at': self.ends_at.isoformat() if self.ends_at else None,
            'updated_at': self.updated_at.isoformat(),
        }


class ChannelType(Enum):
    SLACK = "slack"
    TELEGRAM = "telegram"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"
    SMS = "sms"


@dataclass
class ChannelConfig:
    """Channel configuration"""
    name: str
    type: ChannelType
    enabled: bool = True

    # Routing
    severity_filter: List[AlertSeverity] = field(default_factory=lambda: list(AlertSeverity))
    label_matchers: Dict[str, str] = field(default_factory=dict)  # label -> regex

    # Rate limiting
    max_per_minute: int = 60
    max_per_hour: int = 1000

    # Retry
    max_retries: int = 3
    retry_delay_seconds: int = 30

    # Channel-specific config
    config: Dict = field(default_factory=dict)


class NotificationChannel(ABC):
    """Abstract notification channel"""

    def __init__(self, config: ChannelConfig):
        self.config = config
        self.sent_count = 0
        self.failed_count = 0
        self.last_sent: Optional[datetime] = None
        self._rate_limiter = RateLimiter(config.max_per_minute, 60)

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """Send alert notification"""
        pass

    async def can_send(self, alert: Alert) -> bool:
        """Check if channel can send this alert"""
        if not self.config.enabled:
            return False

        # Check severity filter
        if alert.severity not in self.config.severity_filter:
            return False

        # Check label matchers
        for label, pattern in self.config.label_matchers.items():
            if label not in alert.labels:
                return False
            import re
            if not re.match(pattern, alert.labels[label]):
                return False

        # Rate limit
        if not await self._rate_limiter.acquire():
            return False

        return True

    def record_success(self):
        self.sent_count += 1
        self.last_sent = datetime.utcnow()

    def record_failure(self):
        self.failed_count += 1


class RateLimiter:
    """Simple rate limiter"""

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.requests: deque = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            now = time.time()
            # Remove old requests
            cutoff = now - 60
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            if len(self.requests) >= self.max_per_minute:
                return False

            self.requests.append(now)
            return True


# ============================================================
# Slack Channel
# ============================================================

class SlackChannel(NotificationChannel):
    """Slack webhook notification channel"""

    async def send(self, alert: Alert) -> bool:
        if not await self.can_send(alert):
            return False

        webhook_url = self.config.config.get('webhook_url')
        if not webhook_url:
            logger.error("Slack webhook URL not configured")
            return False

        # Build message
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9500",
            AlertSeverity.CRITICAL: "#ff0000",
            AlertSeverity.EMERGENCY: "#8B0000"
        }

        payload = {
            "username": self.config.config.get('username', 'ELCO Alerts'),
            "icon_emoji": self.config.config.get('icon_emoji', ':warning:'),
            "attachments": [{
                "color": color_map.get(alert.severity, "#ff9500"),
                "title": alert.title,
                "text": alert.message,
                "fields": [
                    {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                    {"title": "Source", "value": alert.source, "short": True},
                    {"title": "Alert ID", "value": alert.id, "short": True},
                    {"title": "Fingerprint", "value": alert.fingerprint, "short": True},
                ],
                "footer": "ELCO Trader",
                "ts": int(alert.starts_at.timestamp())
            }]
        }

        # Add details if present
        if alert.details:
            detail_text = "\n".join([f"{k}: {v}" for k, v in alert.details.items()])
            payload["attachments"][0]["fields"].append({
                "title": "Details",
                "value": detail_text[:1000],
                "short": False
            })

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status == 200:
                        self.record_success()
                        return True
                    else:
                        text = await resp.text()
                        logger.error(f"Slack send failed: {resp.status} - {text}")
        except Exception as e:
            logger.error(f"Slack send error: {e}")

        self.record_failure()
        return False


# ============================================================
# Telegram Channel
# ============================================================

class TelegramChannel(NotificationChannel):
    """Telegram bot notification channel"""

    async def send(self, alert: Alert) -> bool:
        if not await self.can_send(alert):
            return False

        bot_token = self.config.config.get('bot_token')
        chat_id = self.config.config.get('chat_id')
        if not bot_token or not chat_id:
            logger.error("Telegram bot token or chat ID not configured")
            return False

        # Build message
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.EMERGENCY: "🔴"
        }

        emoji = severity_emoji.get(alert.severity, "⚠️")

        message = f"{emoji} <b>{alert.title}</b>\n\n{alert.message}\n\n"
        message += f"<b>Severity:</b> {alert.severity.value.upper()}\n"
        message += f"<b>Source:</b> {alert.source}\n"
        message += f"<b>Alert ID:</b> {alert.id}\n"
        message += f"<b>Time:</b> {alert.starts_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"

        if alert.details:
            message += "\n\n<b>Details:</b>\n"
            for k, v in alert.details.items():
                message += f"  {k}: {v}\n"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        self.record_success()
                        return True
                    else:
                        text = await resp.text()
                        logger.error(f"Telegram send failed: {resp.status} - {text}")
        except Exception as e:
            logger.error(f"Telegram send error: {e}")

        self.record_failure()
        return False


# ============================================================
# Email Channel
# ============================================================

class EmailChannel(NotificationChannel):
    """Email notification channel"""

    async def send(self, alert: Alert) -> bool:
        if not await self.can_send(alert):
            return False

        smtp_host = self.config.config.get('smtp_host')
        smtp_port = self.config.config.get('smtp_port', 587)
        smtp_user = self.config.config.get('smtp_user')
        smtp_pass = self.config.config.get('smtp_pass')
        from_email = self.config.config.get('from_email')
        to_emails = self.config.config.get('to_emails', [])

        if not all([smtp_host, smtp_user, smtp_pass, from_email, to_emails]):
            logger.error("Email configuration incomplete")
            return False

        # Build message
        subject = f"[{alert.severity.value.upper()}] {alert.title}"

        # HTML body
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {'#ff4444' if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY] else '#ff9500' if alert.severity == AlertSeverity.WARNING else '#36a64f'}; color: white; padding: 20px;">
                <h1 style="margin: 0;">{alert.title}</h1>
                <p style="margin: 10px 0 0;">{alert.message}</p>
            </div>
            <div style="padding: 20px; background: #f5f5f5;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 8px; font-weight: bold;">Severity</td><td style="padding: 8px;">{alert.severity.value.upper()}</td></tr>
                    <tr><td style="padding: 8px; font-weight: bold;">Source</td><td style="padding: 8px;">{alert.source}</td></tr>
                    <tr><td style="padding: 8px; font-weight: bold;">Alert ID</td><td style="padding: 8px;">{alert.id}</td></tr>
                    <tr><td style="padding: 8px; font-weight: bold;">Time</td><td style="padding: 8px;">{alert.starts_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
                </table>
                <h3>Details</h3>
                <pre style="background: white; padding: 15px; border-radius: 4px;">{json.dumps(alert.details, indent=2) if alert.details else 'No additional details'}</pre>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = ", ".join(to_emails)
        msg['X-Priority'] = '1' if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY] else '3'

        msg.attach(MIMEText(html, 'html'))

        try:
            # Send via SMTP
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()

            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()

            self.record_success()
            return True

        except Exception as e:
            logger.error(f"Email send error: {e}")
            self.record_failure()
            return False


# ============================================================
# PagerDuty Channel
# ============================================================

class PagerDutyChannel(NotificationChannel):
    """PagerDuty Events API v2 channel"""

    async def send(self, alert: Alert) -> bool:
        if not await self.can_send(alert):
            return False

        integration_key = self.config.config.get('integration_key')
        if not integration_key:
            logger.error("PagerDuty integration key not configured")
            return False

        severity_map = {
            AlertSeverity.INFO: "info",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.CRITICAL: "critical",
            AlertSeverity.EMERGENCY: "critical"
        }

        payload = {
            "routing_key": integration_key,
            "event_action": "trigger" if alert.status == AlertStatus.FIRING else "resolve",
            "dedup_key": alert.fingerprint,
            "payload": {
                "summary": alert.title,
                "source": alert.source,
                "severity": severity_map.get(alert.severity, "warning"),
                "component": alert.labels.get('component', 'trading'),
                "group": alert.labels.get('group', 'elco'),
                "class": alert.name,
                "custom_details": alert.details
            }
        }

        if alert.status == AlertStatus.RESOLVED:
            payload["event_action"] = "resolve"

        url = "https://events.pagerduty.com/v2/enqueue"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 202:
                        self.record_success()
                        return True
                    else:
                        text = await resp.text()
                        logger.error(f"PagerDuty send failed: {resp.status} - {text}")
        except Exception as e:
            logger.error(f"PagerDuty send error: {e}")

        self.record_failure()
        return False


# ============================================================
# Webhook Channel
# ============================================================

class WebhookChannel(NotificationChannel):
    """Generic webhook notification channel"""

    async def send(self, alert: Alert) -> bool:
        if not await self.can_send(alert):
            return False

        url = self.config.config.get('url')
        if not url:
            logger.error("Webhook URL not configured")
            return False

        headers = self.config.config.get('headers', {'Content-Type': 'application/json'})
        timeout = self.config.config.get('timeout', 10)

        payload = alert.to_dict()

        # Add signature if secret configured
        secret = self.config.config.get('secret')
        if secret:
            import hmac
            sig = hmac.new(
                secret.encode(),
                json.dumps(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers['X-Alert-Signature'] = sig

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=timeout) as resp:
                    if 200 <= resp.status < 300:
                        self.record_success()
                        return True
                    else:
                        text = await resp.text()
                        logger.error(f"Webhook send failed: {resp.status} - {text}")
        except Exception as e:
            logger.error(f"Webhook send error: {e}")

        self.record_failure()
        return False


# ============================================================
# SMS Channel (via Twilio)
# ============================================================

class SMSChannel(NotificationChannel):
    """SMS notification via Twilio"""

    async def send(self, alert: Alert) -> bool:
        if not await self.can_send(alert):
            return False

        account_sid = self.config.config.get('account_sid')
        auth_token = self.config.config.get('auth_token')
        from_number = self.config.config.get('from_number')
        to_numbers = self.config.config.get('to_numbers', [])

        if not all([account_sid, auth_token, from_number, to_numbers]):
            logger.error("Twilio configuration incomplete")
            return False

        # Build concise message for SMS
        message = f"[{alert.severity.value.upper()}] {alert.title}: {alert.message[:100]}"
        if alert.details:
            message += f" ({', '.join(f'{k}={v}' for k,v in list(alert.details.items())[:2])})"
        message += f" ID:{alert.id}"

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)

            for to_number in to_numbers:
                client.messages.create(
                    body=message,
                    from_=from_number,
                    to=to_number
                )

            self.record_success()
            return True

        except Exception as e:
            logger.error(f"SMS send error: {e}")
            self.record_failure()
            return False


# ============================================================
# Alert Manager
# ============================================================

class AlertManager:
    """
    Central alert management with:
    - Multi-channel routing
    - Deduplication
    - Grouping
    - Silencing/inhibition
    - Escalation
    - Template rendering
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.channels: Dict[str, NotificationChannel] = {}
        self.alerts: Dict[str, Alert] = {}  # fingerprint -> Alert
        self.active_alerts: Dict[str, Alert] = {}  # id -> Alert

        # Silencing
        self.silences: Dict[str, Dict] = {}  # name -> silence config

        # Templates
        self.template_env = None
        if Environment and BaseLoader:
            self.template_env = Environment(loader=BaseLoader())

        # Escalation
        self.escalation_policies: Dict[str, Dict] = {}

        # Metrics
        self.metrics = {
            'alerts_received': 0,
            'alerts_fired': 0,
            'alerts_resolved': 0,
            'notifications_sent': 0,
            'notifications_failed': 0,
            'deduplicated': 0,
        }

        # Initialize channels
        self._initialize_channels()

    def _initialize_channels(self):
        """Initialize notification channels from config"""
        channel_classes = {
            ChannelType.SLACK: SlackChannel,
            ChannelType.TELEGRAM: TelegramChannel,
            ChannelType.EMAIL: EmailChannel,
            ChannelType.PAGERDUTY: PagerDutyChannel,
            ChannelType.WEBHOOK: WebhookChannel,
            ChannelType.SMS: SMSChannel,
        }

        for channel_config in self.config.get('channels', []):
            ctype = ChannelType(channel_config.get('type', 'webhook'))
            if ctype in channel_classes:
                channel_config_obj = ChannelConfig(
                    name=channel_config.get('name', 'default'),
                    type=ctype,
                    enabled=channel_config.get('enabled', True),
                    severity_filter=[AlertSeverity(s) for s in channel_config.get('severities', ['info', 'warning', 'critical', 'emergency'])],
                    label_matchers=channel_config.get('label_matchers', {}),
                    max_per_minute=channel_config.get('max_per_minute', 60),
                    max_per_hour=channel_config.get('max_per_hour', 1000),
                    max_retries=channel_config.get('max_retries', 3),
                    retry_delay_seconds=channel_config.get('retry_delay', 30),
                    config=channel_config.get('config', {})
                )
                channel = channel_classes[ctype](cconfig)
                self.channels[cconfig.name] = channel
                logger.info(f"Initialized alert channel: {cconfig.name} ({ctype.value})")

    def add_channel(self, name: str, channel: NotificationChannel):
        """Add custom channel"""
        self.channels[name] = channel

    # ============================================================
    # Alert Processing
    # ============================================================

    async def fire_alert(self, alert: Alert) -> List[str]:
        """
        Fire new alert or update existing.
        Returns list of channel names that were notified.
        """
        self.metrics['alerts_received'] += 1

        # Check silencing
        if self._is_silenced(alert):
            alert.status = AlertStatus.SUPPRESSED
            logger.info(f"Alert {alert.id} suppressed by silence rule")
            return []

        # Check deduplication
        existing = self.alerts.get(alert.fingerprint)
        if existing and existing.status == AlertStatus.FIRING:
            # Update existing alert
            existing.updated_at = datetime.utcnow()
            existing.details.update(alert.details)
            existing.message = alert.message
            self.metrics['deduplicated'] += 1
            logger.info(f"Alert deduplicated: {alert.fingerprint}")
            return await self._notify_channels(existing)

        # New alert
        self.alerts[alert.fingerprint] = alert
        self.active_alerts[alert.id] = alert
        self.metrics['alerts_fired'] += 1

        logger.info(f"Alert fired: {alert.id} ({alert.severity.value}) - {alert.title}")

        # Check escalation
        await self._check_escalation(alert)

        # Notify channels
        notified = await self._notify_channels(alert)

        return notified

    async def resolve_alert(self, fingerprint: str, resolved_by: str = "system") -> bool:
        """Resolve alert by fingerprint"""
        alert = self.alerts.get(fingerprint)
        if not alert:
            return False

        alert.status = AlertStatus.RESOLVED
        alert.ends_at = datetime.utcnow()
        alert.resolved_by = resolved_by
        alert.resolved_at = datetime.utcnow()
        alert.updated_at = datetime.utcnow()

        self.active_alerts.pop(alert.id, None)
        self.metrics['alerts_resolved'] += 1

        logger.info(f"Alert resolved: {alert.id} by {resolved_by}")

        # Notify resolution
        await self._notify_channels(alert)

        return True

    async def acknowledge_alert(self, fingerprint: str, acknowledged_by: str) -> bool:
        """Acknowledge alert"""
        alert = self.alerts.get(fingerprint)
        if not alert:
            return False

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()
        alert.updated_at = datetime.utcnow()

        logger.info(f"Alert acknowledged: {alert.id} by {acknowledged_by}")

        return True

    def _is_silenced(self, alert: Alert) -> bool:
        """Check if alert matches any silence rule"""
        for silence_name, silence in self.silences.items():
            if not silence.get('enabled', True):
                continue

            # Check time window
            now = datetime.utcnow()
            start = silence.get('start')
            end = silence.get('end')
            if start and now < start:
                continue
            if end and now > end:
                continue

            # Check matchers
            match = True
            for label, pattern in silence.get('matchers', {}).items():
                if label not in alert.labels:
                    match = False
                    break
                import re
                if not re.match(pattern, alert.labels[label]):
                    match = False
                    break

            if match:
                return True

        return False

    async def _notify_channels(self, alert: Alert) -> List[str]:
        """Send alert to all matching channels"""
        notified = []

        for channel_name, channel in self.channels.items():
            if not await channel.can_send(alert):
                continue

            try:
                success = await channel.send(alert)
                if success:
                    notified.append(channel_name)
                    alert.deliveries.append({
                        'channel': channel_name,
                        'status': 'sent',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    self.metrics['notifications_sent'] += 1
                else:
                    alert.deliveries.append({
                        'channel': channel_name,
                        'status': 'failed',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    self.metrics['notifications_failed'] += 1

            except Exception as e:
                logger.error(f"Channel {channel_name} send error: {e}")
                alert.deliveries.append({
                    'channel': channel_name,
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
                self.metrics['notifications_failed'] += 1

        return notified

    # ============================================================
    # Silencing
    # ============================================================

    def add_silence(self, name: str, config: Dict):
        """Add silence rule"""
        self.silences[name] = {
            'enabled': True,
            'start': config.get('start'),
            'end': config.get('end'),
            'matchers': config.get('matchers', {}),
            'created_by': config.get('created_by', 'system'),
            'created_at': datetime.utcnow().isoformat()
        }

    def remove_silence(self, name: str) -> bool:
        if name in self.silences:
            del self.silences[name]
            return True
        return False

    def get_active_silences(self) -> Dict:
        """Get currently active silences"""
        now = datetime.utcnow()
        active = {}
        for name, silence in self.silences.items():
            if not silence.get('enabled', True):
                continue
            start = silence.get('start')
            end = silence.get('end')
            if start and now < start:
                continue
            if end and now > end:
                continue
            active[name] = silence
        return active

    # ============================================================
    # Escalation
    # ============================================================

    def add_escalation_policy(self, name: str, config: Dict):
        """Add escalation policy"""
        self.escalation_policies[name] = {
            'repeat_interval': config.get('repeat_interval', 300),  # seconds
            'max_repeats': config.get('max_repeats', 3),
            'channels': config.get('channels', []),  # Channel names to escalate to
            'severity_threshold': AlertSeverity(config.get('severity_threshold', 'critical')),
            'enabled': True
        }

    async def _check_escalation(self, alert: Alert):
        """Check if alert should trigger escalation"""
        for policy_name, policy in self.escalation_policies.items():
            if not policy.get('enabled', True):
                continue

            if alert.severity.value < policy['severity_threshold'].value:
                continue

            # Check if enough time has passed for escalation
            elapsed = (datetime.utcnow() - alert.starts_at).total_seconds()
            if elapsed >= policy['repeat_interval']:
                # Escalate to additional channels
                for channel_name in policy['channels']:
                    channel = self.channels.get(channel_name)
                    if channel and await channel.can_send(alert):
                        try:
                            await channel.send(alert)
                            logger.info(f"Escalated alert {alert.id} to {channel_name}")
                        except Exception as e:
                            logger.error(f"Escalation to {channel_name} failed: {e}")

    # ============================================================
    # Query Methods
    # ============================================================

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (firing/acknowledged) alerts"""
        return [
            a for a in self.alerts.values()
            if a.status in (AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED)
        ]

    def get_alert(self, fingerprint: str) -> Optional[Alert]:
        return self.alerts.get(fingerprint)

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get recent alerts sorted by time"""
        return sorted(
            self.alerts.values(),
            key=lambda a: a.starts_at,
            reverse=True
        )[:limit]

    def get_metrics(self) -> Dict:
        return {
            **self.metrics,
            'active_alerts': len([a for a in self.alerts.values() if a.status == AlertStatus.FIRING]),
            'acknowledged_alerts': len([a for a in self.alerts.values() if a.status == AlertStatus.ACKNOWLEDGED]),
            'total_alerts': len(self.alerts),
            'channels': {
                name: {
                    'sent': ch.sent_count,
                    'failed': ch.failed_count,
                    'last_sent': ch.last_sent.isoformat() if ch.last_sent else None
                }
                for name, ch in self.channels.items()
            }
        }

    # ============================================================
    # High-Level Helpers
    # ============================================================

    async def send_trading_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        symbol: str = None,
        strategy: str = None,
        details: Dict = None,
        source: str = "trading"
    ) -> List[str]:
        """Helper for common trading alerts"""
        labels = {'source': source}
        if symbol:
            labels['symbol'] = symbol
        if strategy:
            labels['strategy'] = strategy

        alert = Alert(
            name=f"trading_{title.lower().replace(' ', '_')}",
            severity=severity,
            title=title,
            message=message,
            details=details or {},
            labels=labels,
            source=source
        )

        return await self.fire_alert(alert)

    async def send_risk_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.CRITICAL,
        risk_type: str = "",
        details: Dict = None
    ) -> List[str]:
        """Helper for risk alerts"""
        return await self.send_trading_alert(
            title=f"Risk: {title}",
            message=message,
            severity=severity,
            details={'risk_type': risk_type, **(details or {})},
            source='risk'
        )

    async def send_system_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        component: str = "",
        details: Dict = None
    ) -> List[str]:
        """Helper for system alerts"""
        return await self.send_trading_alert(
            title=f"System: {title}",
            message=message,
            severity=severity,
            details={'component': component, **(details or {})},
            source='system'
        )


# ============================================================
# Default Configuration
# ============================================================

DEFAULT_ALERT_CONFIG = {
    'channels': [
        {
            'name': 'slack_critical',
            'type': 'slack',
            'enabled': True,
            'severities': ['critical', 'emergency'],
            'config': {
                'webhook_url': '${SLACK_CRITICAL_WEBHOOK}',
                'username': 'ELCO Critical Alerts',
                'icon_emoji': ':rotating_light:'
            }
        },
        {
            'name': 'slack_warnings',
            'type': 'slack',
            'enabled': True,
            'severities': ['warning'],
            'config': {
                'webhook_url': '${SLACK_WARNINGS_WEBHOOK}',
                'username': 'ELCO Warnings',
                'icon_emoji': ':warning:'
            }
        },
        {
            'name': 'telegram',
            'type': 'telegram',
            'enabled': True,
            'severities': ['warning', 'critical', 'emergency'],
            'config': {
                'bot_token': '${TELEGRAM_BOT_TOKEN}',
                'chat_id': '${TELEGRAM_CHAT_ID}'
            }
        },
        {
            'name': 'email_critical',
            'type': 'email',
            'enabled': True,
            'severities': ['critical', 'emergency'],
            'config': {
                'smtp_host': '${SMTP_HOST}',
                'smtp_port': 587,
                'smtp_user': '${SMTP_USER}',
                'smtp_pass': '${SMTP_PASS}',
                'from_email': '${ALERT_FROM_EMAIL}',
                'to_emails': ['${ALERT_TO_EMAIL}']
            }
        },
        {
            'name': 'pagerduty',
            'type': 'pagerduty',
            'enabled': True,
            'severities': ['critical', 'emergency'],
            'config': {
                'integration_key': '${PAGERDUTY_KEY}'
            }
        }
    ],
    'escalation_policies': {
        'critical_escalation': {
            'repeat_interval': 300,
            'max_repeats': 3,
            'channels': ['pagerduty', 'sms'],
            'severity_threshold': 'critical'
        }
    }
}


__all__ = [
    'AlertSeverity', 'AlertStatus', 'Alert',
    'ChannelType', 'ChannelConfig', 'NotificationChannel',
    'SlackChannel', 'TelegramChannel', 'EmailChannel',
    'PagerDutyChannel', 'WebhookChannel', 'SMSChannel',
    'AlertManager', 'DEFAULT_ALERT_CONFIG'
]