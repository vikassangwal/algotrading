import logging

logger = logging.getLogger("elco.module.risk.stress")

class StressTestingEngine:
    def __init__(self, risk_params: dict):
        self.params = risk_params

    def analyze(self, current_exposure: float) -> dict:
        result = {
            "approved": False,
            "reasons": []
        }
        
        try:
            crash_2008_impact = current_exposure * -0.55
            covid_crash_impact = current_exposure * -0.40
            
            max_stress_loss = self.params.get("max_stress_loss", 500000)
            
            if abs(crash_2008_impact) > max_stress_loss:
                result["reasons"].append(f"Stress Test FAILED: A 2008-style crash would cause ₹{abs(crash_2008_impact):,.2f} loss, destroying the fund limit (₹{max_stress_loss:,.2f}). De-leverage immediately.")
                return result
                
            result["reasons"].append(f"Historical Stress Test Passed: Portfolio survives a 2008/COVID style crash (Max Est. Impact: -₹{abs(crash_2008_impact):,.2f}).")

            # Removed mock random logic. Assuming passing if historical survives.
            result["approved"] = True

        except Exception as e:
            logger.error(f"Error in StressTestingEngine: {e}")
            result["reasons"].append("Stress Testing Engine: Error running simulations.")

        return result
