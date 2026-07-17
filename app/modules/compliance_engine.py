import datetime
import logging

class AuditTrail:
    def __init__(self, log_file='audit_trail.log'):
        self.logger = logging.getLogger('AuditTrail')
        self.logger.setLevel(logging.INFO)
        # Avoid adding multiple handlers if the logger already exists
        if not self.logger.handlers:
            fh = logging.FileHandler(log_file)
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def log_action(self, action, details):
        self.logger.info(f"Action: {action} | Details: {details}")

class ExchangeRules:
    @staticmethod
    def is_within_trading_hours(current_time=None):
        if current_time is None:
            current_time = datetime.datetime.now().time()
        
        # Defaulting to standard market hours, e.g., NSE
        start_time = datetime.time(9, 15)
        end_time = datetime.time(15, 30)
        
        return start_time <= current_time <= end_time

class ComplianceLimits:
    def __init__(self, max_order_value, max_daily_volume, allowed_symbols):
        self.max_order_value = max_order_value
        self.max_daily_volume = max_daily_volume
        self.allowed_symbols = set(allowed_symbols)
        self.current_daily_volume = 0.0

    def check_order(self, symbol, quantity, price):
        if symbol not in self.allowed_symbols:
            return False, f"Symbol {symbol} is not allowed."
        
        order_value = quantity * price
        if order_value > self.max_order_value:
            return False, f"Order value {order_value} exceeds max order value {self.max_order_value}."
        
        if self.current_daily_volume + order_value > self.max_daily_volume:
            return False, f"Order exceeds max daily volume {self.max_daily_volume}."
            
        return True, "Order is compliant."

    def update_volume(self, executed_value):
        self.current_daily_volume += executed_value

class ComplianceEngine:
    def __init__(self, limits: ComplianceLimits, audit_file='compliance.log'):
        self.limits = limits
        self.audit_trail = AuditTrail(audit_file)
        
    def validate_order(self, order_id, symbol, quantity, price):
        self.audit_trail.log_action("VALIDATING_ORDER", f"ID: {order_id}, Symbol: {symbol}, Qty: {quantity}, Price: {price}")
        
        if not ExchangeRules.is_within_trading_hours():
            msg = "Order rejected: Outside trading hours."
            self.audit_trail.log_action("ORDER_REJECTED", f"ID: {order_id} | Reason: {msg}")
            return False, msg
            
        is_compliant, msg = self.limits.check_order(symbol, quantity, price)
        if not is_compliant:
            self.audit_trail.log_action("ORDER_REJECTED", f"ID: {order_id} | Reason: {msg}")
            return False, msg
            
        self.audit_trail.log_action("ORDER_APPROVED", f"ID: {order_id}")
        return True, "Order approved."
        
    def record_execution(self, order_id, executed_quantity, executed_price):
        executed_value = executed_quantity * executed_price
        self.limits.update_volume(executed_value)
        self.audit_trail.log_action("ORDER_EXECUTED", f"ID: {order_id}, Executed Value: {executed_value}, Total Daily Vol: {self.limits.current_daily_volume}")
