import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { FileText, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { clientAPI } from '@/api/client_api'
import { formatCurrency, formatDateTime } from '@/lib/utils'

export default function FundRequest() {
  const [amount, setAmount] = useState('')
  const [remarks, setRemarks] = useState('')
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchRequests()
  }, [])

  const fetchRequests = async () => {
    try {
      const response = await clientAPI.getFundRequests()
      if (response.success) {
        setRequests(response.data)
      }
    } catch (error) {
      console.error('Error fetching requests:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }
    
    setLoading(true)
    
    try {
      const response = await clientAPI.createFundRequest({
        amount: parseFloat(amount),
        remarks: remarks
      })
      
      if (response.success) {
        toast.success('Fund request submitted successfully!')
        setAmount('')
        setRemarks('')
        fetchRequests()
      } else {
        toast.error(response.message || 'Request failed')
      }
    } catch (error) {
      toast.error(error.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setAmount('')
    setRemarks('')
    toast.info('Form reset')
  }

  const getStatusBadge = (status) => {
    const statusColors = {
      'PENDING': 'bg-yellow-100 text-yellow-700',
      'APPROVED': 'bg-green-100 text-green-700',
      'REJECTED': 'bg-red-100 text-red-700'
    }
    
    return (
      <Badge className={`${statusColors[status]} hover:${statusColors[status]}`}>
        {status}
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="h-8 w-8 text-blue-600" />
        <h1 className="text-3xl font-bold">Fund Request</h1>
      </div>

      {/* Request Form */}
      <Card>
        <CardHeader>
          <CardTitle>Submit Fund Request</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                />
              </div>

              <div>
                <Label className="text-base font-medium mb-2 block">Remarks (Optional)</Label>
                <Input
                  type="text"
                  placeholder="Enter remarks"
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  className="h-12 text-base"
                />
              </div>
            </div>

            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={loading}
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-8 h-11"
              >
                {loading ? 'Submitting...' : 'Submit Request'}
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

      {/* Request History */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Request History</CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchRequests}
              className="text-gray-600 hover:text-gray-900"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Request ID</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Requested At</TableHead>
                <TableHead>Processed At</TableHead>
                <TableHead>Remarks</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {requests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-gray-500">
                    No requests found
                  </TableCell>
                </TableRow>
              ) : (
                requests.map((request) => (
                  <TableRow key={request.id}>
                    <TableCell className="font-medium">{request.request_id}</TableCell>
                    <TableCell>{formatCurrency(request.amount)}</TableCell>
                    <TableCell>{getStatusBadge(request.status)}</TableCell>
                    <TableCell>{formatDateTime(request.requested_at)}</TableCell>
                    <TableCell>
                      {request.processed_at ? formatDateTime(request.processed_at) : '-'}
                    </TableCell>
                    <TableCell>{request.remarks || '-'}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
