import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Wallet, TrendingUp, TrendingDown, RefreshCw, DollarSign } from 'lucide-react'
import { Button } from '@/components/ui/button'
import clientAPI from '@/api/client_api'
import { toast } from 'sonner'

export default function WalletOverview() {
  const [loading, setLoading] = useState(true)
  const [walletData, setWalletData] = useState({
    balance: 0,           // Total topped up by admin (from fund requests)
    totalCredit: 0,       // Total wallet credits
    totalDebit: 0,        // Total wallet debits (settlements)
    payinAmount: 0,       // Net PayIN (after charges)
    grossPayin: 0,        // Gross PayIN
    payinCharges: 0       // PayIN charges
  })

  useEffect(() => {
    loadWalletData()
  }, [])

  const loadWalletData = async () => {
    try {
      setLoading(true)
      const response = await clientAPI.getWalletOverview()
      if (response.success && response.data) {
        setWalletData({
          balance: response.data.balance || 0,              // Total topped up by admin
          totalCredit: response.data.total_credit || 0,     // Total wallet credits
          totalDebit: response.data.total_debit || 0,       // Total settlements
          payinAmount: response.data.payin_amount || 0,     // Net PayIN (after charges)
          grossPayin: response.data.gross_payin || 0,       // Gross PayIN
          payinCharges: response.data.payin_charges || 0    // PayIN charges
        })
      }
    } catch (error) {
      toast.error('Failed to load wallet data')
      console.error('Wallet data error:', error)
    } finally {
      setLoading(false)
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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wallet className="h-8 w-8 text-orange-600" />
          <div>
            <h1 className="text-3xl font-bold">Wallet Overview</h1>
            <p className="text-sm text-gray-600 mt-1">View your wallet balance and transaction summary</p>
          </div>
        </div>
        <Button onClick={loadWalletData} variant="outline" className="flex items-center gap-2">
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

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
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* Wallet Balance - Amount topped up by admin from fund requests */}
            <Card className="border-2 border-green-200 bg-gradient-to-br from-green-50 to-white">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                  <Wallet className="h-4 w-4 text-green-600" />
                  Wallet Balance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <p className="text-3xl font-bold text-green-700">
                    {formatCurrency(walletData.balance)}
                  </p>
                  <p className="text-xs text-gray-500">Topped up by admin from fund requests</p>
                </div>
              </CardContent>
            </Card>

            {/* PayIN Amount - Net amount after charges */}
            <Card className="border-2 border-purple-200 bg-gradient-to-br from-purple-50 to-white">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-purple-600" />
                  Net PayIN Amount
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <p className="text-3xl font-bold text-purple-700">
                    {formatCurrency(walletData.payinAmount)}
                  </p>
                  <p className="text-xs text-gray-500">After deducting charges (₹{walletData.grossPayin.toFixed(2)} - ₹{walletData.payinCharges.toFixed(2)})</p>
                </div>
              </CardContent>
            </Card>

            {/* Total Credits */}
            <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-white">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-blue-600" />
                  Total Credits
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <p className="text-3xl font-bold text-blue-700">
                    {formatCurrency(walletData.totalCredit)}
                  </p>
                  <p className="text-xs text-gray-500">Total wallet credits</p>
                </div>
              </CardContent>
            </Card>

            {/* Total Debits (Settlements) */}
            <Card className="border-2 border-orange-200 bg-gradient-to-br from-orange-50 to-white">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                  <TrendingDown className="h-4 w-4 text-orange-600" />
                  Total Debits
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <p className="text-3xl font-bold text-orange-700">
                    {formatCurrency(walletData.totalDebit)}
                  </p>
                  <p className="text-xs text-gray-500">Total settlements to bank</p>
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
                <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <TrendingUp className="h-5 w-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Net PayIN Amount (After Charges)</p>
                      <p className="text-lg font-bold text-gray-900">{formatCurrency(walletData.payinAmount)}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Gross: {formatCurrency(walletData.grossPayin)} - Charges: {formatCurrency(walletData.payinCharges)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <TrendingUp className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Total Wallet Credits</p>
                      <p className="text-lg font-bold text-gray-900">{formatCurrency(walletData.totalCredit)}</p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-orange-100 rounded-lg">
                      <TrendingDown className="h-5 w-5 text-orange-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Total Wallet Debits (Settlements)</p>
                      <p className="text-lg font-bold text-gray-900">{formatCurrency(walletData.totalDebit)}</p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-100 to-emerald-100 rounded-lg border-2 border-green-200">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded-lg">
                      <Wallet className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-700 font-medium">Current Wallet Balance</p>
                      <p className="text-2xl font-bold text-green-700">{formatCurrency(walletData.balance)}</p>
                      <p className="text-xs text-gray-600 mt-1">Topped up by admin from fund requests</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
