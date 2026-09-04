import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, RefreshCw, Eye } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'
import { formatCurrency, formatDateTime } from '@/lib/utils'

export default function PendingPayout() {
  const [payouts, setPayouts] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchPendingPayouts()
  }, [])

  const fetchPendingPayouts = async () => {
    setLoading(true)
    try {
      const response = await adminAPI.getPendingPayouts()
      if (response.success) {
        setPayouts(response.data)
      }
    } catch (error) {
      console.error('Error fetching pending payouts:', error)
      toast.error('Failed to fetch pending payouts')
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status) => {
    const statusColors = {
      'FAILED': 'bg-red-100 text-red-700',
      'INITIATED': 'bg-blue-100 text-blue-700',
      'INPROCESS': 'bg-yellow-100 text-yellow-700'
    }
    
    return (
      <Badge className={`${statusColors[status]} hover:${statusColors[status]}`}>
        {status}
      </Badge>
    )
  }

  const handleRetry = (txnId) => {
    toast.info('Retry functionality coming soon')
  }

  const handleViewDetails = (payout) => {
    toast.info('View details functionality coming soon')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertCircle className="h-8 w-8 text-orange-600" />
          <h1 className="text-3xl font-bold">Pending Payouts</h1>
        </div>
        <Button
          onClick={fetchPendingPayouts}
          variant="ghost"
          className="text-gray-600 hover:text-gray-900"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Total Pending</p>
            <p className="text-2xl font-bold text-orange-600">{payouts.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Failed</p>
            <p className="text-2xl font-bold text-red-600">
              {payouts.filter(p => p.status === 'FAILED').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">In Process</p>
            <p className="text-2xl font-bold text-yellow-600">
              {payouts.filter(p => p.status === 'INPROCESS').length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Pending Payouts Table */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Payout Transactions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Transaction ID</TableHead>
                  <TableHead>Merchant</TableHead>
                  <TableHead>Beneficiary</TableHead>
                  <TableHead>Bank</TableHead>
                  <TableHead>Account No</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Error Message</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : payouts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center text-gray-500">
                      No pending payouts
                    </TableCell>
                  </TableRow>
                ) : (
                  payouts.map((payout) => (
                    <TableRow key={payout.id}>
                      <TableCell className="font-medium">{payout.txn_id}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{payout.full_name}</div>
                          <div className="text-xs text-gray-500">{payout.merchant_id}</div>
                        </div>
                      </TableCell>
                      <TableCell>{payout.bene_name}</TableCell>
                      <TableCell>{payout.bene_bank}</TableCell>
                      <TableCell>{payout.account_no}</TableCell>
                      <TableCell>{formatCurrency(payout.amount)}</TableCell>
                      <TableCell>{getStatusBadge(payout.status)}</TableCell>
                      <TableCell>
                        <span className="text-xs text-red-600">
                          {payout.error_message || '-'}
                        </span>
                      </TableCell>
                      <TableCell>{formatDateTime(payout.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleViewDetails(payout)}
                            className="text-blue-600 hover:text-blue-700"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          {payout.status === 'FAILED' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleRetry(payout.txn_id)}
                              className="text-green-600 hover:text-green-700"
                            >
                              Retry
                            </Button>
                          )}
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
