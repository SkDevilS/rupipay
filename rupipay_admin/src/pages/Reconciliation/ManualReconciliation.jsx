import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Checkbox } from '../../components/ui/checkbox';
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
import { Search, AlertTriangle, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import TransactionSearch from './TransactionSearch';

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

export default function ManualReconciliation() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState('bulk'); // 'bulk' or 'search'
  const [activeTab, setActiveTab] = useState('payin'); // 'payin' or 'payout'
  const [merchants, setMerchants] = useState([]);
  const [selectedMerchant, setSelectedMerchant] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [transactions, setTransactions] = useState([]);
  const [selectedTxns, setSelectedTxns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [showSummary, setShowSummary] = useState(false);
  const [summary, setSummary] = useState(null);

  // Clear transactions when merchant or dates change
  useEffect(() => {
    setTransactions([]);
    setSelectedTxns([]);
  }, [selectedMerchant, fromDate, toDate]);

  useEffect(() => {
    fetchMerchants();
  }, []);

  const fetchMerchants = async () => {
    try {
      if (!adminAPI.isAuthenticated()) {
        toast.error('Please login to continue');
        navigate('/login', { replace: true });
        return;
      }

      const response = await adminAPI.getReconciliationMerchants();
      
      if (response.success) {
        setMerchants(response.merchants || []);
      } else {
        toast.error(response.message || 'Failed to load merchants');
      }
    } catch (error) {
      console.error('Fetch merchants error:', error);
      if (error.message && (error.message.includes('token') || error.message.includes('401'))) {
        toast.error('Session expired. Please login again.');
        navigate('/login', { replace: true });
      } else {
        toast.error(error.message || 'Failed to load merchants');
      }
    }
  };

  const fetchTransactions = async () => {
    if (!selectedMerchant || !fromDate || !toDate) {
      toast.error('Please select merchant and date range');
      return;
    }

    try {
      setLoading(true);
      setTransactions([]);
      setSelectedTxns([]);

      const payload = {
        merchant_id: selectedMerchant,
        from_date: fromDate,
        to_date: toDate
      };

      let response;
      if (activeTab === 'payin') {
        response = await adminAPI.getReconciliationPayins(payload);
      } else {
        response = await adminAPI.getReconciliationPayouts(payload);
      }

      if (response.success) {
        setTransactions(response[activeTab === 'payin' ? 'payins' : 'payouts'] || []);
        toast.success(`Found ${response.count} transactions`);
      } else {
        toast.error(response.message || 'Failed to load transactions');
      }
    } catch (error) {
      console.error('Fetch transactions error:', error);
      toast.error(error.message || 'Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedTxns(transactions.map(t => t.txn_id));
    } else {
      setSelectedTxns([]);
    }
  };

  const handleSelectTxn = (txnId, checked) => {
    if (checked) {
      setSelectedTxns([...selectedTxns, txnId]);
    } else {
      setSelectedTxns(selectedTxns.filter(id => id !== txnId));
    }
  };

  const processFailedTransactions = async () => {
    if (selectedTxns.length === 0) {
      toast.error('Please select at least one transaction');
      return;
    }

    const confirmed = window.confirm(
      `Are you sure you want to mark ${selectedTxns.length} transaction(s) as FAILED and send callbacks?\n\n` +
      `This action cannot be undone.`
    );

    if (!confirmed) return;

    try {
      setProcessing(true);
      setProgress({ current: 0, total: selectedTxns.length });

      // Simulate progress updates while processing
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev.current < prev.total - 1) {
            return { ...prev, current: prev.current + 1 };
          }
          return prev;
        });
      }, 500);

      let response;
      if (activeTab === 'payin') {
        response = await adminAPI.processFailedPayins({ txn_ids: selectedTxns });
      } else {
        response = await adminAPI.processFailedPayouts({ txn_ids: selectedTxns });
      }

      clearInterval(progressInterval);
      setProgress({ current: selectedTxns.length, total: selectedTxns.length });

      if (response.success) {
        // Prepare summary data
        const summaryData = {
          type: activeTab,
          total: selectedTxns.length,
          processed: response.total_processed || 0,
          failed: response.total_failed || 0,
          callbacksSent: response.processed?.filter(p => p.callback_sent).length || 0,
          callbacksFailed: response.processed?.filter(p => !p.callback_sent && p.callback_response).length || 0,
          details: {
            processed: response.processed || [],
            failed: response.failed || []
          }
        };

        setSummary(summaryData);
        setShowSummary(true);

        toast.success(`Processed ${response.total_processed} transactions successfully`);

        // Refresh the list
        fetchTransactions();
        setSelectedTxns([]);
      } else {
        toast.error(response.message || 'Failed to process transactions');
      }
    } catch (error) {
      console.error('Process failed transactions error:', error);
      toast.error(error.message || 'Failed to process transactions');
    } finally {
      setProcessing(false);
      setProgress({ current: 0, total: 0 });
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
      INITIATED: { color: 'bg-blue-500', text: 'Initiated' },
      QUEUED: { color: 'bg-yellow-500', text: 'Queued' }
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
          <h1 className="text-3xl font-bold">Manual Reconciliation</h1>
          <p className="text-gray-500 mt-1">
            {viewMode === 'bulk' 
              ? 'Bulk mark transactions as failed and process callbacks'
              : 'Search and update individual transactions'
            }
          </p>
        </div>
      </div>

      {/* View Mode Selection */}
      <div className="flex gap-2">
        <Button
          variant={viewMode === 'bulk' ? 'default' : 'outline'}
          onClick={() => setViewMode('bulk')}
        >
          Bulk Processing
        </Button>
        <Button
          variant={viewMode === 'search' ? 'default' : 'outline'}
          onClick={() => setViewMode('search')}
        >
          <Search className="w-4 h-4 mr-2" />
          Search & Update
        </Button>
      </div>

      {/* Render based on view mode */}
      {viewMode === 'search' ? (
        <TransactionSearch />
      ) : (
        <>
          {/* Progress Bar */}
          {processing && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                  <span className="font-semibold text-blue-900">Processing Transactions...</span>
                </div>
                <span className="text-sm text-blue-700">
                  {progress.current} / {progress.total}
                </span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                ></div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Modal */}
      {showSummary && summary && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl max-h-[80vh] overflow-y-auto m-4">
            <CardHeader className="border-b">
              <div className="flex items-center justify-between">
                <CardTitle className="text-2xl">Reconciliation Summary</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowSummary(false)}
                >
                  <XCircle className="w-5 h-5" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{summary.total}</div>
                  <div className="text-sm text-gray-600">Total Selected</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{summary.processed}</div>
                  <div className="text-sm text-gray-600">Marked Failed</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{summary.callbacksSent}</div>
                  <div className="text-sm text-gray-600">Callbacks Sent</div>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{summary.failed}</div>
                  <div className="text-sm text-gray-600">Failed</div>
                </div>
              </div>

              {/* Success Details */}
              {summary.details.processed.length > 0 && (
                <div>
                  <h3 className="font-semibold text-green-700 mb-3 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5" />
                    Successfully Processed ({summary.details.processed.length})
                  </h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {summary.details.processed.map((item, index) => (
                      <div key={index} className="bg-green-50 p-3 rounded border border-green-200">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="font-mono text-sm font-semibold">{item.txn_id}</div>
                          </div>
                          <div className="text-right">
                            {item.callback_sent ? (
                              <Badge className="bg-green-500">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Callback Sent
                              </Badge>
                            ) : (
                              <Badge className="bg-gray-500">No Callback</Badge>
                            )}
                          </div>
                        </div>
                        {item.callback_response && (
                          <div className="mt-2 text-xs text-gray-600">
                            {item.callback_response.status_code && (
                              <span>Status: {item.callback_response.status_code}</span>
                            )}
                            {item.callback_response.error && (
                              <span className="text-red-600">Error: {item.callback_response.error}</span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Failed Details */}
              {summary.details.failed.length > 0 && (
                <div>
                  <h3 className="font-semibold text-red-700 mb-3 flex items-center gap-2">
                    <XCircle className="w-5 h-5" />
                    Failed to Process ({summary.details.failed.length})
                  </h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {summary.details.failed.map((item, index) => (
                      <div key={index} className="bg-red-50 p-3 rounded border border-red-200">
                        <div className="font-mono text-sm font-semibold">{item.txn_id}</div>
                        <div className="text-sm text-red-700 mt-1">{item.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Close Button */}
              <div className="flex justify-end pt-4 border-t">
                <Button onClick={() => setShowSummary(false)}>
                  Close
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Warning Card */}
      <Card className="border-orange-200 bg-orange-50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-orange-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-orange-900">Important Notice</h3>
              <p className="text-sm text-orange-800 mt-1">
                This feature allows you to manually mark transactions as FAILED and send callbacks to merchants.
                Use this carefully as this action cannot be undone. For payouts, the amount will be refunded to merchant wallet.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tab Selection */}
      <div className="flex gap-2">
        <Button
          variant={activeTab === 'payin' ? 'default' : 'outline'}
          onClick={() => {
            setActiveTab('payin');
            setTransactions([]);
            setSelectedTxns([]);
          }}
        >
          Payin Reconciliation
        </Button>
        <Button
          variant={activeTab === 'payout' ? 'default' : 'outline'}
          onClick={() => {
            setActiveTab('payout');
            setTransactions([]);
            setSelectedTxns([]);
          }}
        >
          Payout Reconciliation
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Search Criteria</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-3">
              <label className="block text-sm font-medium mb-2">Select Merchant</label>
              <select
                className="w-full border rounded-md p-2"
                value={selectedMerchant}
                onChange={(e) => setSelectedMerchant(e.target.value)}
              >
                <option value="">-- Select Merchant --</option>
                {merchants.map((merchant) => (
                  <option key={merchant.merchant_id} value={merchant.merchant_id}>
                    {merchant.full_name} ({merchant.merchant_id}) - {merchant.mobile}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">From Date</label>
              <Input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">To Date</label>
              <Input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="w-full"
              />
            </div>
            
            <div className="md:col-span-1 flex items-end">
              <Button 
                onClick={fetchTransactions} 
                disabled={loading || !selectedMerchant || !fromDate || !toDate}
                className="w-full"
              >
                <Search className="w-4 h-4 mr-2" />
                {loading ? 'Searching...' : 'Search Transactions'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {transactions.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>
                {activeTab === 'payin' ? 'Initiated Payins' : 'Queued/Initiated Payouts'} ({transactions.length})
              </CardTitle>
              <div className="flex gap-2">
                <span className="text-sm text-gray-500">
                  Selected: {selectedTxns.length}
                </span>
                <Button
                  variant="destructive"
                  onClick={processFailedTransactions}
                  disabled={processing || selectedTxns.length === 0}
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  {processing ? 'Processing...' : `Mark ${selectedTxns.length} as Failed`}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox
                        checked={selectedTxns.length === transactions.length && transactions.length > 0}
                        onCheckedChange={handleSelectAll}
                      />
                    </TableHead>
                    <TableHead>Transaction ID</TableHead>
                    <TableHead>{activeTab === 'payin' ? 'Order ID' : 'Reference ID'}</TableHead>
                    {activeTab === 'payout' && <TableHead>Beneficiary</TableHead>}
                    {activeTab === 'payout' && <TableHead>Account</TableHead>}
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Service</TableHead>
                    <TableHead>Callback URL</TableHead>
                    <TableHead>Created At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((txn) => (
                    <TableRow key={txn.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedTxns.includes(txn.txn_id)}
                          onCheckedChange={(checked) => handleSelectTxn(txn.txn_id, checked)}
                        />
                      </TableCell>
                      <TableCell className="font-mono text-sm">{txn.txn_id}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {activeTab === 'payin' ? txn.order_id : txn.reference_id}
                      </TableCell>
                      {activeTab === 'payout' && (
                        <TableCell>{txn.bene_name}</TableCell>
                      )}
                      {activeTab === 'payout' && (
                        <TableCell className="font-mono text-xs">
                          {txn.account_no}
                          <div className="text-gray-500">{txn.ifsc_code}</div>
                        </TableCell>
                      )}
                      <TableCell className="font-semibold">{formatAmount(txn.amount)}</TableCell>
                      <TableCell>{getStatusBadge(txn.status)}</TableCell>
                      <TableCell>{formatPGPartnerName(txn.pg_partner)}</TableCell>
                      <TableCell>
                        {txn.callback_url ? (
                          <div className="flex items-center gap-1">
                            <CheckCircle className="w-4 h-4 text-green-500" />
                            <span className="text-xs text-gray-600 truncate max-w-[200px]" title={txn.callback_url}>
                              {txn.callback_url}
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1">
                            <XCircle className="w-4 h-4 text-red-500" />
                            <span className="text-xs text-gray-500">No callback</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">{formatDate(txn.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {!loading && transactions.length === 0 && selectedMerchant && fromDate && toDate && (
        <Card>
          <CardContent className="py-12 text-center text-gray-500">
            No {activeTab === 'payin' ? 'initiated payins' : 'queued/initiated payouts'} found for the selected criteria
          </CardContent>
        </Card>
      )}
        </>
      )}
    </div>
  );
}
