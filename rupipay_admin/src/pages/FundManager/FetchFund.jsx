import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Package, Eye, EyeOff, Search } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'
import { formatCurrency, formatDateTime } from '@/lib/utils'

export default function FetchFund() {
  const [selectedUser, setSelectedUser] = useState('')
  const [users, setUsers] = useState([])
  const [walletBalance, setWalletBalance] = useState(null)
  const [loadingBalance, setLoadingBalance] = useState(false)
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')
  const [tpin, setTpin] = useState('')
  const [showTpin, setShowTpin] = useState(false)
  const [loading, setLoading] = useState(false)
  const [transactions, setTransactions] = useState([])
  const [showFilters, setShowFilters] = useState(false)
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  useEffect(() => {
    fetchUsers()
    fetchTransactions()
  }, [])

  useEffect(() => {
    if (selectedUser) {
      fetchWalletBalance()
    } else {
      setWalletBalance(null)
    }
  }, [selectedUser])

  const fetchWalletBalance = async () => {
    if (!selectedUser) return
    
    setLoadingBalance(true)
    try {
      const response = await adminAPI.getMerchantWalletOverview(selectedUser)
      if (response.success) {
        setWalletBalance(response.data.balance || 0)
      } else {
        setWalletBalance(0)
        toast.error('Failed to fetch wallet balance')
      }
    } catch (error) {
      console.error('Error fetching wallet balance:', error)
      setWalletBalance(0)
      toast.error('Error fetching wallet balance')
    } finally {
      setLoadingBalance(false)
    }
  }

  const fetchUsers = async () => {
    try {
      const response = await adminAPI.getAllUsers()
      if (response.success) {
        const userList = response.users || response.data || []
        setUsers(Array.isArray(userList) ? userList : [])
      } else {
        setUsers([])
      }
    } catch (error) {
      console.error('Error fetching users:', error)
      setUsers([])
    }
  }

  const fetchTransactions = async () => {
    try {
      const filters = {}
      if (fromDate) filters.from_date = fromDate
      if (toDate) filters.to_date = toDate
      
      const response = await adminAPI.getAdminWalletStatement(filters)
      if (response.success) {
        // Filter only fetch fund transactions
        const allTransactions = response.data || []
        const fetchTransactions = allTransactions.filter(t => 
          t.description && t.description.includes('Fetched from merchant')
        )
        setTransactions(fetchTransactions)
      } else {
        setTransactions([])
      }
    } catch (error) {
      console.error('Error fetching transactions:', error)
      setTransactions([])
    }
  }

  const handleFetch = async (e) => {
    e.preventDefault()
    
    if (!selectedUser) {
      toast.error('Please select a user')
      return
    }
    
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }

    // Check if amount exceeds wallet balance
    if (walletBalance !== null && parseFloat(amount) > walletBalance) {
      toast.error(`Insufficient balance. Available: ₹${walletBalance.toLocaleString()}`)
      return
    }

    if (!reason || reason.trim() === '') {
      toast.error('Please enter a reason for fetching funds')
      return
    }
    
    if (!tpin || tpin.length !== 6) {
      toast.error('Please enter a valid 6-digit TPIN')
      return
    }
    
    setLoading(true)
    
    try {
      const response = await adminAPI.fetchFund({
        merchant_id: selectedUser,
        amount: parseFloat(amount),
        tpin: tpin,
        reason: reason
      })
      
      if (response.success) {
        toast.success(`Fetch fund of ₹${parseFloat(amount).toLocaleString()} completed successfully!`)
        setSelectedUser('')
        setAmount('')
        setReason('')
        setTpin('')
        setWalletBalance(null)
        fetchTransactions()
      } else {
        toast.error(response.message || 'Fetch fund failed')
      }
    } catch (error) {
      toast.error(error.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setSelectedUser('')
    setAmount('')
    setReason('')
    setTpin('')
    toast.info('Form reset')
  }

  const handleSearch = () => {
    fetchTransactions()
  }

  const handleClearFilters = () => {
    setFromDate('')
    setToDate('')
    fetchTransactions()
    toast.info('Filters cleared')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Package className="h-8 w-8 text-orange-600" />
        <h1 className="text-3xl font-bold">Fetch Fund</h1>
      </div>

      {/* Fetch Fund Form */}
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleFetch} className="space-y-6">
            {/* First Row - Select User */}
            <div className="grid grid-cols-1 gap-6">
              <div>
                <Label className="text-base font-medium mb-2 block">Select User</Label>
                <select
                  value={selectedUser}
                  onChange={(e) => setSelectedUser(e.target.value)}
                  className="flex h-12 w-full rounded-md border-2 border-gray-300 bg-white px-4 py-2 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select User</option>
                  {users.map((user) => (
                    <option key={user.merchant_id} value={user.merchant_id}>
                      {user.full_name} ({user.merchant_id})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Wallet Balance Display */}
            {selectedUser && (
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Available Wallet Balance</p>
                    {loadingBalance ? (
                      <p className="text-2xl font-bold text-blue-600">Loading...</p>
                    ) : (
                      <p className="text-3xl font-bold text-blue-600">
                        ₹{walletBalance !== null ? walletBalance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}
                      </p>
                    )}
                  </div>
                  <div className="text-blue-600">
                    <Package className="h-12 w-12" />
                  </div>
                </div>
              </div>
            )}

            {/* Second Row - Fetch Amount and Reason */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label className="text-base font-medium mb-2 block">Fetch Amount</Label>
                <Input
                  type="number"
                  placeholder="Amount"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="h-12 text-base"
                  required
                  min="1"
                  step="0.01"
                />
              </div>

              <div>
                <Label className="text-base font-medium mb-2 block">Reason</Label>
                <Input
                  type="text"
                  placeholder="Enter reason for fetching funds"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="h-12 text-base"
                  required
                />
              </div>
            </div>

            {/* Third Row - TPIN */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label className="text-base font-medium mb-2 block">TPIN</Label>
                <div className="relative">
                  <Input
                    type={showTpin ? 'text' : 'password'}
                    placeholder="TPIN"
                    value={tpin}
                    onChange={(e) => setTpin(e.target.value)}
                    className="h-12 text-base pr-12"
                    required
                    maxLength="6"
                    pattern="[0-9]{6}"
                  />
                  <button
                    type="button"
                    onClick={() => setShowTpin(!showTpin)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                  >
                    {showTpin ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={loading}
                className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white px-8 h-11"
              >
                {loading ? 'Processing...' : 'Fetch'}
              </Button>
              <Button
                type="button"
                onClick={handleReset}
                variant="outline"
                className="bg-gray-400 hover:bg-gray-500 text-white px-8 h-11 border-0"
              >
                Close
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Search Button */}
      <div className="flex items-center justify-end">
        <Button
          onClick={() => setShowFilters(!showFilters)}
          className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white"
        >
          <Search className="h-4 w-4 mr-2" />
          Search
        </Button>
      </div>

      {/* Search Filters - Hidden by default */}
      {showFilters && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Search Filters</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium mb-2 block">From Date</Label>
                  <Input
                    type="date"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                    className="h-10"
                  />
                </div>

                <div>
                  <Label className="text-sm font-medium mb-2 block">To Date</Label>
                  <Input
                    type="date"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                    className="h-10"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={handleSearch}
                  className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white px-6"
                >
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
                <Button
                  onClick={handleClearFilters}
                  variant="outline"
                  className="bg-gray-400 hover:bg-gray-500 text-white border-0 px-6"
                >
                  Clear
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Transactions Table */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Show</span>
              <select className="border border-gray-300 rounded px-2 py-1 text-sm">
                <option>10</option>
                <option>25</option>
                <option>50</option>
                <option>100</option>
              </select>
              <span className="text-sm text-gray-600">entries</span>
            </div>
            <div className="text-sm text-gray-600">Search:</div>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="whitespace-nowrap">TRANSACTION TYPE</TableHead>
                  <TableHead className="whitespace-nowrap">EMP/USER NAME</TableHead>
                  <TableHead className="whitespace-nowrap">DATE</TableHead>
                  <TableHead className="whitespace-nowrap">TRANS. AMOUNT</TableHead>
                  <TableHead className="whitespace-nowrap">TRANSACTION ID</TableHead>
                  <TableHead className="whitespace-nowrap">ORDER ID</TableHead>
                  <TableHead className="whitespace-nowrap">CLOSING BALANCE</TableHead>
                  <TableHead className="whitespace-nowrap">OPENING BALANCE</TableHead>
                  <TableHead className="whitespace-nowrap">DESCRIPTION</TableHead>
                  <TableHead className="whitespace-nowrap">UTR</TableHead>
                  <TableHead className="whitespace-nowrap">GST</TableHead>
                  <TableHead className="whitespace-nowrap">AMOUNT</TableHead>
                  <TableHead className="whitespace-nowrap">SERVICE CHARGE</TableHead>
                  <TableHead className="whitespace-nowrap">REMARKS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={14} className="text-center text-gray-500">
                      No transactions found
                    </TableCell>
                  </TableRow>
                ) : (
                  transactions.map((transaction, index) => (
                    <TableRow key={transaction.id} className="hover:bg-gray-50">
                      <TableCell className="font-medium">Fetch Fund</TableCell>
                      <TableCell>{transaction.description.split(' - ')[0].replace('Fetched from merchant ', '')}</TableCell>
                      <TableCell className="whitespace-nowrap">{formatDateTime(transaction.created_at)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(transaction.amount)}</TableCell>
                      <TableCell>{transaction.txn_id}</TableCell>
                      <TableCell>{transaction.txn_id}</TableCell>
                      <TableCell className="text-right">{formatCurrency(transaction.balance_after)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(transaction.balance_before)}</TableCell>
                      <TableCell className="whitespace-nowrap">{transaction.description}</TableCell>
                      <TableCell>-</TableCell>
                      <TableCell>-</TableCell>
                      <TableCell>-</TableCell>
                      <TableCell>{transaction.txn_type}</TableCell>
                      <TableCell>
                        <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                          Completed
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          <div className="flex items-center justify-between mt-4">
            <div className="text-sm text-gray-600">
              Showing 1 to {transactions.length} of {transactions.length} entries
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled>Previous</Button>
              <Button variant="outline" size="sm" className="bg-purple-600 text-white hover:bg-purple-700">1</Button>
              <Button variant="outline" size="sm" disabled>Next</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
