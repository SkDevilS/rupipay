import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FileText, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'
import { formatCurrency, formatDateTime } from '@/lib/utils'

export default function FundRequests() {
  const [fundRequests, setFundRequests] = useState([])
  const [loading, setLoading] = useState(false)
  const [processingId, setProcessingId] = useState(null)
  const [activeTab, setActiveTab] = useState('PENDING')

  useEffect(() => {
    fetchFundRequests()
  }, [activeTab])

  const fetchFundRequests = async () => {
    try {
      const response = await adminAPI.getFundRequests(activeTab)
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

  const pendingCount = fundRequests.filter(r => r.status === 'PENDING').length
  const approvedCount = fundRequests.filter(r => r.status === 'APPROVED').length
  const rejectedCount = fundRequests.filter(r => r.status === 'REJECTED').length

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="h-8 w-8 text-blue-600" />
        <h1 className="text-3xl font-bold">Fund Requests</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Pending Requests</p>
            <p className="text-2xl font-bold text-yellow-600">{pendingCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Approved</p>
            <p className="text-2xl font-bold text-green-600">{approvedCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Rejected</p>
            <p className="text-2xl font-bold text-red-600">{rejectedCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('PENDING')}
          className={`px-6 py-3 font-medium transition-colors relative ${
            activeTab === 'PENDING'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Pending
        </button>
        <button
          onClick={() => setActiveTab('APPROVED')}
          className={`px-6 py-3 font-medium transition-colors relative ${
            activeTab === 'APPROVED'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Approved
        </button>
        <button
          onClick={() => setActiveTab('REJECTED')}
          className={`px-6 py-3 font-medium transition-colors relative ${
            activeTab === 'REJECTED'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Rejected
        </button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Request History</CardTitle>
            <Button
              variant="ghost"
              size="sm"
              className="text-gray-600 hover:text-gray-900"
              onClick={fetchFundRequests}
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
                <TableHead>Merchant Name</TableHead>
                <TableHead>Mobile</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Requested At</TableHead>
                <TableHead>Processed At</TableHead>
                <TableHead>Remarks</TableHead>
                {activeTab === 'PENDING' && <TableHead>Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {fundRequests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={activeTab === 'PENDING' ? 9 : 8} className="text-center text-gray-500">
                    No {activeTab.toLowerCase()} requests
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
                    <TableCell>
                      {request.processed_at ? formatDateTime(request.processed_at) : '-'}
                    </TableCell>
                    <TableCell>{request.remarks || '-'}</TableCell>
                    {activeTab === 'PENDING' && (
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
                    )}
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
