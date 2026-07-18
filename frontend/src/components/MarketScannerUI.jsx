import React, { useState, useEffect, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || '';

const ROWS_PER_PAGE = 20;

const styles = {
  container: {
    padding: '20px',
    backgroundColor: '#1e1e2d',
    color: '#ffffff',
    fontFamily: 'sans-serif',
    minHeight: '100vh'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    flexWrap: 'wrap',
    gap: '15px'
  },
  title: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#00d2ff'
  },
  searchContainer: {
    flex: '1',
    maxWidth: '300px'
  },
  searchInput: {
    padding: '10px',
    borderRadius: '4px',
    border: '1px solid #3f3f5a',
    backgroundColor: '#2b2b40',
    color: '#fff',
    width: '100%',
    fontSize: '16px'
  },
  dashboard: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
    gap: '20px'
  },
  card: {
    backgroundColor: '#2b2b40',
    padding: '15px',
    borderRadius: '8px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
    display: 'flex',
    flexDirection: 'column'
  },
  cardTitle: {
    fontSize: '18px',
    marginBottom: '15px',
    color: '#a1a1aa'
  },
  tableWrapper: {
    flex: 1,
    overflowX: 'auto'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    textAlign: 'left',
    padding: '10px',
    borderBottom: '2px solid #3f3f5a',
    color: '#a1a1aa'
  },
  td: {
    padding: '10px',
    borderBottom: '1px solid #3f3f5a'
  },
  positive: {
    color: '#4ade80'
  },
  negative: {
    color: '#f87171'
  },
  paginationContainer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '15px',
    color: '#a1a1aa',
    fontSize: '14px'
  },
  pageButton: {
    backgroundColor: '#3f3f5a',
    color: '#fff',
    border: 'none',
    padding: '5px 10px',
    borderRadius: '4px',
    cursor: 'pointer',
    margin: '0 5px'
  },
  pageButtonDisabled: {
    backgroundColor: '#1e1e2d',
    color: '#555',
    cursor: 'not-allowed'
  }
};

const Pagination = ({ currentPage, totalRows, onPageChange }) => {
  const totalPages = Math.ceil(totalRows / ROWS_PER_PAGE);
  if (totalPages <= 1) return null;

  return (
    <div style={styles.paginationContainer}>
      <span>Showing {Math.min((currentPage - 1) * ROWS_PER_PAGE + 1, totalRows)} to {Math.min(currentPage * ROWS_PER_PAGE, totalRows)} of {totalRows}</span>
      <div>
        <button 
          style={{...styles.pageButton, ...(currentPage === 1 ? styles.pageButtonDisabled : {})}}
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
        >
          Prev
        </button>
        <span>Page {currentPage} of {totalPages}</span>
        <button 
          style={{...styles.pageButton, ...(currentPage === totalPages ? styles.pageButtonDisabled : {})}}
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
        >
          Next
        </button>
      </div>
    </div>
  );
};

const MarketScannerUI = ({ token }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [gapPage, setGapPage] = useState(1);
  const [volumePage, setVolumePage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [scannerData, setScannerData] = useState({
    gap_up: [],
    breakout: [],
    high_volume: []
  });

  useEffect(() => {
    const fetchScanners = async () => {
      try {
        const res = await fetch(`${API_URL}/api/scanners`, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (res.ok) {
          const data = await res.json();
          setScannerData(data);
        }
      } catch (err) {
        console.error("Failed to fetch scanner data:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchScanners();
    const interval = setInterval(fetchScanners, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, [token]);

  const handleSearch = (e) => {
    setSearchTerm(e.target.value.toUpperCase());
    setGapPage(1);
    setVolumePage(1);
  };

  const filteredGapData = useMemo(() => {
    return scannerData.gap_up.filter(item => item.symbol.toUpperCase().includes(searchTerm));
  }, [scannerData.gap_up, searchTerm]);

  const filteredVolumeData = useMemo(() => {
    return scannerData.high_volume.filter(item => item.symbol.toUpperCase().includes(searchTerm));
  }, [scannerData.high_volume, searchTerm]);

  const filteredMomentumData = useMemo(() => {
    return scannerData.breakout.filter(item => item.symbol.toUpperCase().includes(searchTerm));
  }, [scannerData.breakout, searchTerm]);

  const paginatedGapData = useMemo(() => {
    const startIndex = (gapPage - 1) * ROWS_PER_PAGE;
    return filteredGapData.slice(startIndex, startIndex + ROWS_PER_PAGE);
  }, [filteredGapData, gapPage]);

  const paginatedVolumeData = useMemo(() => {
    const startIndex = (volumePage - 1) * ROWS_PER_PAGE;
    return filteredVolumeData.slice(startIndex, startIndex + ROWS_PER_PAGE);
  }, [filteredVolumeData, volumePage]);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>Market Scanner Dashboard</div>
        <div style={styles.searchContainer}>
          <input 
            type="text" 
            placeholder="Search symbol..." 
            value={searchTerm}
            onChange={handleSearch}
            style={styles.searchInput}
          />
        </div>
      </div>
      
      {loading ? (
        <div style={{textAlign: 'center', padding: '40px', color: '#a1a1aa'}}>
          Fetching Live Market Scanner Data...
        </div>
      ) : (
        <div style={styles.dashboard}>
          {/* Gap Ups/Downs Table */}
          <div style={styles.card}>
            <div style={styles.cardTitle}>Gap Ups / Downs</div>
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Symbol</th>
                    <th style={styles.th}>Price</th>
                    <th style={styles.th}>Change %</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedGapData.length === 0 ? (
                    <tr><td colSpan="3" style={{...styles.td, textAlign: 'center'}}>No gap ups found</td></tr>
                  ) : paginatedGapData.map((data, index) => (
                    <tr key={index}>
                      <td style={styles.td}>{data.symbol}</td>
                      <td style={styles.td}>{data.price}</td>
                      <td style={{...styles.td, ...styles.positive}}>
                        {data.change}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination 
              currentPage={gapPage} 
              totalRows={filteredGapData.length} 
              onPageChange={setGapPage} 
            />
          </div>

          {/* High Volume Table */}
          <div style={styles.card}>
            <div style={styles.cardTitle}>High Volume Scans</div>
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Symbol</th>
                    <th style={styles.th}>Price</th>
                    <th style={styles.th}>Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedVolumeData.length === 0 ? (
                    <tr><td colSpan="3" style={{...styles.td, textAlign: 'center'}}>No high volume data</td></tr>
                  ) : paginatedVolumeData.map((data, index) => (
                    <tr key={index}>
                      <td style={styles.td}>{data.symbol}</td>
                      <td style={{...styles.td}}>{data.price}</td>
                      <td style={{...styles.td, ...styles.positive}}>{data.volume}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination 
              currentPage={volumePage} 
              totalRows={filteredVolumeData.length} 
              onPageChange={setVolumePage} 
            />
          </div>

          {/* Breakouts Table (Replacing Momentum chart for now since backend returns tabular data) */}
          <div style={styles.card}>
            <div style={styles.cardTitle}>Price Breakouts</div>
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Symbol</th>
                    <th style={styles.th}>Price</th>
                    <th style={styles.th}>Change %</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMomentumData.length === 0 ? (
                    <tr><td colSpan="3" style={{...styles.td, textAlign: 'center'}}>No breakouts found</td></tr>
                  ) : filteredMomentumData.slice(0, 10).map((data, index) => (
                    <tr key={index}>
                      <td style={styles.td}>{data.symbol}</td>
                      <td style={{...styles.td}}>{data.price}</td>
                      <td style={{...styles.td, ...styles.positive}}>{data.change}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MarketScannerUI;
