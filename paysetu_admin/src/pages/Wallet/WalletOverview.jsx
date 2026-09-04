import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Wallet, TrendingUp, TrendingDown, RefreshCw, DollarSign, Search, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import adminAPI from '@/api/admin_api'
import { toast } from 'sonner'

export default function WalletOverview() {
  const [loading, setLoading] = useState(false)
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [users, setUsers] = useState([])
  const [filteredUsers, setFilteredUsers] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [showDropdown, setShowDropdown] = useState(false)
  const [walletData, setWalletData] = useState({
    balance: 0,
    payinAmount: 0,
    payoutAmount: 0
  })

  useEffect(() => {
    loadUsers()
  }, [])

  useEffect(() => {
    if (searchTerm) {
      const filtered = users.filter(user => 
        user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.merchant_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(searchTerm.toLowerCase())
      )
      setFilteredUsers(filtered)
    } else {
      setFilteredUsers(users)
    }
  }, [searchTerm, users])

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
        toast.error(response.message || 'Failed to load users')
      }
    } catch (error) {
      console.error('Load users error:', error)
      setUsers([])
      setFilteredUsers([])
      
      // Check if it's an authentication error
      if (error.message && (error.message.includes('401') || error.message.includes('token') || error.message.includes('unauthorized'))) {
        toast.error('Session expired. Please login again.')
      } else {
        toast.error('Failed to load users. Please check if backend is running.')
      }
    } finally {
      setLoadingUsers(false)
    }
  }

  const loadWalletData = async (merchantId) => {
    try {
      setLoading(true)
      const response = await adminAPI.getMerchantWalletOverview(merchantId)
      
      if (response.success && response.data) {
        setWalletData({
          balance: response.data.balance || 0,              // Wallet balance from fund requests
          payinAmount: response.data.payin_amount || 0,     // Net PayIN amount
          payoutAmount: response.data.total_settlements || 0 // Total settlements
        })
      } else {
        setWalletData({
          balance: 0,
          payinAmount: 0,
          payoutAmount: 0
        })
        toast.error(response.message || 'Failed to load wallet data')
      }
    } catch (error) {
      console.error('Wallet data error:', error)
      setWalletData({
        balance: 0,
        payinAmount: 0,
        payoutAmount: 0
      })
      
      // Check if it's an authentication error
      if (error.message && (error.message.includes('401') || error.message.includes('token') || error.message.includes('unauthorized'))) {
        toast.error('Session expired. Please login again.')
      } else {
        toast.error('Failed to load wallet data. Please check if backend is running.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSelectUser = (user) => {
    setSelectedUser(user)
    setSearchTerm(user.full_name)
    setShowDropdown(false)
    loadWalletData(user.merchant_id)
  }

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wallet className="h-8 w-8 text-orange-600" />
          <div>
            <h1 className="text-3xl font-bold">Wallet Overview</h1>
            <p className="text-sm text-gray-600 mt-1">View merchant wallet balance and transaction summary</p>
          </div>
        </div>
        {selectedUser && (
          <Button onClick={() => loadWalletData(selectedUser.merchant_id)} variant="outline" className="flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        )}
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
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
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
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Wallet Data - Only show when user is selected */}
      {selectedUser && (
        <>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">Loading wallet data...</p>
              </div>
            </div>
          ) : (
            <>
              {/* Wallet Balance Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Wallet Balance */}
                <Card className="border-2 border-green-200 bg-gradient-to-br from-green-50 to-white">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-green-600" />
                      Wallet Balance
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <p className="text-3xl font-bold text-green-700">
                        {formatCurrency(walletData.balance)}
                      </p>
                      <p className="text-xs text-gray-500">Available balance</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Payin Amount */}
                <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-white">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-blue-600" />
                      Net PayIN Amount
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <p className="text-3xl font-bold text-blue-700">
                        {formatCurrency(walletData.payinAmount)}
                      </p>
                      <p className="text-xs text-gray-500">Total PayIN after charges</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Payout Amount */}
                <Card className="border-2 border-orange-200 bg-gradient-to-br from-orange-50 to-white">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                      <TrendingDown className="h-4 w-4 text-orange-600" />
                      Total Settlements
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <p className="text-3xl font-bold text-orange-700">
                        {formatCurrency(walletData.payoutAmount)}
                      </p>
                      <p className="text-xs text-gray-500">Settled to bank</p>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Summary Card */}
              <Card>
                <CardHeader>
                  <CardTitle>Wallet Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-100 rounded-lg">
                          <TrendingUp className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Net PayIN Amount</p>
                          <p className="text-lg font-bold text-gray-900">{formatCurrency(walletData.payinAmount)}</p>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-orange-100 rounded-lg">
                          <TrendingDown className="h-5 w-5 text-orange-600" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Total Settlements</p>
                          <p className="text-lg font-bold text-gray-900">{formatCurrency(walletData.payoutAmount)}</p>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gradient-to-r from-orange-100 to-yellow-100 rounded-lg border-2 border-orange-200">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-white rounded-lg">
                          <Wallet className="h-5 w-5 text-orange-600" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-700 font-medium">Wallet Balance</p>
                          <p className="text-2xl font-bold text-orange-700">{formatCurrency(walletData.balance)}</p>
                          <p className="text-xs text-gray-600 mt-1">From approved fund requests</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}

      {/* Empty State */}
      {!selectedUser && !loadingUsers && (
        <Card className="border-2 border-dashed border-gray-300">
          <CardContent className="py-12">
            <div className="text-center">
              <Wallet className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-700 mb-2">No Merchant Selected</h3>
              <p className="text-sm text-gray-500">
                Please select a merchant from the dropdown above to view their wallet details
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
