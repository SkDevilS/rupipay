import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CreditCard, Download, RefreshCw, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'
import jsPDF from 'jspdf'
import 'jspdf-autotable'

export default function MyCommercials() {
  const [loading, setLoading] = useState(true)
  const [commercialData, setCommercialData] = useState({
    scheme: null,
    charges: {
      payout: [],
      payin: []
    }
  })

  useEffect(() => {
    loadCommercials()
  }, [])

  const loadCommercials = async () => {
    try {
      setLoading(true)
      const response = await clientAPI.getCommercials()
      if (response.success) {
        setCommercialData({
          scheme: response.scheme,
          charges: response.charges
        })
      }
    } catch (error) {
      toast.error('Failed to load commercials')
      console.error('Load commercials error:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount)
  }

  const formatChargeValue = (value, type) => {
    if (type === 'PERCENTAGE') {
      return `${value}%`
    }
    return formatAmount(value)
  }

  const handleDownload = () => {
    if (!commercialData.scheme) {
      toast.error('No commercial data to download')
      return
    }

    try {
      const doc = new jsPDF()
      const merchantName = clientAPI.getMerchantName() || 'Merchant'
      const merchantId = clientAPI.getMerchantId() || 'N/A'
      const currentDate = new Date().toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })

      // Add header
      doc.setFontSize(20)
      doc.setTextColor(234, 88, 12) // Orange color
      doc.text('Commercial Scheme Report', 105, 20, { align: 'center' })
      
      // Add merchant info
      doc.setFontSize(10)
      doc.setTextColor(0, 0, 0)
      doc.text(`Merchant: ${merchantName}`, 14, 35)
      doc.text(`Merchant ID: ${merchantId}`, 14, 40)
      doc.text(`Scheme: ${commercialData.scheme.scheme_name}`, 14, 45)
      doc.text(`Generated: ${currentDate}`, 14, 50)
      
      // Add line separator
      doc.setDrawColor(234, 88, 12)
      doc.setLineWidth(0.5)
      doc.line(14, 55, 196, 55)

      let yPosition = 65

      // Add Payout Charges Table
      if (commercialData.charges.payout.length > 0) {
        doc.setFontSize(14)
        doc.setTextColor(234, 88, 12)
        doc.text('Payout Charges', 14, yPosition)
        yPosition += 5

        const payoutData = commercialData.charges.payout.map((item, index) => [
          index + 1,
          item.product_name,
          `Rs.${item.min_amount.toLocaleString('en-IN')} - Rs.${item.max_amount.toLocaleString('en-IN')}`,
          item.charge_type === 'PERCENTAGE' ? `${item.charge_value}%` : `Rs.${item.charge_value.toLocaleString('en-IN')}`,
          item.charge_type === 'PERCENTAGE' ? 'Percentage' : 'Fixed'
        ])

        doc.autoTable({
          startY: yPosition,
          head: [['Sr. No.', 'Product Name', 'Amount Range', 'Charge Value', 'Charge Type']],
          body: payoutData,
          theme: 'grid',
          headStyles: {
            fillColor: [234, 88, 12],
            textColor: [255, 255, 255],
            fontSize: 10,
            fontStyle: 'bold'
          },
          bodyStyles: {
            fontSize: 9
          },
          alternateRowStyles: {
            fillColor: [255, 247, 237]
          },
          margin: { left: 14, right: 14 }
        })

        yPosition = doc.lastAutoTable.finalY + 15
      }

      // Add Payin Charges Table
      if (commercialData.charges.payin.length > 0) {
        // Check if we need a new page
        if (yPosition > 250) {
          doc.addPage()
          yPosition = 20
        }

        doc.setFontSize(14)
        doc.setTextColor(234, 88, 12)
        doc.text('Payin Charges', 14, yPosition)
        yPosition += 5

        const payinData = commercialData.charges.payin.map((item, index) => [
          index + 1,
          item.product_name,
          `Rs.${item.min_amount.toLocaleString('en-IN')} - Rs.${item.max_amount.toLocaleString('en-IN')}`,
          item.charge_type === 'PERCENTAGE' ? `${item.charge_value}%` : `Rs.${item.charge_value.toLocaleString('en-IN')}`,
          item.charge_type === 'PERCENTAGE' ? 'Percentage' : 'Fixed'
        ])

        doc.autoTable({
          startY: yPosition,
          head: [['Sr. No.', 'Product Name', 'Amount Range', 'Charge Value', 'Charge Type']],
          body: payinData,
          theme: 'grid',
          headStyles: {
            fillColor: [59, 130, 246],
            textColor: [255, 255, 255],
            fontSize: 10,
            fontStyle: 'bold'
          },
          bodyStyles: {
            fontSize: 9
          },
          alternateRowStyles: {
            fillColor: [239, 246, 255]
          },
          margin: { left: 14, right: 14 }
        })
      }

      // Add footer
      const pageCount = doc.internal.getNumberOfPages()
      for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i)
        doc.setFontSize(8)
        doc.setTextColor(128, 128, 128)
        doc.text(
          `Page ${i} of ${pageCount}`,
          105,
          doc.internal.pageSize.height - 10,
          { align: 'center' }
        )
        doc.text(
          'Paysetu - Commercial Scheme Report',
          14,
          doc.internal.pageSize.height - 10
        )
      }

      // Save the PDF
      const fileName = `Commercial_Scheme_${commercialData.scheme.scheme_name.replace(/\s+/g, '_')}_${new Date().getTime()}.pdf`
      doc.save(fileName)
      
      toast.success('Commercial scheme report downloaded successfully!')
    } catch (error) {
      console.error('PDF generation error:', error)
      toast.error('Failed to generate PDF report')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading commercials...</p>
        </div>
      </div>
    )
  }

  if (!commercialData.scheme) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <CreditCard className="h-8 w-8 text-orange-600" />
          <h1 className="text-3xl font-bold">My Commercials</h1>
        </div>
        <Card className="border-2 border-dashed border-gray-300">
          <CardContent className="py-12">
            <div className="text-center">
              <AlertCircle className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-700 mb-2">No Scheme Assigned</h3>
              <p className="text-sm text-gray-500">
                Please contact the administrator to assign a commercial scheme to your account.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with Scheme Info and Download Button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CreditCard className="h-8 w-8 text-orange-600" />
          <div>
            <h1 className="text-3xl font-bold">My Commercials</h1>
            <p className="text-sm text-gray-600 mt-1">View your assigned commercial rates and charges</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            onClick={loadCommercials}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button
            onClick={handleDownload}
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
          >
            <Download className="h-4 w-4 mr-2" />
            Download Report
          </Button>
        </div>
      </div>

      {/* Payout Section */}
      {commercialData.charges.payout.length > 0 && (
        <Card className="border border-gray-200 shadow-sm">
          <CardHeader className="border-b bg-gray-50 py-4">
            <CardTitle className="text-lg font-bold text-gray-700 text-center">Payout Charges</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-white border-b">
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">SR / NO</TableHead>
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">Product Name</TableHead>
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">Amount Range</TableHead>
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">Charge Value</TableHead>
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">Charge Type</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {commercialData.charges.payout.map((item, index) => (
                    <TableRow key={index} className="border-b hover:bg-gray-50 transition-colors">
                      <TableCell className="text-sm text-gray-600">{index + 1}</TableCell>
                      <TableCell className="text-sm font-medium text-gray-900">{item.product_name}</TableCell>
                      <TableCell className="text-sm text-gray-700">
                        {formatAmount(item.min_amount)} - {formatAmount(item.max_amount)}
                      </TableCell>
                      <TableCell className="text-sm font-semibold text-orange-600">
                        {formatChargeValue(item.charge_value, item.charge_type)}
                      </TableCell>
                      <TableCell className="text-sm text-gray-700">
                        <Badge variant={item.charge_type === 'PERCENTAGE' ? 'default' : 'secondary'}>
                          {item.charge_type === 'PERCENTAGE' ? 'Percentage' : 'Fixed'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Payin Section */}
      {commercialData.charges.payin.length > 0 && (
        <Card className="border border-gray-200 shadow-sm">
          <CardHeader className="border-b bg-gray-50 py-4">
            <CardTitle className="text-lg font-bold text-gray-700 text-center">Payin Charges</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-white border-b">
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">SR / NO</TableHead>
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">Product Name</TableHead>
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">Amount Range</TableHead>
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">Charge Value</TableHead>
                    <TableHead className="text-xs font-semibold text-gray-600 uppercase">Charge Type</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {commercialData.charges.payin.map((item, index) => (
                    <TableRow key={index} className="border-b hover:bg-gray-50 transition-colors">
                      <TableCell className="text-sm text-gray-600">{index + 1}</TableCell>
                      <TableCell className="text-sm font-medium text-gray-900">{item.product_name}</TableCell>
                      <TableCell className="text-sm text-gray-700">
                        {formatAmount(item.min_amount)} - {formatAmount(item.max_amount)}
                      </TableCell>
                      <TableCell className="text-sm font-semibold text-blue-600">
                        {formatChargeValue(item.charge_value, item.charge_type)}
                      </TableCell>
                      <TableCell className="text-sm text-gray-700">
                        <Badge variant={item.charge_type === 'PERCENTAGE' ? 'default' : 'secondary'}>
                          {item.charge_type === 'PERCENTAGE' ? 'Percentage' : 'Fixed'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State for No Charges */}
      {commercialData.charges.payout.length === 0 && commercialData.charges.payin.length === 0 && (
        <Card className="border-2 border-dashed border-gray-300">
          <CardContent className="py-12">
            <div className="text-center">
              <AlertCircle className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-700 mb-2">No Charges Configured</h3>
              <p className="text-sm text-gray-500">
                The assigned scheme does not have any charges configured yet.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
