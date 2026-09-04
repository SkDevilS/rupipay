import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import adminAPI from '../../api/admin_api';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import { Search, AlertTriangle, CheckCircle, XCircle, Loader2, Edit } from 'lucide-react';

// Helper function to format PG Partner names for display
const formatPGPartnerName = (pgPartner) => {
  if (!pgPartner) return '-';
  
  const nameMap = {
    'Paytouch2': 'PT2',
    'Paytouch3_Trendora': 'PT3',
    'PAYTOUCH2': 'PT2',
    'PAYTOUCH3_TRENDORA': 'PT3'
  };
  
  return nameMap[pgPartner] || pgPartner;
};

export default function TransactionSearch() {
  const [searchQuery, setSearchQuery] = useState('');
  const [transactionType, setTransactionType] = useState('payin');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedTxn, setSelectedTxn] = useState(null);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [updateStatus, setUpdateStatus] = useState('FAILED');
  const [updateReason, setUpdateReason] = useState('');
  const [updating, setUpdating] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a transaction ID or order ID');
      return;
    }

    try {
      setLoading(true);
      setSearchResults([]);

      const response = await adminAPI.searchTransaction(searchQuery.trim(), transactionType);

      if (response.success) {
        setSearchResults(response.results || []);
        if (response.results.length === 0) {
          toast.info('No transactions found');
        } else {
          toast.success(`Found ${response.results.length} transaction(s)`);
        }
      } else {
        toast.error(response.message || 'Search failed');
      }
    } catch (error) {
      console.error('Search error:', error);
      toast.error(error.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const openUpdateModal = (txn) => {
    setSelectedTxn(txn);
    setUpdateStatus(txn.status === 'SUCCESS' ? 'FAILED' : 'SUCCESS');
    setUpdateReason('');
    setShowUpdateModal(true);
  };

  const handleUpdateStatus = async () => {
    if (updateStatus === 'FAILED' && !updateReason.trim()) {
      toast.error('Please provide a reason for marking as FAILED');
      return;
    }

    const confirmed = window.confirm(
      `Are you sure you want to update transaction ${selectedTxn.txn_id} to ${updateStatus}?\n\n` +
      `Current Status: ${selectedTxn.status}\n` +
      `New Status: ${updateStatus}\n` +
      (updateReason ? `Reason: ${updateReason}\n\n` : '\n') +
      `This action will:\n` +
      `- Update the transaction status\n` +
      `- Send a callback to the merchant\n` +
      (updateStatus === 'FAILED' && transactionType === 'payout' ? `- Refund the amount to merchant wallet\n` : '') +
      (updateStatus === 'SUCCESS' && transactionType === 'payin' ? `- Credit the amount to merchant wallet\n` : '') +
      `\nThis action cannot be undone.`
    );

    if (!confirmed) return;

    try {
      setUpdating(true);

      const response = await adminAPI.updateTransactionStatus(
        selectedTxn.txn_id,
        transactionType,
        updateStatus,
        updateReason.trim()
      );

      if (response.success) {
        toast.success(response.message || 'Transaction updated successfully');
        
        // Show callback status
        if (response.callback_sent) {
          toast.success('Callback sent to merchant successfully');
        } else if (response.callback_response && response.callback_response.error) {
          toast.warning(`Callback failed: ${response.callback_response.error}`);
        }

        // Refresh search results
        handleSearch();
        setShowUpdateModal(false);
      } else {
        toast.error(response.message || 'Update failed');
      }
    } catch (error) {
      console.error('Update error:', error);
      toast.error(error.message || 'Update failed');
    } finally {
      setUpdating(false);
    }
  };

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      SUCCESS: { color: 'bg-green-500', text: 'Success' },
      FAILED: { color: 'bg-red-500', text: 'Failed' },
      INITIATED: { color: 'bg-blue-500', text: 'Initiated' },
      QUEUED: { color: 'bg-yellow-500', text: 'Queued' },
      PENDING: { color: 'bg-orange-500', text: 'Pending' }
    };

    const config = statusConfig[status] || { color: 'bg-gray-500', text: status };
    
    return (
      <Badge className={config.color}>
        {config.text}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Transaction Search & Update</h1>
          <p className="text-gray-500 mt-1">
            Search for any transaction and update its status
          </p>
        </div>
      </div>

      {/* Warning Card */}
      <Card className="border-orange-200 bg-orange-50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-orange-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-orange-900">Important Notice</h3>
              <p className="text-sm text-orange-800 mt-1">
                This feature allows you to search for any transaction (regardless of status) and update its status.
                When marking as FAILED, you must provide a reason. The system will automatically send callbacks
                and handle wallet adjustments. Use this feature carefully as changes cannot be undone.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search Section */}
      <Card>
        <CardHeader>
          <CardTitle>Search Transaction</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Transaction Type Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Transaction Type</label>
              <div className="flex gap-2">
                <Button
                  variant={transactionType === 'payin' ? 'default' : 'outline'}
                  onClick={() => {
                    setTransactionType('payin');
                    setSearchResults([]);
                  }}
                >
                  Payin
                </Button>
                <Button
                  variant={transactionType === 'payout' ? 'default' : 'outline'}
                  onClick={() => {
                    setTransactionType('payout');
                    setSearchResults([]);
                  }}
                >
                  Payout
                </Button>
              </div>
            </div>

            {/* Search Input */}
            <div className="flex gap-2">
              <Input
                type="text"
                placeholder={`Enter ${transactionType === 'payin' ? 'Transaction ID or Order ID' : 'Transaction ID, Reference ID, or Order ID'}`}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="flex-1"
              />
              <Button 
                onClick={handleSearch} 
                disabled={loading || !searchQuery.trim()}
              >
                <Search className="w-4 h-4 mr-2" />
                {loading ? 'Searching...' : 'Search'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {searchResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Search Results ({searchResults.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Transaction ID</TableHead>
                    <TableHead>{transactionType === 'payin' ? 'Order ID' : 'Reference ID'}</TableHead>
                    {transactionType === 'payout' && <TableHead>Order ID</TableHead>}
                    <TableHead>Merchant</TableHead>
                    {transactionType === 'payout' && <TableHead>Beneficiary</TableHead>}
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Service</TableHead>
                    <TableHead>PG Txn ID</TableHead>
                    <TableHead>UTR</TableHead>
                    <TableHead>Created At</TableHead>
                    <TableHead>Completed At</TableHead>
                    <TableHead>Callback</TableHead>
                    <TableHead>Remarks</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {searchResults.map((txn) => (
                    <TableRow key={txn.id}>
                      <TableCell className="font-mono text-sm">{txn.txn_id}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {transactionType === 'payin' ? txn.order_id : txn.reference_id}
                      </TableCell>
                      {transactionType === 'payout' && (
                        <TableCell className="font-mono text-sm">{txn.order_id || '-'}</TableCell>
                      )}
                      <TableCell>
                        <div>{txn.merchant_name || '-'}</div>
                        <div className="text-xs text-gray-500">{txn.merchant_id}</div>
                      </TableCell>
                      {transactionType === 'payout' && (
                        <TableCell>
                          <div>{txn.bene_name}</div>
                          <div className="text-xs text-gray-500 font-mono">{txn.account_no}</div>
                        </TableCell>
                      )}
                      <TableCell className="font-semibold">{formatAmount(txn.amount)}</TableCell>
                      <TableCell>{getStatusBadge(txn.status)}</TableCell>
                      <TableCell>{formatPGPartnerName(txn.pg_partner)}</TableCell>
                      <TableCell className="font-mono text-xs">{txn.pg_txn_id || '-'}</TableCell>
                      <TableCell className="font-mono text-xs">{txn.utr || '-'}</TableCell>
                      <TableCell className="text-sm">{formatDate(txn.created_at)}</TableCell>
                      <TableCell className="text-sm">{formatDate(txn.completed_at)}</TableCell>
                      <TableCell>
                        {txn.callback_url ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500" />
                        )}
                      </TableCell>
                      <TableCell className="max-w-xs truncate" title={txn.remarks || txn.error_message}>
                        {txn.remarks || txn.error_message || '-'}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openUpdateModal(txn)}
                        >
                          <Edit className="w-4 h-4 mr-1" />
                          Update
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Update Status Modal */}
      {showUpdateModal && selectedTxn && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl m-4">
            <CardHeader className="border-b">
              <div className="flex items-center justify-between">
                <CardTitle>Update Transaction Status</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowUpdateModal(false)}
                  disabled={updating}
                >
                  <XCircle className="w-5 h-5" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              {/* Transaction Details */}
              <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="font-semibold">Transaction ID:</div>
                  <div className="font-mono">{selectedTxn.txn_id}</div>
                  
                  <div className="font-semibold">Current Status:</div>
                  <div>{getStatusBadge(selectedTxn.status)}</div>
                  
                  <div className="font-semibold">Amount:</div>
                  <div className="font-semibold">{formatAmount(selectedTxn.amount)}</div>
                  
                  <div className="font-semibold">Merchant:</div>
                  <div>{selectedTxn.merchant_name} ({selectedTxn.merchant_id})</div>
                </div>
              </div>

              {/* New Status Selection */}
              <div>
                <label className="block text-sm font-medium mb-2">New Status</label>
                <div className="flex gap-2">
                  <Button
                    variant={updateStatus === 'SUCCESS' ? 'default' : 'outline'}
                    onClick={() => setUpdateStatus('SUCCESS')}
                    disabled={updating}
                    className={updateStatus === 'SUCCESS' ? 'bg-green-500 hover:bg-green-600' : ''}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Mark as SUCCESS
                  </Button>
                  <Button
                    variant={updateStatus === 'FAILED' ? 'default' : 'outline'}
                    onClick={() => setUpdateStatus('FAILED')}
                    disabled={updating}
                    className={updateStatus === 'FAILED' ? 'bg-red-500 hover:bg-red-600' : ''}
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Mark as FAILED
                  </Button>
                </div>
              </div>

              {/* Reason Input */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Reason {updateStatus === 'FAILED' && <span className="text-red-500">*</span>}
                </label>
                <textarea
                  className="w-full border rounded-md p-2 min-h-[100px]"
                  placeholder={updateStatus === 'FAILED' ? 'Enter reason for failure (required)' : 'Enter reason for status change (optional)'}
                  value={updateReason}
                  onChange={(e) => setUpdateReason(e.target.value)}
                  disabled={updating}
                />
              </div>

              {/* Impact Notice */}
              <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">This action will:</h4>
                <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
                  <li>Update transaction status to {updateStatus}</li>
                  <li>Send callback to merchant with updated status</li>
                  {updateStatus === 'FAILED' && transactionType === 'payout' && (
                    <li className="font-semibold">Refund ₹{selectedTxn.amount} to merchant settled wallet</li>
                  )}
                  {updateStatus === 'SUCCESS' && transactionType === 'payin' && (
                    <li className="font-semibold">Credit ₹{selectedTxn.net_amount} to merchant unsettled wallet</li>
                  )}
                  <li>Log the transaction in wallet history</li>
                </ul>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => setShowUpdateModal(false)}
                  disabled={updating}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleUpdateStatus}
                  disabled={updating || (updateStatus === 'FAILED' && !updateReason.trim())}
                  className={updateStatus === 'SUCCESS' ? 'bg-green-500 hover:bg-green-600' : 'bg-red-500 hover:bg-red-600'}
                >
                  {updating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Updating...
                    </>
                  ) : (
                    <>
                      Update to {updateStatus}
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
