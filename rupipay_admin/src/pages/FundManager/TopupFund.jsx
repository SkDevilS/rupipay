import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { IndianRupee, Eye, EyeOff } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'

export default function TopupFund() {
  const [selectedUser, setSelectedUser] = useState('')
  const [users, setUsers] = useState([])
  const [amount, setAmount] = useState('')
  const [tpin, setTpin] = useState('')
  const [showTpin, setShowTpin] = useState(false)
  const [loading, setLoading] = useState(false)
  const [walletBalance, setWalletBalance] = useState({ main_balance: 0 })

  useEffect(() => {
    fetchUsers()
    fetchWalletBalance()
  }, [])

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

  const fetchWalletBalance = async () => {
    try {
      const response = await adminAPI.getAdminWalletOverview()
      if (response.success && response.data) {
        setWalletBalance(response.data)
      } else {
        setWalletBalance({ main_balance: 0 })
      }
    } catch (error) {
      console.error('Error fetching wallet balance:', error)
      setWalletBalance({ main_balance: 0 })
    }
  }

  const handleTopup = async (e) => {
    e.preventDefault()
    
    if (!selectedUser) {
      toast.error('Please select a user')
      return
    }
    
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }
    
    if (!tpin || tpin.length !== 6) {
      toast.error('Please enter a valid 6-digit TPIN')
      return
    }
    
    const balance = walletBalance?.main_balance || 0
    if (parseFloat(amount) > balance) {
      toast.error('Insufficient balance in admin wallet')
      return
    }
    
    setLoading(true)
    
    try {
      const response = await adminAPI.topupFund({
        merchant_id: selectedUser,
        amount: parseFloat(amount),
        tpin: tpin
      })
      
      if (response.success) {
        toast.success(`Topup of ₹${parseFloat(amount).toLocaleString()} completed successfully!`)
        setSelectedUser('')
        setAmount('')
        setTpin('')
        fetchWalletBalance()
      } else {
        toast.error(response.message || 'Topup failed')
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
    setTpin('')
    toast.info('Form reset')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <IndianRupee className="h-8 w-8 text-orange-600" />
        <h1 className="text-3xl font-bold">TopUp Fund</h1>
      </div>

      {/* Wallet Balance Card */}
      <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm mb-1">Admin Wallet Balance</p>
              <p className="text-3xl font-bold">₹{(walletBalance?.main_balance || 0).toLocaleString()}</p>
            </div>
            <div className="bg-white/20 p-3 rounded-full">
              <IndianRupee className="h-8 w-8" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* TopUp Form */}
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleTopup} className="space-y-6">
            {/* First Row - Select User */}
            <div className="grid grid-cols-1 gap-6">
              <div>
                <Label className="text-base font-medium mb-2 block">Select User</Label>
                <select
                  value={selectedUser}
                  onChange={(e) => setSelectedUser(e.target.value)}
                  className="flex h-12 w-full rounded-md border-2 border-blue-500 bg-white px-4 py-2 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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

            {/* Second Row - TopUp Amount and TPIN */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label className="text-base font-medium mb-2 block">TopUp Amount</Label>
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
            <div className="flex gap-4 pt-4">
              <Button
                type="submit"
                disabled={loading}
                className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white px-8 h-11"
              >
                {loading ? 'Processing...' : 'TopUp'}
              </Button>
              <Button
                type="button"
                onClick={handleReset}
                variant="outline"
                className="bg-gray-400 hover:bg-gray-500 text-white px-8 h-11 border-0"
              >
                Reset
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
