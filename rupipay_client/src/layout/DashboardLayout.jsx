import { useState, useEffect } from 'react'
import { Outlet, useNavigate, Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, ArrowLeftRight, Wallet, 
  TrendingUp, Shield, Settings, 
  ChevronDown, LogOut, Bell, Search,
  FileText, Clock, DollarSign, Building,
  Lock, Key, Book, KeyRound, QrCode, CreditCard, User,
  ChevronLeft, ChevronRight
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'
import SessionExpiryWarning from '@/components/SessionExpiryWarning'
import PinNotification from '@/components/PinNotification'

const menuItems = [
  { 
    title: 'Dashboard', 
    icon: LayoutDashboard, 
    path: '/' 
  },
  {
    title: 'Transactions',
    icon: ArrowLeftRight,
    submenu: [
      { title: 'Payin Report', icon: FileText, path: '/transactions/payin-report' },
      { title: 'Payout Report', icon: FileText, path: '/transactions/payout-report' },
    ]
  },
  {
    title: 'Wallet',
    icon: Wallet,
    submenu: [
      { title: 'Wallet Overview', icon: Wallet, path: '/wallet/overview' },
      { title: 'Wallet Statement', icon: FileText, path: '/wallet/statement' },
    ]
  },
  {
    title: 'Fund Manager',
    icon: TrendingUp,
    submenu: [
      { title: 'Fund Request', icon: FileText, path: '/fund-manager/request' },
      { title: 'Settle Fund', icon: DollarSign, path: '/fund-manager/settle' },
    ]
  },
  {
    title: 'Security',
    icon: Shield,
    submenu: [
      { title: 'Change Password', icon: Lock, path: '/security/change-password' },
      { title: 'Change PIN', icon: Key, path: '/security/change-pin' },
    ]
  },
  {
    title: 'Developer Zone',
    icon: Book,
    submenu: [
      { title: 'Documentation', icon: FileText, path: '/developer/documentation' },
      { title: 'Credentials', icon: KeyRound, path: '/developer/credentials' },
    ]
  },
  {
    title: 'Settings',
    icon: Settings,
    submenu: [
      { title: 'Add/Update Bank', icon: Building, path: '/settings/bank' },
    ]
  },
  { 
    title: 'Generate QR', 
    icon: QrCode, 
    path: '/generate-qr' 
  },
  { 
    title: 'My Commercials', 
    icon: CreditCard, 
    path: '/my-commercials' 
  },
]

export default function DashboardLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [expandedMenus, setExpandedMenus] = useState({})
  const [merchantInfo, setMerchantInfo] = useState({
    name: 'Merchant User',
    email: 'merchant@example.com'
  })

  useEffect(() => {
    // Load merchant info from localStorage
    const merchantName = clientAPI.getMerchantName()
    const merchantId = clientAPI.getMerchantId()
    
    if (merchantName) {
      setMerchantInfo({
        name: merchantName,
        email: merchantId || 'merchant@example.com'
      })
    }

    // Verify token on mount
    verifyAuth()
  }, [])

  const verifyAuth = async () => {
    try {
      await clientAPI.verifyToken()
    } catch (error) {
      console.error('Token verification failed:', error)
      handleLogout()
    }
  }

  const handleLogout = () => {
    clientAPI.logout()
    toast.success('Logged out successfully')
    navigate('/login', { replace: true })
  }

  const toggleMenu = (title) => {
    setExpandedMenus(prev => ({ ...prev, [title]: !prev[title] }))
  }

  const isActive = (path) => location.pathname === path

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50">
      <SessionExpiryWarning />
      
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
                    className={`w-full flex items-center ${sidebarOpen ? 'justify-between' : 'justify-center'} p-2.5 rounded-2xl transition-all duration-200 hover:bg-yellow-50 text-gray-700 hover:text-yellow-600 group relative overflow-hidden`}
                    title={!sidebarOpen ? item.title : ''}
                  >
                    <div className={`flex items-center gap-3 relative z-10 ${!sidebarOpen && 'justify-center'}`}>
                      <div className="p-1.5 rounded-xl bg-gray-100 group-hover:bg-yellow-100 transition-colors">
                        <item.icon size={18} className="text-gray-600 group-hover:text-yellow-600 transition-colors" />
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
                      {item.submenu.map((subItem) => (
                        <Link
                          key={subItem.path}
                          to={subItem.path}
                          className={`flex items-center gap-3 p-2.5 rounded-xl transition-all duration-200 group ${
                            isActive(subItem.path) 
                              ? 'bg-gradient-to-r from-yellow-500 to-yellow-400 text-white shadow-lg shadow-yellow-500/30 scale-[1.02]' 
                              : 'text-gray-600 hover:bg-yellow-50 hover:text-yellow-600'
                          }`}
                        >
                          <subItem.icon size={16} className="group-hover:scale-110 transition-transform duration-200" />
                          <span className="text-sm font-medium">{subItem.title}</span>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <Link
                  to={item.path}
                  className={`flex items-center gap-3 p-2.5 rounded-2xl transition-all duration-200 group ${
                    isActive(item.path) 
                      ? 'bg-gradient-to-r from-yellow-500 to-yellow-400 text-white shadow-lg shadow-yellow-500/30 scale-[1.02]' 
                      : 'text-gray-700 hover:bg-yellow-50 hover:text-yellow-600'
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
                        : 'text-gray-600 group-hover:text-yellow-600'
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
                  placeholder="Search transactions, reports..."
                  className="pl-10 bg-gray-50 border-gray-200 focus:bg-white focus:border-yellow-500 rounded-xl"
                />
              </div>
            </div>

            {/* Right Side Actions */}
            <div className="flex items-center gap-4 ml-6">
              {/* Notifications */}
              <button className="relative p-2 text-gray-600 hover:text-yellow-600 hover:bg-yellow-50 rounded-xl transition-colors">
                <Bell size={22} />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>

              {/* User Profile */}
              <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
                <div className="text-right">
                  <p className="text-sm font-semibold text-gray-800">{merchantInfo.name}</p>
                  <p className="text-xs text-gray-500">{merchantInfo.email}</p>
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

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {/* PIN Notification */}
          <PinNotification />
          
          <div className="p-6 animate-slide-in">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  )
}

