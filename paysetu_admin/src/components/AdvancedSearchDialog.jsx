import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent } from './ui/card';
import { toast } from 'sonner';
import { Search, Download, Calendar, TrendingUp } from 'lucide-react';

export default function AdvancedSearchDialog({ open, onOpenChange, type, onSearch }) {
  const [searchMode, setSearchMode] = useState('single'); // 'single' or 'range'
  const [merchantId, setMerchantId] = useState('');
  const [singleDate, setSingleDate] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const handleSearch = async () => {
    // Validation
    if (!merchantId.trim()) {
      toast.error('Please enter a merchant ID');
      return;
    }

    if (searchMode === 'single' && !singleDate) {
      toast.error('Please select a date');
      return;
    }

    if (searchMode === 'range' && (!fromDate || !toDate)) {
      toast.error('Please select both from and to dates');
      return;
    }

    if (searchMode === 'range' && new Date(fromDate) > new Date(toDate)) {
      toast.error('From date cannot be after to date');
      return;
    }

    try {
      setLoading(true);
      const searchData = {
        merchant_id: merchantId.trim(),
        mode: searchMode,
        ...(searchMode === 'single' ? { date: singleDate } : { from_date: fromDate, to_date: toDate })
      };

      const result = await onSearch(searchData);
      setResults(result);
    } catch (error) {
      console.error('Advanced search error:', error);
      toast.error(error.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setMerchantId('');
    setSingleDate('');
    setFromDate('');
    setToDate('');
    setResults(null);
  };

  const handleExport = () => {
    if (!results) return;

    const headers = searchMode === 'single' 
      ? ['Merchant ID', 'Merchant Name', 'Date', 'Total Transactions', 'Total Amount', 'Total Charges', 'Net Amount']
      : ['Merchant ID', 'Merchant Name', 'Date', 'Total Transactions', 'Total Amount', 'Total Charges', 'Net Amount'];

    let rows = [];
    
    if (searchMode === 'single') {
      rows = [[
        results.merchant_id,
        results.merchant_name,
        results.date,
        results.total_transactions,
        results.total_amount,
        results.total_charges,
        results.net_amount
      ]];
    } else {
      rows = results.daily_data.map(day => [
        results.merchant_id,
        results.merchant_name,
        day.date,
        day.total_transactions,
        day.total_amount,
        day.total_charges,
        day.net_amount
      ]);
      
      // Add summary row
      rows.push([
        '',
        'TOTAL',
        `${fromDate} to ${toDate}`,
        results.summary.total_transactions,
        results.summary.total_amount,
        results.summary.total_charges,
        results.summary.net_amount
      ]);
    }

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const filename = `${type}-advanced-search-${merchantId}-${searchMode === 'single' ? singleDate : `${fromDate}_to_${toDate}`}.csv`;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('Report exported successfully');
  };

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount || 0);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Advanced Search - {type === 'payin' ? 'Payin' : 'Payout'} Report
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Search Form */}
          <Card>
            <CardContent className="pt-6 space-y-4">
              {/* Merchant ID */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Merchant ID <span className="text-red-500">*</span>
                </label>
                <Input
                  placeholder="Enter merchant ID (e.g., 9876543210)"
                  value={merchantId}
                  onChange={(e) => setMerchantId(e.target.value)}
                  className="w-full"
                />
              </div>

              {/* Search Mode */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Search Mode <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value="single"
                      checked={searchMode === 'single'}
                      onChange={(e) => setSearchMode(e.target.value)}
                      className="w-4 h-4"
                    />
                    <span>Single Day</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value="range"
                      checked={searchMode === 'range'}
                      onChange={(e) => setSearchMode(e.target.value)}
                      className="w-4 h-4"
                    />
                    <span>Date Range (Day-wise)</span>
                  </label>
                </div>
              </div>

              {/* Date Selection */}
              {searchMode === 'single' ? (
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Select Date <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="date"
                    value={singleDate}
                    onChange={(e) => setSingleDate(e.target.value)}
                    max={new Date().toISOString().split('T')[0]}
                    className="w-full"
                  />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      From Date <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="date"
                      value={fromDate}
                      onChange={(e) => setFromDate(e.target.value)}
                      max={new Date().toISOString().split('T')[0]}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      To Date <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="date"
                      value={toDate}
                      onChange={(e) => setToDate(e.target.value)}
                      max={new Date().toISOString().split('T')[0]}
                      className="w-full"
                    />
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-2 pt-2">
                <Button onClick={handleSearch} disabled={loading} className="flex-1">
                  <Search className="w-4 h-4 mr-2" />
                  {loading ? 'Searching...' : 'Search'}
                </Button>
                <Button variant="outline" onClick={handleReset} disabled={loading}>
                  Reset
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          {results && (
            <Card>
              <CardContent className="pt-6 space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    Search Results
                  </h3>
                  <Button variant="outline" size="sm" onClick={handleExport}>
                    <Download className="w-4 h-4 mr-2" />
                    Export CSV
                  </Button>
                </div>

                {/* Merchant Info */}
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Merchant ID</p>
                      <p className="font-semibold">{results.merchant_id}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Merchant Name</p>
                      <p className="font-semibold">{results.merchant_name}</p>
                    </div>
                  </div>
                </div>

                {/* Single Day Results */}
                {searchMode === 'single' && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white border rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Date</p>
                      <p className="text-lg font-semibold">{results.date}</p>
                    </div>
                    <div className="bg-white border rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Total Transactions</p>
                      <p className="text-2xl font-bold text-blue-600">{results.total_transactions}</p>
                    </div>
                    <div className="bg-white border rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Total Amount</p>
                      <p className="text-lg font-semibold text-green-600">{formatAmount(results.total_amount)}</p>
                    </div>
                    <div className="bg-white border rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Total Charges</p>
                      <p className="text-lg font-semibold text-red-600">{formatAmount(results.total_charges)}</p>
                    </div>
                    <div className="bg-white border rounded-lg p-4 col-span-2">
                      <p className="text-sm text-gray-600 mb-1">Net Amount</p>
                      <p className="text-2xl font-bold text-purple-600">{formatAmount(results.net_amount)}</p>
                    </div>
                  </div>
                )}

                {/* Date Range Results */}
                {searchMode === 'range' && (
                  <>
                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <p className="text-sm text-gray-600 mb-1">Total Transactions</p>
                        <p className="text-2xl font-bold text-blue-600">{results.summary.total_transactions}</p>
                      </div>
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <p className="text-sm text-gray-600 mb-1">Total Amount</p>
                        <p className="text-lg font-semibold text-green-600">{formatAmount(results.summary.total_amount)}</p>
                      </div>
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <p className="text-sm text-gray-600 mb-1">Total Charges</p>
                        <p className="text-lg font-semibold text-red-600">{formatAmount(results.summary.total_charges)}</p>
                      </div>
                      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                        <p className="text-sm text-gray-600 mb-1">Net Amount</p>
                        <p className="text-lg font-semibold text-purple-600">{formatAmount(results.summary.net_amount)}</p>
                      </div>
                    </div>

                    {/* Day-wise Table */}
                    <div className="border rounded-lg overflow-hidden">
                      <div className="bg-gray-50 px-4 py-2 border-b">
                        <h4 className="font-semibold flex items-center gap-2">
                          <Calendar className="w-4 h-4" />
                          Day-wise Breakdown
                        </h4>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead className="bg-gray-100">
                            <tr>
                              <th className="px-4 py-2 text-left text-sm font-semibold">Date</th>
                              <th className="px-4 py-2 text-right text-sm font-semibold">Transactions</th>
                              <th className="px-4 py-2 text-right text-sm font-semibold">Total Amount</th>
                              <th className="px-4 py-2 text-right text-sm font-semibold">Charges</th>
                              <th className="px-4 py-2 text-right text-sm font-semibold">Net Amount</th>
                            </tr>
                          </thead>
                          <tbody>
                            {results.daily_data.map((day, index) => (
                              <tr key={index} className="border-t hover:bg-gray-50">
                                <td className="px-4 py-2 text-sm">{day.date}</td>
                                <td className="px-4 py-2 text-sm text-right font-semibold">{day.total_transactions}</td>
                                <td className="px-4 py-2 text-sm text-right text-green-600">{formatAmount(day.total_amount)}</td>
                                <td className="px-4 py-2 text-sm text-right text-red-600">{formatAmount(day.total_charges)}</td>
                                <td className="px-4 py-2 text-sm text-right font-semibold text-purple-600">{formatAmount(day.net_amount)}</td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot className="bg-gray-100 font-bold">
                            <tr>
                              <td className="px-4 py-3 text-sm">TOTAL</td>
                              <td className="px-4 py-3 text-sm text-right">{results.summary.total_transactions}</td>
                              <td className="px-4 py-3 text-sm text-right text-green-600">{formatAmount(results.summary.total_amount)}</td>
                              <td className="px-4 py-3 text-sm text-right text-red-600">{formatAmount(results.summary.total_charges)}</td>
                              <td className="px-4 py-3 text-sm text-right text-purple-600">{formatAmount(results.summary.net_amount)}</td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
