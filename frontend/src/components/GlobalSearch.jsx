import React, { useState, useEffect, useRef } from 'react';
import { Search, Loader } from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const GlobalSearch = ({ token, onSelect }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
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

  const fetchResults = async (q) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/search?q=${encodeURIComponent(q || '')}`);
      if (response.ok) {
        const data = await response.json();
        setResults(data || []);
        setIsOpen(true);
      }
    } catch (err) {
      console.error('Search failed', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const debounce = setTimeout(() => {
      fetchResults(query);
    }, 150);

    return () => clearTimeout(debounce);
  }, [query]);

  const handleSelect = (stock) => {
    setQuery(stock.symbol);
    setIsOpen(false);
    if (onSelect) {
      onSelect(stock.symbol);
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
              if (!finalSymbol.includes('.NS') && !finalSymbol.includes('.BO')) {
                finalSymbol += '.NS';
              }
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
          top: '105%',
          left: 0,
          right: 0,
          background: '#0f172a',
          border: '1px solid #3b82f6',
          borderRadius: '8px',
          zIndex: 999999,
          maxHeight: '320px',
          overflowY: 'auto',
          boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.8)'
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
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.2)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 'bold', color: '#60a5fa', fontSize: '14px' }}>{stock.symbol}</span>
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>{stock.name}</span>
              </div>
              <span style={{ fontSize: '11px', padding: '2px 6px', background: '#1e293b', borderRadius: '4px', color: '#cbd5e1' }}>{stock.exchange || 'NSE'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default GlobalSearch;
