import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Wallet, Download, Search, User, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'
import { formatCurrency, formatDateTime } from '@/lib/utils'

export default function WalletStatement() {
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [transactions, setTransactions] = useState([])
  const [showFilters, setShowFilters] = useState(false)
  const [entriesPerPage, setEntriesPerPage] = useState(10)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [users, setUsers] = useState([])
  const [filteredUsers, setFilteredUsers] = useState([])
  const [userSearchTerm, setUserSearchTerm] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [showDropdown, setShowDropdown] = useState(false)
  const [walletBalance, setWalletBalance] = useState(0)
  const [filterType, setFilterType] = useState('') // New filter state

  useEffect(() => {
    loadUsers()
  }, [])

  useEffect(() => {
    if (userSearchTerm) {
      const filtered = users.filter(user => 
        user.full_name.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
        user.merchant_id.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(userSearchTerm.toLowerCase())
      )
      setFilteredUsers(filtered)
    } else {
      setFilteredUsers(users)
    }
  }, [userSearchTerm, users])

  const loadUsers = async () => {
    try {
      setLoadingUsers(true)
      const response = await adminAPI.getUsers()
      if (response.success) {
        const userList = response.users || []
        setUsers(Array.isArray(userList) ? userList : [])
        setFilteredUsers(Array.isArray(userList) ? userList : [])
      } else {
        setUsers([])
        setFilteredUsers([])
      }
    } catch (error) {
      toast.error('Failed to load users')
      console.error('Load users error:', error)
      setUsers([])
      setFilteredUsers([])
    } finally {
      setLoadingUsers(false)
    }
  }

  const handleSelectUser = (user) => {
    setSelectedUser(user)
    setUserSearchTerm(user.full_name)
    setShowDropdown(false)
    fetchTransactions(user.merchant_id)
    fetchWalletBalance(user.merchant_id)
  }

  const fetchWalletBalance = async (merchantId) => {
    if (!merchantId) return
    
    try {
      const response = await adminAPI.getMerchantWalletOverview(merchantId)
      if (response.success && response.data) {
        setWalletBalance(response.data.balance || 0)
      }
    } catch (error) {
      console.error('Fetch wallet balance error:', error)
    }
  }

  const fetchTransactions = async (merchantId) => {
    if (!merchantId) return
    
    try {
      setLoading(true)
      const filters = { merchant_id: merchantId }
      if (fromDate) filters.from_date = fromDate
      if (toDate) filters.to_date = toDate
      if (filterType) filters.filter_type = filterType
      
      const response = await adminAPI.getMerchantWalletStatement(merchantId, filters)
      if (response.success) {
        setTransactions(response.transactions || [])
        // Don't set balance from statement, use wallet overview balance
      }
    } catch (error) {
      toast.error('Failed to load transactions')
      console.error('Fetch transactions error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    if (selectedUser) {
      fetchTransactions(selectedUser.merchant_id)
      fetchWalletBalance(selectedUser.merchant_id)
      toast.success('Search applied successfully!')
    } else {
      toast.error('Please select a merchant first')
    }
  }

  const handleReset = () => {
    setFromDate('')
    setToDate('')
    setSearchTerm('')
    setFilterType('')
    if (selectedUser) {
      fetchTransactions(selectedUser.merchant_id)
      fetchWalletBalance(selectedUser.merchant_id)
    }
    toast.info('Filters reset')
  }

  const handleExport = () => {
    if (transactions.length === 0) {
      toast.error('No data to export')
      return
    }
    
    const headers = ['Transaction ID', 'Category', 'Type', 'Amount', 'Description', 'Status', 'Date']
    const csvData = transactions.map(txn => [
      txn.txn_id,
      txn.category,
      txn.txn_type,
      txn.amount,
      txn.description,
      txn.status,
      formatDateTime(txn.created_at)
    ])
    
    const csv = [headers, ...csvData].map(row => row.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `wallet_statement_${selectedUser?.merchant_id}_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    
    toast.success('Report exported successfully!')
  }

  const filteredTransactions = transactions.filter(txn => {
    if (!searchTerm) return true
    return (
      txn.txn_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      txn.description.toLowerCase().includes(searchTerm.toLowerCase())
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
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wallet className="h-8 w-8 text-orange-600" />
          <div>
            <h1 className="text-3xl font-bold">Wallet Statement</h1>
            <p className="text-sm text-gray-600 mt-1">View merchant wallet transactions (topups, fetches, fund requests & settlements)</p>
          </div>
        </div>
        <div className="flex gap-2">
          {selectedUser && (
            <Button
              onClick={() => fetchTransactions(selectedUser.merchant_id)}
              variant="outline"
              className="flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          )}
          <Button
            onClick={handleExport}
            disabled={!selectedUser || transactions.length === 0}
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

      {/* User Selection Card */}
      <Card className="bg-gradient-to-r from-orange-50 to-yellow-50 border-2 border-orange-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5 text-orange-600" />
            Select Merchant
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label>Search by Name, ID, or Email</Label>
            <div className="relative">
              <Input
                placeholder="Type to search merchants..."
                value={userSearchTerm}
                onChange={(e) => {
                  setUserSearchTerm(e.target.value)
                  setShowDropdown(true)
                }}
                onFocus={() => setShowDropdown(true)}
                className="pr-10"
              />
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              
              {/* Dropdown */}
              {showDropdown && filteredUsers.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {loadingUsers ? (
                    <div className="p-4 text-center text-gray-500">Loading users...</div>
                  ) : (
                    filteredUsers.map((user) => (
                      <button
                        key={user.merchant_id}
                        onClick={() => handleSelectUser(user)}
                        className="w-full text-left px-4 py-3 hover:bg-orange-50 border-b border-gray-100 last:border-b-0 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-orange-100 rounded-full">
                            <User className="h-4 w-4 text-orange-600" />
                          </div>
                          <div>
                            <p className="font-semibold text-gray-900">{user.full_name}</p>
                            <p className="text-xs text-gray-500">ID: {user.merchant_id} • {user.email}</p>
                          </div>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
            
            {selectedUser && (
              <div className="mt-4 p-4 bg-white rounded-lg border-2 border-orange-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-3 bg-orange-100 rounded-full">
                      <User className="h-6 w-6 text-orange-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Selected Merchant</p>
                      <p className="text-lg font-bold text-gray-900">{selectedUser.full_name}</p>
                      <p className="text-xs text-gray-500">ID: {selectedUser.merchant_id} • {selectedUser.email}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600">Wallet Balance</p>
                    <p className="text-2xl font-bold text-green-600">{formatCurrency(walletBalance)}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Search Filters */}
      {showFilters && selectedUser && (
        <Card>
          <CardHeader>
            <CardTitle>Search Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-12 gap-4 items-end">
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
              <div className="col-span-3">
                <Label className="text-sm font-medium">Transaction Type</Label>
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                >
                  <option value="">All Transactions</option>
                  <option value="topup">Funds Topped Up by Admin</option>
                  <option value="fetch">Funds Fetched by Admin</option>
                  <option value="fund_request">Fund Requests (All Status)</option>
                  <option value="unsettled_settlement">Settled from Unsettled Wallet</option>
                </select>
              </div>
              <div className="col-span-2">
                <Button 
                  onClick={handleSearch}
                  className="w-full h-9 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800"
                >
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>
              <div className="col-span-1">
                <Button 
                  onClick={handleReset}
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

      {/* Transaction Table - Only show when user is selected */}
      {selectedUser ? (
        <Card>
          <CardContent className="pt-6">
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
                    <TableHead className="font-semibold">CATEGORY</TableHead>
                    <TableHead className="font-semibold">TYPE</TableHead>
                    <TableHead className="font-semibold">AMOUNT</TableHead>
                    <TableHead className="font-semibold">DESCRIPTION</TableHead>
                    <TableHead className="font-semibold">STATUS</TableHead>
                    <TableHead className="font-semibold">DATE</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <div className="flex items-center justify-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                          <span className="ml-3 text-gray-600">Loading transactions...</span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : filteredTransactions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                        No transactions found
                      </TableCell>
                    </TableRow>
                  ) : (
                    currentTransactions.map((txn) => (
                      <TableRow key={txn.id} className="hover:bg-gray-50">
                        <TableCell className="font-mono text-xs">{txn.txn_id}</TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            txn.category === 'TOPUP' ? 'bg-blue-100 text-blue-700' :
                            txn.category === 'FETCH' ? 'bg-orange-100 text-orange-700' :
                            txn.category === 'FUND_REQUEST' ? 'bg-purple-100 text-purple-700' :
                            txn.category === 'UNSETTLED_SETTLEMENT' ? 'bg-teal-100 text-teal-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {txn.category === 'TOPUP' ? 'Topup' :
                             txn.category === 'FETCH' ? 'Fetch' :
                             txn.category === 'FUND_REQUEST' ? 'Fund Request' :
                             txn.category === 'UNSETTLED_SETTLEMENT' ? 'Settlement' :
                             txn.category}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            txn.txn_type === 'CREDIT' 
                              ? 'bg-green-100 text-green-700' 
                              : txn.txn_type === 'DEBIT'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {txn.txn_type}
                          </span>
                        </TableCell>
                        <TableCell className="font-medium">{formatCurrency(txn.amount)}</TableCell>
                        <TableCell className="max-w-xs">{txn.description}</TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            txn.status === 'APPROVED' || txn.status === 'COMPLETED' 
                              ? 'bg-green-100 text-green-700' 
                              : txn.status === 'REJECTED'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {txn.status}
                          </span>
                        </TableCell>
                        <TableCell className="whitespace-nowrap">{formatDateTime(txn.created_at)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {filteredTransactions.length > 0 && (
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
                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((page) => (
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
            )}
          </CardContent>
        </Card>
      ) : (
        /* Empty State */
        <Card className="border-2 border-dashed border-gray-300">
          <CardContent className="py-12">
            <div className="text-center">
              <Wallet className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-700 mb-2">No Merchant Selected</h3>
              <p className="text-sm text-gray-500">
                Please select a merchant from the dropdown above to view their wallet statement
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
