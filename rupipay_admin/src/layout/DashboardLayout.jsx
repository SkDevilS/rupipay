import { useState, useEffect, useRef } from 'react'
import { Outlet, useNavigate, Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, Users, ArrowLeftRight, Wallet, 
  TrendingUp, Shield, Settings, Activity, 
  ChevronDown, LogOut, Menu, X, Bell, Search,
  UserPlus, List, Route, MessageSquare,
  FileText, Clock, DollarSign, Building,
  Lock, Key, CreditCard, Briefcase, Package, User,
  ChevronLeft, ChevronRight, AlertTriangle, RefreshCw,
  BarChart3
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import adminAPI from '@/api/admin_api'
import { toast } from 'sonner'
import PinNotification from '@/components/PinNotification'

const menuItems = [
  { 
    title: 'Dashboard', 
    icon: LayoutDashboard, 
    path: '/' 
  },
  {
    title: 'User',
    icon: Users,
    submenu: [
      { title: 'User Onboarding', icon: UserPlus, path: '/user/onboarding' },
      { title: 'User List', icon: List, path: '/user/list' },
      { title: 'Service Routing', icon: Route, path: '/user/service-routing' },
    ]
  },
  {
    title: 'Transactions',
    icon: ArrowLeftRight,
    submenu: [
      { title: 'Payin Report', icon: FileText, path: '/transactions/payin-report' },
      { title: 'Payout Report', icon: FileText, path: '/transactions/payout-report' },
      { title: 'Manual Reconciliation', icon: RefreshCw, path: '/reconciliation/manual' },
    ]
  },
  {
    title: 'Fund Manager',
    icon: TrendingUp,
    submenu: [
      { title: 'Topup Fund', icon: DollarSign, path: '/fund-manager/topup' },
      { title: 'Fetch Fund', icon: Package, path: '/fund-manager/fetch' },
      { title: 'Fund Requests', icon: FileText, path: '/fund-manager/requests' },
      { title: 'Settle Wallet', icon: Wallet, path: '/wallet/settle' },
      { title: 'Wallet Statement', icon: FileText, path: '/wallet/statement' },
      { title: 'Wallet Summary', icon: Wallet, path: '/wallet/summary' },
    ]
  },
  { 
    title: 'Personal Payout', 
    icon: DollarSign, 
    path: '/payout/personal' 
  },
  { 
    title: 'API Ledger', 
    icon: Activity, 
    path: '/reports/api-ledger' 
  },
  {
    title: 'Monitoring',
    icon: BarChart3,
    submenu: [
      { title: 'Oxymoney_Grosmart VPA', icon: Activity, path: '/oxymoney/vpa-usage' },
    ]
  },
  {
    title: 'Security',
    icon: Shield,
    submenu: [
      { title: 'Change Password', icon: Lock, path: '/security/change-password' },
      { title: 'Change PIN', icon: Key, path: '/security/change-pin' },
      { title: 'IP Security', icon: Shield, path: '/security/ip-security' },
    ]
  },
  {
    title: 'Settings',
    icon: Settings,
    submenu: [
      { title: 'Add/Update Bank', icon: Building, path: '/settings/bank' },
      { title: 'Commercials', icon: CreditCard, path: '/settings/commercials' },
    ]
  },
  { 
    title: 'Activity Logs', 
    icon: Activity, 
    path: '/activity-logs' 
  },
]

export default function DashboardLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [expandedMenus, setExpandedMenus] = useState({})
  const [showNotifications, setShowNotifications] = useState(false)
  const [pendingFundRequests, setPendingFundRequests] = useState([])
  const [notificationCount, setNotificationCount] = useState(0)
  
  // Session expiry state - 15 MINUTES PRODUCTION
  const [showWarning, setShowWarning] = useState(false)
  const [countdown, setCountdown] = useState(20)
  const [refreshing, setRefreshing] = useState(false)
  const lastActivityRef = useRef(Date.now())
  const checkIntervalRef = useRef(null)
  const countdownIntervalRef = useRef(null)
  
  const SESSION_TIMEOUT = 15 * 60 * 1000 // 15 minutes
  const WARNING_TIME = 14 * 60 * 1000 + 40 * 1000 // 14 minutes 40 seconds
  const COUNTDOWN_DURATION = 20 // 20 seconds countdown

  // const SESSION_TIMEOUT = 20000 // 15 minutes
  // const WARNING_TIME = 10000 // 14 minutes 40 seconds
  // const COUNTDOWN_DURATION = 10 // 20 seconds countdown
  
  useEffect(() => {
    console.log('✅ Session monitoring started - 15 minutes timeout')
    lastActivityRef.current = Date.now()
    
    // Load pending fund requests
    loadPendingFundRequests()
    
    // Refresh fund requests every 30 seconds
    const fundRequestInterval = setInterval(() => {
      loadPendingFundRequests()
    }, 30000)
    
    // Check every second
    checkIntervalRef.current = setInterval(() => {
      const elapsed = Date.now() - lastActivityRef.current
      
      if (elapsed >= WARNING_TIME && !showWarning) {
        console.log('🚨 SHOWING WARNING - Session expiring in 20 seconds')
        setShowWarning(true)
        setCountdown(COUNTDOWN_DURATION)
      }
    }, 1000)
    
    const handleActivity = () => {
      if (!showWarning) {
        lastActivityRef.current = Date.now()
      }
    }
    
    const events = ['mousedown', 'keydown', 'scroll', 'click']
    events.forEach(e => window.addEventListener(e, handleActivity, { passive: true }))
    
    return () => {
      if (checkIntervalRef.current) clearInterval(checkIntervalRef.current)
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current)
      if (fundRequestInterval) clearInterval(fundRequestInterval)
      events.forEach(e => window.removeEventListener(e, handleActivity))
    }
  }, [showWarning])
  
  // Separate effect for countdown
  useEffect(() => {
    if (showWarning && countdown > 0) {
      countdownIntervalRef.current = setInterval(() => {
        setCountdown(prev => {
          console.log('⏳ Countdown:', prev - 1)
          if (prev <= 1) {
            clearInterval(countdownIntervalRef.current)
            handleSessionExpired()
            return 0
          }
          return prev - 1
        })
      }, 1000)
      
      return () => {
        if (countdownIntervalRef.current) {
          clearInterval(countdownIntervalRef.current)
        }
      }
    }
  }, [showWarning])
  
  const handleSessionExpired = async () => {
    console.log('🔴 SESSION EXPIRED - Logging out')
    setShowWarning(false)
    
    // Clear all intervals
    if (checkIntervalRef.current) clearInterval(checkIntervalRef.current)
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current)
    
    try {
      // Logout and clear storage
      await adminAPI.logout()
    } catch (error) {
      console.error('Logout error:', error)
    }
    
    // Force navigation to login
    toast.error('Session expired. Please login again.')
    navigate('/login', { replace: true })
  }
  
  const handleRefreshSession = async () => {
    setRefreshing(true)
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current)
    }
    try {
      const response = await adminAPI.verifyToken()
      if (response.success) {
        lastActivityRef.current = Date.now()
        setShowWarning(false)
        setCountdown(COUNTDOWN_DURATION)
        toast.success('Session refreshed!')
      } else {
        throw new Error('Token verification failed')
      }
    } catch (error) {
      console.error('Session refresh error:', error)
      await adminAPI.logout()
      toast.error('Session refresh failed. Please login again.')
      navigate('/login', { replace: true })
    } finally {
      setRefreshing(false)
    }
  }
  
  const handleCloseSession = async () => {
    console.log('🔴 USER CLOSED SESSION - Logging out')
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current)
    }
    if (checkIntervalRef.current) {
      clearInterval(checkIntervalRef.current)
    }
    setShowWarning(false)
    setCountdown(COUNTDOWN_DURATION)
    
    try {
      await adminAPI.logout()
    } catch (error) {
      console.error('Logout error:', error)
    }
    
    toast.info('Logged out')
    navigate('/login', { replace: true })
  }

  const handleLogout = async () => {
    console.log('🔴 MANUAL LOGOUT')
    
    // Clear all intervals
    if (checkIntervalRef.current) clearInterval(checkIntervalRef.current)
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current)
    
    try {
      await adminAPI.logout()
      toast.success('Logged out successfully')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      navigate('/login', { replace: true })
    }
  }

  const loadPendingFundRequests = async () => {
    try {
      const response = await adminAPI.getFundRequests('PENDING')
      if (response.success) {
        const requests = response.data || []
        setPendingFundRequests(requests)
        setNotificationCount(requests.length)
      }
    } catch (error) {
      console.error('Load fund requests error:', error)
    }
  }

  const handleNotificationClick = () => {
    setShowNotifications(!showNotifications)
  }

  const handleViewAllRequests = () => {
    setShowNotifications(false)
    navigate('/fund-manager/requests')
  }

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(amount || 0)
  }

  const formatDateTime = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const toggleMenu = (title) => {
    setExpandedMenus(prev => ({ ...prev, [title]: !prev[title] }))
  }

  const isActive = (path) => location.pathname === path

  return (
    <>
      {/* Session Warning Dialog - INLINE */}
      <Dialog open={showWarning} onOpenChange={() => {}}>
        <DialogContent className="sm:max-w-md" hideClose>
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-3 bg-orange-100 rounded-full">
                <AlertTriangle className="h-6 w-6 text-orange-600" />
              </div>
              <DialogTitle className="text-xl">Session Expiring Soon</DialogTitle>
            </div>
            <DialogDescription className="text-base pt-2">
              Your session will expire in {countdown} seconds
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center justify-center py-6">
            <div className="text-6xl font-bold text-orange-600">{countdown}</div>
            <div className="text-sm text-gray-500 mt-2">seconds remaining</div>
          </div>
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={handleCloseSession} disabled={refreshing} className="flex-1">
              <X className="h-4 w-4 mr-2" />
              Close
            </Button>
            <Button onClick={handleRefreshSession} disabled={refreshing} className="flex-1 bg-orange-500 hover:bg-orange-600">
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      <div className="flex h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50">
        {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-72' : 'w-20'} bg-white border-r border-gray-200 shadow-xl transition-all duration-300 flex flex-col`}>
        {sidebarOpen ? (
          <>
            {/* Logo Section - Open */}
            <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-yellow-50 to-amber-50">
              <div className="flex items-center">
                <img src="/paysetu.png" alt="Paysetu" className="h-12 w-auto" />
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="text-gray-600 hover:text-yellow-600 hover:bg-yellow-50 transition-all rounded-xl"
                title="Close sidebar"
              >
                <ChevronLeft size={20} />
              </Button>
            </div>
          </>
        ) : (
          <>
            {/* Logo Section - Closed */}
            <div className="p-4 border-b border-gray-200 flex flex-col items-center gap-3 bg-gradient-to-r from-yellow-50 to-amber-50">
              <img src="/favicon.png" alt="Paysetu" className="h-12 w-12 object-contain" />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="text-gray-600 hover:text-yellow-600 hover:bg-yellow-50 transition-all p-2 rounded-xl"
                title="Open sidebar"
              >
                <ChevronRight size={20} />
              </Button>
            </div>
          </>
        )}

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
          {menuItems.map((item) => (
            <div key={item.title} className="animate-slide-in">
              {item.submenu ? (
                <div>
                  <button
                    onClick={() => toggleMenu(item.title)}
                    className={`w-full flex items-center ${sidebarOpen ? 'justify-between' : 'justify-center'} p-2.5 rounded-2xl transition-all duration-200 hover:bg-yellow-50 text-gray-700 hover:text-yellow-700 group relative overflow-hidden`}
                    title={!sidebarOpen ? item.title : ''}
                  >
                    <div className={`flex items-center gap-3 relative z-10 ${!sidebarOpen && 'justify-center'}`}>
                      <div className="p-1.5 rounded-xl bg-gray-100 group-hover:bg-yellow-100 transition-colors">
                        <item.icon size={18} className="text-gray-600 group-hover:text-yellow-700 transition-colors" />
                      </div>
                      {sidebarOpen && <span className="font-medium text-sm">{item.title}</span>}
                    </div>
                    {sidebarOpen && (
                      <ChevronDown
                        size={16}
                        className={`transition-transform duration-300 relative z-10 ${expandedMenus[item.title] ? 'rotate-180' : ''}`}
                      />
                    )}
                  </button>
                  {expandedMenus[item.title] && sidebarOpen && (
                    <div className="ml-6 mt-2 space-y-1 animate-slide-in">
                      {item.submenu.map((subItem) => {
                        const isDisabled = subItem.disabled
                        const ItemComponent = isDisabled ? 'div' : Link
                        
                        return (
                          <ItemComponent
                            key={subItem.path}
                            {...(!isDisabled && { to: subItem.path })}
                            className={`flex items-center gap-3 p-2.5 rounded-xl transition-all duration-200 group ${
                              isDisabled
                                ? 'opacity-40 blur-[0.5px] cursor-not-allowed pointer-events-none'
                                : isActive(subItem.path) 
                                  ? 'bg-gradient-to-r from-yellow-500 to-amber-500 text-white shadow-lg shadow-yellow-500/30 scale-[1.02]' 
                                  : 'text-gray-600 hover:bg-yellow-50 hover:text-yellow-700'
                            }`}
                            {...(isDisabled && { title: 'Coming Soon' })}
                          >
                            <subItem.icon size={16} className="group-hover:scale-110 transition-transform duration-200" />
                            <span className="text-sm font-medium">{subItem.title}</span>
                          </ItemComponent>
                        )
                      })}
                    </div>
                  )}
                </div>
              ) : (
                <Link
                  to={item.path}
                  className={`flex items-center gap-3 p-2.5 rounded-2xl transition-all duration-200 group ${
                    isActive(item.path) 
                      ? 'bg-gradient-to-r from-yellow-500 to-amber-500 text-white shadow-lg shadow-yellow-500/30 scale-[1.02]' 
                      : 'text-gray-700 hover:bg-yellow-50 hover:text-yellow-700'
                  } ${!sidebarOpen && 'justify-center'}`}
                  title={!sidebarOpen ? item.title : ''}
                >
                  <div className={`p-1.5 rounded-xl transition-colors ${
                    isActive(item.path) 
                      ? 'bg-white/20' 
                      : 'bg-gray-100 group-hover:bg-yellow-100'
                  }`}>
                    <item.icon size={18} className={`transition-colors ${
                      isActive(item.path) 
                        ? 'text-white' 
                        : 'text-gray-600 group-hover:text-yellow-700'
                    }`} />
                  </div>
                  {sidebarOpen && <span className="font-medium text-sm">{item.title}</span>}
                </Link>
              )}
            </div>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navigation Bar */}
        <header className="bg-white border-b border-gray-200 shadow-md">
          <div className="flex items-center justify-between px-6 py-4">
            {/* Search Bar */}
            <div className="flex-1 max-w-xl">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <Input
                  placeholder="Search transactions, users, reports..."
                  className="pl-10 bg-gray-50 border-gray-200 focus:bg-white focus:border-yellow-500 rounded-xl"
                />
              </div>
            </div>

            {/* Right Side Actions */}
            <div className="flex items-center gap-4 ml-6">
              {/* Notifications */}
              <div className="relative">
                <button 
                  onClick={handleNotificationClick}
                  className="relative p-2 text-gray-600 hover:text-yellow-600 hover:bg-yellow-50 rounded-xl transition-colors"
                >
                  <Bell size={22} />
                  {notificationCount > 0 && (
                    <span className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-semibold">
                      {notificationCount > 9 ? '9+' : notificationCount}
                    </span>
                  )}
                </button>

                {/* Notification Dropdown */}
                {showNotifications && (
                  <div className="absolute right-0 mt-2 w-96 bg-white rounded-xl shadow-2xl border border-gray-200 z-50 max-h-96 overflow-hidden">
                    <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-yellow-50 to-amber-50">
                      <h3 className="font-semibold text-gray-800">Pending Fund Requests</h3>
                      <p className="text-xs text-gray-600 mt-1">{notificationCount} pending request{notificationCount !== 1 ? 's' : ''}</p>
                    </div>
                    
                    <div className="max-h-80 overflow-y-auto">
                      {pendingFundRequests.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                          <Bell className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                          <p>No pending fund requests</p>
                        </div>
                      ) : (
                        pendingFundRequests.map((request) => (
                          <div 
                            key={request.request_id}
                            className="p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer"
                            onClick={handleViewAllRequests}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <p className="font-semibold text-gray-800">{request.merchant_name || request.merchant_id}</p>
                                <p className="text-sm text-gray-600 mt-1">{request.remarks || 'Fund request'}</p>
                                <p className="text-xs text-gray-500 mt-1">{formatDateTime(request.created_at)}</p>
                              </div>
                              <div className="text-right ml-3">
                                <p className="font-bold text-yellow-600">{formatCurrency(request.amount)}</p>
                                <span className="inline-block mt-1 px-2 py-1 text-xs bg-yellow-100 text-yellow-700 rounded-full">
                                  Pending
                                </span>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                    
                    {pendingFundRequests.length > 0 && (
                      <div className="p-3 border-t border-gray-200 bg-gray-50">
                        <button
                          onClick={handleViewAllRequests}
                          className="w-full text-center text-sm text-yellow-600 hover:text-yellow-700 font-medium"
                        >
                          View All Requests →
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* User Profile */}
              <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
                <div className="text-right">
                  <p className="text-sm font-semibold text-gray-800">Admin User</p>
                  <p className="text-xs text-gray-500">{adminAPI.getAdminId() || 'admin@paysetu.shop'}</p>
                </div>
                <div className="w-10 h-10 bg-gradient-to-br from-yellow-500 to-amber-600 rounded-xl flex items-center justify-center text-white font-semibold shadow-md">
                  <User size={20} />
                </div>
              </div>

              {/* Logout Button */}
              <Button
                onClick={handleLogout}
                variant="ghost"
                className="flex items-center gap-2 text-red-600 hover:bg-red-50 hover:text-red-700 rounded-xl transition-all duration-200 px-4 py-2"
              >
                <LogOut size={18} />
                <span className="font-medium text-sm">Logout</span>
              </Button>
            </div>
          </div>
        </header>

        {/* PIN Notification Banner */}
        <PinNotification />

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
          <div className="animate-slide-in">
            <Outlet />
          </div>
        </div>
      </main>
      </div>
    </>
  )
}
