import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Building, Eye, EyeOff, RefreshCw, Wallet } from 'lucide-react'
import { toast } from 'sonner'
import { clientAPI } from '@/api/client_api'
import { formatCurrency, formatDateTime } from '@/lib/utils'

export default function SettleFund() {
  const [banks, setBanks] = useState([])
  const [selectedBank, setSelectedBank] = useState('')
  const [amount, setAmount] = useState('')
  const [tpin, setTpin] = useState('')
  const [showTpin, setShowTpin] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingBanks, setLoadingBanks] = useState(true)
  const [walletBalance, setWalletBalance] = useState(0)
  const [transactions, setTransactions] = useState([])

  useEffect(() => {
    fetchBanks()
    fetchWalletBalance()
    fetchTransactions()
  }, [])

  const fetchBanks = async () => {
    try {
      setLoadingBanks(true)
      const response = await clientAPI.getMerchantBanks()
      console.log('Banks API response:', response)
      if (response.success) {
        const bankList = response.banks || response.data || []
        console.log('Bank list:', bankList)
        const activeBanks = bankList.filter(bank => bank.is_active)
        console.log('Active banks:', activeBanks)
        setBanks(activeBanks)
      } else {
        toast.error('Failed to load bank accounts')
      }
    } catch (error) {
      console.error('Error fetching banks:', error)
      toast.error('Failed to load bank accounts')
    } finally {
      setLoadingBanks(false)
    }
  }

  const fetchWalletBalance = async () => {
    try {
      const response = await clientAPI.getWalletOverview()
      if (response.success) {
        setWalletBalance(response.data.balance || 0)
      }
    } catch (error) {
      console.error('Error fetching wallet balance:', error)
    }
  }

  const fetchTransactions = async () => {
    try {
      const response = await clientAPI.getClientWalletStatement()
      if (response.success) {
        setTransactions(response.data)
      }
    } catch (error) {
      console.error('Error fetching transactions:', error)
    }
  }

  const handleSettle = async (e) => {
    e.preventDefault()
    
    if (!selectedBank) {
      toast.error('Please select a bank account')
      return
    }
    
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }
    
    if (parseFloat(amount) > walletBalance) {
      toast.error('Insufficient balance in wallet')
      return
    }
    
    if (!tpin || tpin.length !== 6) {
      toast.error('Please enter a valid 6-digit TPIN')
      return
    }
    
    setLoading(true)
    
    try {
      const response = await clientAPI.settleFund({
        bank_id: selectedBank,
        amount: parseFloat(amount),
        tpin: tpin
      })
      
      if (response.success) {
        const chargeInfo = response.charges 
          ? ` Charges: ₹${response.charges}, Amount to Bank: ₹${response.net_amount}` 
          : ''
        toast.success(`Settlement initiated!${chargeInfo}`)
        setSelectedBank('')
        setAmount('')
        setTpin('')
        fetchWalletBalance()
        fetchTransactions()
      } else {
        toast.error(response.message || 'Settlement failed')
      }
    } catch (error) {
      toast.error(error.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setSelectedBank('')
    setAmount('')
    setTpin('')
    toast.info('Form reset')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Building className="h-8 w-8 text-orange-600" />
        <h1 className="text-3xl font-bold">Settle Fund</h1>
      </div>

      {/* Wallet Balance Card */}
      <Card className="bg-gradient-to-br from-green-500 to-green-600 text-white">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100 text-sm mb-1">Available Wallet Balance</p>
              <p className="text-3xl font-bold">₹{walletBalance.toLocaleString()}</p>
            </div>
            <div className="bg-white/20 p-3 rounded-full">
              <Wallet className="h-8 w-8" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Settlement Form */}
      <Card>
        <CardHeader>
          <CardTitle>Settle Fund to Bank Account</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSettle} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label className="text-base font-medium mb-2 block">Select Bank Account</Label>
                {loadingBanks ? (
                  <div className="flex h-12 w-full rounded-md border-2 border-gray-300 bg-gray-50 px-4 py-2 text-base items-center text-gray-500">
                    Loading banks...
                  </div>
                ) : banks.length === 0 ? (
                  <div className="flex h-12 w-full rounded-md border-2 border-gray-300 bg-gray-50 px-4 py-2 text-base items-center text-gray-500">
                    No bank accounts found. Please add a bank in Settings → Bank Management.
                  </div>
                ) : (
                  <select
                    value={selectedBank}
                    onChange={(e) => setSelectedBank(e.target.value)}
                    className="flex h-12 w-full rounded-md border-2 border-gray-300 bg-white px-4 py-2 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                    required
                  >
                    <option value="">-- Select Bank Account --</option>
                    {banks.map((bank) => (
                      <option key={bank.id} value={bank.id}>
                        {bank.bank_name} - {bank.account_holder_name} - ****{bank.account_number.slice(-4)}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <Label className="text-base font-medium mb-2 block">Amount</Label>
                <Input
                  type="number"
                  placeholder="Enter amount"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="h-12 text-base"
                  required
                  min="1"
                  step="0.01"
                  max={walletBalance}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label className="text-base font-medium mb-2 block">TPIN</Label>
                <div className="relative">
                  <Input
                    type={showTpin ? 'text' : 'password'}
                    placeholder="Enter 6-digit TPIN"
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

            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={loading}
                className="bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-800 text-white px-8 h-11"
              >
                {loading ? 'Processing...' : 'Settle Fund'}
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

      {/* Transaction History */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Transaction History</CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchTransactions}
              className="text-gray-600 hover:text-gray-900"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Transaction ID</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Balance Before</TableHead>
                  <TableHead>Balance After</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No transactions found
                    </TableCell>
                  </TableRow>
                ) : (
                  transactions.map((txn) => (
                    <TableRow key={txn.id}>
                      <TableCell className="font-medium">{txn.txn_id}</TableCell>
                      <TableCell>
                        <Badge className={txn.txn_type === 'CREDIT' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                          {txn.txn_type}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatCurrency(txn.amount)}</TableCell>
                      <TableCell>{formatCurrency(txn.balance_before)}</TableCell>
                      <TableCell>{formatCurrency(txn.balance_after)}</TableCell>
                      <TableCell>{txn.description}</TableCell>
                      <TableCell>{formatDateTime(txn.created_at)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Information Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h3 className="font-semibold text-blue-900 mb-2">Important Information</h3>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Payout charges will be deducted from the settlement amount as per your scheme</li>
            <li>Example: If you settle ₹100 with ₹10 charges, ₹100 is deducted from wallet and ₹90 goes to bank</li>
            <li>Funds will be transferred to your selected bank account</li>
            <li>TPIN is required for security verification</li>
            <li>Settlement may take 1-2 business days</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
