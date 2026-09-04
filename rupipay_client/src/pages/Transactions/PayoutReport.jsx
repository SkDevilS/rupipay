import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { FileText, Download, RefreshCw, Calendar } from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'

// Helper function to format PG Partner names for display
const formatPGPartnerName = (pgPartner) => {
  if (!pgPartner) return '-';
  
  const nameMap = {
    'Paytouch2': 'PT2',
    'Paytouch3_Trendora': 'PT3',
    'PAYTOUCH2': 'PT2',
    'PAYTOUCH3_TRENDORA': 'PT3'
  };
  
  return nameMap[pgPartner] || pgPartner;
};

export default function PayoutReport() {
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [entriesPerPage, setEntriesPerPage] = useState(10)
  const [searchTerm, setSearchTerm] = useState('') // Server-side search
  const [quickFilter, setQuickFilter] = useState('') // Client-side quick filter
  const [currentPage, setCurrentPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [syncingStatus, setSyncingStatus] = useState({})

  useEffect(() => {
    loadPayoutReport()
  }, [statusFilter, fromDate, toDate])

  const loadPayoutReport = async (filters = {}) => {
    try {
      setLoading(true)
      
      // Build params from state and filters
      const params = {}
      if (fromDate || filters.from_date) params.from_date = filters.from_date || fromDate
      if (toDate || filters.to_date) params.to_date = filters.to_date || toDate
      if (statusFilter || filters.status) params.status = filters.status || statusFilter
      if (searchTerm) params.search = searchTerm
      
      const response = await clientAPI.getPayoutReport(params)
      if (response.success && response.data) {
        setTransactions(response.data)
      }
    } catch (error) {
      toast.error('Failed to load payout report')
      console.error('Payout report error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    setCurrentPage(1)
    loadPayoutReport()
    toast.success('Search applied successfully!')
  }

  const handleReset = () => {
    setFromDate('')
    setToDate('')
    setSearchTerm('')
    setStatusFilter('')
    setCurrentPage(1)
    loadPayoutReport({})
    toast.info('Filters reset')
  }

  const exportToCSV = async (type = 'current') => {
    try {
      setDownloading(true)
      let data = []

      if (type === 'all') {
        // Download all transactions with current filters
        const params = {}
        if (statusFilter) params.status = statusFilter
        if (searchTerm) params.search = searchTerm
        if (fromDate) params.from_date = fromDate
        if (toDate) params.to_date = toDate

        const response = await clientAPI.getAllPayoutReport(params)
        if (response.success) {
          data = response.data
        }
      } else if (type === 'today') {
        // Download today's transactions
        const response = await clientAPI.getTodayPayoutReport()
        if (response.success) {
          data = response.data
        }
      } else if (type === 'filtered') {
        // Download filtered transactions
        const hasFilters = statusFilter || searchTerm || fromDate || toDate
        
        if (!hasFilters) {
          toast.info('No filters applied. Use "Export All" to download all transactions.')
          setDownloading(false)
          return
        }

        const params = {}
        if (statusFilter) params.status = statusFilter
        if (searchTerm) params.search = searchTerm
        if (fromDate) params.from_date = fromDate
        if (toDate) params.to_date = toDate

        const response = await clientAPI.getAllPayoutReport(params)
        if (response.success) {
          data = response.data
        }
      } else {
        // Download current page
        data = filteredTransactions
      }

      if (data.length === 0) {
        toast.info('No transactions to export')
        return
      }

      const headers = ['Transaction ID', 'Reference ID', 'Order ID', 'Account No', 'Beneficiary Name', 'Bank Name', 'IFSC', 'Date', 'Amount', 'Charges', 'Amount Deducted', 'Status', 'UTR', 'Message']
      const rows = data.map(txn => {
        const amount = parseFloat(txn.amount || 0)
        const charges = parseFloat(txn.charge_amount || 0)
        const netAmount = amount - charges
        return [
          txn.txn_id || '-',
          txn.reference_id || '-',
          txn.order_id || '-',
          txn.account_no || '-',
          txn.bene_name || '-',
          txn.bene_bank || '-',
          txn.ifsc_code || '-',
          new Date(txn.created_at).toLocaleString(),
          netAmount,
          charges,
          amount,
          txn.status || '-',
          txn.utr || '-',
          txn.error_message || '-'
        ]
      })

      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n')

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const filename = type === 'today' 
        ? `payout-report-today-${new Date().toISOString().split('T')[0]}.csv`
        : type === 'all'
        ? `payout-report-all-${new Date().toISOString().split('T')[0]}.csv`
        : type === 'filtered'
        ? `payout-report-filtered-${new Date().toISOString().split('T')[0]}.csv`
        : `payout-report-${new Date().toISOString().split('T')[0]}.csv`
      a.download = filename
      a.click()
      window.URL.revokeObjectURL(url)
      
      toast.success(`Exported ${data.length} transactions`)
    } catch (error) {
      toast.error('Failed to export data')
      console.error(error)
    } finally {
      setDownloading(false)
    }
  }

  const handleCheckStatus = async (txn) => {
    try {
      setSyncingStatus(prev => ({ ...prev, [txn.txn_id]: true }))
      
      const response = await clientAPI.syncPayoutStatus(txn.txn_id)
      
      if (response.success) {
        toast.success('Status updated successfully')
        setTransactions(prevTransactions => 
          prevTransactions.map(t => 
            t.txn_id === txn.txn_id ? response.data : t
          )
        )
      } else {
        toast.error(response.message || 'Failed to check status')
      }
    } catch (error) {
      console.error('Check status error:', error)
      toast.error(error.message || 'Failed to check status')
    } finally {
      setSyncingStatus(prev => ({ ...prev, [txn.txn_id]: false }))
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getStatusBadge = (status) => {
    const statusUpper = (status || '').toUpperCase()
    if (statusUpper === 'SUCCESS' || statusUpper === 'COMPLETED') {
      return 'bg-green-100 text-green-700'
    } else if (statusUpper === 'FAILED' || statusUpper === 'REJECTED') {
      return 'bg-red-100 text-red-700'
    } else if (statusUpper === 'PENDING' || statusUpper === 'INITIATED' || statusUpper === 'QUEUED') {
      return 'bg-yellow-100 text-yellow-700'
    }
    return 'bg-gray-100 text-gray-700'
  }

  const filteredTransactions = transactions.filter(txn => {
    if (!quickFilter) return true
    const searchLower = quickFilter.toLowerCase()
    return (
      (txn.merchant_id || '').toLowerCase().includes(searchLower) ||
      (txn.txn_id || '').toLowerCase().includes(searchLower) ||
      (txn.reference_id || '').toLowerCase().includes(searchLower) ||
      (txn.order_id || '').toLowerCase().includes(searchLower) ||
      (txn.account_no || '').includes(searchLower) ||
      (txn.bene_name || '').toLowerCase().includes(searchLower) ||
      (txn.utr || '').toLowerCase().includes(searchLower)
    )
  })

  // Pagination calculations
  const totalPages = Math.ceil(filteredTransactions.length / entriesPerPage)
  const startIndex = (currentPage - 1) * entriesPerPage
  const endIndex = startIndex + entriesPerPage
  const currentTransactions = filteredTransactions.slice(startIndex, endIndex)

  const handlePageChange = (page) => {
    setCurrentPage(page)
  }

  const handlePrevious = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1)
    }
  }

  const handleNext = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header with Export Buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-orange-600" />
          <h1 className="text-3xl font-bold">Payout Report</h1>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => loadPayoutReport()}
            disabled={loading}
            variant="outline"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={() => exportToCSV('current')}
            disabled={downloading}
            className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800"
          >
            <Download className="h-4 w-4 mr-2" />
            Export Page
          </Button>
          <Button
            onClick={() => exportToCSV('filtered')}
            disabled={downloading || (!statusFilter && !searchTerm && !fromDate && !toDate)}
            variant="outline"
            className="bg-blue-50 hover:bg-blue-100 border-blue-200 disabled:opacity-50"
          >
            <Download className="h-4 w-4 mr-2" />
            Download Filtered
          </Button>
          <Button
            onClick={() => exportToCSV('all')}
            disabled={downloading}
            className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800"
          >
            <Download className="h-4 w-4 mr-2" />
            Export All
          </Button>
          <Button
            onClick={() => exportToCSV('today')}
            disabled={downloading}
            className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800"
          >
            <Calendar className="h-4 w-4 mr-2" />
            Today's Report
          </Button>
        </div>
      </div>

      {/* Search Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Search Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-12 gap-4 items-end">
            <div className="col-span-3">
              <Label className="text-sm font-medium">Search</Label>
              <Input
                placeholder="Search by TXN ID, Order ID, Reference ID, Account..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-9"
              />
            </div>
            <div className="col-span-2">
              <Label className="text-sm font-medium">Status</Label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All</option>
                <option value="SUCCESS">Success</option>
                <option value="FAILED">Failed</option>
                <option value="PENDING">Pending</option>
                <option value="QUEUED">Queued</option>
                <option value="INITIATED">Initiated</option>
              </select>
            </div>
            <div className="col-span-2">
              <Label className="text-sm font-medium">From Date</Label>
              <Input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="h-9"
              />
            </div>
            <div className="col-span-2">
              <Label className="text-sm font-medium">To Date</Label>
              <Input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="h-9"
              />
            </div>
            <div className="col-span-2">
              <Button 
                onClick={handleSearch}
                disabled={loading}
                className="w-full h-9 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800"
              >
                Search
              </Button>
            </div>
            <div className="col-span-2">
              <Button 
                onClick={handleReset}
                disabled={loading}
                variant="outline"
                className="w-full h-9"
              >
                Reset
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Transaction Table */}
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">Loading payout report...</p>
              </div>
            </div>
          ) : (
            <>
              {/* Table Controls */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm">Show</span>
                  <select
                    value={entriesPerPage}
                    onChange={(e) => {
                      setEntriesPerPage(Number(e.target.value))
                      setCurrentPage(1)
                    }}
                    className="flex h-9 w-20 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                  >
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                  <span className="text-sm">entries</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm">Quick Filter:</span>
                  <Input
                    value={quickFilter}
                    onChange={(e) => {
                      setQuickFilter(e.target.value)
                      setCurrentPage(1)
                    }}
                    className="w-64 h-9"
                    placeholder="Filter current page..."
                  />
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto border rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead className="font-semibold">TRANSACTION ID</TableHead>
                      <TableHead className="font-semibold">REFERENCE ID</TableHead>
                      <TableHead className="font-semibold">ORDER ID</TableHead>
                      <TableHead className="font-semibold">ACCOUNT NO</TableHead>
                      <TableHead className="font-semibold">BENEFICIARY NAME</TableHead>
                      <TableHead className="font-semibold">BANK NAME</TableHead>
                      <TableHead className="font-semibold">IFSC CODE</TableHead>
                      <TableHead className="font-semibold">DATE</TableHead>
                      <TableHead className="font-semibold">AMOUNT</TableHead>
                      <TableHead className="font-semibold">CHARGES</TableHead>
                      <TableHead className="font-semibold">AMOUNT DEDUCTED</TableHead>
                      <TableHead className="font-semibold">STATUS</TableHead>
                      <TableHead className="font-semibold">UTR</TableHead>
                      <TableHead className="font-semibold">MESSAGE</TableHead>
                      <TableHead className="font-semibold text-center">ACTIONS</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTransactions.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={15} className="text-center py-8 text-gray-500">
                          No payout transactions found
                        </TableCell>
                      </TableRow>
                    ) : (
                      currentTransactions.map((txn) => {
                        const amount = parseFloat(txn.amount || 0)
                        const charges = parseFloat(txn.charge_amount || 0)
                        const netAmount = amount - charges
                        return (
                          <TableRow key={txn.id} className="hover:bg-gray-50">
                            <TableCell className="font-mono text-xs">{txn.txn_id || '-'}</TableCell>
                            <TableCell className="font-mono text-xs">{txn.reference_id || '-'}</TableCell>
                            <TableCell className="font-mono text-xs">{txn.order_id || '-'}</TableCell>
                            <TableCell className="font-mono text-xs">{txn.account_no || '-'}</TableCell>
                            <TableCell>{txn.bene_name || '-'}</TableCell>
                            <TableCell>{txn.bene_bank || '-'}</TableCell>
                            <TableCell className="font-mono text-xs">{txn.ifsc_code || '-'}</TableCell>
                            <TableCell className="whitespace-nowrap">{formatDate(txn.created_at)}</TableCell>
                            <TableCell className="font-medium">₹{netAmount.toLocaleString()}</TableCell>
                            <TableCell className="text-center">{charges > 0 ? `₹${charges.toLocaleString()}` : '-'}</TableCell>
                            <TableCell className="font-medium text-green-700">₹{amount.toLocaleString()}</TableCell>
                            <TableCell>
                              <span className={`px-2 py-1 rounded text-xs font-medium inline-flex items-center gap-1 ${getStatusBadge(txn.status)}`}>
                                {txn.status === 'FAILED' && '⚠'}
                                {txn.status}
                              </span>
                            </TableCell>
                            <TableCell className="font-mono text-xs">{txn.utr || '-'}</TableCell>
                            <TableCell className="max-w-xs truncate">{txn.error_message || '-'}</TableCell>
                            <TableCell className="text-center">
                              {txn.status === 'INITIATED' && txn.pg_partner === 'Mudrape' && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleCheckStatus(txn)}
                                  disabled={syncingStatus[txn.txn_id]}
                                  className="text-xs h-7"
                                >
                                  <RefreshCw className={`h-3 w-3 mr-1 ${syncingStatus[txn.txn_id] ? 'animate-spin' : ''}`} />
                                  {syncingStatus[txn.txn_id] ? 'Checking...' : 'Check'}
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-4">
                <div className="text-sm text-gray-600">
                  Showing {startIndex + 1} to {Math.min(endIndex, filteredTransactions.length)} of {filteredTransactions.length} entries
                </div>
                <div className="flex gap-1">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handlePrevious}
                    disabled={currentPage === 1}
                    className="text-sm"
                  >
                    Previous
                  </Button>
                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                    let pageNum
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (currentPage <= 3) {
                      pageNum = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = currentPage - 2 + i
                    }
                    return (
                      <Button
                        key={pageNum}
                        variant={currentPage === pageNum ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePageChange(pageNum)}
                        className={`text-sm ${
                          currentPage === pageNum 
                            ? 'bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800' 
                            : ''
                        }`}
                      >
                        {pageNum}
                      </Button>
                    )
                  })}
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleNext}
                    disabled={currentPage === totalPages}
                    className="text-sm"
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
