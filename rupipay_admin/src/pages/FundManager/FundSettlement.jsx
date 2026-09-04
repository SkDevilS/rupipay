import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Building, Eye, EyeOff, RefreshCw, CheckCircle, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'
import { formatCurrency, formatDateTime } from '@/lib/utils'

export default function FundSettlement() {
  const [fundRequests, setFundRequests] = useState([])
  const [loading, setLoading] = useState(false)
  const [processingId, setProcessingId] = useState(null)

  useEffect(() => {
    fetchFundRequests()
  }, [])

  const fetchFundRequests = async () => {
    try {
      const response = await adminAPI.getFundRequests('PENDING')
      if (response.success) {
        setFundRequests(response.data)
      }
    } catch (error) {
      console.error('Error fetching fund requests:', error)
    }
  }

  const handleApprove = async (requestId) => {
    setProcessingId(requestId)
    setLoading(true)
    
    try {
      const response = await adminAPI.processFundRequest(requestId, {
        action: 'APPROVE',
        remarks: 'Approved by admin'
      })
      
      if (response.success) {
        toast.success('Fund request approved successfully!')
        fetchFundRequests()
      } else {
        toast.error(response.message || 'Approval failed')
      }
    } catch (error) {
      toast.error(error.message || 'An error occurred')
    } finally {
      setLoading(false)
      setProcessingId(null)
    }
  }

  const handleReject = async (requestId) => {
    setProcessingId(requestId)
    setLoading(true)
    
    try {
      const response = await adminAPI.processFundRequest(requestId, {
        action: 'REJECT',
        remarks: 'Rejected by admin'
      })
      
      if (response.success) {
        toast.success('Fund request rejected')
        fetchFundRequests()
      } else {
        toast.error(response.message || 'Rejection failed')
      }
    } catch (error) {
      toast.error(error.message || 'An error occurred')
    } finally {
      setLoading(false)
      setProcessingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Building className="h-8 w-8 text-orange-600" />
        <h1 className="text-3xl font-bold">Fund Settlement</h1>
      </div>

      {/* Pending Fund Requests */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Pending Fund Requests</h2>
            <Button
              variant="ghost"
              size="sm"
              className="text-gray-600 hover:text-gray-900"
              onClick={fetchFundRequests}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Request ID</TableHead>
                  <TableHead>Merchant Name</TableHead>
                  <TableHead>Mobile</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Requested At</TableHead>
                  <TableHead>Remarks</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fundRequests.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No pending requests
                    </TableCell>
                  </TableRow>
                ) : (
                  fundRequests.map((request) => (
                    <TableRow key={request.id}>
                      <TableCell className="font-medium">{request.request_id}</TableCell>
                      <TableCell>{request.full_name}</TableCell>
                      <TableCell>{request.mobile}</TableCell>
                      <TableCell>{request.email}</TableCell>
                      <TableCell>{formatCurrency(request.amount)}</TableCell>
                      <TableCell>{formatDateTime(request.requested_at)}</TableCell>
                      <TableCell>{request.remarks || '-'}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleApprove(request.request_id)}
                            disabled={loading && processingId === request.request_id}
                            className="text-green-600 hover:text-green-700 hover:bg-green-50"
                          >
                            <CheckCircle className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleReject(request.request_id)}
                            disabled={loading && processingId === request.request_id}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            <XCircle className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
