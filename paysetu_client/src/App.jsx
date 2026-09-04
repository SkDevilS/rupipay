import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from './components/ui/sonner'
import ProtectedRoute from './components/ProtectedRoute'
import PublicRoute from './components/PublicRoute'
import DashboardLayout from './layout/DashboardLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import { usePageTitle } from './hooks/usePageTitle'

// Transaction pages
import PayinReport from './pages/Transactions/PayinReport'
import PayoutReport from './pages/Transactions/PayoutReport'

// Wallet pages
import WalletOverview from './pages/Wallet/WalletOverview'
import WalletStatement from './pages/Wallet/WalletStatement'

// Fund Manager pages
import SettleFund from './pages/FundManager/SettleFund'
import FundRequest from './pages/FundManager/FundRequest'

// Security pages
import ChangePassword from './pages/Security/ChangePassword'
import ChangePin from './pages/Security/ChangePin'

// Developer Zone pages
import Documentation from './pages/DeveloperZone/Documentation'
import Credentials from './pages/DeveloperZone/Credentials'

// Settings pages
import BankManagement from './pages/Settings/BankManagement'

// Generate QR
import GenerateQR from './pages/GenerateQR'

// My Commercials
import MyCommercials from './pages/MyCommercials'

function App() {
  // Use the page title hook to dynamically update title based on route
  usePageTitle();
  
  return (
    <>
      <Routes>
        {/* Public Route - Login */}
        <Route 
          path="/login" 
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          } 
        />
        
        {/* Protected Routes - Dashboard */}
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          
          {/* Transaction Routes */}
          <Route path="transactions/payin-report" element={<PayinReport />} />
          <Route path="transactions/payout-report" element={<PayoutReport />} />
          
          {/* Wallet Routes */}
          <Route path="wallet/overview" element={<WalletOverview />} />
          <Route path="wallet/statement" element={<WalletStatement />} />
          
          {/* Fund Manager Routes */}
          <Route path="fund-manager/settle" element={<SettleFund />} />
          <Route path="fund-manager/request" element={<FundRequest />} />
          
          {/* Security Routes */}
          <Route path="security/change-password" element={<ChangePassword />} />
          <Route path="security/change-pin" element={<ChangePin />} />
          
          {/* Developer Zone Routes */}
          <Route path="developer/documentation" element={<Documentation />} />
          <Route path="developer/credentials" element={<Credentials />} />
          
          {/* Settings Routes */}
          <Route path="settings/bank" element={<BankManagement />} />
          
          {/* Generate QR */}
          <Route path="generate-qr" element={<GenerateQR />} />
          
          {/* My Commercials */}
          <Route path="my-commercials" element={<MyCommercials />} />
        </Route>
        
        {/* Catch all - redirect to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster />
    </>
  )
}

export default App
