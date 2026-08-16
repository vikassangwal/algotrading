import threading
import uuid

_alerts = []
_lock = threading.Lock()

def add_alert(symbol: str, condition: str, price: float):
    with _lock:
        alert = {
            "id": str(uuid.uuid4()),
            "symbol": symbol.upper(),
            "condition": condition, # 'above' or 'below'
            "price": price,
            "triggered": False
        }
        _alerts.append(alert)
        return alert

def get_alerts():
    with _lock:
        return [a for a in _alerts if not a["triggered"]]

def check_alerts(live_cache):
    triggered = []
    with _lock:
        for alert in _alerts:
            if alert["triggered"]:
                continue
                
            quote = live_cache.get(alert["symbol"])
            if not quote:
                continue
                
            ltp = quote.get("price", 0)
            if ltp == 0:
                continue
                
            if alert["condition"] == "above" and ltp >= alert["price"]:
                alert["triggered"] = True
                triggered.append(alert)
            elif alert["condition"] == "below" and ltp <= alert["price"]:
                alert["triggered"] = True
                triggered.append(alert)
    return triggered

def remove_alert(alert_id: str):
    global _alerts
    with _lock:
        _alerts = [a for a in _alerts if a["id"] != alert_id]
