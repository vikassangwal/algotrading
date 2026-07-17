"""Valuation Analysis — price vs intrinsic value and multiples vs sector."""
import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.valuation")


class ValuationModule(AnalysisModule):
    name = "valuation"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            f = self.provider.get_fundamentals(symbol) or {}
            reasons = []
            score = 0.0

            ltp = None
            try:
                ltp = self.provider.get_quote(symbol).ltp
            except Exception:
                pass

            # --- DCF fair value vs current price ---
            dcf = f.get("dcf_fair_value")
            if dcf and ltp:
                upside = (float(dcf) - ltp) / ltp
                if upside > 0.10:
                    score += 0.35; reasons.append(f"Trades {upside*100:.0f}% below DCF fair value ({dcf})")
                elif upside < -0.10:
                    score -= 0.35; reasons.append(f"Trades {abs(upside)*100:.0f}% above DCF fair value ({dcf})")
                else:
                    reasons.append(f"Near DCF fair value ({dcf})")

            # --- PE vs sector ---
            pe = f.get("pe_ratio")
            sector = self.provider.get_sector_data("") or {}
            sec_pe = sector.get("sector_current_pe")
            sec_hist_pe = sector.get("sector_historical_pe")
            if pe and sec_pe:
                if pe < sec_pe * 0.85:
                    score += 0.25; reasons.append(f"PE {pe} cheaper than sector {sec_pe}")
                elif pe > sec_pe * 1.15:
                    score -= 0.25; reasons.append(f"PE {pe} pricier than sector {sec_pe}")
            if sec_pe and sec_hist_pe and sec_pe > sec_hist_pe * 1.2:
                score -= 0.1; reasons.append(f"Sector PE {sec_pe} stretched vs historical {sec_hist_pe}")

            # --- PB / EV-EBITDA sanity ---
            pb = f.get("pb_ratio")
            if pb is not None:
                if pb < 1.5:
                    score += 0.1; reasons.append(f"Low P/B {pb}")
                elif pb > 5:
                    score -= 0.15; reasons.append(f"High P/B {pb}")
            ev_ebitda = f.get("ev_ebitda")
            if ev_ebitda is not None and ev_ebitda < 8:
                score += 0.1; reasons.append(f"Reasonable EV/EBITDA {ev_ebitda}")

            if not reasons:
                return ModuleSignal(self.name, 0.0, 0.15, ["Insufficient valuation data."])

            confidence = 0.8 if (dcf and ltp) else 0.55
            return ModuleSignal(self.name, max(-1.0, min(1.0, score)), confidence, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
