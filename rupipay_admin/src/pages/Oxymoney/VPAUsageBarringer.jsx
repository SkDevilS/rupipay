import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import adminAPI from '@/api/admin_api';

const VPAUsageBarringer = () => {
  const [vpaStats, setVpaStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dailyLimit, setDailyLimit] = useState(990000);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchVPAUsage = async () => {
    try {
      setRefreshing(true);
      const response = await adminAPI.getOxymoneyBarringerVPAUsage();
      
      if (response.success) {
        setVpaStats(response.vpa_stats);
        setDailyLimit(response.daily_limit);
        setLastUpdated(new Date());
      } else {
        alert(response.message || 'Failed to fetch VPA usage');
      }
    } catch (error) {
      console.error('Error fetching VPA usage:', error);
      alert('Failed to fetch VPA usage data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchVPAUsage();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchVPAUsage, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat('en-IN').format(num);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'AVAILABLE':
        return 'bg-green-500';
      case 'NEAR_LIMIT':
        return 'bg-yellow-500';
      case 'AT_LIMIT':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'AVAILABLE':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'NEAR_LIMIT':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'AT_LIMIT':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      'AVAILABLE': 'default',
      'NEAR_LIMIT': 'warning',
      'AT_LIMIT': 'destructive'
    };
    
    return (
      <Badge variant={variants[status] || 'secondary'}>
        {status.replace('_', ' ')}
      </Badge>
    );
  };

  const getTotalUsage = () => {
    return vpaStats.reduce((sum, vpa) => sum + vpa.total_usage, 0);
  };

  const getTotalTransactions = () => {
    return vpaStats.reduce((sum, vpa) => sum + vpa.transaction_count, 0);
  };

  const getTotalCapacity = () => {
    return dailyLimit * vpaStats.length;
  };

  const getTotalRemaining = () => {
    return vpaStats.reduce((sum, vpa) => sum + vpa.remaining, 0);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading VPA usage data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Oxymoney_Barringer VPA Usage Monitor</h1>
          <p className="text-gray-600 mt-1">
            Real-time monitoring of VPA daily limits (9.9 Lakh per VPA)
          </p>
        </div>
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-sm text-gray-500">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <Button
            onClick={fetchVPAUsage}
            disabled={refreshing}
            variant="outline"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Usage Today</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(getTotalUsage())}</div>
            <p className="text-xs text-gray-500 mt-1">
              {((getTotalUsage() / getTotalCapacity()) * 100).toFixed(1)}% of total capacity
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Transactions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(getTotalTransactions())}</div>
            <p className="text-xs text-gray-500 mt-1">Across all VPAs</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Capacity</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(getTotalCapacity())}</div>
            <p className="text-xs text-gray-500 mt-1">
              {vpaStats.length} VPAs × ₹9.9 Lakh
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Remaining Capacity</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(getTotalRemaining())}</div>
            <p className="text-xs text-gray-500 mt-1">
              {((getTotalRemaining() / getTotalCapacity()) * 100).toFixed(1)}% available
            </p>
          </CardContent>
        </Card>
      </div>

      {/* VPA Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {vpaStats.map((vpa) => (
          <Card key={vpa.vpa_index} className="relative overflow-hidden">
            <div className={`absolute top-0 left-0 right-0 h-1 ${getStatusColor(vpa.status)}`} />
            
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-lg">VPA {vpa.vpa_index}</CardTitle>
                  <CardDescription className="text-xs mt-1 font-mono">
                    {vpa.vpa}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusIcon(vpa.status)}
                  {getStatusBadge(vpa.status)}
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Usage Progress */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Usage</span>
                  <span className="font-semibold">{vpa.usage_percentage}%</span>
                </div>
                <Progress 
                  value={vpa.usage_percentage} 
                  className="h-2"
                  indicatorClassName={
                    vpa.usage_percentage >= 95 ? 'bg-red-500' :
                    vpa.usage_percentage >= 80 ? 'bg-yellow-500' :
                    'bg-green-500'
                  }
                />
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-4 pt-2">
                <div>
                  <p className="text-xs text-gray-500">Used</p>
                  <p className="text-sm font-semibold">{formatCurrency(vpa.total_usage)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Remaining</p>
                  <p className="text-sm font-semibold">{formatCurrency(vpa.remaining)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Transactions</p>
                  <p className="text-sm font-semibold">{formatNumber(vpa.transaction_count)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Daily Limit</p>
                  <p className="text-sm font-semibold">{formatCurrency(vpa.daily_limit)}</p>
                </div>
              </div>

              {/* Warning Message */}
              {vpa.status === 'NEAR_LIMIT' && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mt-2">
                  <p className="text-xs text-yellow-800">
                    <AlertTriangle className="h-3 w-3 inline mr-1" />
                    Approaching daily limit. System will auto-rotate to next VPA.
                  </p>
                </div>
              )}

              {vpa.status === 'AT_LIMIT' && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3 mt-2">
                  <p className="text-xs text-red-800">
                    <XCircle className="h-3 w-3 inline mr-1" />
                    Daily limit reached. This VPA is unavailable until tomorrow.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Info Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardHeader>
          <CardTitle className="text-lg">ℹ️ Important Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>
            <strong>Daily Limit:</strong> Each VPA has a daily limit of ₹9,90,000 (9.9 Lakh)
          </p>
          <p>
            <strong>Safety Threshold:</strong> System automatically rotates to next VPA at ₹9,85,000 (99.5%)
          </p>
          <p>
            <strong>Auto-Rotation:</strong> When a VPA approaches its limit, the system automatically uses the next available VPA
          </p>
          <p>
            <strong>Daily Reset:</strong> VPA usage resets at midnight (00:00 IST)
          </p>
          <p>
            <strong>Bank Block Prevention:</strong> If a VPA exceeds 9.9 Lakh, the bank may block it. The safety threshold prevents this.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default VPAUsageBarringer;
