from typing import List, Dict, Optional
from dataclasses import dataclass, field
import logging

from .config import config, TradingStyle
from .modules.base import AnalysisModule, ModuleSignal
from .data.provider import DataProvider

logger = logging.getLogger("elco.engine")

@dataclass
class FusedSignal:
    symbol: str
    overall_score: float         # -1 (strong sell) to +1 (strong buy)
    overall_confidence: float    # 0 to 1
    style: TradingStyle
    contributions: Dict[str, ModuleSignal] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    
    @property
    def action(self) -> str:
        if self.overall_score >= 0.5:
            return "BUY"
        elif self.overall_score <= -0.5:
            return "SELL"
        else:
            return "NEUTRAL"


class SignalFusionEngine:
    def __init__(self, provider: DataProvider):
        self.provider = provider
        self.modules: Dict[str, AnalysisModule] = {}
        
        # Style-specific weightings for different modules (0 to 1).
        # These can be made dynamic/configurable later.
        self.style_weights: Dict[TradingStyle, Dict[str, float]] = {
            TradingStyle.SCALPING: {
                "technical": 0.8,
                "options_flow": 0.9,
                "fundamental": 0.0,
                "news_risk": 0.7,
                "sentiment": 0.5,
                "quant": 0.4,
            },
            TradingStyle.INTRADAY: {
                "technical": 0.7,
                "options_flow": 0.7,
                "fundamental": 0.1,
                "news_risk": 0.8,
                "sentiment": 0.6,
                "quant": 0.5,
            },
            TradingStyle.SWING: {
                "technical": 0.6,
                "options_flow": 0.4,
                "fundamental": 0.5,
                "news_risk": 0.7,
                "sentiment": 0.4,
                "quant": 0.6,
            },
            TradingStyle.POSITIONAL: {
                "technical": 0.4,
                "options_flow": 0.2,
                "fundamental": 0.9,
                "news_risk": 0.6,
                "sentiment": 0.3,
                "quant": 0.5,
            },
            TradingStyle.OPTIONS: {
                "technical": 0.6,
                "options_flow": 1.0,
                "fundamental": 0.0,
                "news_risk": 0.7,
                "sentiment": 0.5,
                "quant": 0.7,
            },
            TradingStyle.LONG_TERM: {
                "technical": 0.2,
                "options_flow": 0.0,
                "fundamental": 1.0,
                "news_risk": 0.5,
                "sentiment": 0.2,
                "quant": 0.3,
            }
        }

    def register_module(self, module: AnalysisModule):
        self.modules[module.name] = module
        logger.info(f"Registered module: {module.name}")

    def analyze(self, symbol: str, style: TradingStyle = TradingStyle.INTRADAY) -> FusedSignal:
        """
        Runs all active modules, aggregates their signals based on trading style weights,
        and returns a FusedSignal.
        """
        contributions: Dict[str, ModuleSignal] = {}
        all_reasons: List[str] = []
        
        total_weighted_score = 0.0
        total_weight = 0.0
        total_confidence = 0.0
        
        style_weight_map = self.style_weights.get(style, {})
        
        for name, module in self.modules.items():
            if not config.modules_enabled.get(name, False):
                continue
                
            try:
                signal = module.analyze(symbol)
                contributions[name] = signal
                
                # Default weight to 0.5 if not explicitly configured for the style
                weight = style_weight_map.get(name, 0.5) 
                
                # Combine score taking into account the module's own confidence
                effective_weight = weight * signal.confidence
                
                total_weighted_score += signal.score * effective_weight
                total_weight += effective_weight
                total_confidence += signal.confidence
                
                for reason in signal.reasons:
                    all_reasons.append(f"[{name.upper()}] {reason}")
                    
            except Exception as e:
                logger.error(f"Module {name} failed on {symbol}: {e}")
                
        if total_weight > 0:
            final_score = total_weighted_score / total_weight
            final_confidence = total_confidence / len(contributions)
        else:
            final_score = 0.0
            final_confidence = 0.0
            all_reasons.append("No active modules contributed to this signal.")
            
        return FusedSignal(
            symbol=symbol,
            overall_score=final_score,
            overall_confidence=final_confidence,
            style=style,
            contributions=contributions,
            reasons=all_reasons
        )

    def analyze_all_styles(self, symbol: str) -> dict:
        """Run every active module ONCE (in parallel), then fuse the results
        under each trading style's weights. Powers the unified Command Center —
        one pass over the modules, a verdict per trading type.
        """
        # 1. Run every enabled module a single time, concurrently. Modules are
        # I/O-bound (data fetches) so a thread pool cuts wall-clock sharply.
        from concurrent.futures import ThreadPoolExecutor, as_completed

        active = [(name, mod) for name, mod in self.modules.items()
                  if config.modules_enabled.get(name, False)]

        module_signals: Dict[str, ModuleSignal] = {}

        def _run(item):
            name, module = item
            return name, module.analyze(symbol)

        if active:
            with ThreadPoolExecutor(max_workers=min(12, len(active))) as pool:
                futures = {pool.submit(_run, item): item[0] for item in active}
                for fut in as_completed(futures):
                    name = futures[fut]
                    try:
                        n, sig = fut.result()
                        module_signals[n] = sig
                    except Exception as e:
                        logger.error(f"Module {name} failed on {symbol}: {e}")

        # 2. Fuse per style using the pre-computed module signals.
        per_style = {}
        for style in TradingStyle:
            weight_map = self.style_weights.get(style, {})
            tw_score = 0.0
            tw = 0.0
            conf_sum = 0.0
            for name, sig in module_signals.items():
                weight = weight_map.get(name, 0.5)
                eff = weight * sig.confidence
                tw_score += sig.score * eff
                tw += eff
                conf_sum += sig.confidence
            score = (tw_score / tw) if tw > 0 else 0.0
            confidence = (conf_sum / len(module_signals)) if module_signals else 0.0
            if score >= 0.5:
                action = "BUY"
            elif score <= -0.5:
                action = "SELL"
            else:
                action = "NEUTRAL"
            per_style[style.value] = {
                "action": action,
                "score": round(score, 4),
                "confidence": round(confidence, 4),
            }

        return {
            "per_style": per_style,
            "modules": {
                name: {
                    "score": round(sig.score, 4),
                    "confidence": round(sig.confidence, 4),
                    "reasons": sig.reasons[:6],
                }
                for name, sig in module_signals.items()
            },
        }
