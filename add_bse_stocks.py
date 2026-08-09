"""
Add BSE stocks (.BO suffix) to symbols_db.py
Most NSE stocks are dual-listed on BSE. We add .BO variants + BSE-exclusive stocks.
"""
import sys
sys.path.insert(0, '.')

from app.symbols_db import INDIAN_STOCKS

# Get existing NSE stocks
existing_symbols = {s["symbol"] for s in INDIAN_STOCKS}
print(f"Existing NSE stocks: {len(existing_symbols)}")

# Create BSE versions of all NSE stocks
bse_stocks = []
for stock in INDIAN_STOCKS:
    if stock["symbol"].endswith(".NS"):
        bse_sym = stock["symbol"].replace(".NS", ".BO")
        if bse_sym not in existing_symbols:
            bse_stocks.append({
                "symbol": bse_sym,
                "name": stock["name"],
                "exchange": "BSE"
            })

# BSE-exclusive / popular BSE stocks not on NSE
bse_exclusive = [
    {"symbol": "RPOWER.BO", "name": "Reliance Power Ltd", "exchange": "BSE"},
    {"symbol": "RCOM.BO", "name": "Reliance Communications Ltd", "exchange": "BSE"},
    {"symbol": "JPASSOCIAT.BO", "name": "Jaiprakash Associates Ltd", "exchange": "BSE"},
    {"symbol": "GTLINFRA.BO", "name": "GTL Infrastructure Ltd", "exchange": "BSE"},
    {"symbol": "UNITECH.BO", "name": "Unitech Ltd", "exchange": "BSE"},
    {"symbol": "SUZLON.BO", "name": "Suzlon Energy Ltd", "exchange": "BSE"},
    {"symbol": "JAIPRAKASH.BO", "name": "Jaiprakash Power Ventures Ltd", "exchange": "BSE"},
    {"symbol": "DBCORP.BO", "name": "D B Corp Ltd", "exchange": "BSE"},
    {"symbol": "SADBHAV.BO", "name": "Sadbhav Engineering Ltd", "exchange": "BSE"},
    {"symbol": "ORIENTCEM.BO", "name": "Orient Cement Ltd", "exchange": "BSE"},
    {"symbol": "DCMSHRIRAM.BO", "name": "DCM Shriram Ltd", "exchange": "BSE"},
    {"symbol": "KALPATPOWR.BO", "name": "Kalpataru Projects International", "exchange": "BSE"},
    {"symbol": "IFCI.BO", "name": "IFCI Ltd", "exchange": "BSE"},
    {"symbol": "MMTC.BO", "name": "MMTC Ltd", "exchange": "BSE"},
    {"symbol": "HCC.BO", "name": "Hindustan Construction Company Ltd", "exchange": "BSE"},
    {"symbol": "RELINFRA.BO", "name": "Reliance Infrastructure Ltd", "exchange": "BSE"},
    {"symbol": "RTNPOWER.BO", "name": "RattanIndia Power Ltd", "exchange": "BSE"},
    {"symbol": "ADANIGAS.BO", "name": "Adani Total Gas Ltd", "exchange": "BSE"},
    {"symbol": "PCJEWELLER.BO", "name": "PC Jeweller Ltd", "exchange": "BSE"},
    {"symbol": "DISHTV.BO", "name": "Dish TV India Ltd", "exchange": "BSE"},
]

for s in bse_exclusive:
    if s["symbol"] not in existing_symbols:
        bse_stocks.append(s)

all_stocks = INDIAN_STOCKS + bse_stocks

# Deduplicate
seen = set()
unique = []
for s in all_stocks:
    if s["symbol"] not in seen:
        seen.add(s["symbol"])
        unique.append(s)

print(f"BSE stocks added: {len(bse_stocks)}")
print(f"Total unique stocks: {len(unique)}")

# Rewrite symbols_db.py
with open("app/symbols_db.py", "w", encoding="utf-8") as f:
    f.write("# Auto-generated: Comprehensive Indian Stock Database\n")
    f.write(f"# NSE + BSE — Total {len(unique)} stocks\n\n")
    f.write("INDIAN_STOCKS = [\n")
    for i, stock in enumerate(unique):
        name = stock["name"].replace('"', '\\"').replace("'", "\\'")
        comma = "," if i < len(unique) - 1 else ""
        f.write(f'    {{"symbol": "{stock["symbol"]}", "name": "{name}", "exchange": "{stock["exchange"]}"}}{comma}\n')
    f.write("]\n\n\n")
    
    f.write('''def search_symbols(query: str):
    """Search stocks by symbol or name. Returns top 20 matches."""
    if not query:
        return INDIAN_STOCKS[:15]
    
    query = query.lower().strip()
    
    # Remove .NS/.BO suffix if user typed it
    clean_query = query.replace(".ns", "").replace(".bo", "")
    
    results = []
    
    # Priority 1: Exact symbol prefix match
    for stock in INDIAN_STOCKS:
        sym_clean = stock["symbol"].lower().replace(".ns", "").replace(".bo", "")
        if sym_clean.startswith(clean_query):
            results.append(stock)
            if len(results) >= 20:
                return results
    
    # Priority 2: Name starts with query
    for stock in INDIAN_STOCKS:
        if stock not in results and stock["name"].lower().startswith(query):
            results.append(stock)
            if len(results) >= 20:
                return results
    
    # Priority 3: Substring match in symbol or name
    for stock in INDIAN_STOCKS:
        if stock not in results:
            sym_clean = stock["symbol"].lower().replace(".ns", "").replace(".bo", "")
            if clean_query in sym_clean or query in stock["name"].lower():
                results.append(stock)
                if len(results) >= 20:
                    return results
    
    return results[:20]
''')

print(f"Done! Written {len(unique)} stocks to app/symbols_db.py")
