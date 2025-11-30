import { useState, useMemo, useRef, useEffect, useCallback } from 'react'
import { Save, X, Plus, Trash2, ChevronLeft, ChevronRight, Edit3, FileText, Settings, GripVertical, Undo2, Redo2, ChevronsLeft, ChevronsRight, Check, Pencil } from 'lucide-react'
import toast from 'react-hot-toast'
import apiClient from '../api/client'
import { CSVData } from '../types'

interface CSVEditorProps {
  data: CSVData
  onUpdate: (data: CSVData) => void
  onReset: () => void
}

const CSVEditor = ({ data, onUpdate, onReset }: CSVEditorProps) => {
  const [editedData, setEditedData] = useState<CSVData>(data)
  const [isSaving, setIsSaving] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageInput, setPageInput] = useState('')
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({})
  const [resizingColumn, setResizingColumn] = useState<string | null>(null)
  const [isEditingFilename, setIsEditingFilename] = useState(false)
  const [tempFilename, setTempFilename] = useState(data.filename)
  
  // Undo/Redo history
  const [history, setHistory] = useState<CSVData[]>([data])
  const [historyIndex, setHistoryIndex] = useState(0)
  const maxHistorySize = 50
  
  const tableRef = useRef<HTMLTableElement>(null)
  const rowsPerPage = 10

  // Initialize column widths
  useEffect(() => {
    if (editedData.headers.length > 0 && Object.keys(columnWidths).length === 0) {
      const initialWidths: Record<string, number> = {}
      editedData.headers.forEach(header => {
        initialWidths[header] = 150 // Default width
      })
      setColumnWidths(initialWidths)
    }
  }, [editedData.headers])

  // Update tempFilename when data changes
  useEffect(() => {
    setTempFilename(editedData.filename)
  }, [editedData.filename])

  // Save state to history
  const saveToHistory = (newData: CSVData) => {
    setHistory(prev => {
      const newHistory = prev.slice(0, historyIndex + 1)
      newHistory.push(JSON.parse(JSON.stringify(newData))) // Deep copy
      
      // Limit history size
      if (newHistory.length > maxHistorySize) {
        newHistory.shift()
        return newHistory
      }
      
      return newHistory
    })
    setHistoryIndex(prev => Math.min(prev + 1, maxHistorySize - 1))
  }

  // Undo function
  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1
      setHistoryIndex(newIndex)
      setEditedData(JSON.parse(JSON.stringify(history[newIndex]))) // Deep copy
      toast.success('Undone')
    } else {
      toast.error('Nothing to undo')
    }
  }, [historyIndex, history])

  // Redo function
  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1
      setHistoryIndex(newIndex)
      setEditedData(JSON.parse(JSON.stringify(history[newIndex]))) // Deep copy
      toast.success('Redone')
    } else {
      toast.error('Nothing to redo')
    }
  }, [historyIndex, history])


  // Handle column resize
  const handleMouseDown = (header: string, e: React.MouseEvent) => {
    e.preventDefault()
    setResizingColumn(header)
    const startX = e.pageX
    const startWidth = columnWidths[header] || 150

    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.pageX - startX
      const newWidth = Math.max(100, startWidth + diff) // Minimum width 100px
      setColumnWidths(prev => ({ ...prev, [header]: newWidth }))
    }

    const handleMouseUp = () => {
      setResizingColumn(null)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  // Debounce timer for cell changes
  const cellChangeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleCellChange = (rowIndex: number, header: string, value: string) => {
    const newRows = [...editedData.rows]
    newRows[rowIndex] = { ...newRows[rowIndex], [header]: value }
    const newData = { ...editedData, rows: newRows, row_count: newRows.length }
    setEditedData(newData)
    
    // Debounce history saving for cell changes (save after 1 second of no changes)
    if (cellChangeTimerRef.current) {
      clearTimeout(cellChangeTimerRef.current)
    }
    cellChangeTimerRef.current = setTimeout(() => {
      saveToHistory(newData)
    }, 1000)
  }

  const handleAddRow = () => {
    const newRow: Record<string, string> = {}
    editedData.headers.forEach(header => {
      newRow[header] = ''
    })
    const newData = {
      ...editedData,
      rows: [...editedData.rows, newRow],
      row_count: editedData.rows.length + 1,
    }
    setEditedData(newData)
    saveToHistory(newData)
    toast.success('Row added')
  }

  const handleDeleteRow = (rowIndex: number) => {
    const newRows = editedData.rows.filter((_, index) => index !== rowIndex)
    const newData = {
      ...editedData,
      rows: newRows,
      row_count: newRows.length,
    }
    setEditedData(newData)
    saveToHistory(newData)
    
    // Adjust current page if needed
    const totalPages = Math.ceil(newRows.length / rowsPerPage)
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(totalPages)
    }
    
    toast.success('Row deleted')
  }

  // Pagination calculations
  const totalPages = Math.ceil(editedData.rows.length / rowsPerPage)
  const startIndex = (currentPage - 1) * rowsPerPage
  const endIndex = startIndex + rowsPerPage
  const currentRows = useMemo(() => {
    return editedData.rows.slice(startIndex, endIndex)
  }, [editedData.rows, startIndex, endIndex])

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage)
      setPageInput('')
      // Don't scroll - keep page position stable
    }
  }

  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    if (value === '' || (/^\d+$/.test(value) && parseInt(value) >= 1 && parseInt(value) <= totalPages)) {
      setPageInput(value)
    }
  }

  const handlePageInputSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (pageInput) {
      const page = parseInt(pageInput)
      if (page >= 1 && page <= totalPages) {
        handlePageChange(page)
      }
    }
  }

  // Smart pagination: generate page numbers to display
  const getPageNumbers = (): (number | string)[] => {
    const pages: (number | string)[] = []
    const maxVisible = 7 // Maximum number of page buttons to show
    
    if (totalPages <= maxVisible) {
      // Show all pages if total is small
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }

    // Always show first page
    pages.push(1)

    // Calculate start and end of visible range around current page
    let start = Math.max(2, currentPage - 1)
    let end = Math.min(totalPages - 1, currentPage + 1)

    // Adjust if we're near the beginning
    if (currentPage <= 3) {
      end = Math.min(5, totalPages - 1)
    }

    // Adjust if we're near the end
    if (currentPage >= totalPages - 2) {
      start = Math.max(2, totalPages - 4)
    }

    // Add ellipsis and pages
    if (start > 2) {
      pages.push('ellipsis-start')
    }

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }

    if (end < totalPages - 1) {
      pages.push('ellipsis-end')
    }

    // Always show last page
    if (totalPages > 1) {
      pages.push(totalPages)
    }

    return pages
  }

  // Update page when data changes
  useMemo(() => {
    const newTotalPages = Math.ceil(editedData.rows.length / rowsPerPage)
    if (currentPage > newTotalPages && newTotalPages > 0) {
      setCurrentPage(newTotalPages)
    } else if (currentPage < 1 && editedData.rows.length > 0) {
      setCurrentPage(1)
    }
  }, [editedData.rows.length, currentPage])

  // Keyboard shortcuts for undo/redo
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        handleUndo()
      } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault()
        handleRedo()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [historyIndex, history, handleUndo, handleRedo])

  const handleFilenameChange = (newFilename: string) => {
    // Ensure filename ends with .csv
    const filename = newFilename.endsWith('.csv') ? newFilename : `${newFilename}.csv`
    const newData = { ...editedData, filename }
    setEditedData(newData)
    saveToHistory(newData)
  }

  const handleFilenameEdit = () => {
    setIsEditingFilename(true)
    setTempFilename(editedData.filename)
  }

  const handleFilenameSave = () => {
    if (tempFilename.trim()) {
      handleFilenameChange(tempFilename.trim())
    }
    setIsEditingFilename(false)
  }

  const handleFilenameCancel = () => {
    setTempFilename(editedData.filename)
    setIsEditingFilename(false)
  }

  const handleFilenameKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleFilenameSave()
    } else if (e.key === 'Escape') {
      handleFilenameCancel()
    }
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const response = await apiClient.post(
        '/files/save/',
        {
          filename: editedData.filename,
          headers: editedData.headers,
          rows: editedData.rows,
        },
        {
          responseType: 'blob',
        }
      )

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', editedData.filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      toast.success('File saved successfully!')
      onUpdate(editedData)
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to save file'
      toast.error(errorMessage)
    } finally {
      setIsSaving(false)
    }
  }

  // Color theme: #2596be with variations
  const primaryColor = '#2596be'
  const primaryDark = '#1a7a9a'  // Darker shade

  return (
    <div 
      className="rounded-3xl overflow-hidden transition-all duration-300"
      style={{ 
        background: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(0, 0, 0, 0.08)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)'
      }}
    >
      <div 
        className="p-8 border-b"
        style={{ 
          background: `linear-gradient(135deg, ${primaryColor} 0%, ${primaryDark} 100%)`,
          borderColor: 'rgba(255, 255, 255, 0.1)'
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div 
              className="p-3 rounded-2xl backdrop-blur-xl transition-all duration-300"
              style={{ 
                background: 'rgba(255, 255, 255, 0.15)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)'
              }}
            >
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <h2 className="text-3xl font-semibold tracking-tight text-white">CSV Editor</h2>
              <div className="text-sm text-white/90 mt-1 flex items-center gap-2 flex-wrap">
                {isEditingFilename ? (
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <input
                      type="text"
                      value={tempFilename}
                      onChange={(e) => setTempFilename(e.target.value)}
                      onKeyDown={handleFilenameKeyDown}
                      onBlur={handleFilenameSave}
                      className="px-2 py-1 rounded bg-white/20 backdrop-blur-sm border border-white/30 text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-white/50 min-w-0 flex-1"
                      style={{ maxWidth: '300px' }}
                      placeholder="Enter filename..."
                      autoFocus
                    />
                    <button
                      onClick={handleFilenameSave}
                      className="p-1 rounded hover:bg-white/20 transition-colors"
                      title="Save filename (Enter)"
                    >
                      <Check className="w-4 h-4 text-white" />
                    </button>
                    <button
                      onClick={handleFilenameCancel}
                      className="p-1 rounded hover:bg-white/20 transition-colors"
                      title="Cancel (Esc)"
                    >
                      <X className="w-4 h-4 text-white" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="truncate">{editedData.filename}</span>
                    <button
                      onClick={handleFilenameEdit}
                      className="p-1 rounded hover:bg-white/20 transition-colors flex-shrink-0"
                      title="Edit filename"
                    >
                      <Pencil className="w-3 h-3 text-white/80" />
                    </button>
                    <span className="flex-shrink-0">•</span>
                    <span className="flex-shrink-0">{editedData.row_count} rows</span>
                    <span className="flex-shrink-0">•</span>
                    <span className="flex-shrink-0">{editedData.headers.length} columns</span>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Undo/Redo buttons */}
            <div 
              className="flex items-center gap-0.5 rounded-xl p-1 backdrop-blur-xl"
              style={{ 
                background: 'rgba(255, 255, 255, 0.15)',
                border: '1px solid rgba(255, 255, 255, 0.2)'
              }}
            >
              <button
                onClick={handleUndo}
                disabled={historyIndex === 0}
                className="flex items-center justify-center p-2.5 text-white rounded-lg hover:bg-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200"
                title="Undo (Ctrl+Z)"
              >
                <Undo2 className="w-4 h-4" />
              </button>
              <div className="w-px h-6 bg-white/20"></div>
              <button
                onClick={handleRedo}
                disabled={historyIndex >= history.length - 1}
                className="flex items-center justify-center p-2.5 text-white rounded-lg hover:bg-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200"
                title="Redo (Ctrl+Y or Ctrl+Shift+Z)"
              >
                <Redo2 className="w-4 h-4" />
              </button>
            </div>
            
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2.5 px-5 py-2.5 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium shadow-lg hover:shadow-xl"
              style={{ 
                backgroundColor: 'white', 
                color: primaryColor,
                transform: 'translateY(0)'
              }}
              onMouseEnter={(e) => {
                if (!e.currentTarget.disabled) {
                  e.currentTarget.style.transform = 'translateY(-1px)'
                  e.currentTarget.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.15)'
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.12)'
              }}
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={onReset}
              className="flex items-center gap-2.5 px-5 py-2.5 rounded-xl backdrop-blur-xl transition-all duration-200"
              style={{ 
                background: 'rgba(255, 255, 255, 0.15)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: 'white'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.25)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)'
              }}
            >
              <X className="w-4 h-4" />
              Close
            </button>
          </div>
        </div>
      </div>

      <div className="p-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div 
              className="p-2.5 rounded-xl"
              style={{ 
                background: `linear-gradient(135deg, ${primaryColor}15 0%, ${primaryColor}08 100%)`,
                border: `1px solid ${primaryColor}20`
              }}
            >
              <Settings className="w-5 h-5" style={{ color: primaryColor }} />
            </div>
            <div>
              <h3 className="text-xl font-semibold tracking-tight" style={{ color: '#1d1d1f' }}>Data Table</h3>
              <p className="text-sm mt-1 flex items-center gap-1.5" style={{ color: '#86868b' }}>
                Showing {startIndex + 1}-{Math.min(endIndex, editedData.rows.length)} of {editedData.rows.length} rows
              </p>
            </div>
          </div>
          <button
            onClick={handleAddRow}
            className="flex items-center gap-2.5 px-5 py-2.5 text-white rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl font-medium"
            style={{ 
              backgroundColor: primaryColor,
              transform: 'translateY(0)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = primaryDark
              e.currentTarget.style.transform = 'translateY(-1px)'
              e.currentTarget.style.boxShadow = '0 12px 40px rgba(37, 150, 190, 0.25)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = primaryColor
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 8px 24px rgba(37, 150, 190, 0.2)'
            }}
          >
            <Plus className="w-4 h-4" />
            Add Row
          </button>
        </div>

        <div 
          className="overflow-x-auto rounded-2xl"
          style={{ 
            border: '1px solid rgba(0, 0, 0, 0.06)',
            boxShadow: '0 2px 16px rgba(0, 0, 0, 0.04)'
          }}
          id="csv-table-container"
        >
          <table ref={tableRef} className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr style={{ background: `linear-gradient(to right, ${primaryColor}, ${primaryDark})` }}>
                <th 
                  className="px-5 py-4 text-center text-xs font-semibold text-white uppercase tracking-wider sticky left-0 z-10" 
                  style={{ 
                    backgroundColor: primaryColor, 
                    minWidth: '90px', 
                    width: '90px',
                    borderRight: '1px solid rgba(255, 255, 255, 0.1)'
                  }}
                >
                  <div className="flex items-center justify-center gap-2">
                    <Settings className="w-4 h-4" />
                    <span>Actions</span>
                  </div>
                </th>
                {editedData.headers.map((header) => (
                  <th
                    key={header}
                    className="px-5 py-4 text-left text-xs font-semibold text-white uppercase tracking-wider relative group"
                    style={{ 
                      width: columnWidths[header] || 150, 
                      minWidth: columnWidths[header] || 150,
                      borderRight: '1px solid rgba(255, 255, 255, 0.1)'
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate pr-2">{header}</span>
                      <div
                        className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-white/30 transition-colors flex items-center justify-center"
                        onMouseDown={(e) => handleMouseDown(header, e)}
                        style={{ cursor: resizingColumn === header ? 'col-resize' : 'col-resize' }}
                      >
                        <GripVertical className="w-3 h-3 text-white/60 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody style={{ background: 'white' }}>
              {currentRows.map((row, displayIndex) => {
                const actualRowIndex = startIndex + displayIndex
                const isEven = displayIndex % 2 === 0
                return (
                  <tr 
                    key={actualRowIndex} 
                    className="transition-all duration-200"
                    style={{ 
                      backgroundColor: isEven ? 'white' : 'rgba(249, 250, 251, 0.5)',
                      borderBottom: '1px solid rgba(0, 0, 0, 0.04)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = `${primaryColor}08`
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = isEven ? 'white' : 'rgba(249, 250, 251, 0.5)'
                    }}
                  >
                    <td 
                      className="px-5 py-4 whitespace-nowrap sticky left-0 z-10" 
                      style={{ 
                        minWidth: '90px', 
                        width: '90px',
                        backgroundColor: 'inherit',
                        borderRight: '1px solid rgba(0, 0, 0, 0.06)'
                      }}
                    >
                      <div className="flex items-center justify-center">
                        <button
                          onClick={() => handleDeleteRow(actualRowIndex)}
                          className="flex items-center justify-center p-2.5 rounded-xl transition-all duration-200"
                          style={{ 
                            color: '#dc2626',
                            backgroundColor: '#fee2e2',
                            border: '1px solid #fecaca',
                            boxShadow: '0 2px 8px rgba(220, 38, 38, 0.1)'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.color = 'white'
                            e.currentTarget.style.backgroundColor = '#ef4444'
                            e.currentTarget.style.borderColor = '#ef4444'
                            e.currentTarget.style.transform = 'scale(1.05)'
                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(239, 68, 68, 0.25)'
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.color = '#dc2626'
                            e.currentTarget.style.backgroundColor = '#fee2e2'
                            e.currentTarget.style.borderColor = '#fecaca'
                            e.currentTarget.style.transform = 'scale(1)'
                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(220, 38, 38, 0.1)'
                          }}
                          title="Delete row"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                    {editedData.headers.map((header) => (
                      <td key={header} className="px-5 py-4 whitespace-nowrap group relative">
                        <div className="relative">
                          <input
                            type="text"
                            value={row[header] || ''}
                            onChange={(e) => handleCellChange(actualRowIndex, header, e.target.value)}
                            className="w-full px-4 py-2.5 border rounded-xl focus:outline-none focus:ring-2 transition-all duration-200 bg-white text-sm"
                            style={{ 
                              borderColor: 'rgba(0, 0, 0, 0.1)',
                              '--focus-color': primaryColor
                            } as React.CSSProperties}
                            onFocus={(e) => {
                              e.currentTarget.style.borderColor = primaryColor
                              e.currentTarget.style.boxShadow = `0 0 0 3px ${primaryColor}20`
                              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.95)'
                            }}
                            onBlur={(e) => {
                              e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.1)'
                              e.currentTarget.style.boxShadow = 'none'
                              e.currentTarget.style.backgroundColor = 'white'
                            }}
                            onMouseEnter={(e) => {
                              if (document.activeElement !== e.currentTarget) {
                                e.currentTarget.style.borderColor = `${primaryColor}60`
                                e.currentTarget.style.backgroundColor = 'rgba(249, 250, 251, 0.8)'
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (document.activeElement !== e.currentTarget) {
                                e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.1)'
                                e.currentTarget.style.backgroundColor = 'white'
                              }
                            }}
                            placeholder="Enter value..."
                          />
                          <Edit3 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                        </div>
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {editedData.rows.length === 0 && (
          <div className="text-center py-16">
            <div 
              className="inline-flex items-center justify-center w-20 h-20 rounded-2xl mb-5"
              style={{ 
                background: `linear-gradient(135deg, ${primaryColor}15 0%, ${primaryColor}08 100%)`,
                border: `1px solid ${primaryColor}20`
              }}
            >
              <FileText className="w-10 h-10" style={{ color: primaryColor }} />
            </div>
            <p className="text-lg font-semibold tracking-tight mb-2" style={{ color: '#1d1d1f' }}>No data rows</p>
            <p className="text-sm" style={{ color: '#86868b' }}>Click "Add Row" to add data</p>
          </div>
        )}

        {/* Pagination Controls - Fixed height to prevent layout shifts */}
        {editedData.rows.length > 0 && (
          <div 
            className="mt-8" 
            style={{ 
              minHeight: totalPages > 1 ? '140px' : '0px',
              borderTop: '1px solid rgba(0, 0, 0, 0.06)'
            }}
          >
            {totalPages > 1 ? (
              <div className="pt-8">
                <div className="flex flex-col gap-4">
                  {/* Main pagination controls - Fixed width container */}
                  <div className="flex items-center justify-center">
                    <div className="flex items-center gap-2" style={{ minWidth: '500px', justifyContent: 'center' }}>
                      {/* First page button */}
                      <button
                        onClick={() => handlePageChange(1)}
                        disabled={currentPage === 1}
                        className="flex items-center justify-center w-10 h-10 rounded-xl border transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed flex-shrink-0"
                        style={currentPage === 1 
                          ? { 
                              backgroundColor: 'rgba(0, 0, 0, 0.04)', 
                              borderColor: 'rgba(0, 0, 0, 0.08)', 
                              color: '#86868b',
                              boxShadow: 'none'
                            }
                          : { 
                              backgroundColor: 'white', 
                              borderColor: 'rgba(0, 0, 0, 0.1)', 
                              color: primaryColor,
                              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
                            }
                        }
                        onMouseEnter={(e) => {
                          if (!e.currentTarget.disabled && currentPage !== 1) {
                            e.currentTarget.style.backgroundColor = primaryColor
                            e.currentTarget.style.color = 'white'
                            e.currentTarget.style.borderColor = primaryColor
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!e.currentTarget.disabled && currentPage !== 1) {
                            e.currentTarget.style.backgroundColor = 'white'
                            e.currentTarget.style.color = primaryColor
                            e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.1)'
                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.04)'
                          }
                        }}
                        title="First page"
                      >
                        <ChevronsLeft className="w-5 h-5" />
                      </button>

                      {/* Previous page button */}
                      <button
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                        className="flex items-center justify-center w-10 h-10 rounded-xl border transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed flex-shrink-0"
                        style={currentPage === 1 
                          ? { 
                              backgroundColor: 'rgba(0, 0, 0, 0.04)', 
                              borderColor: 'rgba(0, 0, 0, 0.08)', 
                              color: '#86868b',
                              boxShadow: 'none'
                            }
                          : { 
                              backgroundColor: 'white', 
                              borderColor: 'rgba(0, 0, 0, 0.1)', 
                              color: primaryColor,
                              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
                            }
                        }
                        onMouseEnter={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = primaryColor
                            e.currentTarget.style.color = 'white'
                            e.currentTarget.style.borderColor = primaryColor
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = 'white'
                            e.currentTarget.style.color = primaryColor
                            e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.1)'
                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.04)'
                          }
                        }}
                        title="Previous page"
                      >
                        <ChevronLeft className="w-5 h-5" />
                      </button>

                      {/* Page number buttons - Fixed width container */}
                      <div className="flex items-center gap-1 justify-center" style={{ minWidth: '280px', maxWidth: '280px' }}>
                        {getPageNumbers().map((page, idx) => {
                          if (page === 'ellipsis-start' || page === 'ellipsis-end') {
                            return (
                              <span key={`ellipsis-${idx}`} className="px-2 text-gray-400 font-medium flex-shrink-0" style={{ width: '32px', textAlign: 'center' }}>
                                ...
                              </span>
                            )
                          }
                          
                          const pageNum = page as number
                          const isActive = currentPage === pageNum
                          
                          return (
                            <button
                              key={pageNum}
                              onClick={() => handlePageChange(pageNum)}
                              className="flex items-center justify-center w-10 h-10 rounded-xl border font-medium transition-all duration-200 flex-shrink-0"
                              style={isActive
                                ? { 
                                    backgroundColor: primaryColor, 
                                    color: 'white', 
                                    borderColor: primaryColor,
                                    boxShadow: `0 4px 16px ${primaryColor}30`
                                  }
                                : { 
                                    backgroundColor: 'white', 
                                    color: primaryColor, 
                                    borderColor: 'rgba(0, 0, 0, 0.1)',
                                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
                                  }
                              }
                              onMouseEnter={(e) => {
                                if (!isActive) {
                                  e.currentTarget.style.backgroundColor = `${primaryColor}15`
                                  e.currentTarget.style.borderColor = primaryColor
                                }
                              }}
                              onMouseLeave={(e) => {
                                if (!isActive) {
                                  e.currentTarget.style.backgroundColor = 'white'
                                  e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.1)'
                                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.04)'
                                }
                              }}
                            >
                              {pageNum}
                            </button>
                          )
                        })}
                      </div>

                      {/* Next page button */}
                      <button
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage === totalPages}
                        className="flex items-center justify-center w-10 h-10 rounded-xl border transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed flex-shrink-0"
                        style={currentPage === totalPages 
                          ? { 
                              backgroundColor: 'rgba(0, 0, 0, 0.04)', 
                              borderColor: 'rgba(0, 0, 0, 0.08)', 
                              color: '#86868b',
                              boxShadow: 'none'
                            }
                          : { 
                              backgroundColor: 'white', 
                              borderColor: 'rgba(0, 0, 0, 0.1)', 
                              color: primaryColor,
                              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
                            }
                        }
                        onMouseEnter={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = primaryColor
                            e.currentTarget.style.color = 'white'
                            e.currentTarget.style.borderColor = primaryColor
                            e.currentTarget.style.boxShadow = `0 4px 16px ${primaryColor}30`
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = 'white'
                            e.currentTarget.style.color = primaryColor
                            e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.1)'
                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.04)'
                          }
                        }}
                        title="Next page"
                      >
                        <ChevronRight className="w-5 h-5" />
                      </button>

                      {/* Last page button */}
                      <button
                        onClick={() => handlePageChange(totalPages)}
                        disabled={currentPage === totalPages}
                        className="flex items-center justify-center w-10 h-10 rounded-xl border transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed flex-shrink-0"
                        style={currentPage === totalPages 
                          ? { 
                              backgroundColor: 'rgba(0, 0, 0, 0.04)', 
                              borderColor: 'rgba(0, 0, 0, 0.08)', 
                              color: '#86868b',
                              boxShadow: 'none'
                            }
                          : { 
                              backgroundColor: 'white', 
                              borderColor: 'rgba(0, 0, 0, 0.1)', 
                              color: primaryColor,
                              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
                            }
                        }
                        onMouseEnter={(e) => {
                          if (!e.currentTarget.disabled && currentPage !== totalPages) {
                            e.currentTarget.style.backgroundColor = primaryColor
                            e.currentTarget.style.color = 'white'
                            e.currentTarget.style.borderColor = primaryColor
                            e.currentTarget.style.boxShadow = `0 4px 16px ${primaryColor}30`
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!e.currentTarget.disabled && currentPage !== totalPages) {
                            e.currentTarget.style.backgroundColor = 'white'
                            e.currentTarget.style.color = primaryColor
                            e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.1)'
                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.04)'
                          }
                        }}
                        title="Last page"
                      >
                        <ChevronsRight className="w-5 h-5" />
                      </button>
                    </div>
                  </div>

                  {/* Page info and jump to page - Fixed height */}
                  <div className="flex items-center justify-center gap-4 flex-wrap" style={{ minHeight: '40px' }}>
                    <div className="flex items-center gap-2 text-sm font-medium" style={{ color: primaryColor }}>
                      <FileText className="w-4 h-4 flex-shrink-0" />
                      <span>Page <span className="font-bold">{currentPage}</span> of <span className="font-bold">{totalPages}</span></span>
                      <span className="text-gray-400">•</span>
                      <span className="text-gray-600">Showing {startIndex + 1}-{Math.min(endIndex, editedData.rows.length)} of {editedData.rows.length} rows</span>
                    </div>
                    
                    {/* Jump to page input */}
                    <form onSubmit={handlePageInputSubmit} className="flex items-center gap-2 flex-shrink-0">
                      <label htmlFor="page-input" className="text-sm font-medium text-gray-700 whitespace-nowrap">
                        Go to:
                      </label>
                      <input
                        id="page-input"
                        type="text"
                        value={pageInput}
                        onChange={handlePageInputChange}
                        placeholder={currentPage.toString()}
                        className="w-16 px-2 py-1 text-center border border-gray-300 rounded-lg focus:outline-none focus:ring-2 transition-all text-sm font-medium"
                        style={{
                          '--focus-color': primaryColor
                        } as React.CSSProperties}
                        onFocus={(e) => {
                          e.currentTarget.style.borderColor = primaryColor
                          e.currentTarget.style.boxShadow = `0 0 0 2px ${primaryColor}40`
                        }}
                        onBlur={(e) => {
                          e.currentTarget.style.borderColor = '#d1d5db'
                          e.currentTarget.style.boxShadow = 'none'
                        }}
                      />
                      <button
                        type="submit"
                        className="px-3 py-1 text-sm font-medium text-white rounded-lg transition-all shadow-sm whitespace-nowrap"
                        style={{ backgroundColor: primaryColor }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = primaryDark
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = primaryColor
                        }}
                      >
                        Go
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            ) : (
              <div className="pt-6" style={{ minHeight: '40px' }}>
                <div className="flex items-center justify-center">
                  <div className="flex items-center gap-2 text-sm font-medium" style={{ color: primaryColor }}>
                    <FileText className="w-4 h-4" />
                    <span className="text-gray-600">Showing all {editedData.rows.length} rows</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default CSVEditor

