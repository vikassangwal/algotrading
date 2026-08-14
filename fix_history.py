import os

path = "app/main.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    'ticker_symbol = symbol if ".NS" in symbol or ".BO" in symbol else f"{symbol}.NS"',
    'from app.data.dhan_provider import _yf_symbol\n    ticker_symbol = _yf_symbol(symbol.upper())'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
