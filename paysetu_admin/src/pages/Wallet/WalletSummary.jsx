import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { toast } from 'sonner';
import adminAPI from '../../api/admin_api';
import { Wallet, TrendingUp, TrendingDown, DollarSign, Calendar, RefreshCw } from 'lucide-react';

export default function WalletSummary() {
  const navigate = useNavigate();
  const [merchants, setMerchants] = useState([]);
  const [selectedMerchant, setSelectedMerchant] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

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

      const response = await adminAPI.getUsers();
      if (response.success) {
        setMerchants(response.users || []);
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

  const fetchMerchantSummary = async (merchantId) => {
    try {
      setLoading(true);
      
      if (!adminAPI.isAuthenticated()) {
        toast.error('Please login to continue');
        navigate('/login', { replace: true });
        return;
      }

      const params = { merchant_id: merchantId };
      if (fromDate) params.from_date = fromDate;
      if (toDate) params.to_date = toDate;

      const response = await adminAPI.getMerchantWalletSummary(params);
      
      if (response.success) {
        setSummary(response.data);
      } else {
        toast.error(response.message || 'Failed to load summary');
      }
    } catch (error) {
      console.error('Fetch summary error:', error);
      if (error.message && (error.message.includes('token') || error.message.includes('401'))) {
        toast.error('Session expired. Please login again.');
        navigate('/login', { replace: true });
      } else {
        toast.error(error.message || 'Failed to load summary');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleMerchantSelect = (merchant) => {
    setSelectedMerchant(merchant);
    fetchMerchantSummary(merchant.merchant_id);
  };

  const handleRefresh = () => {
    if (selectedMerchant) {
      fetchMerchantSummary(selectedMerchant.merchant_id);
    }
  };

  const handleClearFilters = () => {
    setFromDate('');
    setToDate('');
    if (selectedMerchant) {
      fetchMerchantSummary(selectedMerchant.merchant_id);
    }
  };

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount || 0);
  };

  const filteredMerchants = merchants.filter(merchant =>
    merchant.merchant_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    merchant.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    merchant.mobile?.includes(searchTerm)
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Wallet Summary</h1>
          <p className="text-sm text-gray-600 mt-1">View merchant wallet summary with payin and payout details</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Merchant Selection Panel */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="h-5 w-5" />
              Select Merchant
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Input
                placeholder="Search merchant..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full"
              />
              
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {filteredMerchants.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-4">No merchants found</p>
                ) : (
                  filteredMerchants.map((merchant) => (
                    <div
                      key={merchant.merchant_id}
                      onClick={() => handleMerchantSelect(merchant)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedMerchant?.merchant_id === merchant.merchant_id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="font-medium text-sm">{merchant.full_name}</div>
                      <div className="text-xs text-gray-600">{merchant.merchant_id}</div>
                      <div className="text-xs text-gray-500">{merchant.mobile}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Summary Details Panel */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Merchant Summary
              </CardTitle>
              {selectedMerchant && (
                <Button
                  onClick={handleRefresh}
                  disabled={loading}
                  size="sm"
                  variant="outline"
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedMerchant ? (
              <div className="text-center py-12">
                <Wallet className="h-16 w-16 mx-auto text-gray-300 mb-4" />
                <p className="text-gray-500">Select a merchant to view summary</p>
              </div>
            ) : loading ? (
              <div className="text-center py-12">
                <RefreshCw className="h-8 w-8 mx-auto text-blue-500 animate-spin mb-4" />
                <p className="text-gray-500">Loading summary...</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Merchant Info */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-lg border border-blue-200">
                  <h3 className="font-semibold text-lg mb-2">{selectedMerchant.full_name}</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-600">Merchant ID:</span>
                      <span className="ml-2 font-medium">{selectedMerchant.merchant_id}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Mobile:</span>
                      <span className="ml-2 font-medium">{selectedMerchant.mobile}</span>
                    </div>
                  </div>
                </div>

                {/* Date Filters */}
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                  <Calendar className="h-5 w-5 text-gray-600" />
                  <div className="flex-1 grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-gray-600 mb-1 block">From Date</label>
                      <Input
                        type="date"
                        value={fromDate}
                        onChange={(e) => setFromDate(e.target.value)}
                        className="w-full"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-600 mb-1 block">To Date</label>
                      <Input
                        type="date"
                        value={toDate}
                        onChange={(e) => setToDate(e.target.value)}
                        className="w-full"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={() => fetchMerchantSummary(selectedMerchant.merchant_id)} size="sm">
                      Apply
                    </Button>
                    <Button onClick={handleClearFilters} size="sm" variant="outline">
                      Clear
                    </Button>
                  </div>
                </div>

                {summary && (
                  <>
                    {/* Wallet Balances */}
                    <div className="grid grid-cols-2 gap-4">
                      <Card className="border-2 border-green-200 bg-gradient-to-br from-green-50 to-white">
                        <CardContent className="pt-6">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-gray-600">Settled Balance</p>
                              <p className="text-2xl font-bold text-green-600">
                                {formatAmount(summary.settled_balance)}
                              </p>
                            </div>
                            <Wallet className="h-10 w-10 text-green-500 opacity-50" />
                          </div>
                        </CardContent>
                      </Card>

                      <Card className="border-2 border-yellow-200 bg-gradient-to-br from-yellow-50 to-white">
                        <CardContent className="pt-6">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-gray-600">Unsettled Balance</p>
                              <p className="text-2xl font-bold text-yellow-600">
                                {formatAmount(summary.unsettled_balance)}
                              </p>
                            </div>
                            <Wallet className="h-10 w-10 text-yellow-500 opacity-50" />
                          </div>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Payin Summary */}
                    <div>
                      <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-green-600" />
                        Payin Summary
                      </h3>
                      <div className="grid grid-cols-2 gap-4">
                        <Card className="border border-green-200">
                          <CardContent className="pt-6">
                            <p className="text-sm text-gray-600 mb-1">Before Deducting Charges</p>
                            <p className="text-xl font-bold text-green-600">
                              {formatAmount(summary.payin_before_charges)}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              Charges: {formatAmount(summary.payin_total_charges)}
                            </p>
                          </CardContent>
                        </Card>

                        <Card className="border border-green-200">
                          <CardContent className="pt-6">
                            <p className="text-sm text-gray-600 mb-1">After Deducting Charges</p>
                            <p className="text-xl font-bold text-green-600">
                              {formatAmount(summary.payin_after_charges)}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              Count: {summary.payin_count || 0} transactions
                            </p>
                          </CardContent>
                        </Card>
                      </div>
                    </div>

                    {/* Payout Summary */}
                    <div>
                      <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                        <TrendingDown className="h-5 w-5 text-red-600" />
                        Payout Summary
                      </h3>
                      <div className="grid grid-cols-2 gap-4">
                        <Card className="border border-red-200">
                          <CardContent className="pt-6">
                            <p className="text-sm text-gray-600 mb-1">Before Adding Charges</p>
                            <p className="text-xl font-bold text-red-600">
                              {formatAmount(summary.payout_before_charges)}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              Count: {summary.payout_count || 0} transactions
                            </p>
                          </CardContent>
                        </Card>

                        <Card className="border border-red-200">
                          <CardContent className="pt-6">
                            <p className="text-sm text-gray-600 mb-1">After Adding Charges</p>
                            <p className="text-xl font-bold text-red-600">
                              {formatAmount(summary.payout_after_charges)}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              Charges: {formatAmount(summary.payout_total_charges)}
                            </p>
                          </CardContent>
                        </Card>
                      </div>
                    </div>

                    {/* Net Summary */}
                    <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-white">
                      <CardContent className="pt-6">
                        <h3 className="font-semibold text-lg mb-3">Net Summary</h3>
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <p className="text-xs text-gray-600">Net Payin</p>
                            <p className="text-lg font-bold text-green-600">
                              {formatAmount(summary.payin_after_charges)}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-600">Net Payout</p>
                            <p className="text-lg font-bold text-red-600">
                              {formatAmount(summary.payout_before_charges)}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-600">Net Balance</p>
                            <p className={`text-lg font-bold ${
                              (summary.payin_after_charges - summary.payout_before_charges) >= 0
                                ? 'text-green-600'
                                : 'text-red-600'
                            }`}>
                              {formatAmount(summary.payin_after_charges - summary.payout_before_charges)}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
