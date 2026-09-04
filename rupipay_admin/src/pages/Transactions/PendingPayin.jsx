import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Clock, Download, Check, X, Search, RefreshCw, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'

export default function PendingPayin() {
  const [fromDate, setFromDate] = useState('2026-02-01')
  const [toDate, setToDate] = useState('2026-02-13')
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [showFilters, setShowFilters] = useState(false)
  const [entriesPerPage, setEntriesPerPage] = useState(10)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedTxn, setSelectedTxn] = useState(null)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [confirmAction, setConfirmAction] = useState(null)
  const [remarks, setRemarks] = useState('')
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    fetchPendingTransactions()
  }, [])

  const fetchPendingTransactions = async () => {
    try {
      setLoading(true)
      const response = await adminAPI.getPendingPayin()
      
      if (response.success) {
        setTransactions(response.transactions)
      }
    } catch (error) {
      toast.error('Failed to load pending transactions')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleCheckStatus = async (txn) => {
    try {
      toast.info('Checking transaction status...')
      const response = await adminAPI.checkPayinStatus(txn.txn_id)
      
      if (response.success) {
        const updatedTxn = response.transaction
        toast.success(`Status: ${updatedTxn.status}`)
        
        // Update local state
        setTransactions(prev => 
          prev.map(t => t.txn_id === txn.txn_id ? updatedTxn : t)
        )
        
        // If status changed, refresh list
        if (updatedTxn.status !== 'INITIATED' && updatedTxn.status !== 'PENDING') {
          setTimeout(fetchPendingTransactions, 1000)
        }
      }
    } catch (error) {
      toast.error('Failed to check status')
      console.error(error)
    }
  }

  const handleManualAction = (txn, action) => {
    setSelectedTxn(txn)
    setConfirmAction(action)
    setRemarks('')
    setShowConfirmDialog(true)
  }

  const confirmManualAction = async () => {
    if (!selectedTxn || !confirmAction) return
    
    try {
      setProcessing(true)
      const response = await adminAPI.manualCompletePayin(
        selectedTxn.txn_id,
        confirmAction,
        remarks
      )
      
      if (response.success) {
        toast.success(response.message)
        setShowConfirmDialog(false)
        setSelectedTxn(null)
        setConfirmAction(null)
        setRemarks('')
        
        // Refresh list
        fetchPendingTransactions()
      }
    } catch (error) {
      toast.error(error.message || 'Failed to process transaction')
      console.error(error)
    } finally {
      setProcessing(false)
    }
  }

  const handleExport = () => {
    const headers = ['Transaction ID', 'Order ID', 'Merchant', 'Amount', 'Charge', 'Net Amount', 'Status', 'Date']
    const rows = filteredTransactions.map(txn => [
      txn.txn_id,
      txn.order_id,
      txn.merchant_name || txn.merchant_id,
      txn.amount,
      txn.charge_amount,
      txn.net_amount,
      txn.status,
      formatDate(txn.created_at)
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pending-payin-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount)
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const filteredTransactions = transactions.filter(txn => {
    if (!searchTerm) return true
    const search = searchTerm.toLowerCase()
    return (
      txn.txn_id?.toLowerCase().includes(search) ||
      txn.order_id?.toLowerCase().includes(search) ||
      txn.merchant_id?.toLowerCase().includes(search) ||
      txn.merchant_name?.toLowerCase().includes(search) ||
      txn.payee_mobile?.includes(search)
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading pending transactions...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header with Export and Search Buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Clock className="h-8 w-8 text-orange-600" />
          <div>
            <h1 className="text-3xl font-bold">Pending Pay In</h1>
            <p className="text-sm text-gray-500 mt-1">
              {transactions.length} pending transaction{transactions.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={fetchPendingTransactions}
            variant="outline"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button
            onClick={handleExport}
            className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800"
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Transaction Table */}
      <Card>
        <CardContent className="pt-6">
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
              <span className="text-sm">Search:</span>
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-64 h-9"
                placeholder="Search by TXN ID, Order ID, Merchant..."
              />
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50">
                  <TableHead className="font-semibold">TRANSACTION ID</TableHead>
                  <TableHead className="font-semibold">ORDER ID</TableHead>
                  <TableHead className="font-semibold">MERCHANT</TableHead>
                  <TableHead className="font-semibold">CUSTOMER</TableHead>
                  <TableHead className="font-semibold">AMOUNT</TableHead>
                  <TableHead className="font-semibold">CHARGE</TableHead>
                  <TableHead className="font-semibold">NET AMOUNT</TableHead>
                  <TableHead className="font-semibold">STATUS</TableHead>
                  <TableHead className="font-semibold">DATE</TableHead>
                  <TableHead className="font-semibold text-center">ACTIONS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {currentTransactions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center py-8 text-gray-500">
                      <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                      <p>No pending transactions found</p>
                    </TableCell>
                  </TableRow>
                ) : (
                  currentTransactions.map((txn) => (
                    <TableRow key={txn.id} className="hover:bg-gray-50">
                      <TableCell className="font-mono text-xs">{txn.txn_id}</TableCell>
                      <TableCell className="font-mono text-xs">{txn.order_id}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{txn.merchant_name}</div>
                          <div className="text-xs text-gray-500">{txn.merchant_id}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="text-sm">{txn.payee_name || '-'}</div>
                          <div className="text-xs text-gray-500">{txn.payee_mobile || '-'}</div>
                        </div>
                      </TableCell>
                      <TableCell className="font-semibold">{formatAmount(txn.amount)}</TableCell>
                      <TableCell className="text-red-600">
                        -{formatAmount(txn.charge_amount)}
                      </TableCell>
                      <TableCell className="font-semibold text-green-600">
                        {formatAmount(txn.net_amount)}
                      </TableCell>
                      <TableCell>
                        <Badge className="bg-blue-500">
                          {txn.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm whitespace-nowrap">{formatDate(txn.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex gap-1 justify-center">
                          <Button
                            size="sm"
                            onClick={() => handleCheckStatus(txn)}
                            className="bg-purple-600 hover:bg-purple-700 text-white text-xs h-7 px-2"
                            title="Check Status"
                          >
                            <RefreshCw className="h-3 w-3" />
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleManualAction(txn, 'success')}
                            className="bg-green-600 hover:bg-green-700 text-white text-xs h-7 px-2"
                            title="Mark as Success"
                          >
                            <Check className="h-3 w-3" />
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleManualAction(txn, 'failed')}
                            className="bg-red-600 hover:bg-red-700 text-white text-xs h-7 px-2"
                            title="Mark as Failed"
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <div className="text-sm text-gray-600">
                Pages {currentPage} / {totalPages}
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
          )}
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {confirmAction === 'success' ? 'Confirm Success' : 'Confirm Failure'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-gray-50 p-4 rounded-lg space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Transaction ID:</span>
                <span className="font-mono">{selectedTxn?.txn_id}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Order ID:</span>
                <span className="font-mono">{selectedTxn?.order_id}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Amount:</span>
                <span className="font-semibold">{formatAmount(selectedTxn?.amount || 0)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Net Amount:</span>
                <span className="font-semibold text-green-600">
                  {formatAmount(selectedTxn?.net_amount || 0)}
                </span>
              </div>
            </div>
            
            <div>
              <Label>Remarks (Optional)</Label>
              <Input
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Enter remarks..."
                className="mt-1"
              />
            </div>

            {confirmAction === 'success' && (
              <div className="bg-green-50 border border-green-200 p-3 rounded-lg text-sm text-green-800">
                <p className="font-medium">This will:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>Mark transaction as SUCCESS</li>
                  <li>Credit ₹{selectedTxn?.net_amount} to merchant wallet</li>
                  <li>Create wallet transaction entry</li>
                </ul>
              </div>
            )}

            {confirmAction === 'failed' && (
              <div className="bg-red-50 border border-red-200 p-3 rounded-lg text-sm text-red-800">
                <p className="font-medium">This will:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>Mark transaction as FAILED</li>
                  <li>No wallet credit will be made</li>
                </ul>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowConfirmDialog(false)}
              disabled={processing}
            >
              Cancel
            </Button>
            <Button
              onClick={confirmManualAction}
              disabled={processing}
              className={confirmAction === 'success' 
                ? 'bg-green-600 hover:bg-green-700' 
                : 'bg-red-600 hover:bg-red-700'
              }
            >
              {processing ? 'Processing...' : 'Confirm'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
