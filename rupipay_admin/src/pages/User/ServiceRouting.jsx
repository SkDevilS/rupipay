import { useState, useEffect } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import { toast } from 'sonner';
import adminAPI from '../../api/admin_api';

export default function ServiceRouting() {
  const [activeTab, setActiveTab] = useState('SINGLE_USER');
  const [routes, setRoutes] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [pgPartners, setPgPartners] = useState([]);
  const [selectedMerchant, setSelectedMerchant] = useState('');
  const [loading, setLoading] = useState(true);
  
  const [selectedPayinGateways, setSelectedPayinGateways] = useState([]);
  const [selectedPayoutGateways, setSelectedPayoutGateways] = useState([]);

  useEffect(() => {
    fetchInitialData();
  }, []);

  useEffect(() => {
    if (activeTab === 'SINGLE_USER' && selectedMerchant) {
      fetchMerchantRoutes();
    } else if (activeTab === 'ALL_USERS') {
      fetchAllUsersRoutes();
    }
  }, [activeTab, selectedMerchant]);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      const [routesRes, merchantsRes, partnersRes] = await Promise.all([
        adminAPI.getServiceRouting(),
        adminAPI.getMerchantsForRouting(),
        adminAPI.getPGPartners()
      ]);

      if (routesRes.success) {
        setRoutes(routesRes.routes);
      }
      
      if (merchantsRes.success) {
        setMerchants(merchantsRes.merchants || []);
      }
      
      if (partnersRes.success) {
        setPgPartners(partnersRes.partners || []);
      }
      
      fetchAllUsersRoutes();
    } catch (error) {
      toast.error('Failed to load data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllUsersRoutes = () => {
    const payinActive = routes
      .filter(r => r.service_type === 'PAYIN' && r.routing_type === 'ALL_USERS' && r.is_active)
      .map(r => r.pg_partner);
    
    const payoutActive = routes
      .filter(r => r.service_type === 'PAYOUT' && r.routing_type === 'ALL_USERS' && r.is_active)
      .map(r => r.pg_partner);
    
    setSelectedPayinGateways(payinActive);
    setSelectedPayoutGateways(payoutActive);
  };

  const fetchMerchantRoutes = () => {
    if (!selectedMerchant) {
      setSelectedPayinGateways([]);
      setSelectedPayoutGateways([]);
      return;
    }

    const payinActive = routes
      .filter(r => 
        r.service_type === 'PAYIN' && 
        r.routing_type === 'SINGLE_USER' && 
        r.merchant_id === selectedMerchant &&
        r.is_active
      )
      .map(r => r.pg_partner);
    
    const payoutActive = routes
      .filter(r => 
        r.service_type === 'PAYOUT' && 
        r.routing_type === 'SINGLE_USER' && 
        r.merchant_id === selectedMerchant &&
        r.is_active
      )
      .map(r => r.pg_partner);
    
    setSelectedPayinGateways(payinActive);
    setSelectedPayoutGateways(payoutActive);
  };

  const handlePayinToggle = async (gatewayId) => {
    if (activeTab === 'SINGLE_USER' && !selectedMerchant) {
      toast.error('Please select a merchant first');
      return;
    }

    const isCurrentlySelected = selectedPayinGateways.includes(gatewayId);
    
    if (isCurrentlySelected) {
      toast.info('This gateway is already active. Select another gateway to switch.');
      return;
    }

    try {
      const existingRoute = routes.find((r) => {
        return r.service_type === 'PAYIN' && 
               r.routing_type === activeTab && 
               r.pg_partner === gatewayId &&
               (activeTab === 'ALL_USERS' || r.merchant_id === selectedMerchant);
      });
      
      if (existingRoute) {
        await adminAPI.updateServiceRouting(existingRoute.id, { isActive: true });
      } else {
        await adminAPI.createServiceRouting({
          merchantId: activeTab === 'SINGLE_USER' ? selectedMerchant : null,
          serviceType: 'PAYIN',
          routingType: activeTab,
          pgPartner: gatewayId,
          priority: 1
        });
      }
      
      setSelectedPayinGateways([gatewayId]);
      toast.success(`Switched to ${gatewayId} gateway`);
      
      const routesRes = await adminAPI.getServiceRouting();
      if (routesRes.success) {
        setRoutes(routesRes.routes);
      }
    } catch (error) {
      toast.error('Failed to update gateway');
      console.error(error);
    }
  };

  const handlePayoutToggle = async (gatewayId) => {
    if (activeTab === 'SINGLE_USER' && !selectedMerchant) {
      toast.error('Please select a merchant first');
      return;
    }

    const isCurrentlySelected = selectedPayoutGateways.includes(gatewayId);
    
    if (isCurrentlySelected) {
      toast.info('This gateway is already active. Select another gateway to switch.');
      return;
    }

    try {
      const existingRoute = routes.find((r) => {
        return r.service_type === 'PAYOUT' && 
               r.routing_type === activeTab && 
               r.pg_partner === gatewayId &&
               (activeTab === 'ALL_USERS' || r.merchant_id === selectedMerchant);
      });
      
      if (existingRoute) {
        await adminAPI.updateServiceRouting(existingRoute.id, { isActive: true });
      } else {
        await adminAPI.createServiceRouting({
          merchantId: activeTab === 'SINGLE_USER' ? selectedMerchant : null,
          serviceType: 'PAYOUT',
          routingType: activeTab,
          pgPartner: gatewayId,
          priority: 1
        });
      }
      
      setSelectedPayoutGateways([gatewayId]);
      toast.success(`Switched to ${gatewayId} gateway`);
      
      const routesRes = await adminAPI.getServiceRouting();
      if (routesRes.success) {
        setRoutes(routesRes.routes);
      }
    } catch (error) {
      toast.error('Failed to update gateway');
      console.error(error);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setSelectedMerchant('');
    setSelectedPayinGateways([]);
    setSelectedPayoutGateways([]);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        <Button
          variant={activeTab === 'SINGLE_USER' ? 'default' : 'outline'}
          onClick={() => handleTabChange('SINGLE_USER')}
          className={activeTab === 'SINGLE_USER' ? '' : 'bg-white'}
        >
          Single User
        </Button>
        <Button
          variant="outline"
          disabled
          className="bg-gray-100 text-gray-400 cursor-not-allowed opacity-50"
        >
          All User
        </Button>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">
          {activeTab === 'SINGLE_USER' ? 'Single User' : 'All User'}
        </h2>

        {activeTab === 'SINGLE_USER' && (
          <div className="mb-6">
            <Label className="text-base font-medium mb-2 block">Select Merchant</Label>
            <select
              value={selectedMerchant}
              onChange={(e) => setSelectedMerchant(e.target.value)}
              className="w-full max-w-md border-2 border-gray-300 rounded-md p-3 text-base focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">-- Select Merchant --</option>
              {merchants.map((merchant) => (
                <option key={merchant.merchant_id} value={merchant.merchant_id}>
                  {merchant.full_name} ({merchant.merchant_id})
                </option>
              ))}
            </select>
          </div>
        )}

        {(activeTab === 'ALL_USERS' || selectedMerchant) && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="pt-6">
                <h3 className="font-semibold mb-2">UPI/QR (Payin)</h3>
                <p className="text-xs text-gray-500 mb-4">Select ONE payment gateway (only one can be active at a time)</p>
                <div className="space-y-3">
                  {pgPartners.length === 0 ? (
                    <p className="text-gray-500 text-sm">No payment gateways available</p>
                  ) : (
                    pgPartners
                      .filter(gateway => gateway.supports.includes('PAYIN'))
                      .map((gateway) => (
                        <div key={gateway.id} className="flex items-center space-x-2">
                          <input
                            type="radio"
                            id={`payin-${gateway.id}`}
                            name="payin-gateway"
                            checked={selectedPayinGateways.includes(gateway.id)}
                            onChange={() => handlePayinToggle(gateway.id)}
                            className="w-4 h-4 text-purple-600 focus:ring-purple-500"
                          />
                          <label
                            htmlFor={`payin-${gateway.id}`}
                            className="text-sm font-medium leading-none cursor-pointer"
                          >
                            {gateway.name}
                          </label>
                        </div>
                      ))
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <h3 className="font-semibold mb-2">Payout</h3>
                <p className="text-xs text-gray-500 mb-4">Select ONE payment gateway (only one can be active at a time)</p>
                <div className="space-y-3">
                  {pgPartners.length === 0 ? (
                    <p className="text-gray-500 text-sm">No payment gateways available</p>
                  ) : (
                    pgPartners
                      .filter(gateway => gateway.supports.includes('PAYOUT'))
                      .map((gateway) => (
                        <div key={gateway.id} className="flex items-center space-x-2">
                          <input
                            type="radio"
                            id={`payout-${gateway.id}`}
                            name="payout-gateway"
                            checked={selectedPayoutGateways.includes(gateway.id)}
                            onChange={() => handlePayoutToggle(gateway.id)}
                            className="w-4 h-4 text-purple-600 focus:ring-purple-500"
                          />
                          <label
                            htmlFor={`payout-${gateway.id}`}
                            className="text-sm font-medium leading-none cursor-pointer"
                          >
                            {gateway.name}
                          </label>
                        </div>
                      ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'SINGLE_USER' && !selectedMerchant && (
          <Card>
            <CardContent className="pt-6">
              <p className="text-center text-gray-500 py-8">
                Please select a merchant to configure their payment gateway routing
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
