import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { toast } from 'sonner';
import adminAPI from '../../api/admin_api';
import ApiResponseDialog from '../../components/ApiResponseDialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import { Download, RefreshCw, Eye, Code } from 'lucide-react';


// Helper function to format PG Partner names for display
const formatPGPartnerName = (pgPartner) => {
  if (!pgPartner) return 'PayU';
  
  const nameMap = {
    'Paytouch2': 'PT2',
    'Paytouch3_Trendora': 'PT3',
    'PAYTOUCH2': 'PT2',
    'PAYTOUCH3_TRENDORA': 'PT3'
  };
  
  return nameMap[pgPartner] || pgPartner;
};

export default function PayoutReport() {
  const navigate = useNavigate();
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [selectedPayout, setSelectedPayout] = useState(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [syncingStatus, setSyncingStatus] = useState({});
  const [showApiResponseDialog, setShowApiResponseDialog] = useState(false);
  const [apiResponseLogs, setApiResponseLogs] = useState(null);
  const [loadingApiResponse, setLoadingApiResponse] = useState(false);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 50,
    total: 0,
    pages: 0
  });

  useEffect(() => {
    fetchPayouts();
  }, [pagination.page]);

  // Separate effect for filters with debounce
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      fetchPayouts();
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [statusFilter, searchTerm, fromDate, toDate]);

  const fetchPayouts = async () => {
    try {
      setLoading(true);
      
      // Check authentication first
      if (!adminAPI.isAuthenticated()) {
        toast.error('Please login to continue');
        navigate('/login', { replace: true });
        return;
      }

      const params = {
        page: pagination.page,
        limit: pagination.limit
      };
      if (statusFilter) {
        params.status = statusFilter;
      }
      if (searchTerm) {
        params.search = searchTerm;
      }
      if (fromDate) {
        params.from_date = fromDate;
      }
      if (toDate) {
        params.to_date = toDate;
      }

      const response = await adminAPI.getPayoutReport(params);
      
      if (response.success) {
        setPayouts(response.data || []);
        setPagination(prev => ({
          ...prev,
          ...(response.pagination || {})
        }));
      } else {
        toast.error(response.message || 'Failed to load payouts');
      }
    } catch (error) {
      console.error('Fetch payouts error:', error);
      
      // Check if it's an authentication error
      if (error.message && (error.message.includes('token') || error.message.includes('401') || error.message.includes('Session expired'))) {
        toast.error('Session expired. Please login again.');
        navigate('/login', { replace: true });
      } else {
        toast.error(error.message || 'Failed to load payouts');
      }
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      SUCCESS: { color: 'bg-green-500', text: 'Success' },
      FAILED: { color: 'bg-red-500', text: 'Failed' },
      INITIATED: { color: 'bg-blue-500', text: 'Initiated' },
      QUEUED: { color: 'bg-yellow-500', text: 'Queued' },
      INPROCESS: { color: 'bg-orange-500', text: 'In Process' },
      REVERSED: { color: 'bg-purple-500', text: 'Reversed' }
    };

    const config = statusConfig[status] || { color: 'bg-gray-500', text: status };
    
    return (
      <Badge className={config.color}>
        {config.text}
      </Badge>
    );
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

  // No client-side filtering - backend handles everything
  const filteredPayouts = payouts;

  const handleClearFilters = () => {
    setSearchTerm('');
    setStatusFilter('');
    setFromDate('');
    setToDate('');
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const exportToCSV = () => {
    const headers = ['Transaction ID', 'Reference ID', 'Order ID', 'Merchant/Admin', 'Beneficiary', 'Bank', 'IFSC', 'Account No', 'Amount', 'Charges', 'Net Amount', 'Status', 'UTR', 'Date', 'Time'];
    const rows = filteredPayouts.map(payout => {
      // Split date and time
      let date = '';
      let time = '';
      if (payout.created_at) {
        const dt = new Date(payout.created_at);
        date = dt.toLocaleDateString('en-IN');
        time = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      }
      
      return [
        payout.txn_id,
        payout.reference_id,
        payout.order_id || '-',
        payout.payer_name || payout.full_name || 'Admin Payout',
        payout.bene_name,
        payout.bene_bank || '-',
        payout.ifsc_code || '-',
        payout.account_no || payout.vpa || '-',
        payout.net_amount,
        payout.charge_amount,
        payout.amount,
        payout.status,
        payout.utr || payout.bank_ref_no || '-',
        date,
        time
      ];
    });

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `payout-report-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('Report exported successfully');
  };

  const exportTodayReport = async () => {
    try {
      toast.info('Fetching today\'s payouts...');
      
      // Fetch ALL today's payouts from backend
      const response = await adminAPI.getTodayPayoutReport();
      
      if (!response.success || !response.data) {
        toast.error('Failed to fetch today\'s payouts');
        return;
      }

      const todayPayouts = response.data;

      if (todayPayouts.length === 0) {
        toast.error('No payouts found for today');
        return;
      }

      const headers = ['Transaction ID', 'Reference ID', 'Order ID', 'Merchant/Admin', 'Beneficiary', 'Bank', 'IFSC', 'Account No', 'Amount', 'Charges', 'Net Amount', 'Status', 'UTR', 'Date', 'Time'];
      const rows = todayPayouts.map(payout => {
        // Split date and time
        let date = '';
        let time = '';
        if (payout.created_at) {
          const dt = new Date(payout.created_at);
          date = dt.toLocaleDateString('en-IN');
          time = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
        
        return [
          payout.txn_id,
          payout.reference_id,
          payout.order_id || '-',
          payout.payer_name || payout.full_name || 'Admin Payout',
          payout.bene_name,
          payout.bene_bank || '-',
          payout.ifsc_code || '-',
          payout.account_no || payout.vpa || '-',
          payout.net_amount,
          payout.charge_amount,
          payout.amount,
          payout.status,
          payout.utr || payout.bank_ref_no || '-',
          date,
          time
        ];
      });

      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const today = new Date().toISOString().split('T')[0];
      a.download = `payout-report-today-${today}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success(`Today's report exported (${todayPayouts.length} payouts)`);
    } catch (error) {
      console.error('Export today report error:', error);
      toast.error('Failed to export today\'s report');
    }
  };

  const exportFilteredReport = async () => {
    try {
      // Check if any filters are applied
      const hasFilters = statusFilter || searchTerm || fromDate || toDate;
      
      if (!hasFilters) {
        toast.info('No filters applied. Use "Export All" to download all payouts.');
        return;
      }

      toast.info('Downloading filtered payouts...');
      
      // Build query params with current filters
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);
      if (searchTerm) params.append('search', searchTerm);
      if (fromDate) params.append('from_date', fromDate);
      if (toDate) params.append('to_date', toDate);
      
      // Use CSV streaming endpoint
      const response = await adminAPI.downloadPayoutReportCSV(params.toString());
      
      if (!response.success) {
        toast.error(response.message || 'Failed to download filtered payouts');
        return;
      }

      toast.success('Filtered report downloaded successfully');
    } catch (error) {
      console.error('Export filtered report error:', error);
      toast.error('Failed to export filtered report');
    }
  };

  const handleViewDetails = (payout) => {
    setSelectedPayout(payout);
    setShowDetailsDialog(true);
  };

  const handleCheckStatus = async (txnId) => {
    try {
      setSyncingStatus(prev => ({ ...prev, [txnId]: true }));
      
      const response = await adminAPI.syncPayoutStatus(txnId);
      
      if (response.success) {
        toast.success('Status updated successfully');
        // Update the payout in the list
        setPayouts(prevPayouts => 
          prevPayouts.map(p => 
            p.txn_id === txnId ? response.data : p
          )
        );
      } else {
        toast.error(response.message || 'Failed to check status');
      }
    } catch (error) {
      console.error('Check status error:', error);
      toast.error(error.message || 'Failed to check status');
    } finally {
      setSyncingStatus(prev => ({ ...prev, [txnId]: false }));
    }
  };

  const handleViewApiResponse = async (payout) => {
    try {
      setLoadingApiResponse(true);
      
      const response = await adminAPI.getPayoutTransactionLogs(payout.txn_id);
      
      if (response.success) {
        setApiResponseLogs(response.logs);
        setShowApiResponseDialog(true);
      } else {
        toast.error(response.message || 'Failed to load API response');
      }
    } catch (error) {
      console.error('Load API response error:', error);
      toast.error(error.message || 'Failed to load API response');
    } finally {
      setLoadingApiResponse(false);
    }
  };

  if (loading && payouts.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading payouts...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Payout Report</h1>
          <p className="text-gray-500 mt-1">
            View all payout transactions for admin and merchants
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchPayouts}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" onClick={exportTodayReport} disabled={payouts.length === 0} className="bg-green-50 hover:bg-green-100 border-green-200">
            <Download className="w-4 h-4 mr-2" />
            Today's Report
          </Button>
          <Button 
            variant="outline" 
            onClick={exportFilteredReport}
            disabled={!statusFilter && !searchTerm && !fromDate && !toDate}
            className="bg-blue-50 hover:bg-blue-100 border-blue-200 disabled:opacity-50"
          >
            <Download className="w-4 h-4 mr-2" />
            Download Filtered
          </Button>
          <Button onClick={exportToCSV} disabled={payouts.length === 0}>
            <Download className="w-4 h-4 mr-2" />
            Export All
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <Input
                placeholder="Search by TXN ID, Reference ID, Merchant, Beneficiary..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setPagination(prev => ({ ...prev, page: 1 }));
                }}
                className="w-full"
              />
            </div>
            <div>
              <select
                className="w-full border rounded-md p-2"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPagination(prev => ({ ...prev, page: 1 }));
                }}
              >
                <option value="">All Status</option>
                <option value="SUCCESS">Success</option>
                <option value="FAILED">Failed</option>
                <option value="INITIATED">Initiated</option>
                <option value="QUEUED">Queued</option>
                <option value="INPROCESS">In Process</option>
                <option value="REVERSED">Reversed</option>
              </select>
            </div>
            <div>
              <Input
                type="date"
                placeholder="From Date"
                value={fromDate}
                onChange={(e) => {
                  setFromDate(e.target.value);
                  setPagination(prev => ({ ...prev, page: 1 }));
                }}
                className="w-full"
              />
            </div>
            <div>
              <Input
                type="date"
                placeholder="To Date"
                value={toDate}
                onChange={(e) => {
                  setToDate(e.target.value);
                  setPagination(prev => ({ ...prev, page: 1 }));
                }}
                className="w-full"
              />
            </div>
            <div>
              <Button
                variant="outline"
                onClick={handleClearFilters}
                className="w-full"
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Payouts Table */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Payout Transactions ({pagination.total})</CardTitle>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Show:</span>
              <select
                className="border rounded-md p-1 text-sm"
                value={pagination.limit}
                onChange={(e) => {
                  setPagination(prev => ({ 
                    ...prev, 
                    limit: Number(e.target.value),
                    page: 1 
                  }));
                }}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span className="text-sm text-gray-500">per page</span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Transaction ID</TableHead>
                  <TableHead>Reference ID</TableHead>
                  <TableHead>Order ID</TableHead>
                  <TableHead>Merchant/Admin</TableHead>
                  <TableHead>Beneficiary</TableHead>
                  <TableHead>Bank</TableHead>
                  <TableHead>Account No</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Charges</TableHead>
                  <TableHead>Net Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Payment Type</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-center">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payouts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={14} className="text-center py-8 text-gray-500">
                      No payout transactions found
                    </TableCell>
                  </TableRow>
                ) : (
                  payouts.map((payout) => (
                    <TableRow key={payout.id}>
                      <TableCell className="font-mono text-sm">{payout.txn_id}</TableCell>
                      <TableCell className="font-mono text-sm">{payout.reference_id}</TableCell>
                      <TableCell className="font-mono text-sm">{payout.order_id || '-'}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{payout.payer_name || payout.full_name || 'Admin Payout'}</div>
                          <div className="text-xs text-gray-500">{payout.merchant_id || payout.admin_id || 'N/A'}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="text-sm">{payout.bene_name}</div>
                          <div className="text-xs text-gray-500">{payout.bene_mobile || '-'}</div>
                        </div>
                      </TableCell>
                      <TableCell>{payout.bene_bank || '-'}</TableCell>
                      <TableCell className="font-mono text-sm">{payout.account_no || payout.vpa || '-'}</TableCell>
                      <TableCell className="font-semibold">{formatAmount(payout.net_amount)}</TableCell>
                      <TableCell className="text-red-600">
                        -{formatAmount(payout.charge_amount)}
                        <div className="text-xs text-gray-500">{payout.charge_type}</div>
                      </TableCell>
                      <TableCell className="font-semibold text-green-600">
                        {formatAmount(payout.amount)}
                      </TableCell>
                      <TableCell>{getStatusBadge(payout.status)}</TableCell>
                      <TableCell>{payout.payment_type || 'IMPS'}</TableCell>
                      <TableCell className="text-sm">{formatDate(payout.created_at)}</TableCell>
                      <TableCell className="text-center">
                        <div className="flex gap-1 justify-center">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleViewDetails(payout)}
                            className="text-xs h-7"
                          >
                            <Eye className="h-3 w-3 mr-1" />
                            View
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleViewApiResponse(payout)}
                            disabled={loadingApiResponse}
                            className="text-xs h-7 bg-purple-50 hover:bg-purple-100 border-purple-200"
                            title="View API Response"
                          >
                            <Code className="h-3 w-3 mr-1" />
                            API
                          </Button>
                          {payout.status === 'INITIATED' && payout.pg_partner === 'Mudrape' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleCheckStatus(payout.txn_id)}
                              disabled={syncingStatus[payout.txn_id]}
                              className="text-xs h-7"
                            >
                              <RefreshCw className={`h-3 w-3 mr-1 ${syncingStatus[payout.txn_id] ? 'animate-spin' : ''}`} />
                              {syncingStatus[payout.txn_id] ? 'Checking...' : 'Check'}
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

          {/* Pagination Controls */}
          {pagination.pages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <div className="text-sm text-gray-500">
                Page {pagination.page} of {pagination.pages} (Total: {pagination.total} entries)
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPagination(prev => ({ ...prev, page: 1 }))}
                  disabled={pagination.page === 1}
                >
                  First
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                  disabled={pagination.page === 1}
                >
                  Previous
                </Button>
                <span className="text-sm">Page {pagination.page}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                  disabled={pagination.page === pagination.pages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payout Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Payout Transaction Details</DialogTitle>
          </DialogHeader>
          {selectedPayout && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Transaction ID</p>
                  <p className="font-mono text-sm font-medium">{selectedPayout.txn_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Reference ID</p>
                  <p className="font-mono text-sm font-medium">{selectedPayout.reference_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Order ID</p>
                  <p className="font-mono text-sm font-medium">{selectedPayout.order_id || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Merchant/Admin</p>
                  <p className="font-medium">{selectedPayout.payer_name || selectedPayout.full_name || 'Admin Payout'}</p>
                  <p className="text-xs text-gray-500">{selectedPayout.merchant_id || selectedPayout.admin_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <div className="mt-1">{getStatusBadge(selectedPayout.status)}</div>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Amount</p>
                  <p className="font-semibold">{formatAmount(selectedPayout.amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Charge Amount</p>
                  <p className="font-semibold text-red-600">-{formatAmount(selectedPayout.charge_amount)}</p>
                  <p className="text-xs text-gray-500">{selectedPayout.charge_type}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Net Amount</p>
                  <p className="font-semibold text-green-600">{formatAmount(selectedPayout.net_amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Payment Type</p>
                  <p className="font-medium">{selectedPayout.payment_type || 'IMPS'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Beneficiary Name</p>
                  <p className="font-medium">{selectedPayout.bene_name || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Beneficiary Mobile</p>
                  <p className="font-medium">{selectedPayout.bene_mobile || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Beneficiary Email</p>
                  <p className="font-medium">{selectedPayout.bene_email || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Bank Name</p>
                  <p className="font-medium">{selectedPayout.bene_bank || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">IFSC Code</p>
                  <p className="font-mono text-sm">{selectedPayout.ifsc_code || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Account Number</p>
                  <p className="font-mono text-sm">{selectedPayout.account_no || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">VPA/UPI ID</p>
                  <p className="font-mono text-sm">{selectedPayout.vpa || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">PG Partner</p>
                  <p className="font-medium">{formatPGPartnerName(selectedPayout.pg_partner)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">PG Transaction ID</p>
                  <p className="font-mono text-xs">{selectedPayout.pg_txn_id || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">UTR Number</p>
                  <p className="font-mono text-xs">{selectedPayout.utr || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Bank Reference</p>
                  <p className="font-mono text-xs">{selectedPayout.bank_ref_no || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Name with Bank</p>
                  <p className="text-sm">{selectedPayout.name_with_bank || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Name Match Score</p>
                  <p className="text-sm">{selectedPayout.name_match_score || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created At</p>
                  <p className="text-sm">{formatDate(selectedPayout.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Completed At</p>
                  <p className="text-sm">{formatDate(selectedPayout.completed_at)}</p>
                </div>
                {selectedPayout.purpose && (
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">Purpose</p>
                    <p className="text-sm">{selectedPayout.purpose}</p>
                  </div>
                )}
                {selectedPayout.remarks && (
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">Remarks</p>
                    <p className="text-sm">{selectedPayout.remarks}</p>
                  </div>
                )}
                {selectedPayout.error_message && (
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">Error Message</p>
                    <p className="text-sm text-red-600">{selectedPayout.error_message}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* API Response Dialog */}
      <ApiResponseDialog
        open={showApiResponseDialog}
        onOpenChange={setShowApiResponseDialog}
        logs={apiResponseLogs}
        type="payout"
      />
    </div>
  );
}
