from fastapi import APIRouter
from pydantic import BaseModel
import logging

from app.scanner.ai_technical_scanner import AITechnicalScanner

router = APIRouter()
logger = logging.getLogger("elco.api.scanner")

# Initialize the scanner engine once
scanner_engine = AITechnicalScanner()

@router.get("/api/scanner/top20")
def get_top20_scans():
    """
    Runs the Institutional AI Technical Scanner.
    Returns exactly Top 10 Bullish and Top 10 Bearish stocks with all metrics.
    """
    logger.info("Executing Full Market Scan (Top 10 Bullish/Bearish)")
    
    # In production, this would be cached or run via Celery workers in the background
    # Since we reduced the symbol list to ~30 for fast testing, this will complete quickly.
    results = scanner_engine.run_full_scan()
    
    return {
        "status": "success",
        "data": results
    }
