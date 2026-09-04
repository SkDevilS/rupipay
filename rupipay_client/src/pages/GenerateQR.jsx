import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { QrCode, Download, Copy, RefreshCw, Loader2, CheckCircle, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'
import * as QRCodeLib from 'qrcode'

export default function GenerateQRMudrape() {
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
  const [checking, setChecking] = useState(false)
  const [paymentStatus, setPaymentStatus] = useState(null)
  const [gateway, setGateway] = useState('PayU')
  const [statusInterval, setStatusInterval] = useState(null)
  const [successToastShown, setSuccessToastShown] = useState(false)

  // Generate a suggested Order ID
  const generateSuggestedOrderId = () => {
    const timestamp = Date.now()
    const random = Math.floor(Math.random() * 1000)
    return `ORD${timestamp}${random}`
  }

  useEffect(() => {
    fetchMerchantGateway()
    
    return () => {
      if (statusInterval) {
        clearInterval(statusInterval)
      }
    }
  }, [])

  const fetchMerchantGateway = async () => {
    try {
      const response = await clientAPI.getMerchantGateway('PAYIN')
      if (response.success) {
        setGateway(response.gateway)
      }
    } catch (error) {
      console.error('Failed to fetch gateway:', error)
      setGateway('PayU') // Default to PayU
    }
  }

  const handleGenerate = async (e) => {
    e.preventDefault()
    
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }

    if (!formData.orderId || formData.orderId.trim() === '') {
      toast.error('Please enter an Order ID')
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
      setPaymentStatus(null)
      setSuccessToastShown(false) // Reset the flag when generating new QR

      // Use user-provided Order ID
      const orderId = formData.orderId.trim()

      // First encrypt the payload
      const payload = {
        amount: formData.amount,
        orderid: orderId,
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

      let orderResponse
      
      console.log('Creating order with gateway:', gateway)
      
      if (gateway === 'Mudrape') {
        // Create Mudrape order
        orderResponse = await clientAPI.createMudrapeOrder({
          data: encryptResponse.encryptedText
        })
      } else {
        // Create PayU or Tourquest order (both use generic payin endpoint)
        orderResponse = await clientAPI.createPayinOrder({
          data: encryptResponse.encryptedText
        })
      }

      console.log('Order response:', orderResponse)

      if (!orderResponse.success) {
        toast.error(orderResponse.message || 'Failed to create order')
        return
      }

      // Decrypt response
      const decryptResponse = await clientAPI.decryptData(orderResponse.data)
      
      console.log('Decrypt response:', decryptResponse)
      
      if (!decryptResponse.success) {
        toast.error('Failed to decrypt response')
        return
      }

      const orderData = JSON.parse(decryptResponse.decryptedText)
      
      console.log('Order data:', orderData)
      console.log('PG Partner from response:', orderData.pg_partner)
      
      // Get the payment data (could be UPI string or image URL)
      const paymentData = orderData.payment_link || orderData.qr_string || orderData.upi_link
      
      console.log('Payment data:', paymentData)
      
      // Check if it's an image URL or a UPI string
      const isImageUrl = paymentData && (
        paymentData.startsWith('http://') || 
        paymentData.startsWith('https://') ||
        paymentData.includes('.png') ||
        paymentData.includes('.jpg') ||
        paymentData.includes('showQr') ||
        paymentData.includes('qrPath')
      )
      
      console.log('Is image URL?', isImageUrl)
      console.log('Payment data type:', typeof paymentData)
      
      if (isImageUrl) {
        // It's an image URL (Tourquest) - use it directly
        console.log('Detected image URL, displaying directly:', paymentData)
        setQrImage(paymentData)
        setQrData({
          ...orderData,
          gateway: gateway,
          upiLink: paymentData,
          isImageUrl: true
        })
      } else {
        // It's a UPI string (PayU/Mudrape) - generate QR code
        console.log('Detected UPI string, generating QR code:', paymentData)
        
        let qrImageData
        if (gateway === 'PayU') {
          // For PayU, generate payment URL with parameters
          const paymentParams = new URLSearchParams(orderData.payment_params)
          const paymentUrl = `${orderData.payment_url}?${paymentParams.toString()}`
          
          qrImageData = await QRCodeLib.toDataURL(paymentUrl, {
            width: 300,
            margin: 2,
            color: {
              dark: '#000000',
              light: '#FFFFFF'
            }
          })
          
          setQrData({
            ...orderData,
            gateway: 'PayU',
            paymentUrl,
            isImageUrl: false
          })
        } else {
          // For Mudrape or others with UPI string
          qrImageData = await QRCodeLib.toDataURL(paymentData, {
            width: 300,
            margin: 2,
            color: {
              dark: '#000000',
              light: '#FFFFFF'
            }
          })
          
          setQrData({
            ...orderData,
            gateway: gateway,
            upiLink: paymentData,
            isImageUrl: false
          })
        }
        
        setQrImage(qrImageData)
      }
      
      // Start polling for payment status
      if (gateway === 'Mudrape') {
        // Use order_id for Mudrape
        startStatusPolling(orderData.order_id, 'order_id')
      } else if (gateway === 'Tourquest') {
        // Use txn_id for Tourquest
        startStatusPolling(orderData.txn_id, 'txn_id')
      } else {
        // Use txn_id for others (PayU)
        startStatusPolling(orderData.txn_id, 'txn_id')
      }

      toast.success(`Payment QR generated successfully via ${gateway}!`)
    } catch (error) {
      console.error('Generate QR error:', error)
      toast.error(error.message || 'Failed to generate QR code')
    } finally {
      setLoading(false)
    }
  }

  const startStatusPolling = (identifier, identifierType = 'txn_id') => {
    // Clear any existing interval
    if (statusInterval) {
      clearInterval(statusInterval)
    }

    // Don't start polling if payment is already completed
    if (paymentStatus === 'SUCCESS' || paymentStatus === 'FAILED' || paymentStatus === 'CANCELLED') {
      return
    }

    // Poll every 5 seconds
    const interval = setInterval(async () => {
      await checkPaymentStatus(identifier, identifierType)
    }, 5000)

    setStatusInterval(interval)
  }

  const checkPaymentStatus = async (identifier = null, identifierType = 'txn_id') => {
    if (!identifier && !qrData) return

    // For Mudrape, use order_id (refId), for PayU/Tourquest use txn_id
    const transactionId = identifier || (gateway === 'Mudrape' ? qrData.order_id : qrData.txn_id)

    try {
      setChecking(true)

      let statusResponse
      
      if (gateway === 'Mudrape') {
        // Use order_id for Mudrape status check
        statusResponse = await clientAPI.getMudrapeStatusByOrderId(transactionId)
      } else {
        // Use txn_id for PayU and Tourquest
        statusResponse = await clientAPI.getPayinStatus(transactionId)
      }

      if (statusResponse.success) {
        const status = statusResponse.status || statusResponse.transaction?.status

        setPaymentStatus(status)

        if (status === 'SUCCESS') {
          // Stop polling immediately
          if (statusInterval) {
            clearInterval(statusInterval)
            setStatusInterval(null)
          }
          // Only show toast if it hasn't been shown yet
          if (!successToastShown) {
            toast.success('Payment successful!')
            setSuccessToastShown(true)
          }
          setChecking(false)
          return // Exit immediately
        } else if (status === 'FAILED' || status === 'CANCELLED') {
          // Stop polling immediately
          if (statusInterval) {
            clearInterval(statusInterval)
            setStatusInterval(null)
          }
          toast.error('Payment failed')
          setChecking(false)
          return // Exit immediately
        }
      }
    } catch (error) {
      console.error('Check status error:', error)
    } finally {
      setChecking(false)
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
    
    const link = gateway === 'Mudrape' ? qrData.upiLink : qrData.paymentUrl
    navigator.clipboard.writeText(link)
    toast.success('Payment link copied to clipboard!')
  }

  const handleReset = () => {
    setQrData(null)
    setQrImage('')
    setPaymentStatus(null)
    setSuccessToastShown(false) // Reset the flag
    if (statusInterval) {
      clearInterval(statusInterval)
      setStatusInterval(null)
    }
    setFormData({
      amount: '',
      orderId: '',
      customerName: '',
      customerMobile: '',
      customerEmail: ''
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Generate Payment QR</h1>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-100 text-purple-700 rounded-md text-sm font-medium">
          <QrCode className="h-4 w-4" />
          Gateway: {gateway}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form Section */}
        <Card>
          <CardHeader>
            <CardTitle>Payment Details</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <Label htmlFor="amount">Amount (₹)</Label>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  placeholder="Enter amount"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  disabled={loading || !!qrData}
                  required
                />
              </div>

              <div>
                <Label htmlFor="orderId">Order ID</Label>
                <div className="flex gap-2">
                  <Input
                    id="orderId"
                    type="text"
                    placeholder="Enter unique order ID"
                    value={formData.orderId}
                    onChange={(e) => setFormData({ ...formData, orderId: e.target.value })}
                    disabled={loading || !!qrData}
                    required
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setFormData({ ...formData, orderId: generateSuggestedOrderId() })}
                    disabled={loading || !!qrData}
                    className="whitespace-nowrap"
                  >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Generate
                  </Button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Enter a unique order ID from your system or click Generate
                </p>
              </div>

              <div>
                <Label htmlFor="customerName">Customer Name</Label>
                <Input
                  id="customerName"
                  type="text"
                  placeholder="Enter customer name"
                  value={formData.customerName}
                  onChange={(e) => setFormData({ ...formData, customerName: e.target.value })}
                  disabled={loading || !!qrData}
                  required
                />
              </div>

              <div>
                <Label htmlFor="customerMobile">Mobile Number</Label>
                <Input
                  id="customerMobile"
                  type="tel"
                  placeholder="10-digit mobile number"
                  maxLength="10"
                  value={formData.customerMobile}
                  onChange={(e) => setFormData({ ...formData, customerMobile: e.target.value.replace(/\D/g, '') })}
                  disabled={loading || !!qrData}
                  required
                />
              </div>

              <div>
                <Label htmlFor="customerEmail">Email Address</Label>
                <Input
                  id="customerEmail"
                  type="email"
                  placeholder="customer@example.com"
                  value={formData.customerEmail}
                  onChange={(e) => setFormData({ ...formData, customerEmail: e.target.value })}
                  disabled={loading || !!qrData}
                  required
                />
              </div>

              <div className="flex gap-2">
                {!qrData ? (
                  <Button type="submit" disabled={loading} className="flex-1">
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <QrCode className="mr-2 h-4 w-4" />
                        Generate QR
                      </>
                    )}
                  </Button>
                ) : (
                  <Button type="button" onClick={handleReset} variant="outline" className="flex-1">
                    Generate New QR
                  </Button>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        {/* QR Display Section */}
        <Card>
          <CardHeader>
            <CardTitle>Payment QR Code</CardTitle>
          </CardHeader>
          <CardContent>
            {qrImage ? (
              <div className="space-y-4">
                <div className="flex justify-center">
                  <div className="p-4 bg-white rounded-lg border-2 border-gray-200">
                    <img src={qrImage} alt="Payment QR Code" className="w-64 h-64" />
                  </div>
                </div>

                {/* Payment Status */}
                {paymentStatus && (
                  <div className={`flex items-center justify-center gap-2 p-3 rounded-md ${
                    paymentStatus === 'SUCCESS' ? 'bg-green-100 text-green-700' :
                    paymentStatus === 'FAILED' || paymentStatus === 'CANCELLED' ? 'bg-red-100 text-red-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {paymentStatus === 'SUCCESS' ? (
                      <CheckCircle className="h-5 w-5" />
                    ) : paymentStatus === 'FAILED' || paymentStatus === 'CANCELLED' ? (
                      <XCircle className="h-5 w-5" />
                    ) : (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    )}
                    <span className="font-medium">Status: {paymentStatus}</span>
                  </div>
                )}

                {/* Transaction Details */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Transaction ID:</span>
                    <span className="font-mono">{qrData.txn_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Order ID:</span>
                    <span className="font-mono">{qrData.order_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Amount:</span>
                    <span className="font-semibold">₹{qrData.amount}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Gateway:</span>
                    <span className="font-medium">{qrData.gateway}</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <Button onClick={handleDownload} variant="outline" className="flex-1">
                    <Download className="mr-2 h-4 w-4" />
                    Download
                  </Button>
                  <Button onClick={handleCopyLink} variant="outline" className="flex-1">
                    <Copy className="mr-2 h-4 w-4" />
                    Copy Link
                  </Button>
                  {gateway === 'Mudrape' && paymentStatus !== 'SUCCESS' && paymentStatus !== 'FAILED' && (
                    <Button 
                      onClick={() => checkPaymentStatus()} 
                      variant="outline" 
                      disabled={checking}
                      className="flex-1"
                    >
                      {checking ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="mr-2 h-4 w-4" />
                      )}
                      Check Status
                    </Button>
                  )}
                </div>

                {gateway === 'Mudrape' && (
                  <p className="text-xs text-gray-500 text-center">
                    Payment status is automatically checked every 5 seconds
                  </p>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <QrCode className="h-16 w-16 mb-4" />
                <p>QR code will appear here</p>
                <p className="text-sm mt-2">Fill the form and click Generate QR</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
