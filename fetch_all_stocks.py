"""
Fetch ALL NSE/BSE stocks from multiple sources and generate symbols_db.py
"""
import urllib.request
import csv
import json
import ssl
import io

def fetch_nse_stocks():
    """Try multiple methods to get NSE stock list"""
    stocks = []
    
    # Method 1: NSE Equity List CSV
    urls = [
        "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
        "https://www1.nseindia.com/content/equities/EQUITY_L.csv",
    ]
    
    for url in urls:
        try:
            print(f"Trying: {url}")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/csv,text/plain,*/*',
            })
            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                content = response.read().decode('utf-8', errors='ignore')
                reader = csv.reader(io.StringIO(content))
                header = next(reader)
                for row in reader:
                    if len(row) >= 2 and row[0].strip():
                        sym = row[0].strip()
                        name = row[1].strip()
                        if sym and name and len(sym) <= 20:
                            stocks.append({"symbol": f"{sym}.NS", "name": name, "exchange": "NSE"})
            if stocks:
                print(f"SUCCESS: Got {len(stocks)} stocks from {url}")
                return stocks
        except Exception as e:
            print(f"  Failed: {e}")
    
    return stocks

def get_comprehensive_fallback():
    """Comprehensive hardcoded list if online fetch fails"""
    # This covers Nifty 50, Nifty Next 50, Nifty Midcap 100, Nifty Smallcap, and popular stocks
    return [
        # === NIFTY 50 ===
        {"symbol": "RELIANCE.NS", "name": "Reliance Industries Ltd", "exchange": "NSE"},
        {"symbol": "TCS.NS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE"},
        {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Ltd", "exchange": "NSE"},
        {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Ltd", "exchange": "NSE"},
        {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd", "exchange": "NSE"},
        {"symbol": "SBIN.NS", "name": "State Bank of India", "exchange": "NSE"},
        {"symbol": "INFY.NS", "name": "Infosys Ltd", "exchange": "NSE"},
        {"symbol": "LICI.NS", "name": "Life Insurance Corporation of India", "exchange": "NSE"},
        {"symbol": "ITC.NS", "name": "ITC Ltd", "exchange": "NSE"},
        {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever Ltd", "exchange": "NSE"},
        {"symbol": "LT.NS", "name": "Larsen & Toubro Ltd", "exchange": "NSE"},
        {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance Ltd", "exchange": "NSE"},
        {"symbol": "HCLTECH.NS", "name": "HCL Technologies Ltd", "exchange": "NSE"},
        {"symbol": "MARUTI.NS", "name": "Maruti Suzuki India Ltd", "exchange": "NSE"},
        {"symbol": "SUNPHARMA.NS", "name": "Sun Pharmaceutical Industries Ltd", "exchange": "NSE"},
        {"symbol": "ADANIENT.NS", "name": "Adani Enterprises Ltd", "exchange": "NSE"},
        {"symbol": "TATAMOTORS.NS", "name": "Tata Motors Ltd", "exchange": "NSE"},
        {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank Ltd", "exchange": "NSE"},
        {"symbol": "TITAN.NS", "name": "Titan Company Ltd", "exchange": "NSE"},
        {"symbol": "ONGC.NS", "name": "Oil and Natural Gas Corporation Ltd", "exchange": "NSE"},
        {"symbol": "NTPC.NS", "name": "NTPC Ltd", "exchange": "NSE"},
        {"symbol": "AXISBANK.NS", "name": "Axis Bank Ltd", "exchange": "NSE"},
        {"symbol": "ADANIPORTS.NS", "name": "Adani Ports and Special Economic Zone Ltd", "exchange": "NSE"},
        {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement Ltd", "exchange": "NSE"},
        {"symbol": "ASIANPAINT.NS", "name": "Asian Paints Ltd", "exchange": "NSE"},
        {"symbol": "COALINDIA.NS", "name": "Coal India Ltd", "exchange": "NSE"},
        {"symbol": "BAJAJFINSV.NS", "name": "Bajaj Finserv Ltd", "exchange": "NSE"},
        {"symbol": "BAJAJ-AUTO.NS", "name": "Bajaj Auto Ltd", "exchange": "NSE"},
        {"symbol": "POWERGRID.NS", "name": "Power Grid Corporation of India Ltd", "exchange": "NSE"},
        {"symbol": "NESTLEIND.NS", "name": "Nestle India Ltd", "exchange": "NSE"},
        {"symbol": "WIPRO.NS", "name": "Wipro Ltd", "exchange": "NSE"},
        {"symbol": "M&M.NS", "name": "Mahindra & Mahindra Ltd", "exchange": "NSE"},
        {"symbol": "JSWSTEEL.NS", "name": "JSW Steel Ltd", "exchange": "NSE"},
        {"symbol": "TATASTEEL.NS", "name": "Tata Steel Ltd", "exchange": "NSE"},
        {"symbol": "HDFCLIFE.NS", "name": "HDFC Life Insurance Company Ltd", "exchange": "NSE"},
        {"symbol": "SBILIFE.NS", "name": "SBI Life Insurance Company Ltd", "exchange": "NSE"},
        {"symbol": "BRITANNIA.NS", "name": "Britannia Industries Ltd", "exchange": "NSE"},
        {"symbol": "DIVISLAB.NS", "name": "Divi's Laboratories Ltd", "exchange": "NSE"},
        {"symbol": "GRASIM.NS", "name": "Grasim Industries Ltd", "exchange": "NSE"},
        {"symbol": "CIPLA.NS", "name": "Cipla Ltd", "exchange": "NSE"},
        {"symbol": "TECHM.NS", "name": "Tech Mahindra Ltd", "exchange": "NSE"},
        {"symbol": "DRREDDY.NS", "name": "Dr. Reddy's Laboratories Ltd", "exchange": "NSE"},
        {"symbol": "BPCL.NS", "name": "Bharat Petroleum Corporation Ltd", "exchange": "NSE"},
        {"symbol": "EICHERMOT.NS", "name": "Eicher Motors Ltd", "exchange": "NSE"},
        {"symbol": "APOLLOHOSP.NS", "name": "Apollo Hospitals Enterprise Ltd", "exchange": "NSE"},
        {"symbol": "INDUSINDBK.NS", "name": "IndusInd Bank Ltd", "exchange": "NSE"},
        {"symbol": "TATACONSUM.NS", "name": "Tata Consumer Products Ltd", "exchange": "NSE"},
        {"symbol": "HEROMOTOCO.NS", "name": "Hero MotoCorp Ltd", "exchange": "NSE"},
        {"symbol": "HINDALCO.NS", "name": "Hindalco Industries Ltd", "exchange": "NSE"},
        {"symbol": "SHRIRAMFIN.NS", "name": "Shriram Finance Ltd", "exchange": "NSE"},
        # === NIFTY NEXT 50 ===
        {"symbol": "ADANIGREEN.NS", "name": "Adani Green Energy Ltd", "exchange": "NSE"},
        {"symbol": "ADANIPOWER.NS", "name": "Adani Power Ltd", "exchange": "NSE"},
        {"symbol": "ATGL.NS", "name": "Adani Total Gas Ltd", "exchange": "NSE"},
        {"symbol": "AWL.NS", "name": "Adani Wilmar Ltd", "exchange": "NSE"},
        {"symbol": "AMBUJACEM.NS", "name": "Ambuja Cements Ltd", "exchange": "NSE"},
        {"symbol": "DMART.NS", "name": "Avenue Supermarts Ltd (DMart)", "exchange": "NSE"},
        {"symbol": "BANKBARODA.NS", "name": "Bank of Baroda", "exchange": "NSE"},
        {"symbol": "BEL.NS", "name": "Bharat Electronics Ltd", "exchange": "NSE"},
        {"symbol": "BHEL.NS", "name": "Bharat Heavy Electricals Ltd", "exchange": "NSE"},
        {"symbol": "BOSCHLTD.NS", "name": "Bosch Ltd", "exchange": "NSE"},
        {"symbol": "CANBK.NS", "name": "Canara Bank", "exchange": "NSE"},
        {"symbol": "CHOLAFIN.NS", "name": "Cholamandalam Investment and Finance", "exchange": "NSE"},
        {"symbol": "COLPAL.NS", "name": "Colgate-Palmolive India Ltd", "exchange": "NSE"},
        {"symbol": "DLF.NS", "name": "DLF Ltd", "exchange": "NSE"},
        {"symbol": "DABUR.NS", "name": "Dabur India Ltd", "exchange": "NSE"},
        {"symbol": "GAIL.NS", "name": "GAIL India Ltd", "exchange": "NSE"},
        {"symbol": "GODREJCP.NS", "name": "Godrej Consumer Products Ltd", "exchange": "NSE"},
        {"symbol": "HAL.NS", "name": "Hindustan Aeronautics Ltd", "exchange": "NSE"},
        {"symbol": "HAVELLS.NS", "name": "Havells India Ltd", "exchange": "NSE"},
        {"symbol": "ICICIGI.NS", "name": "ICICI Lombard General Insurance", "exchange": "NSE"},
        {"symbol": "ICICIPRULI.NS", "name": "ICICI Prudential Life Insurance", "exchange": "NSE"},
        {"symbol": "IOC.NS", "name": "Indian Oil Corporation Ltd", "exchange": "NSE"},
        {"symbol": "IRCTC.NS", "name": "Indian Railway Catering and Tourism", "exchange": "NSE"},
        {"symbol": "IRFC.NS", "name": "Indian Railway Finance Corporation Ltd", "exchange": "NSE"},
        {"symbol": "INDIGO.NS", "name": "InterGlobe Aviation Ltd (IndiGo)", "exchange": "NSE"},
        {"symbol": "JINDALSTEL.NS", "name": "Jindal Steel & Power Ltd", "exchange": "NSE"},
        {"symbol": "JIOFIN.NS", "name": "Jio Financial Services Ltd", "exchange": "NSE"},
        {"symbol": "LTIM.NS", "name": "LTIMindtree Ltd", "exchange": "NSE"},
        {"symbol": "LICI.NS", "name": "Life Insurance Corporation of India", "exchange": "NSE"},
        {"symbol": "MARICO.NS", "name": "Marico Ltd", "exchange": "NSE"},
        {"symbol": "NHPC.NS", "name": "NHPC Ltd", "exchange": "NSE"},
        {"symbol": "PIDILITIND.NS", "name": "Pidilite Industries Ltd", "exchange": "NSE"},
        {"symbol": "PFC.NS", "name": "Power Finance Corporation Ltd", "exchange": "NSE"},
        {"symbol": "PNB.NS", "name": "Punjab National Bank", "exchange": "NSE"},
        {"symbol": "RECLTD.NS", "name": "REC Ltd", "exchange": "NSE"},
        {"symbol": "SBICARD.NS", "name": "SBI Cards and Payment Services", "exchange": "NSE"},
        {"symbol": "SIEMENS.NS", "name": "Siemens Ltd", "exchange": "NSE"},
        {"symbol": "TATAPOWER.NS", "name": "Tata Power Company Ltd", "exchange": "NSE"},
        {"symbol": "TORNTPHARM.NS", "name": "Torrent Pharmaceuticals Ltd", "exchange": "NSE"},
        {"symbol": "TRENT.NS", "name": "Trent Ltd", "exchange": "NSE"},
        {"symbol": "UNIONBANK.NS", "name": "Union Bank of India", "exchange": "NSE"},
        {"symbol": "VEDL.NS", "name": "Vedanta Ltd", "exchange": "NSE"},
        {"symbol": "ZOMATO.NS", "name": "Zomato Ltd", "exchange": "NSE"},
        {"symbol": "ZYDUSLIFE.NS", "name": "Zydus Lifesciences Ltd", "exchange": "NSE"},
        # === MIDCAP POPULAR ===
        {"symbol": "AARTIIND.NS", "name": "Aarti Industries Ltd", "exchange": "NSE"},
        {"symbol": "ABBOTINDIA.NS", "name": "Abbott India Ltd", "exchange": "NSE"},
        {"symbol": "ABB.NS", "name": "ABB India Ltd", "exchange": "NSE"},
        {"symbol": "ACC.NS", "name": "ACC Ltd", "exchange": "NSE"},
        {"symbol": "ALKEM.NS", "name": "Alkem Laboratories Ltd", "exchange": "NSE"},
        {"symbol": "ASHOKLEY.NS", "name": "Ashok Leyland Ltd", "exchange": "NSE"},
        {"symbol": "ASTRAL.NS", "name": "Astral Ltd", "exchange": "NSE"},
        {"symbol": "AUROPHARMA.NS", "name": "Aurobindo Pharma Ltd", "exchange": "NSE"},
        {"symbol": "BALKRISIND.NS", "name": "Balkrishna Industries Ltd", "exchange": "NSE"},
        {"symbol": "BANDHANBNK.NS", "name": "Bandhan Bank Ltd", "exchange": "NSE"},
        {"symbol": "BATAINDIA.NS", "name": "Bata India Ltd", "exchange": "NSE"},
        {"symbol": "BERGEPAINT.NS", "name": "Berger Paints India Ltd", "exchange": "NSE"},
        {"symbol": "BIOCON.NS", "name": "Biocon Ltd", "exchange": "NSE"},
        {"symbol": "BSE.NS", "name": "BSE Ltd", "exchange": "NSE"},
        {"symbol": "CANFINHOME.NS", "name": "Can Fin Homes Ltd", "exchange": "NSE"},
        {"symbol": "CDSL.NS", "name": "Central Depository Services Ltd", "exchange": "NSE"},
        {"symbol": "CENTRALBK.NS", "name": "Central Bank of India", "exchange": "NSE"},
        {"symbol": "CGPOWER.NS", "name": "CG Power and Industrial Solutions Ltd", "exchange": "NSE"},
        {"symbol": "CLEAN.NS", "name": "Clean Science and Technology Ltd", "exchange": "NSE"},
        {"symbol": "COFORGE.NS", "name": "Coforge Ltd", "exchange": "NSE"},
        {"symbol": "CONCOR.NS", "name": "Container Corporation of India Ltd", "exchange": "NSE"},
        {"symbol": "COROMANDEL.NS", "name": "Coromandel International Ltd", "exchange": "NSE"},
        {"symbol": "CROMPTON.NS", "name": "Crompton Greaves Consumer Electricals", "exchange": "NSE"},
        {"symbol": "CUB.NS", "name": "City Union Bank Ltd", "exchange": "NSE"},
        {"symbol": "CUMMINSIND.NS", "name": "Cummins India Ltd", "exchange": "NSE"},
        {"symbol": "DALBHARAT.NS", "name": "Dalmia Bharat Ltd", "exchange": "NSE"},
        {"symbol": "DEEPAKNTR.NS", "name": "Deepak Nitrite Ltd", "exchange": "NSE"},
        {"symbol": "DELTACORP.NS", "name": "Delta Corp Ltd", "exchange": "NSE"},
        {"symbol": "DEVYANI.NS", "name": "Devyani International Ltd", "exchange": "NSE"},
        {"symbol": "DIXON.NS", "name": "Dixon Technologies India Ltd", "exchange": "NSE"},
        {"symbol": "ELGIEQUIP.NS", "name": "Elgi Equipments Ltd", "exchange": "NSE"},
        {"symbol": "EMAMILTD.NS", "name": "Emami Ltd", "exchange": "NSE"},
        {"symbol": "ESCORTS.NS", "name": "Escorts Kubota Ltd", "exchange": "NSE"},
        {"symbol": "EXIDEIND.NS", "name": "Exide Industries Ltd", "exchange": "NSE"},
        {"symbol": "FEDERALBNK.NS", "name": "Federal Bank Ltd", "exchange": "NSE"},
        {"symbol": "FORTIS.NS", "name": "Fortis Healthcare Ltd", "exchange": "NSE"},
        {"symbol": "GLENMARK.NS", "name": "Glenmark Pharmaceuticals Ltd", "exchange": "NSE"},
        {"symbol": "GMRAIRPORT.NS", "name": "GMR Airports Infrastructure Ltd", "exchange": "NSE"},
        {"symbol": "GNFC.NS", "name": "Gujarat Narmada Valley Fertilizers", "exchange": "NSE"},
        {"symbol": "GODREJPROP.NS", "name": "Godrej Properties Ltd", "exchange": "NSE"},
        {"symbol": "GRANULES.NS", "name": "Granules India Ltd", "exchange": "NSE"},
        {"symbol": "GSPL.NS", "name": "Gujarat State Petronet Ltd", "exchange": "NSE"},
        {"symbol": "GUJGASLTD.NS", "name": "Gujarat Gas Ltd", "exchange": "NSE"},
        {"symbol": "HAPPSTMNDS.NS", "name": "Happiest Minds Technologies Ltd", "exchange": "NSE"},
        {"symbol": "HDFCAMC.NS", "name": "HDFC Asset Management Company Ltd", "exchange": "NSE"},
        {"symbol": "HINDPETRO.NS", "name": "Hindustan Petroleum Corporation Ltd", "exchange": "NSE"},
        {"symbol": "HONAUT.NS", "name": "Honeywell Automation India Ltd", "exchange": "NSE"},
        {"symbol": "IDFCFIRSTB.NS", "name": "IDFC First Bank Ltd", "exchange": "NSE"},
        {"symbol": "IEX.NS", "name": "Indian Energy Exchange Ltd", "exchange": "NSE"},
        {"symbol": "IPCALAB.NS", "name": "IPCA Laboratories Ltd", "exchange": "NSE"},
        {"symbol": "IREDA.NS", "name": "Indian Renewable Energy Development Agency", "exchange": "NSE"},
        {"symbol": "ISEC.NS", "name": "ICICI Securities Ltd", "exchange": "NSE"},
        {"symbol": "JKCEMENT.NS", "name": "JK Cement Ltd", "exchange": "NSE"},
        {"symbol": "JSWENERGY.NS", "name": "JSW Energy Ltd", "exchange": "NSE"},
        {"symbol": "JUBLFOOD.NS", "name": "Jubilant FoodWorks Ltd", "exchange": "NSE"},
        {"symbol": "KALYANKJIL.NS", "name": "Kalyan Jewellers India Ltd", "exchange": "NSE"},
        {"symbol": "KEI.NS", "name": "KEI Industries Ltd", "exchange": "NSE"},
        {"symbol": "KPITTECH.NS", "name": "KPIT Technologies Ltd", "exchange": "NSE"},
        {"symbol": "LALPATHLAB.NS", "name": "Dr Lal PathLabs Ltd", "exchange": "NSE"},
        {"symbol": "LAURUSLABS.NS", "name": "Laurus Labs Ltd", "exchange": "NSE"},
        {"symbol": "LICHSGFIN.NS", "name": "LIC Housing Finance Ltd", "exchange": "NSE"},
        {"symbol": "LUPIN.NS", "name": "Lupin Ltd", "exchange": "NSE"},
        {"symbol": "MANAPPURAM.NS", "name": "Manappuram Finance Ltd", "exchange": "NSE"},
        {"symbol": "MAXHEALTH.NS", "name": "Max Healthcare Institute Ltd", "exchange": "NSE"},
        {"symbol": "MCX.NS", "name": "Multi Commodity Exchange of India Ltd", "exchange": "NSE"},
        {"symbol": "METROPOLIS.NS", "name": "Metropolis Healthcare Ltd", "exchange": "NSE"},
        {"symbol": "MFSL.NS", "name": "Max Financial Services Ltd", "exchange": "NSE"},
        {"symbol": "MOTHERSON.NS", "name": "Samvardhana Motherson International", "exchange": "NSE"},
        {"symbol": "MRF.NS", "name": "MRF Ltd", "exchange": "NSE"},
        {"symbol": "MUTHOOTFIN.NS", "name": "Muthoot Finance Ltd", "exchange": "NSE"},
        {"symbol": "NAM-INDIA.NS", "name": "Nippon Life India Asset Management", "exchange": "NSE"},
        {"symbol": "NATIONALUM.NS", "name": "National Aluminium Company Ltd", "exchange": "NSE"},
        {"symbol": "NAUKRI.NS", "name": "Info Edge India Ltd (Naukri)", "exchange": "NSE"},
        {"symbol": "NAVINFLUOR.NS", "name": "Navin Fluorine International Ltd", "exchange": "NSE"},
        {"symbol": "NMDC.NS", "name": "NMDC Ltd", "exchange": "NSE"},
        {"symbol": "NYKAA.NS", "name": "FSN E-Commerce Ventures Ltd (Nykaa)", "exchange": "NSE"},
        {"symbol": "OBEROIRLTY.NS", "name": "Oberoi Realty Ltd", "exchange": "NSE"},
        {"symbol": "OFSS.NS", "name": "Oracle Financial Services Software", "exchange": "NSE"},
        {"symbol": "PAGEIND.NS", "name": "Page Industries Ltd", "exchange": "NSE"},
        {"symbol": "PAYTM.NS", "name": "One97 Communications Ltd (Paytm)", "exchange": "NSE"},
        {"symbol": "PERSISTENT.NS", "name": "Persistent Systems Ltd", "exchange": "NSE"},
        {"symbol": "PETRONET.NS", "name": "Petronet LNG Ltd", "exchange": "NSE"},
        {"symbol": "PIIND.NS", "name": "PI Industries Ltd", "exchange": "NSE"},
        {"symbol": "POLICYBZR.NS", "name": "PB Fintech Ltd (PolicyBazaar)", "exchange": "NSE"},
        {"symbol": "POLYCAB.NS", "name": "Polycab India Ltd", "exchange": "NSE"},
        {"symbol": "POONAWALLA.NS", "name": "Poonawalla Fincorp Ltd", "exchange": "NSE"},
        {"symbol": "PRESTIGE.NS", "name": "Prestige Estates Projects Ltd", "exchange": "NSE"},
        {"symbol": "PVRINOX.NS", "name": "PVR INOX Ltd", "exchange": "NSE"},
        {"symbol": "RAJESHEXPO.NS", "name": "Rajesh Exports Ltd", "exchange": "NSE"},
        {"symbol": "RAMCOCEM.NS", "name": "Ramco Cements Ltd", "exchange": "NSE"},
        {"symbol": "RBLBANK.NS", "name": "RBL Bank Ltd", "exchange": "NSE"},
        {"symbol": "SAIL.NS", "name": "Steel Authority of India Ltd", "exchange": "NSE"},
        {"symbol": "SOLARINDS.NS", "name": "Solar Industries India Ltd", "exchange": "NSE"},
        {"symbol": "SONACOMS.NS", "name": "Sona BLW Precision Forgings Ltd", "exchange": "NSE"},
        {"symbol": "SRF.NS", "name": "SRF Ltd", "exchange": "NSE"},
        {"symbol": "STAR.NS", "name": "Star Health and Allied Insurance", "exchange": "NSE"},
        {"symbol": "SUNDARMFIN.NS", "name": "Sundaram Finance Ltd", "exchange": "NSE"},
        {"symbol": "SUNDRMFAST.NS", "name": "Sundram Fasteners Ltd", "exchange": "NSE"},
        {"symbol": "SUZLON.NS", "name": "Suzlon Energy Ltd", "exchange": "NSE"},
        {"symbol": "SYNGENE.NS", "name": "Syngene International Ltd", "exchange": "NSE"},
        {"symbol": "TATACOMM.NS", "name": "Tata Communications Ltd", "exchange": "NSE"},
        {"symbol": "TATAELXSI.NS", "name": "Tata Elxsi Ltd", "exchange": "NSE"},
        {"symbol": "TATACHEM.NS", "name": "Tata Chemicals Ltd", "exchange": "NSE"},
        {"symbol": "THERMAX.NS", "name": "Thermax Ltd", "exchange": "NSE"},
        {"symbol": "TIINDIA.NS", "name": "Tube Investments of India Ltd", "exchange": "NSE"},
        {"symbol": "TORNTPOWER.NS", "name": "Torrent Power Ltd", "exchange": "NSE"},
        {"symbol": "TVSMOTOR.NS", "name": "TVS Motor Company Ltd", "exchange": "NSE"},
        {"symbol": "UBL.NS", "name": "United Breweries Ltd", "exchange": "NSE"},
        {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement Ltd", "exchange": "NSE"},
        {"symbol": "UPL.NS", "name": "UPL Ltd", "exchange": "NSE"},
        {"symbol": "VOLTAS.NS", "name": "Voltas Ltd", "exchange": "NSE"},
        {"symbol": "WHIRLPOOL.NS", "name": "Whirlpool of India Ltd", "exchange": "NSE"},
        {"symbol": "YESBANK.NS", "name": "Yes Bank Ltd", "exchange": "NSE"},
        # === SMALLCAP POPULAR / NEW AGE / IPO FAVORITES ===
        {"symbol": "ADANIWILMAR.NS", "name": "Adani Wilmar Ltd", "exchange": "NSE"},
        {"symbol": "ANGELONE.NS", "name": "Angel One Ltd", "exchange": "NSE"},
        {"symbol": "APTUS.NS", "name": "Aptus Value Housing Finance Ltd", "exchange": "NSE"},
        {"symbol": "BSOFT.NS", "name": "Birlasoft Ltd", "exchange": "NSE"},
        {"symbol": "CAMPUS.NS", "name": "Campus Activewear Ltd", "exchange": "NSE"},
        {"symbol": "CARTRADE.NS", "name": "CarTrade Tech Ltd", "exchange": "NSE"},
        {"symbol": "CELLO.NS", "name": "Cello World Ltd", "exchange": "NSE"},
        {"symbol": "DELHIVERY.NS", "name": "Delhivery Ltd", "exchange": "NSE"},
        {"symbol": "EASEMYTRIP.NS", "name": "Easy Trip Planners Ltd", "exchange": "NSE"},
        {"symbol": "ETHOSLTD.NS", "name": "Ethos Ltd", "exchange": "NSE"},
        {"symbol": "FIVESTAR.NS", "name": "Five-Star Business Finance Ltd", "exchange": "NSE"},
        {"symbol": "GLAND.NS", "name": "Gland Pharma Ltd", "exchange": "NSE"},
        {"symbol": "HSCL.NS", "name": "Himadri Speciality Chemical Ltd", "exchange": "NSE"},
        {"symbol": "HUDCO.NS", "name": "Housing & Urban Development Corp", "exchange": "NSE"},
        {"symbol": "IDEA.NS", "name": "Vodafone Idea Ltd", "exchange": "NSE"},
        {"symbol": "INDIANB.NS", "name": "Indian Bank", "exchange": "NSE"},
        {"symbol": "INDIAMART.NS", "name": "IndiaMART InterMESH Ltd", "exchange": "NSE"},
        {"symbol": "IOLCP.NS", "name": "IOL Chemicals and Pharmaceuticals", "exchange": "NSE"},
        {"symbol": "JBCHEPHARM.NS", "name": "JB Chemicals & Pharmaceuticals", "exchange": "NSE"},
        {"symbol": "JSWINFRA.NS", "name": "JSW Infrastructure Ltd", "exchange": "NSE"},
        {"symbol": "KAYNES.NS", "name": "Kaynes Technology India Ltd", "exchange": "NSE"},
        {"symbol": "KEC.NS", "name": "KEC International Ltd", "exchange": "NSE"},
        {"symbol": "LATENTVIEW.NS", "name": "Latent View Analytics Ltd", "exchange": "NSE"},
        {"symbol": "LXCHEM.NS", "name": "Laxmi Organic Industries Ltd", "exchange": "NSE"},
        {"symbol": "MAPMYINDIA.NS", "name": "CE Info Systems Ltd (MapMyIndia)", "exchange": "NSE"},
        {"symbol": "MASTEK.NS", "name": "Mastek Ltd", "exchange": "NSE"},
        {"symbol": "MEDANTA.NS", "name": "Global Health Ltd (Medanta)", "exchange": "NSE"},
        {"symbol": "MOTILALOFS.NS", "name": "Motilal Oswal Financial Services", "exchange": "NSE"},
        {"symbol": "MPHASIS.NS", "name": "Mphasis Ltd", "exchange": "NSE"},
        {"symbol": "MULTIBAGGER.NS", "name": "Multi Commodity Exchange", "exchange": "NSE"},
        {"symbol": "NAZARA.NS", "name": "Nazara Technologies Ltd", "exchange": "NSE"},
        {"symbol": "OLECTRA.NS", "name": "Olectra Greentech Ltd", "exchange": "NSE"},
        {"symbol": "RVNL.NS", "name": "Rail Vikas Nigam Ltd", "exchange": "NSE"},
        {"symbol": "PGHH.NS", "name": "Procter & Gamble Health Ltd", "exchange": "NSE"},
        {"symbol": "PHOENIXLTD.NS", "name": "The Phoenix Mills Ltd", "exchange": "NSE"},
        {"symbol": "POWERINDIA.NS", "name": "Hitachi Energy India Ltd", "exchange": "NSE"},
        {"symbol": "RADICO.NS", "name": "Radico Khaitan Ltd", "exchange": "NSE"},
        {"symbol": "RAINBOW.NS", "name": "Rainbow Children's Medicare", "exchange": "NSE"},
        {"symbol": "RITES.NS", "name": "RITES Ltd", "exchange": "NSE"},
        {"symbol": "ROUTE.NS", "name": "Route Mobile Ltd", "exchange": "NSE"},
        {"symbol": "SAPPHIRE.NS", "name": "Sapphire Foods India Ltd", "exchange": "NSE"},
        {"symbol": "SJVN.NS", "name": "SJVN Ltd", "exchange": "NSE"},
        {"symbol": "SPARC.NS", "name": "Sun Pharma Advanced Research", "exchange": "NSE"},
        {"symbol": "SWIGGY.NS", "name": "Swiggy Ltd", "exchange": "NSE"},
        {"symbol": "SYMPHONY.NS", "name": "Symphony Ltd", "exchange": "NSE"},
        {"symbol": "TANLA.NS", "name": "Tanla Platforms Ltd", "exchange": "NSE"},
        {"symbol": "TATAINVEST.NS", "name": "Tata Investment Corporation Ltd", "exchange": "NSE"},
        {"symbol": "TATATECH.NS", "name": "Tata Technologies Ltd", "exchange": "NSE"},
        {"symbol": "TITAGARH.NS", "name": "Titagarh Rail Systems Ltd", "exchange": "NSE"},
        {"symbol": "TRIDENT.NS", "name": "Trident Ltd", "exchange": "NSE"},
        {"symbol": "VAIBHAVGBL.NS", "name": "Vaibhav Global Ltd", "exchange": "NSE"},
        {"symbol": "VBL.NS", "name": "Varun Beverages Ltd", "exchange": "NSE"},
        {"symbol": "ZEEL.NS", "name": "Zee Entertainment Enterprises Ltd", "exchange": "NSE"},
        {"symbol": "JIOFIN.NS", "name": "Jio Financial Services Ltd", "exchange": "NSE"},
        # === PSU & DEFENCE ===
        {"symbol": "COCHINSHIP.NS", "name": "Cochin Shipyard Ltd", "exchange": "NSE"},
        {"symbol": "GRSE.NS", "name": "Garden Reach Shipbuilders & Engineers", "exchange": "NSE"},
        {"symbol": "MAZAGONDOCK.NS", "name": "Mazagon Dock Shipbuilders Ltd", "exchange": "NSE"},
        {"symbol": "BDL.NS", "name": "Bharat Dynamics Ltd", "exchange": "NSE"},
        {"symbol": "PARAS.NS", "name": "Paras Defence and Space Technologies", "exchange": "NSE"},
        {"symbol": "DATAPATTNS.NS", "name": "Data Patterns India Ltd", "exchange": "NSE"},
        {"symbol": "IDEAFORGE.NS", "name": "ideaForge Technology Ltd", "exchange": "NSE"},
        {"symbol": "MIDHANI.NS", "name": "Mishra Dhatu Nigam Ltd", "exchange": "NSE"},
        {"symbol": "IRCON.NS", "name": "Ircon International Ltd", "exchange": "NSE"},
        {"symbol": "NBCC.NS", "name": "NBCC India Ltd", "exchange": "NSE"},
        {"symbol": "NLC.NS", "name": "NLC India Ltd", "exchange": "NSE"},
        {"symbol": "RECLTD.NS", "name": "REC Ltd", "exchange": "NSE"},
        {"symbol": "NHPC.NS", "name": "NHPC Ltd", "exchange": "NSE"},
        {"symbol": "HFCL.NS", "name": "HFCL Ltd", "exchange": "NSE"},
        {"symbol": "RVNL.NS", "name": "Rail Vikas Nigam Ltd", "exchange": "NSE"},
        # === ENERGY / GREEN / EV ===
        {"symbol": "TATAPOWER.NS", "name": "Tata Power Company Ltd", "exchange": "NSE"},
        {"symbol": "ADANIGREEN.NS", "name": "Adani Green Energy Ltd", "exchange": "NSE"},
        {"symbol": "NHPC.NS", "name": "NHPC Ltd", "exchange": "NSE"},
        {"symbol": "SJVN.NS", "name": "SJVN Ltd", "exchange": "NSE"},
        {"symbol": "SUZLON.NS", "name": "Suzlon Energy Ltd", "exchange": "NSE"},
        {"symbol": "IREDA.NS", "name": "Indian Renewable Energy Dev Agency", "exchange": "NSE"},
        {"symbol": "EXIDEIND.NS", "name": "Exide Industries Ltd", "exchange": "NSE"},
        {"symbol": "AMARAJABAT.NS", "name": "Amara Raja Energy & Mobility Ltd", "exchange": "NSE"},
        # === FINANCIAL SERVICES ===
        {"symbol": "BAJAJHLDNG.NS", "name": "Bajaj Holdings and Investment Ltd", "exchange": "NSE"},
        {"symbol": "CHOLAHLDNG.NS", "name": "Murugappa Group Holdings", "exchange": "NSE"},
        {"symbol": "CRISIL.NS", "name": "CRISIL Ltd", "exchange": "NSE"},
        {"symbol": "ICRA.NS", "name": "ICRA Ltd", "exchange": "NSE"},
        {"symbol": "IIFL.NS", "name": "IIFL Finance Ltd", "exchange": "NSE"},
        {"symbol": "L&TFH.NS", "name": "L&T Finance Ltd", "exchange": "NSE"},
        {"symbol": "MFSL.NS", "name": "Max Financial Services Ltd", "exchange": "NSE"},
        {"symbol": "PNBHOUSING.NS", "name": "PNB Housing Finance Ltd", "exchange": "NSE"},
        {"symbol": "RNAM.NS", "name": "Nippon Life India Asset Management", "exchange": "NSE"},
        {"symbol": "UTIAMC.NS", "name": "UTI Asset Management Company Ltd", "exchange": "NSE"},
        # === METALS & MINING ===
        {"symbol": "HINDZINC.NS", "name": "Hindustan Zinc Ltd", "exchange": "NSE"},
        {"symbol": "MOIL.NS", "name": "MOIL Ltd", "exchange": "NSE"},
        {"symbol": "RATNAMANI.NS", "name": "Ratnamani Metals & Tubes Ltd", "exchange": "NSE"},
        {"symbol": "APLAPOLLO.NS", "name": "APL Apollo Tubes Ltd", "exchange": "NSE"},
        {"symbol": "WELCORP.NS", "name": "Welspun Corp Ltd", "exchange": "NSE"},
        # === CONSUMER / RETAIL / FMCG ===
        {"symbol": "JUBLFOOD.NS", "name": "Jubilant FoodWorks Ltd", "exchange": "NSE"},
        {"symbol": "TRENT.NS", "name": "Trent Ltd (Westside/Zudio)", "exchange": "NSE"},
        {"symbol": "SHOPERSTOP.NS", "name": "Shoppers Stop Ltd", "exchange": "NSE"},
        {"symbol": "VMART.NS", "name": "V-Mart Retail Ltd", "exchange": "NSE"},
        {"symbol": "RELAXO.NS", "name": "Relaxo Footwears Ltd", "exchange": "NSE"},
        {"symbol": "RAYMOND.NS", "name": "Raymond Ltd", "exchange": "NSE"},
        {"symbol": "TITAN.NS", "name": "Titan Company Ltd", "exchange": "NSE"},
        {"symbol": "MANYAVAR.NS", "name": "Vedant Fashions Ltd (Manyavar)", "exchange": "NSE"},
        {"symbol": "NYKAA.NS", "name": "FSN E-Commerce Ventures (Nykaa)", "exchange": "NSE"},
        {"symbol": "MAMAEARTH.NS", "name": "Honasa Consumer Ltd (Mamaearth)", "exchange": "NSE"},
        # === REAL ESTATE ===
        {"symbol": "DLF.NS", "name": "DLF Ltd", "exchange": "NSE"},
        {"symbol": "GODREJPROP.NS", "name": "Godrej Properties Ltd", "exchange": "NSE"},
        {"symbol": "LODHA.NS", "name": "Macrotech Developers Ltd (Lodha)", "exchange": "NSE"},
        {"symbol": "OBEROIRLTY.NS", "name": "Oberoi Realty Ltd", "exchange": "NSE"},
        {"symbol": "PRESTIGE.NS", "name": "Prestige Estates Projects Ltd", "exchange": "NSE"},
        {"symbol": "BRIGADE.NS", "name": "Brigade Enterprises Ltd", "exchange": "NSE"},
        {"symbol": "SOBHA.NS", "name": "Sobha Ltd", "exchange": "NSE"},
        # === TELECOM / MEDIA ===
        {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd", "exchange": "NSE"},
        {"symbol": "IDEA.NS", "name": "Vodafone Idea Ltd", "exchange": "NSE"},
        {"symbol": "TTML.NS", "name": "Tata Teleservices Maharashtra Ltd", "exchange": "NSE"},
        {"symbol": "ZEEL.NS", "name": "Zee Entertainment Enterprises Ltd", "exchange": "NSE"},
        {"symbol": "SUNTV.NS", "name": "Sun TV Network Ltd", "exchange": "NSE"},
        {"symbol": "NETWORK18.NS", "name": "Network18 Media & Investments", "exchange": "NSE"},
        # === AUTO & AUTO ANCILLARY ===
        {"symbol": "TATAMOTORS.NS", "name": "Tata Motors Ltd", "exchange": "NSE"},
        {"symbol": "M&M.NS", "name": "Mahindra & Mahindra Ltd", "exchange": "NSE"},
        {"symbol": "MARUTI.NS", "name": "Maruti Suzuki India Ltd", "exchange": "NSE"},
        {"symbol": "BAJAJ-AUTO.NS", "name": "Bajaj Auto Ltd", "exchange": "NSE"},
        {"symbol": "HEROMOTOCO.NS", "name": "Hero MotoCorp Ltd", "exchange": "NSE"},
        {"symbol": "EICHERMOT.NS", "name": "Eicher Motors Ltd (Royal Enfield)", "exchange": "NSE"},
        {"symbol": "TVSMOTOR.NS", "name": "TVS Motor Company Ltd", "exchange": "NSE"},
        {"symbol": "BOSCHLTD.NS", "name": "Bosch Ltd", "exchange": "NSE"},
        {"symbol": "MRF.NS", "name": "MRF Ltd", "exchange": "NSE"},
        {"symbol": "APOLLOTYRE.NS", "name": "Apollo Tyres Ltd", "exchange": "NSE"},
        {"symbol": "CEATLTD.NS", "name": "CEAT Ltd", "exchange": "NSE"},
        {"symbol": "ENDURANCE.NS", "name": "Endurance Technologies Ltd", "exchange": "NSE"},
        {"symbol": "MOTHERSON.NS", "name": "Samvardhana Motherson International", "exchange": "NSE"},
        {"symbol": "OLECTRA.NS", "name": "Olectra Greentech Ltd (EV Buses)", "exchange": "NSE"},
        {"symbol": "ATGL.NS", "name": "Adani Total Gas Ltd", "exchange": "NSE"},
        # === PHARMA & HEALTHCARE ===
        {"symbol": "SUNPHARMA.NS", "name": "Sun Pharmaceutical Industries Ltd", "exchange": "NSE"},
        {"symbol": "DRREDDY.NS", "name": "Dr Reddy's Laboratories Ltd", "exchange": "NSE"},
        {"symbol": "CIPLA.NS", "name": "Cipla Ltd", "exchange": "NSE"},
        {"symbol": "LUPIN.NS", "name": "Lupin Ltd", "exchange": "NSE"},
        {"symbol": "DIVISLAB.NS", "name": "Divi's Laboratories Ltd", "exchange": "NSE"},
        {"symbol": "AUROPHARMA.NS", "name": "Aurobindo Pharma Ltd", "exchange": "NSE"},
        {"symbol": "BIOCON.NS", "name": "Biocon Ltd", "exchange": "NSE"},
        {"symbol": "TORNTPHARM.NS", "name": "Torrent Pharmaceuticals Ltd", "exchange": "NSE"},
        {"symbol": "ALKEM.NS", "name": "Alkem Laboratories Ltd", "exchange": "NSE"},
        {"symbol": "GLENMARK.NS", "name": "Glenmark Pharmaceuticals Ltd", "exchange": "NSE"},
        {"symbol": "NATCOPHARMA.NS", "name": "Natco Pharma Ltd", "exchange": "NSE"},
        {"symbol": "APOLLOHOSP.NS", "name": "Apollo Hospitals Enterprise Ltd", "exchange": "NSE"},
        {"symbol": "MAXHEALTH.NS", "name": "Max Healthcare Institute Ltd", "exchange": "NSE"},
        {"symbol": "FORTIS.NS", "name": "Fortis Healthcare Ltd", "exchange": "NSE"},
        # === IT & TECH ===
        {"symbol": "TCS.NS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE"},
        {"symbol": "INFY.NS", "name": "Infosys Ltd", "exchange": "NSE"},
        {"symbol": "HCLTECH.NS", "name": "HCL Technologies Ltd", "exchange": "NSE"},
        {"symbol": "WIPRO.NS", "name": "Wipro Ltd", "exchange": "NSE"},
        {"symbol": "TECHM.NS", "name": "Tech Mahindra Ltd", "exchange": "NSE"},
        {"symbol": "LTIM.NS", "name": "LTIMindtree Ltd", "exchange": "NSE"},
        {"symbol": "MPHASIS.NS", "name": "Mphasis Ltd", "exchange": "NSE"},
        {"symbol": "COFORGE.NS", "name": "Coforge Ltd", "exchange": "NSE"},
        {"symbol": "PERSISTENT.NS", "name": "Persistent Systems Ltd", "exchange": "NSE"},
        {"symbol": "TATAELXSI.NS", "name": "Tata Elxsi Ltd", "exchange": "NSE"},
        {"symbol": "KPITTECH.NS", "name": "KPIT Technologies Ltd", "exchange": "NSE"},
        {"symbol": "HAPPSTMNDS.NS", "name": "Happiest Minds Technologies Ltd", "exchange": "NSE"},
        {"symbol": "BSOFT.NS", "name": "Birlasoft Ltd", "exchange": "NSE"},
        {"symbol": "MASTEK.NS", "name": "Mastek Ltd", "exchange": "NSE"},
        {"symbol": "LATENTVIEW.NS", "name": "Latent View Analytics Ltd", "exchange": "NSE"},
        {"symbol": "TATATECH.NS", "name": "Tata Technologies Ltd", "exchange": "NSE"},
        # === CEMENT & INFRA ===
        {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement Ltd", "exchange": "NSE"},
        {"symbol": "AMBUJACEM.NS", "name": "Ambuja Cements Ltd", "exchange": "NSE"},
        {"symbol": "ACC.NS", "name": "ACC Ltd", "exchange": "NSE"},
        {"symbol": "SHREECEM.NS", "name": "Shree Cement Ltd", "exchange": "NSE"},
        {"symbol": "DALBHARAT.NS", "name": "Dalmia Bharat Ltd", "exchange": "NSE"},
        {"symbol": "RAMCOCEM.NS", "name": "Ramco Cements Ltd", "exchange": "NSE"},
        {"symbol": "JKCEMENT.NS", "name": "JK Cement Ltd", "exchange": "NSE"},
        {"symbol": "LT.NS", "name": "Larsen & Toubro Ltd", "exchange": "NSE"},
        {"symbol": "KEC.NS", "name": "KEC International Ltd", "exchange": "NSE"},
        {"symbol": "NBCC.NS", "name": "NBCC India Ltd", "exchange": "NSE"},
        {"symbol": "IRCON.NS", "name": "Ircon International Ltd", "exchange": "NSE"},
        # === INDICES (for reference) ===
        {"symbol": "^NSEI", "name": "NIFTY 50 Index", "exchange": "NSE"},
        {"symbol": "^NSEBANK", "name": "NIFTY Bank Index", "exchange": "NSE"},
        {"symbol": "^BSESN", "name": "BSE SENSEX Index", "exchange": "BSE"},
    ]


def generate():
    stocks = fetch_nse_stocks()
    
    if not stocks:
        print("Online fetch failed. Using comprehensive fallback list...")
        stocks = get_comprehensive_fallback()
    
    # Remove duplicates based on symbol
    seen = set()
    unique_stocks = []
    for s in stocks:
        if s["symbol"] not in seen:
            seen.add(s["symbol"])
            unique_stocks.append(s)
    stocks = unique_stocks
    
    print(f"\nTotal unique stocks: {len(stocks)}")
    
    # Write symbols_db.py
    with open("app/symbols_db.py", "w", encoding="utf-8") as f:
        f.write("# Auto-generated: Comprehensive Indian Stock Database\n")
        f.write("# Covers NSE & BSE — Nifty 50, Next 50, Midcap, Smallcap, IPO Favorites\n\n")
        f.write("INDIAN_STOCKS = [\n")
        for i, stock in enumerate(stocks):
            name = stock["name"].replace('"', '\\"')
            comma = "," if i < len(stocks) - 1 else ""
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
    
    print(f"Written {len(stocks)} stocks to app/symbols_db.py")


if __name__ == "__main__":
    generate()
