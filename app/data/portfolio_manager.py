import os
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger("elco.data.portfolio_manager")

class PortfolioManager:
    """
    Manages the persistent state of the portfolio via a JSON database.
    """
    def __init__(self, db_path: str = None):
        if not db_path:
            # Default to a file in the data directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(base_dir, "portfolio_db.json")
        else:
            self.db_path = db_path
            
        self._ensure_db_exists()
        
    def _ensure_db_exists(self):
        if not os.path.exists(self.db_path):
            default_state = {
                "cash_balance": 1000000.0,  # 10 Lakh starting cash
                "max_sector_weight_limit": 0.25,
                "max_stock_weight_limit": 0.10,
                "positions": [
                    {
                        "symbol": "RELIANCE.NS",
                        "quantity": 50,
                        "average_price": 2800.0,
                        "sector": "Energy",
                        "factor": "Value"
                    },
                    {
                        "symbol": "TCS.NS",
                        "quantity": 25,
                        "average_price": 3800.0,
                        "sector": "IT",
                        "factor": "Quality"
                    }
                ]
            }
            self.save_portfolio(default_state)
            logger.info(f"Created default portfolio database at {self.db_path}")

    def load_portfolio(self) -> Dict[str, Any]:
        """Loads the portfolio state from the JSON file."""
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load portfolio database: {e}")
            return {}

    def save_portfolio(self, state: Dict[str, Any]) -> bool:
        """Saves the portfolio state to the JSON file."""
        try:
            with open(self.db_path, "w") as f:
                json.dump(state, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to save portfolio database: {e}")
            return False

    def get_positions(self) -> List[Dict[str, Any]]:
        """Returns the list of current positions."""
        portfolio = self.load_portfolio()
        return portfolio.get("positions", [])
        
    def get_cash_balance(self) -> float:
        """Returns current cash balance."""
        return self.load_portfolio().get("cash_balance", 0.0)
