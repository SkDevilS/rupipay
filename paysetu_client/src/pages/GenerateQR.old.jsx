import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { QrCode, Download, Copy, ExternalLink, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'
import * as QRCodeLib from 'qrcode'

export default function GenerateQR() {
  const [formData, setFormData] = useState({
    amount: '',
    orderId: '',
    customerName: '',
    customerMobile: '',
    customerEmail: ''
  })
  const [qrData, setQrData] = useState(null)
  const [qrImage, setQrImage] = useState('')
  const [loading, setLoading] = useState(false)
  const [recentTransactions, setRecentTransactions] = useState([])

  useEffect(() => {
    fetchRecentTransactions()
  }, [])

  const fetchRecentTransactions = async () => {
    try {
      const response = await clientAPI.getPayinTransactions({ limit: 5 })
      if (response.success) {
        setRecentTransactions(response.transactions)
      }
    } catch (error) {
      console.error('Failed to fetch recent transactions:', error)
    }
  }

  const handleGenerate = async (e) => {
    e.preventDefault()
    
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }

    if (!formData.orderId) {
      toast.error('Please enter an order ID')
      return
    }

    if (!formData.customerMobile || formData.customerMobile.length !== 10) {
      toast.error('Please enter a valid 10-digit mobile number')
      return
    }

    if (!formData.customerEmail || !formData.customerEmail.includes('@')) {
      toast.error('Please enter a valid email address')
      return
    }

    try {
      setLoading(true)

      // First encrypt the payload
      const payload = {
        amount: formData.amount,
        orderid: formData.orderId,
        payee_fname: formData.customerName.split(' ')[0] || formData.customerName,
        payee_lname: formData.customerName.split(' ').slice(1).join(' ') || '',
        payee_mobile: formData.customerMobile,
        payee_email: formData.customerEmail,
        productinfo: 'Payment'
      }

      const encryptResponse = await clientAPI.encryptData(JSON.stringify(payload))
      
      if (!encryptResponse.success) {
        toast.error('Failed to encrypt data')
        return
      }

      // Create payin order
      const orderResponse = await clientAPI.createPayinOrder({
        data: encryptResponse.encryptedText
      })

      if (!orderResponse.success) {
        toast.error(orderResponse.message || 'Failed to create order')
        return
      }

      // Decrypt response
      const decryptResponse = await clientAPI.decryptData(orderResponse.data)
      
      if (!decryptResponse.success) {
        toast.error('Failed to decrypt response')
        return
      }

      const orderData = JSON.parse(decryptResponse.decryptedText)
      
      // Generate payment URL with parameters
      const paymentParams = new URLSearchParams(orderData.payment_params)
      const paymentUrl = `${orderData.payment_url}?${paymentParams.toString()}`

      // Generate QR code
      const qrImageData = await QRCodeLib.toDataURL(paymentUrl, {
        width: 300,
        margin: 2,
        color: {
          dark: '#000000',
          light: '#FFFFFF'
        }
      })

      setQrImage(qrImageData)
      setQrData({
        ...orderData,
        paymentUrl
      })

      toast.success('Payment QR generated successfully!')
      fetchRecentTransactions()
    } catch (error) {
      console.error('Generate QR error:', error)
      toast.error(error.message || 'Failed to generate QR code')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    if (!qrImage) return
    
    const link = document.createElement('a')
    link.href = qrImage
    link.download = `payment-qr-${formData.orderId}.png`
    link.click()
    toast.success('QR Code downloaded!')
  }

  const handleCopyLink = () => {
    if (!qrData) return
    
    navigator.clipboard.writeText(qrData.paymentUrl)
    toast.success('Payment link copied to clipboard!')
  }

  const handleOpenPayment = () => {
    if (!qrData) return
    
    window.open(qrData.paymentUrl, '_blank')
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

  const getStatusBadge = (status) => {
    const statusConfig = {
      SUCCESS: 'bg-green-100 text-green-700',
      PENDING: 'bg-yellow-100 text-yellow-700',
      INITIATED: 'bg-blue-100 text-blue-700',
      FAILED: 'bg-red-100 text-red-700'
    }
    return statusConfig[status] || 'bg-gray-100 text-gray-700'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <QrCode className="h-8 w-8 text-orange-600" />
        <h1 className="text-3xl font-bold">Generate Payment QR</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Payment Details</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleGenerate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="amount">Amount (₹) *</Label>
                <Input
                  id="amount"
                  type="number"
                  placeholder="Enter amount"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  className="h-12 text-base"
                  required
                  min="1"
                  step="0.01"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="orderId">Order ID *</Label>
                <Input
                  id="orderId"
                  type="text"
                  placeholder="Enter unique order ID"
                  value={formData.orderId}
                  onChange={(e) => setFormData({ ...formData, orderId: e.target.value })}
                  className="h-12 text-base"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="customerName">Customer Name *</Label>
                <Input
                  id="customerName"
                  type="text"
                  placeholder="Enter customer name"
                  value={formData.customerName}
                  onChange={(e) => setFormData({ ...formData, customerName: e.target.value })}
                  className="h-12 text-base"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="customerMobile">Customer Mobile *</Label>
                <Input
                  id="customerMobile"
                  type="tel"
                  placeholder="Enter 10-digit mobile number"
                  value={formData.customerMobile}
                  onChange={(e) => setFormData({ ...formData, customerMobile: e.target.value })}
                  className="h-12 text-base"
                  required
                  maxLength="10"
                  pattern="[0-9]{10}"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="customerEmail">Customer Email *</Label>
                <Input
                  id="customerEmail"
                  type="email"
                  placeholder="Enter customer email"
                  value={formData.customerEmail}
                  onChange={(e) => setFormData({ ...formData, customerEmail: e.target.value })}
                  className="h-12 text-base"
                  required
                />
              </div>

              <Button 
                type="submit"
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 h-12"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <QrCode className="h-5 w-5 mr-2" />
                    Generate Payment QR
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Generated QR Code</CardTitle>
          </CardHeader>
          <CardContent>
            {qrData ? (
              <div className="space-y-4">
                <div className="flex justify-center p-8 bg-gray-50 rounded-lg">
                  {qrImage && (
                    <img 
                      src={qrImage} 
                      alt="Payment QR Code" 
                      className="w-64 h-64 border-4 border-white rounded-lg shadow-lg"
                    />
                  )}
                </div>

                <div className="space-y-3">
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm text-gray-600">Amount</p>
                    <p className="text-xl font-bold text-blue-600">{formatAmount(qrData.amount)}</p>
                  </div>

                  <div className="p-3 bg-green-50 rounded-lg">
                    <p className="text-sm text-gray-600">Net Amount (After Charges)</p>
                    <p className="text-xl font-bold text-green-600">{formatAmount(qrData.net_amount)}</p>
                    <p className="text-xs text-gray-500 mt-1">Charge: {formatAmount(qrData.charge_amount)}</p>
                  </div>

                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Transaction ID</p>
                    <p className="font-mono text-xs break-all">{qrData.txn_id}</p>
                  </div>

                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Payment Link</p>
                    <p className="font-mono text-xs break-all">{qrData.paymentUrl}</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <Button 
                    onClick={handleDownload}
                    className="bg-gradient-to-r from-green-600 to-green-700"
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Download
                  </Button>
                  <Button 
                    onClick={handleCopyLink}
                    variant="outline"
                  >
                    <Copy className="h-4 w-4 mr-1" />
                    Copy
                  </Button>
                  <Button 
                    onClick={handleOpenPayment}
                    variant="outline"
                  >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    Open
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-gray-400">
                <QrCode className="h-24 w-24 mb-4" />
                <p className="text-center">Fill in the payment details and click Generate to create your QR code</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Transactions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentTransactions.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No recent transactions</p>
            ) : (
              recentTransactions.map((txn) => (
                <div key={txn.txn_id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
                  <div className="flex items-center gap-4">
                    <QrCode className="h-8 w-8 text-gray-400" />
                    <div>
                      <p className="font-medium">{txn.order_id}</p>
                      <p className="text-sm text-gray-500">{formatDate(txn.created_at)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="font-bold">{formatAmount(txn.amount)}</p>
                      <p className="text-xs text-gray-500">Net: {formatAmount(txn.net_amount)}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBadge(txn.status)}`}>
                      {txn.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
