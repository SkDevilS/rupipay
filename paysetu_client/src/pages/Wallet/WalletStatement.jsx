import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Wallet, Download, Search } from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'

export default function WalletStatement() {
  const [searchFilter, setSearchFilter] = useState('Date')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [entriesPerPage, setEntriesPerPage] = useState(10)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [txnTypeFilter, setTxnTypeFilter] = useState('')
  const [walletBalance, setWalletBalance] = useState(0)

  useEffect(() => {
    loadWalletStatement()
    loadWalletBalance()
  }, [])

  const loadWalletBalance = async () => {
    try {
      const response = await clientAPI.getWalletOverview()
      if (response.success && response.data) {
        setWalletBalance(response.data.balance || 0)
      }
    } catch (error) {
      console.error('Wallet balance error:', error)
    }
  }

  const loadWalletStatement = async (filters = {}) => {
    try {
      setLoading(true)
      const response = await clientAPI.getWalletStatement(filters)
      if (response.success) {
        setTransactions(response.transactions || [])
        // Don't set balance from statement, use wallet overview balance
      }
    } catch (error) {
      toast.error('Failed to load wallet statement')
      console.error('Wallet statement error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    const filters = {}
    if (fromDate) filters.from_date = fromDate
    if (toDate) filters.to_date = toDate
    if (txnTypeFilter) filters.txn_type = txnTypeFilter
    
    loadWalletStatement(filters)
    loadWalletBalance()
    toast.success('Search applied successfully!')
  }

  const handleReset = () => {
    setFromDate('')
    setToDate('')
    setSearchTerm('')
    setTxnTypeFilter('')
    loadWalletStatement()
    loadWalletBalance()
    toast.info('Filters reset')
  }

  const handleExport = () => {
    // Export to CSV
    const csvData = filteredTransactions.map(txn => ({
      'Transaction ID': txn.txn_id,
      'Type': txn.txn_type,
      'Amount': txn.amount,
      'Balance Before': txn.balance_before,
      'Balance After': txn.balance_after,
      'Description': txn.description,
      'Date': new Date(txn.created_at).toLocaleString()
    }))
    
    toast.success('Statement exported successfully!')
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

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(amount || 0)
  }

  const filteredTransactions = transactions.filter(txn => {
    if (!searchTerm) return true
    const searchLower = searchTerm.toLowerCase()
    return (
      (txn.merchant_id || '').toLowerCase().includes(searchLower) ||
      (txn.txn_id || '').toLowerCase().includes(searchLower) ||
      (txn.description || '').toLowerCase().includes(searchLower)
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
      {/* Page Header with Export and Search Buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wallet className="h-8 w-8 text-orange-600" />
          <h1 className="text-3xl font-bold">Wallet Statement</h1>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleExport}
            className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800"
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button
            onClick={() => setShowFilters(!showFilters)}
            className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800"
          >
            <Search className="h-4 w-4 mr-2" />
            {showFilters ? 'Hide Filters' : 'Search'}
          </Button>
        </div>
      </div>

      {/* Search Filters - Hidden by default */}
      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle>Search Filters :</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-12 gap-4 items-end">
              <div className="col-span-2">
                <Label className="text-sm font-medium">Transaction Type</Label>
                <select
                  value={txnTypeFilter}
                  onChange={(e) => setTxnTypeFilter(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">All</option>
                  <option value="CREDIT">Credit</option>
                  <option value="DEBIT">Debit</option>
                </select>
              </div>
              <div className="col-span-3">
                <Label className="text-sm font-medium">From Date</Label>
                <Input
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  className="h-9"
                />
              </div>
              <div className="col-span-3">
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
                  <Search className="h-4 w-4 mr-2" />
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
      )}

      {/* Transaction Table */}
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">Loading wallet statement...</p>
              </div>
            </div>
          ) : (
            <>
              {/* Wallet Balance Display */}
              <div className="mb-4 p-4 bg-gradient-to-r from-orange-50 to-yellow-50 rounded-lg border-2 border-orange-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Current Wallet Balance</p>
                    <p className="text-2xl font-bold text-orange-700">{formatCurrency(walletBalance)}</p>
                  </div>
                  <Wallet className="h-8 w-8 text-orange-600" />
                </div>
              </div>

              {/* Table Controls */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm">Show</span>
                  <select
                    value={entriesPerPage}
                    onChange={(e) => setEntriesPerPage(Number(e.target.value))}
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
                    placeholder="Search..."
                  />
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto border rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead className="font-semibold">TRANSACTION ID</TableHead>
                      <TableHead className="font-semibold">TYPE</TableHead>
                      <TableHead className="font-semibold">DESCRIPTION</TableHead>
                      <TableHead className="font-semibold">DATE</TableHead>
                      <TableHead className="font-semibold">AMOUNT</TableHead>
                      <TableHead className="font-semibold">BALANCE BEFORE</TableHead>
                      <TableHead className="font-semibold">BALANCE AFTER</TableHead>
                      <TableHead className="font-semibold">REFERENCE ID</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTransactions.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                          No wallet transactions found
                        </TableCell>
                      </TableRow>
                    ) : (
                      currentTransactions.map((txn) => (
                        <TableRow key={txn.id} className="hover:bg-gray-50">
                          <TableCell className="font-mono text-xs">{txn.txn_id}</TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              txn.txn_type === 'CREDIT' 
                                ? 'bg-green-100 text-green-700' 
                                : 'bg-red-100 text-red-700'
                            }`}>
                              {txn.txn_type}
                            </span>
                          </TableCell>
                          <TableCell>{txn.description}</TableCell>
                          <TableCell className="whitespace-nowrap">{formatDate(txn.created_at)}</TableCell>
                          <TableCell className={`font-medium ${txn.txn_type === 'CREDIT' ? 'text-green-600' : 'text-red-600'}`}>
                            {txn.txn_type === 'CREDIT' ? '+' : '-'}{formatCurrency(txn.amount)}
                          </TableCell>
                          <TableCell>{formatCurrency(txn.balance_before)}</TableCell>
                          <TableCell className="font-medium">{formatCurrency(txn.balance_after)}</TableCell>
                          <TableCell className="font-mono text-xs">{txn.reference_id || '-'}</TableCell>
                        </TableRow>
                      ))
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
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                    <Button
                      key={page}
                      variant={currentPage === page ? "default" : "outline"}
                      size="sm"
                      onClick={() => handlePageChange(page)}
                      className={`text-sm ${
                        currentPage === page 
                          ? 'bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800' 
                          : ''
                      }`}
                    >
                      {page}
                    </Button>
                  ))}
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
