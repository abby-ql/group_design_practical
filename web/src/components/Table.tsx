import { useState } from 'react'

interface Column<T> {
  key: keyof T
  label: string
  render?: (value: T[keyof T], item: T) => React.ReactNode
  sortable?: boolean | ((item: T) => string | number | null)
}

interface TableProps<T> {
  data: T[]
  columns: Column<T>[]
  onRowClick?: (item: T) => void
  className?: string
}

type SortDirection = 'asc' | 'desc' | null

export function Table<T>({ data, columns, onRowClick, className = '' }: TableProps<T>) {
  const [sortConfig, setSortConfig] = useState<{
    key: keyof T
    direction: SortDirection
  } | null>(null)

  const sortedData = data.slice().sort((a, b) => {
    if (!sortConfig) return 0

    const column = columns.find(col => col.key === sortConfig.key)
    if (!column) return 0

    let aValue: string | number | null
    let bValue: string | number | null

    if (typeof column.sortable === 'function') {
      aValue = column.sortable(a)
      bValue = column.sortable(b)
    } else {
      aValue = a[sortConfig.key] as string | number | null
      bValue = b[sortConfig.key] as string | number | null
    }

    if (aValue === null || aValue === undefined) return 1
    if (bValue === null || bValue === undefined) return -1

    if (aValue < bValue) {
      return sortConfig.direction === 'asc' ? -1 : 1
    }
    if (aValue > bValue) {
      return sortConfig.direction === 'asc' ? 1 : -1
    }
    return 0
  })

  const handleSort = (key: keyof T) => {
    let direction: SortDirection = 'asc'
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc'
    } else if (sortConfig && sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = null
    }
    setSortConfig(direction ? { key, direction } : null)
  }

  const getSortIcon = (columnKey: keyof T) => {
    if (!sortConfig || sortConfig.key !== columnKey) {
      return <span className="text-gray-400 ml-1">↕</span>
    }
    return (
      <span className="text-gray-600 ml-1">
        {sortConfig.direction === 'asc' ? '↑' : '↓'}
      </span>
    )
  }

  return (
    <table className={`w-full border-collapse ${className}`}>
      <thead>
        <tr>
          {columns.map((column) => (
            <th
              key={String(column.key)}
              className={`border-b border-gray-200 p-1.5 align-top ${
                column.sortable ? 'cursor-pointer hover:bg-gray-50' : ''
              }`}
              onClick={() => column.sortable && handleSort(column.key)}
            >
              <div className="flex items-center">
                {column.label}
                {column.sortable && getSortIcon(column.key)}
              </div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sortedData.map((item, index) => (
          <tr
            key={index}
            className={onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}
            onClick={() => onRowClick?.(item)}
          >
            {columns.map((column) => (
              <td
                key={String(column.key)}
                className="border-b border-gray-200 p-1.5 align-top"
              >
                {column.render
                  ? column.render(item[column.key], item)
                  : String(item[column.key] ?? '')
                }
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
