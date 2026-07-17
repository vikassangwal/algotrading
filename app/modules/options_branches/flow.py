import logging

logger = logging.getLogger("elco.module.options.flow")

class OptionsFlowEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            pcr_oi = self.data.get("pcr_oi")
            
            if pcr_oi is not None:
                if pcr_oi > 1.5:
                    score -= 0.15
                    reasons.append(f"Options Flow (PCR): PCR OI is {pcr_oi:.2f} (Extreme Overbought). Contrarian Bearish reversal likely.")
                elif pcr_oi > 1.1:
                    score += 0.2
                    reasons.append(f"Options Flow (PCR): PCR OI is {pcr_oi:.2f} (Bullish support base). Heavy Put writing detected.")
                elif pcr_oi < 0.6:
                    score += 0.15
                    reasons.append(f"Options Flow (PCR): PCR OI is {pcr_oi:.2f} (Extreme Oversold). Contrarian Bullish bounce likely.")
                elif pcr_oi < 0.9:
                    score -= 0.2
                    reasons.append(f"Options Flow (PCR): PCR OI is {pcr_oi:.2f} (Bearish resistance). Heavy Call writing detected.")

            oi_status = self.data.get("futures_oi_status")
            if oi_status is not None:
                if oi_status == "Long Buildup":
                    score += 0.25
                    reasons.append("Options Flow (OI): Strong Long Buildup in Futures (Bullish Institutional flow).")
                elif oi_status == "Short Cover":
                    score += 0.15
                    reasons.append("Options Flow (OI): Short Covering rally detected (Bears are trapping out).")
                elif oi_status == "Short Buildup":
                    score -= 0.25
                    reasons.append("Options Flow (OI): Strong Short Buildup in Futures (Bearish Institutional flow).")
                elif oi_status == "Long Unwind":
                    score -= 0.15
                    reasons.append("Options Flow (OI): Long Unwinding detected (Bulls are booking profits).")

            call_block_volume = self.data.get("call_block_volume")
            put_block_volume = self.data.get("put_block_volume")
            
            if call_block_volume is not None and put_block_volume is not None:
                if call_block_volume > put_block_volume * 1.5:
                    score += 0.2
                    reasons.append("Options Flow (Blocks): Massive Institutional Call Buying detected on the Ask.")
                elif put_block_volume > call_block_volume * 1.5:
                    score -= 0.2
                    reasons.append("Options Flow (Blocks): Massive Institutional Put Buying detected on the Ask.")

        except Exception as e:
            logger.error(f"Error in OptionsFlowEngine: {e}")
            reasons.append("Options Flow Engine: Error calculating PCR and OI flow.")

        return {
            "branch": "Options Flow & OI Analysis",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
