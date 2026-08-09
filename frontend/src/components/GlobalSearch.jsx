import React, { useState, useEffect, useRef } from 'react';
import { Search, Loader } from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

// Built-in offline fallback database of top Indian stocks for zero-latency search
const TOP_STOCKS = [
  { symbol: 'TATASTEEL.NS', name: 'Tata Steel Limited', exchange: 'NSE' },
  { symbol: 'TATAPOWER.NS', name: 'Tata Power Company Limited', exchange: 'NSE' },
  { symbol: 'TATAMOTORS.NS', name: 'Tata Motors Limited', exchange: 'NSE' },
  { symbol: 'TCS.NS', name: 'Tata Consultancy Services Limited', exchange: 'NSE' },
  { symbol: 'TATACHEM.NS', name: 'Tata Chemicals Limited', exchange: 'NSE' },
  { symbol: 'TATACOMM.NS', name: 'Tata Communications Limited', exchange: 'NSE' },
  { symbol: 'TATACONSUM.NS', name: 'Tata Consumer Products Limited', exchange: 'NSE' },
  { symbol: 'TATAELXSI.NS', name: 'Tata Elxsi Limited', exchange: 'NSE' },
  { symbol: 'TATATECH.NS', name: 'Tata Technologies Limited', exchange: 'NSE' },
  { symbol: 'RELIANCE.NS', name: 'Reliance Industries Limited', exchange: 'NSE' },
  { symbol: 'SBIN.NS', name: 'State Bank of India', exchange: 'NSE' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank Limited', exchange: 'NSE' },
  { symbol: 'ICICIBANK.NS', name: 'ICICI Bank Limited', exchange: 'NSE' },
  { symbol: 'INFY.NS', name: 'Infosys Limited', exchange: 'NSE' },
  { symbol: 'SUZLON.NS', name: 'Suzlon Energy Limited', exchange: 'NSE' },
  { symbol: 'ZOMATO.NS', name: 'Zomato Limited', exchange: 'NSE' },
  { symbol: 'IREDA.NS', name: 'Indian Renewable Energy Development Agency', exchange: 'NSE' },
  { symbol: 'JIOFIN.NS', name: 'Jio Financial Services Limited', exchange: 'NSE' },
  { symbol: 'ADANIENT.NS', name: 'Adani Enterprises Limited', exchange: 'NSE' },
  { symbol: 'ADANIPORTS.NS', name: 'Adani Ports and Special Economic Zone', exchange: 'NSE' },
  { symbol: 'ITC.NS', name: 'ITC Limited', exchange: 'NSE' },
  { symbol: 'LT.NS', name: 'Larsen & Toubro Limited', exchange: 'NSE' },
  { symbol: 'AXISBANK.NS', name: 'Axis Bank Limited', exchange: 'NSE' },
  { symbol: 'BHARTIARTL.NS', name: 'Bharti Airtel Limited', exchange: 'NSE' },
  { symbol: 'BAJFINANCE.NS', name: 'Bajaj Finance Limited', exchange: 'NSE' }
];

const GlobalSearch = ({ token, onSelect }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(TOP_STOCKS.slice(0, 8));
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filterStocks = (q) => {
    if (!q || q.trim() === '') return TOP_STOCKS.slice(0, 10);
    const cleanQ = q.toLowerCase().trim();
    return TOP_STOCKS.filter(s => 
      s.symbol.toLowerCase().includes(cleanQ) || 
      s.name.toLowerCase().includes(cleanQ)
    );
  };

  const fetchResults = async (q) => {
    const localMatches = filterStocks(q);
    if (localMatches.length > 0) {
      setResults(localMatches);
      setIsOpen(true);
    }
    
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/search?q=${encodeURIComponent(q || '')}`);
      if (response.ok) {
        const data = await response.json();
        if (data && data.length > 0) {
          setResults(data);
          setIsOpen(true);
        }
      }
    } catch (err) {
      console.error('Search API fallback to local data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const debounce = setTimeout(() => {
      fetchResults(query);
    }, 100);

    return () => clearTimeout(debounce);
  }, [query]);

  const handleSelect = (stock) => {
    const cleanSym = stock.symbol.replace('.NS', '').replace('.BO', '');
    setQuery(cleanSym);
    setIsOpen(false);
    if (onSelect) {
      onSelect(cleanSym);
    }
  };

  return (
    <div ref={wrapperRef} style={{ position: 'relative', width: '100%', maxWidth: '450px', zIndex: 99999 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        background: 'rgba(255, 255, 255, 0.12)',
        border: '1px solid rgba(255,255,255,0.3)',
        borderRadius: '6px',
        padding: '0.4rem 0.8rem'
      }}>
        <Search size={16} style={{ color: '#94a3b8', marginRight: '8px' }} />
        <input
          type="text"
          placeholder="Search NSE/BSE stocks (e.g. RELIANCE, TATA)..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && query.trim() !== '') {
              let finalSymbol = query.trim().toUpperCase();
              setIsOpen(false);
              if (onSelect) onSelect(finalSymbol);
            }
          }}
          onFocus={() => {
            fetchResults(query);
            setIsOpen(true);
          }}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#ffffff',
            outline: 'none',
            width: '100%',
            fontSize: '14px',
            fontWeight: 500
          }}
        />
        {loading && <Loader size={14} className="spin" style={{ color: '#3b82f6' }} />}
      </div>
      
      {isOpen && results.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '108%',
          left: 0,
          right: 0,
          background: '#0f172a',
          border: '2px solid #3b82f6',
          borderRadius: '8px',
          zIndex: 999999,
          maxHeight: '320px',
          overflowY: 'auto',
          boxShadow: '0 12px 30px rgba(0, 0, 0, 0.9)'
        }}>
          {results.map((stock) => (
            <div 
              key={stock.symbol}
              onClick={() => handleSelect(stock)}
              style={{
                padding: '10px 14px',
                cursor: 'pointer',
                borderBottom: '1px solid rgba(255,255,255,0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.25)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 'bold', color: '#60a5fa', fontSize: '14px' }}>{stock.symbol}</span>
                <span style={{ fontSize: '12px', color: '#cbd5e1' }}>{stock.name}</span>
              </div>
              <span style={{ fontSize: '11px', padding: '2px 6px', background: '#1e293b', borderRadius: '4px', color: '#94a3b8' }}>{stock.exchange || 'NSE'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default GlobalSearch;
