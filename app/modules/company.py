import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.company")


def _num(value, default=None):
    """Coerce provider values to float, tolerating None/strings/bools."""
    if value is None or isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class CompanyModule(AnalysisModule):
    """Business-quality read of a company from its fundamentals.

    Rewards durable, growing, cash-generative businesses run by aligned,
    unlevered promoters; penalises debt, promoter pledging and decay.
    """

    name = "company"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            fund = self.provider.get_fundamentals(symbol)
            if not isinstance(fund, dict):
                fund = {}

            score = 0.0
            reasons = []
            used = 0  # number of pillars that had real data (drives confidence)

            # --- 1. Profitability: Return on Equity -------------------------
            net_income = _num(fund.get("net_income"))
            equity = _num(fund.get("shareholder_equity"))
            if net_income is not None and equity is not None and equity > 0:
                roe = net_income / equity
                used += 1
                if roe >= 0.20:
                    score += 0.28
                    reasons.append(f"Elite ROE {roe*100:.1f}% — compounds capital fast.")
                elif roe >= 0.15:
                    score += 0.18
                    reasons.append(f"Strong ROE {roe*100:.1f}% — quality profitability.")
                elif roe >= 0.10:
                    score += 0.06
                    reasons.append(f"Moderate ROE {roe*100:.1f}% — acceptable returns.")
                elif roe >= 0:
                    score -= 0.10
                    reasons.append(f"Weak ROE {roe*100:.1f}% — earns below cost of equity.")
                else:
                    score -= 0.22
                    reasons.append(f"Negative ROE {roe*100:.1f}% — destroying equity.")

            # --- 2. Capital efficiency: Return on Capital Employed ----------
            ebit = _num(fund.get("ebit"))
            cap_emp = _num(fund.get("capital_employed"))
            if ebit is not None and cap_emp is not None and cap_emp > 0:
                roce = ebit / cap_emp
                used += 1
                if roce >= 0.20:
                    score += 0.22
                    reasons.append(f"High ROCE {roce*100:.1f}% — strong moat/pricing power.")
                elif roce >= 0.13:
                    score += 0.12
                    reasons.append(f"Healthy ROCE {roce*100:.1f}%.")
                elif roce >= 0.08:
                    score += 0.03
                    reasons.append(f"Fair ROCE {roce*100:.1f}%.")
                else:
                    score -= 0.15
                    reasons.append(f"Low ROCE {roce*100:.1f}% — capital not working hard.")

            # --- 3. Growth: earnings / EPS + revenue ------------------------
            eps_g = _num(fund.get("eps_growth_yoy"))
            rev_g = _num(fund.get("revenue_growth_yoy"))
            growth_bits = [g for g in (eps_g, rev_g) if g is not None]
            if growth_bits:
                used += 1
                if eps_g is not None:
                    if eps_g >= 0.20:
                        score += 0.22
                        reasons.append(f"EPS growth {eps_g*100:.1f}% YoY — strong earnings compounding.")
                    elif eps_g >= 0.10:
                        score += 0.12
                        reasons.append(f"EPS growth {eps_g*100:.1f}% YoY — steady expansion.")
                    elif eps_g >= 0:
                        score += 0.02
                        reasons.append(f"Flat EPS growth {eps_g*100:.1f}% YoY.")
                    else:
                        score -= 0.20
                        reasons.append(f"EPS declining {eps_g*100:.1f}% YoY — earnings contraction.")
                if rev_g is not None and eps_g is None:
                    if rev_g >= 0.15:
                        score += 0.12
                        reasons.append(f"Revenue growth {rev_g*100:.1f}% YoY.")
                    elif rev_g < 0:
                        score -= 0.12
                        reasons.append(f"Revenue shrinking {rev_g*100:.1f}% YoY.")

            # --- 4. Promoter pledge (alignment / distress risk) -------------
            pledge = _num(fund.get("promoter_pledge_pct"))
            if pledge is not None:
                used += 1
                # accept either fraction (0.05) or percent (5.0) conventions
                pledge_frac = pledge / 100.0 if pledge > 1.5 else pledge
                pct = pledge_frac * 100.0
                if pledge_frac <= 0.02:
                    score += 0.15
                    reasons.append(f"Negligible promoter pledge {pct:.1f}% — clean, aligned ownership.")
                elif pledge_frac <= 0.15:
                    score += 0.03
                    reasons.append(f"Low promoter pledge {pct:.1f}% — manageable.")
                elif pledge_frac <= 0.35:
                    score -= 0.15
                    reasons.append(f"Elevated promoter pledge {pct:.1f}% — governance/leverage risk.")
                else:
                    score -= 0.30
                    reasons.append(f"High promoter pledge {pct:.1f}% — serious distress/margin-call risk.")

            # --- 5. Debt load (net_income vs total_debt burden) -------------
            total_debt = _num(fund.get("total_debt"))
            if total_debt is not None:
                used += 1
                if equity is not None and equity > 0:
                    de = total_debt / equity
                    if de <= 0.3:
                        score += 0.14
                        reasons.append(f"Low leverage: D/E {de:.2f} — resilient balance sheet.")
                    elif de <= 1.0:
                        score += 0.04
                        reasons.append(f"Moderate leverage: D/E {de:.2f}.")
                    elif de <= 2.0:
                        score -= 0.14
                        reasons.append(f"High leverage: D/E {de:.2f} — vulnerable to rate/earnings shocks.")
                    else:
                        score -= 0.26
                        reasons.append(f"Excessive leverage: D/E {de:.2f} — solvency risk.")
                elif net_income is not None and net_income > 0:
                    cover = net_income / total_debt if total_debt > 0 else 999
                    if cover >= 0.5:
                        score += 0.08
                        reasons.append(f"Debt well covered by earnings (NI/Debt {cover:.2f}).")
                    else:
                        score -= 0.10
                        reasons.append(f"Debt heavy vs earnings (NI/Debt {cover:.2f}).")

            # --- 6. Moat proxy: operating margin durability -----------------
            op_income = _num(fund.get("operating_income"))
            revenue = _num(fund.get("revenue"))
            if op_income is not None and revenue is not None and revenue > 0:
                used += 1
                op_margin = op_income / revenue
                if op_margin >= 0.20:
                    score += 0.12
                    reasons.append(f"Wide operating margin {op_margin*100:.1f}% — pricing-power moat.")
                elif op_margin >= 0.10:
                    score += 0.04
                    reasons.append(f"Decent operating margin {op_margin*100:.1f}%.")
                elif op_margin >= 0:
                    score -= 0.06
                    reasons.append(f"Thin operating margin {op_margin*100:.1f}% — commodity-like economics.")
                else:
                    score -= 0.18
                    reasons.append(f"Negative operating margin {op_margin*100:.1f}% — unprofitable core.")

            # --- Confidence from data coverage ------------------------------
            # 6 potential pillars; scale coverage into a calibrated band.
            if used == 0:
                return ModuleSignal(
                    self.name, 0.0, 0.05,
                    ["company: no usable fundamental fields — neutral."],
                )
            confidence = round(min(0.90, 0.25 + 0.11 * used), 2)

            score = max(-1.0, min(1.0, score))

            verdict = (
                "high-quality business" if score >= 0.35 else
                "above-average quality" if score >= 0.12 else
                "poor/low-quality business" if score <= -0.35 else
                "weak business quality" if score <= -0.12 else
                "average business quality"
            )
            reasons.insert(0, f"Company quality: {verdict} (score {score:+.2f}, {used}/6 pillars).")

            return ModuleSignal(
                module=self.name,
                score=round(score, 3),
                confidence=confidence,
                reasons=reasons[:6],
            )

        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
