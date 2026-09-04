import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Activity, Download, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import { formatDateTime } from '@/lib/utils'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'
import jsPDF from 'jspdf'
import 'jspdf-autotable'

export default function ActivityLogs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [dateRange, setDateRange] = useState({ from: '', to: '' })
  const [statusFilter, setStatusFilter] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 20,
    total_records: 0,
    total_pages: 0,
    has_next: false,
    has_prev: false
  })

  useEffect(() => {
    loadLogs()
  }, [pagination.page, searchTerm, dateRange.from, dateRange.to, statusFilter, actionFilter])

  const loadLogs = async () => {
    try {
      setLoading(true)
      const params = {
        page: pagination.page,
        per_page: pagination.per_page,
        search: searchTerm,
        from_date: dateRange.from,
        to_date: dateRange.to,
        status: statusFilter,
        action: actionFilter
      }
      
      // Remove empty params
      Object.keys(params).forEach(key => {
        if (params[key] === '' || params[key] === null || params[key] === undefined) {
          delete params[key]
        }
      })
      
      const response = await adminAPI.getActivityLogs(params)
      if (response.success) {
        setLogs(response.logs || [])
        if (response.pagination) {
          setPagination(response.pagination)
        }
      }
    } catch (error) {
      toast.error('Failed to load activity logs')
      console.error('Load logs error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    loadLogs()
  }

  const handleClearFilters = () => {
    setSearchTerm('')
    setDateRange({ from: '', to: '' })
    setStatusFilter('')
    setActionFilter('')
    setPagination(prev => ({ ...prev, page: 1 }))
  }

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }))
  }

  const downloadCSV = async () => {
    try {
      const params = {
        search: searchTerm,
        from_date: dateRange.from,
        to_date: dateRange.to,
        status: statusFilter,
        action: actionFilter
      }
      
      // Remove empty params
      Object.keys(params).forEach(key => {
        if (params[key] === '' || params[key] === null || params[key] === undefined) {
          delete params[key]
        }
      })
      
      await adminAPI.downloadActivityLogs(params)
      toast.success('CSV downloaded successfully!')
    } catch (error) {
      toast.error('Failed to download CSV')
      console.error('Download CSV error:', error)
    }
  }

  const exportToPDF = () => {
    const doc = new jsPDF()
    
    // Add header
    doc.setFontSize(18)
    doc.text('Activity Logs Report', 14, 20)
    
    // Add date
    doc.setFontSize(10)
    doc.text(`Generated on: ${new Date().toLocaleString()}`, 14, 28)
    
    // Add admin info
    const adminId = adminAPI.getAdminId()
    doc.text(`Admin ID: ${adminId}`, 14, 34)
    
    // Add filter info
    let yPos = 40
    if (searchTerm) {
      doc.text(`Search: ${searchTerm}`, 14, yPos)
      yPos += 6
    }
    if (dateRange.from || dateRange.to) {
      doc.text(`Date Range: ${dateRange.from || 'Start'} to ${dateRange.to || 'End'}`, 14, yPos)
      yPos += 6
    }
    if (statusFilter) {
      doc.text(`Status: ${statusFilter}`, 14, yPos)
      yPos += 6
    }
    if (actionFilter) {
      doc.text(`Action: ${actionFilter}`, 14, yPos)
      yPos += 6
    }
    
    // Prepare table data
    const tableData = logs.map((log, index) => [
      ((pagination.page - 1) * pagination.per_page) + index + 1,
      log.admin_id,
      log.action,
      log.ip_address || 'N/A',
      log.status,
      formatDateTime(log.created_at)
    ])
    
    // Add table
    doc.autoTable({
      startY: yPos + 5,
      head: [['#', 'Admin ID', 'Action', 'IP Address', 'Status', 'Date & Time']],
      body: tableData,
      theme: 'grid',
      headStyles: {
        fillColor: [59, 130, 246],
        textColor: 255,
        fontStyle: 'bold'
      },
      alternateRowStyles: {
        fillColor: [245, 247, 250]
      },
      styles: {
        fontSize: 9,
        cellPadding: 3
      }
    })
    
    // Add footer
    const pageCount = doc.internal.getNumberOfPages()
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i)
      doc.setFontSize(8)
      doc.text(
        `Page ${i} of ${pageCount}`,
        doc.internal.pageSize.getWidth() / 2,
        doc.internal.pageSize.getHeight() - 10,
        { align: 'center' }
      )
    }
    
    // Save PDF
    doc.save(`activity-logs-${new Date().toISOString().split('T')[0]}.pdf`)
    toast.success('PDF exported successfully!')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold">Activity Logs</h1>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline"
            onClick={loadLogs}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button 
            variant="outline"
            onClick={downloadCSV}
            disabled={!searchTerm && !dateRange.from && !dateRange.to && !statusFilter && !actionFilter}
            className="bg-blue-50 hover:bg-blue-100 border-blue-200 disabled:opacity-50"
          >
            <Download className="h-4 w-4 mr-2" />
            Download Filtered
          </Button>
          <Button 
            onClick={exportToPDF}
            disabled={logs.length === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            Export PDF
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <div>
              <Input
                placeholder="Search activities..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setPagination(prev => ({ ...prev, page: 1 }))
                }}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            
            <div>
              <Input
                type="date"
                placeholder="From Date"
                value={dateRange.from}
                onChange={(e) => {
                  setDateRange({ ...dateRange, from: e.target.value })
                  setPagination(prev => ({ ...prev, page: 1 }))
                }}
              />
            </div>
            
            <div>
              <Input
                type="date"
                placeholder="To Date"
                value={dateRange.to}
                onChange={(e) => {
                  setDateRange({ ...dateRange, to: e.target.value })
                  setPagination(prev => ({ ...prev, page: 1 }))
                }}
              />
            </div>
            
            <div>
              <select
                className="w-full border rounded-md p-2 h-10"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value)
                  setPagination(prev => ({ ...prev, page: 1 }))
                }}
              >
                <option value="">All Status</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="locked">Locked</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            
            <div>
              <select
                className="w-full border rounded-md p-2 h-10"
                value={actionFilter}
                onChange={(e) => {
                  setActionFilter(e.target.value)
                  setPagination(prev => ({ ...prev, page: 1 }))
                }}
              >
                <option value="">All Actions</option>
                <option value="login">Login</option>
                <option value="login_attempt">Login Attempt</option>
                <option value="logout">Logout</option>
                <option value="change_password">Change Password</option>
                <option value="change_pin">Change PIN</option>
              </select>
            </div>
            
            <div>
              <Button onClick={handleClearFilters} variant="outline" className="w-full">
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Activity History</CardTitle>
            <div className="text-sm text-gray-600">
              Showing {logs.length > 0 ? ((pagination.page - 1) * pagination.per_page) + 1 : 0} - {Math.min(pagination.page * pagination.per_page, pagination.total_records)} of {pagination.total_records} records
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">Loading activity logs...</p>
              </div>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>Admin ID</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>IP Address</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Date & Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                          No activity logs found
                        </TableCell>
                      </TableRow>
                    ) : (
                      logs.map((log, index) => (
                        <TableRow key={log.id}>
                          <TableCell>{((pagination.page - 1) * pagination.per_page) + index + 1}</TableCell>
                          <TableCell className="font-medium">{log.admin_id}</TableCell>
                          <TableCell>{log.action}</TableCell>
                          <TableCell>{log.ip_address || 'N/A'}</TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded-full text-xs ${
                              log.status.toLowerCase() === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                            }`}>
                              {log.status}
                            </span>
                          </TableCell>
                          <TableCell>{formatDateTime(log.created_at)}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
              
              {/* Pagination */}
              {pagination.total_pages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <div className="text-sm text-gray-600">
                    Page {pagination.page} of {pagination.total_pages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(pagination.page - 1)}
                      disabled={!pagination.has_prev}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(pagination.page + 1)}
                      disabled={!pagination.has_next}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
