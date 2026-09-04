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
import { Download, RefreshCw, Eye, FileText, Code } from 'lucide-react';


export default function PayinReport() {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [selectedTxn, setSelectedTxn] = useState(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(false);
  const [creatingInvoice, setCreatingInvoice] = useState(null);
  const [showApiResponseDialog, setShowApiResponseDialog] = useState(false);
  const [apiResponseLogs, setApiResponseLogs] = useState(null);
  const [loadingApiResponse, setLoadingApiResponse] = useState(false);
  const [showInvoiceDialog, setShowInvoiceDialog] = useState(false);
  const [selectedInvoiceTxn, setSelectedInvoiceTxn] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 50,
    total: 0,
    pages: 0
  });

  useEffect(() => {
    fetchTransactions();
  }, [pagination.page]);

  // Separate effect for filters with debounce
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setPagination(prev => ({ ...prev, page: 1 }));
      fetchTransactions();
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [statusFilter, searchTerm, fromDate, toDate]);

  const fetchTransactions = async () => {
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

      const response = await adminAPI.getPayinTransactions(params);
      
      if (response.success) {
        setTransactions(response.transactions || []);
        setPagination(prev => ({
          ...prev,
          ...(response.pagination || {})
        }));
      } else {
        toast.error(response.message || 'Failed to load transactions');
      }
    } catch (error) {
      console.error('Fetch transactions error:', error);
      
      // Check if it's an authentication error
      if (error.message && (error.message.includes('token') || error.message.includes('401') || error.message.includes('Session expired'))) {
        toast.error('Session expired. Please login again.');
        navigate('/login', { replace: true });
      } else {
        toast.error(error.message || 'Failed to load transactions');
      }
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      SUCCESS: { color: 'bg-green-500', text: 'Success' },
      PENDING: { color: 'bg-yellow-500', text: 'Pending' },
      INITIATED: { color: 'bg-blue-500', text: 'Initiated' },
      FAILED: { color: 'bg-red-500', text: 'Failed' },
      CANCELLED: { color: 'bg-gray-500', text: 'Cancelled' }
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

  // Backend search is now used, no need for client-side filtering
  const filteredTransactions = transactions;

  const exportToCSV = () => {
    try {
      toast.info('Preparing CSV download...');
      
      // Use new CSV streaming endpoint for all transactions
      const token = localStorage.getItem('adminToken');
      const url = `${adminAPI.baseURL}/payin/admin/transactions/download-csv`;
      
      // Download using fetch with authorization
      fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(async response => {
        if (!response.ok) {
          // Check if response is JSON error
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Download failed');
          }
          throw new Error('Download failed');
        }
        
        // Check if response is actually CSV
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('text/csv')) {
          throw new Error('Invalid response format. Expected CSV but received ' + (contentType || 'unknown'));
        }
        
        // Get filename from Content-Disposition header if available
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `payin-report-all-${new Date().toISOString().split('T')[0]}.csv`;
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }
        return response.blob().then(blob => ({ blob, filename }));
      })
      .then(({ blob, filename }) => {
        // Use the blob directly - don't wrap it again
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        setTimeout(() => {
          document.body.removeChild(a);
          window.URL.revokeObjectURL(blobUrl);
        }, 100);
        
        toast.success('CSV download started!');
      })
      .catch(error => {
        console.error('Download error:', error);
        toast.error(error.message || 'Failed to download CSV');
      });
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Failed to export report');
    }
  };

  const exportTodayReport = async () => {
    try {
      toast.info('Fetching today\'s transactions...');
      
      // Fetch ALL today's transactions from backend
      const response = await adminAPI.getTodayPayinTransactions();
      
      if (!response.success || !response.transactions) {
        toast.error('Failed to fetch today\'s transactions');
        return;
      }

      const todayTransactions = response.transactions;

      if (todayTransactions.length === 0) {
        toast.error('No transactions found for today');
        return;
      }

      const headers = ['Transaction ID', 'Order ID', 'Merchant', 'Amount', 'Charge', 'Net Amount', 'UTR/Bank Ref', 'PG Transaction ID', 'Status', 'Payment Mode', 'Service', 'Date', 'Time'];
      const rows = todayTransactions.map(txn => {
        // Split date and time
        let date = '';
        let time = '';
        if (txn.created_at) {
          const dt = new Date(txn.created_at);
          date = dt.toLocaleDateString('en-IN');
          time = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
        
        return [
          txn.txn_id,
          txn.order_id,
          txn.merchant_name || txn.merchant_id,
          txn.amount,
          txn.charge_amount,
          txn.net_amount,
          txn.bank_ref_no || txn.utr || '-',
          txn.pg_txn_id || '-',
          txn.status,
          txn.payment_mode || '-',
          txn.service_name || '-',
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
      a.download = `payin-report-today-${today}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success(`Today's report exported (${todayTransactions.length} transactions)`);
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
        toast.info('No filters applied. Use "Export All" to download all transactions.');
        return;
      }

      toast.info('Preparing CSV download...');
      
      // Build query params for CSV download
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);
      if (searchTerm) params.append('search', searchTerm);
      if (fromDate) params.append('from_date', fromDate);
      if (toDate) params.append('to_date', toDate);
      
      // Use new CSV streaming endpoint
      const token = localStorage.getItem('adminToken');
      const url = `${adminAPI.baseURL}/payin/admin/transactions/download-csv?${params.toString()}`;
      
      // Download using fetch with authorization
      fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(async response => {
        if (!response.ok) {
          // Check if response is JSON error
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Download failed');
          }
          throw new Error('Download failed');
        }
        
        // Check if response is actually CSV
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('text/csv')) {
          throw new Error('Invalid response format. Expected CSV but received ' + (contentType || 'unknown'));
        }
        
        // Get filename from Content-Disposition header if available
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `payin-report-filtered-${new Date().toISOString().split('T')[0]}.csv`;
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }
        return response.blob().then(blob => ({ blob, filename }));
      })
      .then(({ blob, filename }) => {
        // Use the blob directly - don't wrap it again
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        setTimeout(() => {
          document.body.removeChild(a);
          window.URL.revokeObjectURL(blobUrl);
        }, 100);
        
        toast.success('CSV download started!');
      })
      .catch(error => {
        console.error('Download error:', error);
        toast.error(error.message || 'Failed to download CSV');
      });
      
    } catch (error) {
      console.error('Export filtered report error:', error);
      toast.error('Failed to export filtered report');
    }
  };

  const handleCheckStatus = async (txn) => {
    try {
      setCheckingStatus(true);
      
      // Check authentication
      if (!adminAPI.isAuthenticated()) {
        toast.error('Please login to continue');
        navigate('/login', { replace: true });
        return;
      }

      const response = await adminAPI.checkPayinStatus(txn.txn_id);
      
      if (response.success) {
        const updatedTxn = response.transaction;
        
        // Update local state
        setTransactions(prev => 
          prev.map(t => t.txn_id === txn.txn_id ? updatedTxn : t)
        );
        
        // Show details dialog
        setSelectedTxn(updatedTxn);
        setShowDetailsDialog(true);
        
        toast.success('Status updated');
      } else {
        toast.error(response.message || 'Failed to check status');
      }
    } catch (error) {
      console.error('Check status error:', error);
      
      // Check if it's an authentication error
      if (error.message && (error.message.includes('token') || error.message.includes('401'))) {
        toast.error('Session expired. Please login again.');
        navigate('/login', { replace: true });
      } else {
        toast.error(error.message || 'Failed to check status');
      }
    } finally {
      setCheckingStatus(false);
    }
  };

  const handleCreateInvoice = async (txn) => {
    // Show dialog to select invoice provider
    try {
      // Validate transaction status
      if (txn.status !== 'SUCCESS') {
        toast.error('Invoice can only be created for successful transactions');
        return;
      }

      // Show provider selection dialog
      setSelectedInvoiceTxn(txn);
      setShowInvoiceDialog(true);
    } catch (error) {
      console.error('Invoice creation error:', error);
      toast.error(error.message || 'Failed to create invoice');
    }
  };

  const handleInvoiceProviderSelect = async (provider) => {
    // Create invoice with selected provider
    const txn = selectedInvoiceTxn;
    
    try {
      // Close dialog
      setShowInvoiceDialog(false);
      
      // Set loading state
      setCreatingInvoice(txn.txn_id);
      
      console.log('=== Creating Invoice ===');
      console.log('Transaction ID:', txn.txn_id);
      console.log('Provider:', provider);
      console.log('Sending to backend endpoint...');
      
      // Call backend with provider parameter
      const response = await adminAPI.createInvoice(txn.txn_id, provider);
      
      console.log('Backend response:', response);
      
      if (response.success) {
        toast.success(`Invoice created successfully via ${provider}!`);
        
        // Show receipt number if available
        if (response.data?.order?.receipt_number) {
          toast.success(`Receipt: ${response.data.order.receipt_number}`, {
            duration: 5000
          });
        }
      } else {
        toast.error(response.message || 'Failed to create invoice');
      }
    } catch (error) {
      console.error('Invoice creation error:', error);
      toast.error(error.message || 'Failed to create invoice');
    } finally {
      setCreatingInvoice(null);
      setSelectedInvoiceTxn(null);
    }
  };

  const handleViewApiResponse = async (txn) => {
    try {
      setLoadingApiResponse(true);
      
      const response = await adminAPI.getPayinTransactionLogs(txn.txn_id);
      
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

  if (loading && transactions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading transactions...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Payin Report</h1>
          <p className="text-gray-500 mt-1">
            View all payin transactions across all merchants
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchTransactions}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" onClick={exportTodayReport} className="bg-green-50 hover:bg-green-100 border-green-200">
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
          <Button onClick={exportToCSV}>
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
                placeholder="Search by TXN ID, Order ID, Merchant, UTR, PG TXN ID..."
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
                <option value="PENDING">Pending</option>
                <option value="INITIATED">Initiated</option>
                <option value="FAILED">Failed</option>
                <option value="CANCELLED">Cancelled</option>
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
                onClick={() => {
                  setSearchTerm('');
                  setStatusFilter('');
                  setFromDate('');
                  setToDate('');
                  setPagination(prev => ({ ...prev, page: 1 }));
                }}
                className="w-full"
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Transactions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Transactions ({pagination.total})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Transaction ID</TableHead>
                  <TableHead>Order ID</TableHead>
                  <TableHead>Merchant</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Charge</TableHead>
                  <TableHead>Net Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Payment Mode</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-center">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTransactions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={11} className="text-center py-8 text-gray-500">
                      No transactions found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTransactions.map((txn) => (
                    <TableRow key={txn.id}>
                      <TableCell className="font-mono text-sm">{txn.txn_id}</TableCell>
                      <TableCell className="font-mono text-sm">{txn.order_id}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{txn.merchant_name}</div>
                          <div className="text-xs text-gray-500">{txn.merchant_id}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="text-sm">{txn.payee_name}</div>
                          <div className="text-xs text-gray-500">{txn.payee_mobile}</div>
                        </div>
                      </TableCell>
                      <TableCell className="font-semibold">{formatAmount(txn.amount)}</TableCell>
                      <TableCell className="text-red-600">
                        -{formatAmount(txn.charge_amount)}
                        <div className="text-xs text-gray-500">{txn.charge_type}</div>
                      </TableCell>
                      <TableCell className="font-semibold text-green-600">
                        {formatAmount(txn.net_amount)}
                      </TableCell>
                      <TableCell>{getStatusBadge(txn.status)}</TableCell>
                      <TableCell>{txn.payment_mode || '-'}</TableCell>
                      <TableCell className="text-sm">{formatDate(txn.created_at)}</TableCell>
                      <TableCell className="text-center">
                        <div className="flex gap-2 justify-center">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleCheckStatus(txn)}
                            disabled={checkingStatus}
                            className="text-xs h-7"
                          >
                            <Eye className="h-3 w-3 mr-1" />
                            Check
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleViewApiResponse(txn)}
                            disabled={loadingApiResponse}
                            className="text-xs h-7 bg-purple-50 hover:bg-purple-100 border-purple-200"
                            title="View API Response"
                          >
                            <Code className="h-3 w-3 mr-1" />
                            API
                          </Button>
                          {txn.status === 'SUCCESS' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleCreateInvoice(txn)}
                              disabled={creatingInvoice === txn.txn_id}
                              className="text-xs h-7 bg-blue-50 hover:bg-blue-100 border-blue-200"
                              title="Create Invoice"
                            >
                              <FileText className="h-3 w-3 mr-1" />
                              {creatingInvoice === txn.txn_id ? 'Creating...' : 'Invoice'}
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

          {/* Pagination */}
          {pagination.pages > 1 && (
            <div className="flex justify-between items-center mt-4">
              <div className="text-sm text-gray-500">
                Page {pagination.page} of {pagination.pages}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pagination.page === 1}
                  onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pagination.page === pagination.pages}
                  onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Transaction Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Transaction Details</DialogTitle>
          </DialogHeader>
          {selectedTxn && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Transaction ID</p>
                  <p className="font-mono text-sm font-medium">{selectedTxn.txn_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Order ID</p>
                  <p className="font-mono text-sm font-medium">{selectedTxn.order_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Merchant</p>
                  <p className="font-medium">{selectedTxn.merchant_name}</p>
                  <p className="text-xs text-gray-500">{selectedTxn.merchant_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <div className="mt-1">{getStatusBadge(selectedTxn.status)}</div>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Amount</p>
                  <p className="font-semibold">{formatAmount(selectedTxn.amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Charge Amount</p>
                  <p className="font-semibold text-red-600">-{formatAmount(selectedTxn.charge_amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Net Amount</p>
                  <p className="font-semibold text-green-600">{formatAmount(selectedTxn.net_amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Payment Mode</p>
                  <p className="font-medium">{selectedTxn.payment_mode || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Customer Name</p>
                  <p className="font-medium">{selectedTxn.payee_name || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Customer Mobile</p>
                  <p className="font-medium">{selectedTxn.payee_mobile || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Customer Email</p>
                  <p className="font-medium">{selectedTxn.payee_email || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">PG Transaction ID</p>
                  <p className="font-mono text-xs">{selectedTxn.pg_txn_id || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Bank Reference</p>
                  <p className="font-mono text-xs">{selectedTxn.bank_ref_no || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created At</p>
                  <p className="text-sm">{formatDate(selectedTxn.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Completed At</p>
                  <p className="text-sm">{formatDate(selectedTxn.completed_at)}</p>
                </div>
                {selectedTxn.remarks && (
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">Remarks</p>
                    <p className="text-sm">{selectedTxn.remarks}</p>
                  </div>
                )}
                {selectedTxn.error_message && (
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">Error Message</p>
                    <p className="text-sm text-red-600">{selectedTxn.error_message}</p>
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
        type="payin"
      />

      {/* Invoice Provider Selection Dialog */}
      <Dialog open={showInvoiceDialog} onOpenChange={setShowInvoiceDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Select Invoice Provider</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-sm text-gray-600">
              Choose the invoice provider to generate the invoice:
            </p>
            <div className="grid grid-cols-2 gap-4">
              <Button
                onClick={() => handleInvoiceProviderSelect('truaxis')}
                className="h-20 flex flex-col items-center justify-center gap-2"
                variant="outline"
              >
                <FileText className="h-6 w-6" />
                <span className="font-semibold">Truaxis</span>
              </Button>
              <Button
                onClick={() => handleInvoiceProviderSelect('grosmart')}
                className="h-20 flex flex-col items-center justify-center gap-2"
                variant="outline"
              >
                <FileText className="h-6 w-6" />
                <span className="font-semibold">Grosmart</span>
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
