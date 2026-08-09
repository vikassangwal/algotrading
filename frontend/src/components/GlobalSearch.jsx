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
    // Close dropdown if clicked outside
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
      const response = await fetch(`${API_URL}/api/search?q=${encodeURIComponent(q)}`);
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
    }, 200);

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
    <div ref={wrapperRef} style={{ position: 'relative', width: '100%', maxWidth: '450px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        background: 'rgba(255, 255, 255, 0.1)',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: '4px',
        padding: '0.3rem 0.6rem'
      }}>
        <Search size={16} style={{ color: 'rgba(255,255,255,0.5)', marginRight: '8px' }} />
        <input
          type="text"
          placeholder="Search NSE/BSE stocks (e.g. RELIANCE, TATA)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
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
            color: 'white',
            outline: 'none',
            width: '100%',
            fontSize: '14px'
          }}
        />
        {loading && <Loader size={14} className="spin" style={{ color: 'rgba(255,255,255,0.5)' }} />}
      </div>
      
      {isOpen && results.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          background: '#1a1a2e',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '4px',
          marginTop: '4px',
          zIndex: 1000,
          maxHeight: '300px',
          overflowY: 'auto',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
        }}>
          {results.map((stock) => (
            <div 
              key={stock.symbol}
              onClick={() => handleSelect(stock)}
              style={{
                padding: '10px',
                cursor: 'pointer',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                display: 'flex',
                flexDirection: 'column'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              <span style={{ fontWeight: 'bold', color: '#4ade80' }}>{stock.symbol}</span>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>{stock.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default GlobalSearch;
