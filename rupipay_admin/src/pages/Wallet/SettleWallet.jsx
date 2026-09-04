import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Wallet, Search, User, DollarSign, ArrowRight, RefreshCw } from 'lucide-react'
import adminAPI from '@/api/admin_api'
import { toast } from 'sonner'

export default function SettleWallet() {
  const [loading, setLoading] = useState(false)
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [users, setUsers] = useState([])
  const [filteredUsers, setFilteredUsers] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [showDropdown, setShowDropdown] = useState(false)
  const [walletData, setWalletData] = useState({
    settled_balance: 0,
    unsettled_balance: 0
  })
  const [settlementAmount, setSettlementAmount] = useState('')
  const [remarks, setRemarks] = useState('')
  const [processing, setProcessing] = useState(false)

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
      toast.error('Failed to load users')
    } finally {
      setLoadingUsers(false)
    }
  }

  const loadWalletData = async (merchantId) => {
    try {
      setLoading(true)
      const response = await adminAPI.getMerchantWalletDetails(merchantId)
      
      if (response.success && response.data) {
        setWalletData({
          settled_balance: response.data.settled_balance || 0,
          unsettled_balance: response.data.unsettled_balance || 0
        })
      } else {
        setWalletData({
          settled_balance: 0,
          unsettled_balance: 0
        })
        toast.error(response.message || 'Failed to load wallet data')
      }
    } catch (error) {
      console.error('Wallet data error:', error)
      setWalletData({
        settled_balance: 0,
        unsettled_balance: 0
      })
      toast.error('Failed to load wallet data')
    } finally {
      setLoading(false)
    }
  }

  const handleUserSelect = (user) => {
    setSelectedUser(user)
    setSearchTerm(user.full_name)
    setShowDropdown(false)
    loadWalletData(user.merchant_id)
    setSettlementAmount('')
    setRemarks('')
  }

  const handleSettle = async () => {
    if (!selectedUser) {
      toast.error('Please select a user')
      return
    }

    if (!settlementAmount || parseFloat(settlementAmount) <= 0) {
      toast.error('Please enter a valid settlement amount')
      return
    }

    const amount = parseFloat(settlementAmount)
    if (amount > walletData.unsettled_balance) {
      toast.error(`Amount cannot exceed unsettled balance (₹${walletData.unsettled_balance.toFixed(2)})`)
      return
    }

    try {
      setProcessing(true)
      const response = await adminAPI.settleWallet({
        merchant_id: selectedUser.merchant_id,
        amount: amount,
        remarks: remarks
      })

      if (response.success) {
        toast.success('Wallet settled successfully')
        // Reload wallet data
        loadWalletData(selectedUser.merchant_id)
        setSettlementAmount('')
        setRemarks('')
      } else {
        toast.error(response.message || 'Failed to settle wallet')
      }
    } catch (error) {
      console.error('Settlement error:', error)
      toast.error('Failed to settle wallet')
    } finally {
      setProcessing(false)
    }
  }

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Wallet className="h-8 w-8 text-orange-600" />
        <div>
          <h1 className="text-3xl font-bold">Settle Wallet</h1>
          <p className="text-sm text-gray-600 mt-1">Transfer unsettled amount to settled wallet for merchants</p>
        </div>
      </div>

      {/* User Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Select Merchant
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Label htmlFor="user-search">Search Merchant</Label>
            <div className="relative mt-2">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <Input
                id="user-search"
                type="text"
                placeholder="Search by name, merchant ID, or email..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setShowDropdown(true)
                }}
                onFocus={() => setShowDropdown(true)}
                className="pl-10"
              />
            </div>

            {showDropdown && filteredUsers.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {filteredUsers.map((user) => (
                  <div
                    key={user.merchant_id}
                    onClick={() => handleUserSelect(user)}
                    className="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                  >
                    <div className="font-medium">{user.full_name}</div>
                    <div className="text-sm text-gray-600">{user.merchant_id}</div>
                    <div className="text-xs text-gray-500">{user.email}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {selectedUser && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{selectedUser.full_name}</p>
                  <p className="text-sm text-gray-600">{selectedUser.merchant_id}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadWalletData(selectedUser.merchant_id)}
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Wallet Details */}
      {selectedUser && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="border-2 border-green-200 bg-gradient-to-br from-green-50 to-white">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                  <Wallet className="h-4 w-4 text-green-600" />
                  Settled Balance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-green-700">
                  {formatCurrency(walletData.settled_balance)}
                </p>
                <p className="text-xs text-gray-500 mt-2">Available for payout</p>
              </CardContent>
            </Card>

            <Card className="border-2 border-orange-200 bg-gradient-to-br from-orange-50 to-white">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-orange-600" />
                  Unsettled Balance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-orange-700">
                  {formatCurrency(walletData.unsettled_balance)}
                </p>
                <p className="text-xs text-gray-500 mt-2">Pending admin approval</p>
              </CardContent>
            </Card>
          </div>

          {/* Settlement Form */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowRight className="h-5 w-5" />
                Settle Amount
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="amount">Settlement Amount</Label>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="0"
                  max={walletData.unsettled_balance}
                  placeholder="Enter amount to settle"
                  value={settlementAmount}
                  onChange={(e) => setSettlementAmount(e.target.value)}
                  className="mt-2"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Maximum: {formatCurrency(walletData.unsettled_balance)}
                </p>
              </div>

              <div>
                <Label htmlFor="remarks">Remarks (Optional)</Label>
                <Textarea
                  id="remarks"
                  placeholder="Enter any remarks or notes..."
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  className="mt-2"
                  rows={3}
                />
              </div>

              <Button
                onClick={handleSettle}
                disabled={processing || !settlementAmount || parseFloat(settlementAmount) <= 0}
                className="w-full"
              >
                {processing ? 'Processing...' : 'Settle Wallet'}
              </Button>
            </CardContent>
          </Card>
        </>
      )}

      {!selectedUser && (
        <Card>
          <CardContent className="py-12 text-center text-gray-500">
            <User className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>Select a merchant to view wallet details and settle amount</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
