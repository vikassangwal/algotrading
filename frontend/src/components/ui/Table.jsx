import { clsx } from '../../design-system';
import { formatters } from '../../design-system';

const tableBase = `
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-family-sans);
  font-size: var(--table-font-size);
  color: var(--color-text-primary);
`;

const tableContainer = `
  overflow-x: auto;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-surface-border);
  background: var(--color-surface-panel);
`;

const tableStyles = `
  ${tableBase}
  thead {
    background: var(--color-surface-interactive);
    border-bottom: 2px solid var(--color-surface-border);
  }
  th {
    padding: var(--table-cell-padding);
    text-align: left;
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-secondary);
    font-size: var(--font-size-xs);
    text-transform: uppercase;
    letter-spacing: var(--letter-spacing-wider);
    white-space: nowrap;
    border-bottom: 1px solid var(--color-surface-border);
  }
  tbody tr {
    border-bottom: 1px solid var(--color-surface-border);
    transition: background var(--transition-fast);
  }
  tbody tr:last-child {
    border-bottom: none;
  }
  tbody tr:hover {
    background: var(--color-surface-panel-hover);
  }
  td {
    padding: var(--table-cell-padding);
    vertical-align: middle;
    border-bottom: 1px solid var(--color-surface-border);
  }
  td:last-child, th:last-child {
    padding-right: var(--space-6);
  }
  td:first-child, th:first-child {
    padding-left: var(--space-6);
  }
`;

export function Table({
  columns = [],
  data = [],
  keyField = 'id',
  sortable = false,
  sortColumn,
  sortDirection,
  onSort,
  selectable = false,
  selectedRows = [],
  onSelectionChange,
  striped = false,
  hoverable = true,
  compact = false,
  emptyMessage = 'No data available',
  loading = false,
  className = '',
  style = {},
  renderRow,
  rowClassName,
  onRowClick,
  ...props
}) {
  const handleSort = (column) => {
    if (!sortable || !column.sortable) return;
    if (onSort) {
      const newDirection = sortColumn === column.key && sortDirection === 'asc' ? 'desc' : 'asc';
      onSort(column.key, newDirection);
    }
  };

  const handleSelectAll = (e) => {
    if (onSelectionChange) {
      if (e.target.checked) {
        onSelectionChange(data.map(row => row[keyField]));
      } else {
        onSelectionChange([]);
      }
    }
  };

  const handleSelectRow = (rowId, e) => {
    e.stopPropagation();
    if (onSelectionChange) {
      const newSelection = selectedRows.includes(rowId)
        ? selectedRows.filter(id => id !== rowId)
        : [...selectedRows, rowId];
      onSelectionChange(newSelection);
    }
  };

  const getRowClass = (row) => {
    const classes = [];
    if (rowClassName) classes.push(rowClassName(row));
    if (onRowClick) classes.push('clickable');
    if (selectedRows.includes(row[keyField])) classes.push('selected');
    return classes.join(' ');
  };

  return (
    <div className={clsx('elco-table-container', className)} style={style}>
      {loading && (
        <div className="elco-table-loading" style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--color-surface-overlay)',
          zIndex: 10,
        }}>
          <div className="elco-spinner" style={{
            width: '32px',
            height: '32px',
            border: '3px solid var(--color-surface-border)',
            borderTopColor: 'var(--color-brand-500)',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          <style jsx>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}
      <div className="elco-table-wrapper" style={tableContainer}>
        <table className="elco-table" {...props}>
          <thead>
            <tr>
              {selectable && (
                <th style={{ width: '40px', padding: 'var(--table-cell-padding)' }}>
                  <input
                    type="checkbox"
                    checked={data.length > 0 && selectedRows.length === data.length}
                    indeterminate={selectedRows.length > 0 && selectedRows.length < data.length}
                    onChange={handleSelectAll}
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {columns.map((column) => (
                <th
                  key={column.key}
                  style={{
                    ...(column.width && { width: column.width }),
                    ...(column.align && { textAlign: column.align }),
                    cursor: column.sortable ? 'pointer' : 'default',
                    userSelect: column.sortable ? 'none' : 'auto',
                  }}
                  onClick={() => handleSort(column)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    {column.header}
                    {column.sortable && (
                      <span style={{ fontSize: '10px', color: sortColumn === column.key ? 'var(--color-brand-500)' : 'var(--color-text-tertiary)' }}>
                        {sortColumn === column.key
                          ? (sortDirection === 'asc' ? '▲' : '▼')
                          : '⇅'}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && !loading && (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)} style={{
                  padding: 'var(--space-8)',
                  textAlign: 'center',
                  color: 'var(--color-text-tertiary)',
                }}>
                  {emptyMessage}
                </td>
              </tr>
            )}
            {data.map((row, rowIndex) => {
              const rowKey = row[keyField];
              const isSelected = selectedRows.includes(rowKey);

              if (renderRow) {
                return renderRow(row, rowIndex);
              }

              return (
                <tr
                  key={rowKey}
                  className={clsx(getRowClass(row))}
                  style={{
                    ...(isSelected && { background: 'var(--color-brand-100)' }),
                    ...(onRowClick && { cursor: 'pointer' }),
                  }}
                  onClick={() => onRowClick?.(row, rowIndex)}
                >
                  {selectable && (
                    <td style={{ padding: 'var(--table-cell-padding)' }}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => handleSelectRow(rowKey, e)}
                        aria-label={`Select row ${rowIndex + 1}`}
                      />
                    </td>
                  )}
                  {columns.map((column) => {
                    const value = row[column.key];
                    let cellContent = value;

                    if (column.render) {
                      cellContent = column.render(value, row, rowIndex);
                    } else if (column.format) {
                      cellContent = formatters[column.format](value, column.formatOptions);
                    }

                    return (
                      <td
                        key={column.key}
                        style={{
                          ...(column.align && { textAlign: column.align }),
                          ...(column.width && { width: column.width }),
                          fontFamily: column.mono ? 'var(--font-family-mono)' : undefined,
                          fontVariantNumeric: column.numeric ? 'tabular-nums' : undefined,
                        }}
                      >
                        {cellContent}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        <style jsx>{tableStyles}</style>
      </div>
    </div>
  );
}

// Virtualized Table for large datasets
export function VirtualizedTable({
  columns = [],
  data = [],
  keyField = 'id',
  height = 600,
  rowHeight = 48,
  headerHeight = 40,
  overscan = 5,
  ...tableProps
}) {
  const [scrollTop, setScrollTop] = React.useState(0);
  const containerRef = React.useRef(null);

  const visibleStart = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const visibleEnd = Math.min(data.length, Math.ceil((scrollTop + height) / rowHeight) + overscan);
  const visibleData = data.slice(visibleStart, visibleEnd);

  const handleScroll = (e) => {
    setScrollTop(e.target.scrollTop);
  };

  return (
    <div
      ref={containerRef}
      className="elco-virtual-table"
      style={{
        height,
        overflowY: 'auto',
        border: '1px solid var(--color-surface-border)',
        borderRadius: 'var(--radius-lg)',
        background: 'var(--color-surface-panel)',
        position: 'relative',
      }}
      onScroll={handleScroll}
    >
      <div style={{ height: data.length * rowHeight, position: 'relative' }}>
        <Table
          columns={columns}
          data={visibleData}
          keyField={keyField}
          {...tableProps}
        />
      </div>
    </div>
  );
}

// Data Grid with advanced features
export function DataGrid({
  columns = [],
  data = [],
  keyField = 'id',
  // Toolbar
  searchable = false,
  searchPlaceholder = 'Search...',
  onSearch,
  filterable = false,
  filters = {},
  onFilterChange,
  // Pagination
  paginated = false,
  pageSize = 25,
  pageSizeOptions = [10, 25, 50, 100],
  onPageChange,
  onPageSizeChange,
  totalRows,
  currentPage = 1,
  // Selection
  selectable = false,
  selectedRows = [],
  onSelectionChange,
  // Export
  exportable = false,
  onExport,
  // Custom toolbar
  toolbar,
  // Loading
  loading = false,
  // Empty state
  emptyMessage = 'No data available',
  // Row actions
  rowActions,
  // Class/style
  className = '',
  style = {},
}) {
  const [searchTerm, setSearchTerm] = React.useState('');
  const [sortColumn, setSortColumn] = React.useState(null);
  const [sortDirection, setSortDirection] = React.useState('asc');
  const [localFilters, setLocalFilters] = React.useState(filters);

  const handleSort = React.useCallback((columnKey, direction) => {
    setSortColumn(columnKey);
    setSortDirection(direction);
  }, []);

  const handleSearch = React.useCallback((e) => {
    const value = e.target.value;
    setSearchTerm(value);
    onSearch?.(value);
  }, [onSearch]);

  const handleFilterChange = React.useCallback((key, value) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFilterChange?.(newFilters);
  }, [localFilters, onFilterChange]);

  const filteredData = React.useMemo(() => {
    let result = data;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(row =>
        columns.some(col => {
          const value = row[col.key];
          return value?.toString().toLowerCase().includes(term);
        })
      );
    }
    if (sortColumn) {
      result = [...result].sort((a, b) => {
        const aVal = a[sortColumn];
        const bVal = b[sortColumn];
        const dir = sortDirection === 'asc' ? 1 : -1;
        if (aVal < bVal) return -1 * dir;
        if (aVal > bVal) return 1 * dir;
        return 0;
      });
    }
    return result;
  }, [data, searchTerm, sortColumn, sortDirection]);

  const paginatedData = React.useMemo(() => {
    if (!paginated) return filteredData;
    const start = (currentPage - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, paginated, currentPage, pageSize]);

  const totalPages = Math.ceil(filteredData.length / pageSize);

  return (
    <div className={clsx('elco-data-grid', className)} style={style}>
      {/* Toolbar */}
      <div className="elco-data-grid-toolbar" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 'var(--space-4)',
        padding: 'var(--space-4)',
        borderBottom: '1px solid var(--color-surface-border)',
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
          {toolbar && <div>{toolbar}</div>}
          {searchable && (
            <div className="elco-search" style={{ position: 'relative', flexShrink: 0 }}>
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                style={{
                  position: 'absolute',
                  left: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--color-text-tertiary)',
                  pointerEvents: 'none',
                }}
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder={searchPlaceholder}
                value={searchTerm}
                onChange={handleSearch}
                className="elco-input"
                style={{
                  width: '280px',
                  paddingLeft: '36px',
                  height: '36px',
                  fontSize: 'var(--font-size-sm)',
                }}
                aria-label={searchPlaceholder}
              />
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          {filterable && Object.entries(localFilters).map(([key, value]) => (
            <Badge
              key={key}
              variant="outline"
              size="sm"
              removable
              onRemove={() => handleFilterChange(key, undefined)}
              style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
            >
              {key}: {value}
            </Badge>
          ))}
          {exportable && (
            <Button variant="outline" size="sm" onClick={onExport} leftIcon={<DownloadIcon />}>
              Export
            </Button>
          )}
        </div>
      </div>

      {/* Table */}
      <Table
        columns={columns}
        data={paginatedData}
        keyField={keyField}
        sortable
        sortColumn={sortColumn}
        sortDirection={sortDirection}
        onSort={handleSort}
        selectable={selectable}
        selectedRows={selectedRows}
        onSelectionChange={onSelectionChange}
        loading={loading}
        emptyMessage={emptyMessage}
        rowActions={rowActions}
      />

      {/* Pagination */}
      {paginated && (
        <div className="elco-data-grid-pagination" style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--space-4)',
          borderTop: '1px solid var(--color-surface-border)',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
        }}>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
            Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, filteredData.length)} of {filteredData.length} results
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Select
              value={pageSize}
              onChange={(e) => onPageSizeChange?.(parseInt(e.target.value))}
              options={pageSizeOptions.map(size => ({ value: size, label: `${size} rows` }))}
              size="sm"
              style={{ width: 'auto' }}
            />
            <ButtonGroup>
              <IconButton
                icon={<ChevronLeftIcon />}
                size="iconSm"
                disabled={currentPage <= 1}
                onClick={() => onPageChange?.(currentPage - 1)}
                aria-label="Previous page"
              />
              <IconButton
                icon={<ChevronRightIcon />}
                size="iconSm"
                disabled={currentPage >= totalPages}
                onClick={() => onPageChange?.(currentPage + 1)}
                aria-label="Next page"
              />
            </ButtonGroup>
            <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-tertiary)' }}>
              Page {currentPage} of {totalPages || 1}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// Icon components for DataGrid
function DownloadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

import React from 'react';

export default Table;