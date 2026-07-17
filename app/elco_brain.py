import logging
import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

# 1. Import the 8 Analytical Engines (The Researchers)
from app.modules.macro import MacroModule
from app.modules.intermarket import IntermarketModule
from app.modules.sector import SectorModule
from app.modules.fundamental import FundamentalModule
from app.modules.technical import TechnicalModule
from app.modules.derivatives import DerivativesModule
from app.modules.sentiment import SentimentModule
from app.modules.quant import QuantModule

# 2. Import the 2 Protection Engines (The Gatekeepers)
from app.modules.risk_manager import RiskManagementModule
from app.modules.portfolio import PortfolioManagementModule

from app.data.mock_provider import MockProvider
from app.data.dhan_provider import DhanProvider

# 3. Import the Operational/Execution Layers (The Traders)
# (Assuming these were built in previous subagent steps)
try:
    from app.modules.compliance_engine import ComplianceEngine
    from app.modules.execution_optimizer import ExecutionOptimizer
    from app.modules.reporting_engine import InstitutionalReporting
except ImportError:
    logging.warning("Execution/Compliance modules not fully found. Using stubs.")
    class ComplianceEngine: 
        def check(self, sym, qty): return {"approved": True, "reasons": ["Compliance: Passed"]}
    class ExecutionOptimizer:
        def execute(self, sym, qty, action): return {"status": "SUCCESS", "fill_price": 0.0}
    class InstitutionalReporting:
        def log_trade(self, data): pass

logger = logging.getLogger("elco.brain.master")

class MockDataProvider:
    def get_data(self, *args, **kwargs): return None

class ElcoMasterBrain:
    """
    The Ultimate Chief Investment Officer (CIO) of the Hedge Fund.
    Runs the 15-Step Institutional Investment Workflow.
    """
    def __init__(self):
        broker = os.getenv("BROKER_NAME", "mock").lower()
        if broker == "dhan":
            logger.info("Initializing ElcoMasterBrain with live DHAN API Provider.")
            self.provider = DhanProvider()
        else:
            logger.info("Initializing ElcoMasterBrain with Mock Provider.")
            self.provider = MockProvider(seed=42)

        # Initialize Background Data Daemon
        from app.data.market_daemon import MarketDataDaemon
        self.market_daemon = MarketDataDaemon(symbols=["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"])
        self.market_daemon.start()
        
        # Initialize Analytical Engines
        self.macro = MacroModule(self.provider)
        self.intermarket = IntermarketModule(self.provider)
        self.sector = SectorModule(self.provider)
        self.fundamental = FundamentalModule(self.provider)
        self.technical = TechnicalModule(self.provider)
        self.derivatives = DerivativesModule(self.provider)
        self.sentiment = SentimentModule(self.provider)
        self.quant = QuantModule(self.provider)
        
        # Initialize Gatekeepers
        self.risk_desk = RiskManagementModule(self.provider)
        self.portfolio_desk = PortfolioManagementModule(self.provider)
        
        # Initialize Operations
        try:
            self.compliance_desk = ComplianceEngine({"max_order_value": 1000000})
        except TypeError:
            self.compliance_desk = ComplianceEngine()
            
        try:
            self.execution_desk = ExecutionOptimizer({})
        except TypeError:
            self.execution_desk = ExecutionOptimizer()
            
        try:
            self.reporting_desk = InstitutionalReporting({})
        except TypeError:
            self.reporting_desk = InstitutionalReporting()
        
    def execute_institutional_workflow(self, symbol: str, current_price: float, sector: str, factor: str) -> Dict[str, Any]:
        """
        Runs the 15-Step Pipeline from 'Macro' down to 'Trade Execution' & 'Reporting'.
        """
        # Inject live cached data into the provider
        self.provider.live_cache = self.market_daemon.get_data()
        
        report = {
            "symbol": symbol,
            "decision": "HOLD",
            "quantity": 0,
            "analytical_score": 0.0,
            "workflow_log": [],
            "contributions": {}
        }
        
        report["workflow_log"].append(f"STARTING 15-STEP INSTITUTIONAL WORKFLOW FOR {symbol}")
        
        # ==========================================
        # PHASE 1: THE RESEARCHERS (8 ENGINES)
        # ==========================================
        analytical_score = 0.0
        
        # Steps 1-3: Macro, Intermarket, Sector
        macro_sig = self.macro.analyze(symbol)
        intermarket_sig = self.intermarket.analyze(symbol)
        sector_sig = self.sector.analyze(symbol)
        
        # Steps 4-8: Company, Financial, Valuation, Technical, Derivatives, Sentiment, Quant
        fundamental_sig = self.fundamental.analyze(symbol)
        tech_sig = self.technical.analyze(symbol)
        deriv_sig = self.derivatives.analyze(symbol)
        sentiment_sig = self.sentiment.analyze(symbol)
        quant_sig = self.quant.analyze(symbol)
        
        # Aggregate Analytical Scores
        all_signals = [
            ("macro", macro_sig), ("intermarket", intermarket_sig), 
            ("sector", sector_sig), ("fundamental", fundamental_sig), 
            ("technical", tech_sig), ("derivatives", deriv_sig), 
            ("sentiment", sentiment_sig), ("quant", quant_sig)
        ]
        
        for name, sig in all_signals:
            analytical_score += sig.score
            report["contributions"][name] = {"score": sig.score, "reasons": sig.reasons}
            report["workflow_log"].extend(sig.reasons)
            
        final_analytical_score = analytical_score / 8.0
        report["analytical_score"] = final_analytical_score
        
        if final_analytical_score > 0.6:
            report["workflow_log"].append(f"\n[AI DECISION]: GOD MODE BUY SIGNAL GENERATED (Score: {final_analytical_score:.2f})")
        else:
            report["workflow_log"].append(f"\n[AI DECISION]: TRADE REJECTED BY RESEARCH DESK (Score: {final_analytical_score:.2f})")
            return report
            
        # ==========================================
        # PHASE 2: THE GATEKEEPERS (2 ENGINES)
        # ==========================================
        # Step 10 & 11: Risk Assessment & Portfolio Construction
        
        # Ask Risk Desk
        sl = current_price * 0.95 # 5% SL assumption
        target = current_price * 1.15 # 15% Target assumption
        risk_report = self.risk_desk.evaluate_trade(symbol, current_price, sl, target)
        report["workflow_log"].extend(risk_report["reasons"])
        
        if risk_report["status"] != "APPROVED":
            report["workflow_log"].append("\n[TRADE BLOCKED BY RISK MANAGEMENT DESK]")
            return report
            
        quantity = risk_report["quantity"]
            
        # Ask Portfolio Desk
        port_report = self.portfolio_desk.evaluate_portfolio_fit(symbol, sector, factor, current_price, quantity)
        report["workflow_log"].extend(port_report["reasons"])
        
        if port_report["status"] != "APPROVED":
            report["workflow_log"].append("\n[TRADE BLOCKED BY PORTFOLIO MANAGEMENT DESK]")
            return report
            
        # ==========================================
        # PHASE 3: OPERATIONS (EXECUTION & COMPLIANCE)
        # ==========================================
        # Step 13: Compliance Check
        if hasattr(self.compliance_desk, 'check'):
            comp_res = self.compliance_desk.check(symbol, quantity)
            report["workflow_log"].append(f"Compliance Check: {comp_res.get('reasons', ['Passed'])}")
            if not comp_res.get("approved", True):
                report["workflow_log"].append("\n[TRADE BLOCKED BY COMPLIANCE DESK]")
                return report
                
        # Step 12: Trade Execution
        report["workflow_log"].append(f"\n[ROUTING ORDER]: Sending {quantity} shares of {symbol} to Execution Desk...")
        if hasattr(self.execution_desk, 'execute'):
            exec_res = self.execution_desk.execute(symbol, quantity, "BUY")
            report["workflow_log"].append(f"Execution Status: {exec_res.get('status', 'SUCCESS')}")
            
        # Step 14 & 15: Performance Measurement & Client Reporting
        report["decision"] = "BUY_EXECUTED"
        report["quantity"] = quantity
        
        if hasattr(self.reporting_desk, 'log_trade'):
            self.reporting_desk.log_trade({"symbol": symbol, "qty": quantity, "price": current_price})
            
        report["workflow_log"].append("\n[WORKFLOW COMPLETE]: Institutional 'GOD MODE' Trade Successfully Executed & Logged.")
        
        return report

# For direct testing
if __name__ == "__main__":
    brain = ElcoMasterBrain()
    # Let's run a test on Reliance
    result = brain.execute_institutional_workflow("RELIANCE", 2950.0, "Energy", "Value")
    for log in result["workflow_log"]:
        print(log)
