import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

// Map routes to page titles
const routeTitles = {
  '/': 'Dashboard',
  '/login': 'Login',
  
  // User
  '/user/onboarding': 'User Onboarding',
  '/user/list': 'User List',
  '/user/service-routing': 'Service Routing',
  '/user/otp-service': 'OTP Service',
  
  // Transactions
  '/transactions/payin-report': 'PayIN Report',
  '/transactions/payout-report': 'PayOUT Report',
  '/transactions/pending-payin': 'Pending PayIN',
  '/transactions/pending-payout': 'Pending PayOUT',
  
  // Payout
  '/payout/personal': 'Personal Payout',
  
  // Wallet
  '/wallet/overview': 'Wallet Overview',
  '/wallet/statement': 'Wallet Statement',
  
  // Fund Manager
  '/fund-manager/topup': 'Topup Fund',
  '/fund-manager/settlement': 'Fund Settlement',
  '/fund-manager/fetch': 'Fetch Fund',
  '/fund-manager/requests': 'Fund Requests',
  
  // Security
  '/security/change-password': 'Change Password',
  '/security/change-pin': 'Change PIN',
  
  // Settings
  '/settings/bank': 'Bank Management',
  '/settings/services': 'Manage Services',
  '/settings/commercials': 'Commercials',
  
  // Activity Logs
  '/activity-logs': 'Activity Logs',
};

export const usePageTitle = (customTitle = null) => {
  const location = useLocation();

  useEffect(() => {
    const pageTitle = customTitle || routeTitles[location.pathname] || 'Paysetu Admin';
    document.title = `${pageTitle} | Paysetu Admin`;
  }, [location.pathname, customTitle]);
};
