import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { RefreshCw, TrendingUp, DollarSign, CheckCircle, Activity } from 'lucide-react';

export default function ApiLedger() {
  const navigate = useNavigate();
  const [serviceType, setServiceType] = useState('PAYIN');
  const [apis, setApis] = useState([]);
  const [selectedApi, setSelectedApi] = useState('');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [merchantStats, setMerchantStats] = useState([]);
  const [period, setPeriod] = useState('today');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [showMerchantWise, setShowMerchantWise] = useState(false);

  useEffect(() => {
    fetchApis();
  }, [serviceType]);

  useEffect(() => {
    if (selectedApi) {
      fetchStats();
    }
  }, [selectedApi, period, fromDate, toDate]);

  const fetchApis = async () => {
    try {
      setLoading(true);
      
      if (!adminAPI.isAuthenticated()) {
        toast.error('Please login to continue');
        navigate('/login', { replace: true });
        return;
      }

      const response = await adminAPI.getApiLedgerApis(serviceType);
      
      if (response.success) {
        setApis(response.apis || []);
        if (response.apis && response.apis.length > 0) {
          setSelectedApi(response.apis[0].id);
        }
      } else {
        toast.error(response.message || 'Failed to load APIs');
      }
    } catch (error) {
      console.error('Fetch APIs error:', error);
      
      if (error.message && (error.message.includes('token') || error.message.includes('401') || error.message.includes('Session expired'))) {
        toast.error('Session expired. Please login again.');
        navigate('/login', { replace: true });
      } else {
        toast.error(error.message || 'Failed to load APIs');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      setLoading(true);
      
      if (!adminAPI.isAuthenticated()) {
        toast.error('Please login to continue');
        navigate('/login', { replace: true });
        return;
      }

      const response = await adminAPI.getApiLedgerStats(
        selectedApi,
        serviceType,
        period,
        fromDate,
        toDate
      );
      
      if (response.success) {
        setStats(response.stats);
      } else {
        toast.error(response.message || 'Failed to load statistics');
      }
    } catch (error) {
      console.error('Fetch stats error:', error);
      
      if (error.message && (error.message.includes('token') || error.message.includes('401') || error.message.includes('Session expired'))) {
        toast.error('Session expired. Please login again.');
        navigate('/login', { replace: true });
      } else {
        toast.error(error.message || 'Failed to load statistics');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchMerchantWiseStats = async () => {
    try {
      setLoading(true);
      
      if (!adminAPI.isAuthenticated()) {
        toast.error('Please login to continue');
        navigate('/login', { replace: true });
        return;
      }

      const response = await adminAPI.getApiLedgerMerchantWise(
        selectedApi,
        serviceType,
        period,
        fromDate,
        toDate
      );
      
      if (response.success) {
        setMerchantStats(response.merchant_stats || []);
        setShowMerchantWise(true);
      } else {
        toast.error(response.message || 'Failed to load merchant-wise statistics');
      }
    } catch (error) {
      console.error('Fetch merchant-wise stats error:', error);
      
      if (error.message && (error.message.includes('token') || error.message.includes('401') || error.message.includes('Session expired'))) {
        toast.error('Session expired. Please login again.');
        navigate('/login', { replace: true });
      } else {
        toast.error(error.message || 'Failed to load merchant-wise statistics');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  const handlePeriodChange = (newPeriod) => {
    setPeriod(newPeriod);
    if (newPeriod !== 'custom') {
      setFromDate('');
      setToDate('');
    }
  };

  const handleRefresh = () => {
    fetchStats();
    if (showMerchantWise) {
      fetchMerchantWiseStats();
    }
  };

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading API Ledger...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">API Ledger</h1>
          <p className="text-gray-500 mt-1">
            View transaction statistics for each payment gateway API
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Service Type and API Selection */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Service Type</label>
              <select
                className="w-full border rounded-md p-2"
                value={serviceType}
                onChange={(e) => {
                  setServiceType(e.target.value);
                  setSelectedApi('');
                  setStats(null);
                  setShowMerchantWise(false);
                }}
              >
                <option value="PAYIN">PayIn</option>
                <option value="PAYOUT">Payout</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Select API</label>
              <select
                className="w-full border rounded-md p-2"
                value={selectedApi}
                onChange={(e) => {
                  setSelectedApi(e.target.value);
                  setShowMerchantWise(false);
                }}
                disabled={apis.length === 0}
              >
                {apis.length === 0 ? (
                  <option value="">No APIs configured</option>
                ) : (
                  apis.map((api) => (
                    <option key={api.id} value={api.id}>
                      {api.name}
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Period Filter */}
      {selectedApi && (
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Period</label>
                <select
                  className="w-full border rounded-md p-2"
                  value={period}
                  onChange={(e) => handlePeriodChange(e.target.value)}
                >
                  <option value="today">Today</option>
                  <option value="yesterday">Yesterday</option>
                  <option value="last_7_days">Last 7 Days</option>
                  <option value="last_30_days">Last 30 Days</option>
                  <option value="custom">Custom Range</option>
                </select>
              </div>
              {period === 'custom' && (
                <>
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
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Transactions</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_transactions}</div>
              <p className="text-xs text-muted-foreground mt-1">
                All transactions
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Count</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{stats.success_count}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {stats.total_transactions > 0 
                  ? `${((stats.success_count / stats.total_transactions) * 100).toFixed(1)}% success rate`
                  : 'No transactions'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Amount</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatAmount(stats.total_amount)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Net Amount {serviceType === 'PAYIN' ? '(after deducting charges)' : '(after adding charges)'}
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{formatAmount(stats.total_net_amount)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Merchant-Wise Button */}
      {stats && (
        <div className="flex justify-center">
          <Button 
            onClick={fetchMerchantWiseStats}
            disabled={loading}
            className="w-full md:w-auto"
          >
            {showMerchantWise ? 'Refresh' : 'View'} Merchant-Wise Statistics
          </Button>
        </div>
      )}

      {/* Merchant-Wise Statistics Table */}
      {showMerchantWise && (
        <Card>
          <CardHeader>
            <CardTitle>Merchant-Wise Statistics for {apis.find(a => a.id === selectedApi)?.name || selectedApi}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Merchant ID</TableHead>
                    <TableHead>Merchant Name</TableHead>
                    <TableHead>Total Transactions</TableHead>
                    <TableHead>Success Count</TableHead>
                    <TableHead>Success Rate</TableHead>
                    <TableHead>Total Amount</TableHead>
                    <TableHead>Net Amount {serviceType === 'PAYIN' ? '(after deducting charges)' : '(after adding charges)'}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {merchantStats.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                        No merchant transactions found
                      </TableCell>
                    </TableRow>
                  ) : (
                    merchantStats.map((merchant) => (
                      <TableRow key={merchant.merchant_id}>
                        <TableCell className="font-mono text-sm">{merchant.merchant_id}</TableCell>
                        <TableCell className="font-medium">{merchant.merchant_name}</TableCell>
                        <TableCell>{merchant.total_transactions}</TableCell>
                        <TableCell className="text-green-600 font-semibold">{merchant.success_count}</TableCell>
                        <TableCell>
                          <Badge className={
                            merchant.total_transactions > 0 && (merchant.success_count / merchant.total_transactions) >= 0.8
                              ? 'bg-green-500'
                              : merchant.total_transactions > 0 && (merchant.success_count / merchant.total_transactions) >= 0.5
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }>
                            {merchant.total_transactions > 0 
                              ? `${((merchant.success_count / merchant.total_transactions) * 100).toFixed(1)}%`
                              : '0%'}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-semibold">{formatAmount(merchant.total_amount)}</TableCell>
                        <TableCell className="font-semibold text-blue-600">{formatAmount(merchant.total_net_amount)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
