import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Wallet, Eye, EyeOff, Search } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'

export default function PersonalPayout() {
  const [banks, setBanks] = useState([])
  const [filteredBanks, setFilteredBanks] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedBank, setSelectedBank] = useState('')
  const [amount, setAmount] = useState('')
  const [tpin, setTpin] = useState('')
  const [showTpin, setShowTpin] = useState(false)
  const [loading, setLoading] = useState(false)
  const [pgPartner, setPgPartner] = useState('')  // Payment gateway selection
  const [pgPartners, setPgPartners] = useState([])  // Available payment gateways
  const [loadingPartners, setLoadingPartners] = useState(true)

  useEffect(() => {
    fetchBanks()
    fetchPgPartners()
  }, [])

  const fetchBanks = async () => {
    try {
      const response = await adminAPI.getAdminBanks()
      if (response.success) {
        // Backend returns 'banks' not 'data'
        const bankList = response.banks || []
        const activeBanks = bankList.filter(bank => bank.is_active)
        setBanks(activeBanks)
        setFilteredBanks(activeBanks)
      }
    } catch (error) {
      console.error('Error fetching banks:', error)
      toast.error('Failed to load bank accounts')
      setBanks([])
      setFilteredBanks([])
    }
  }

  // Search filter function
  const handleSearch = (query) => {
    setSearchQuery(query)
    
    if (!query.trim()) {
      setFilteredBanks(banks)
      return
    }
    
    const searchLower = query.toLowerCase()
    const filtered = banks.filter(bank => {
      const bankName = (bank.bank_name || '').toLowerCase()
      const accountHolder = (bank.account_holder_name || '').toLowerCase()
      const accountNumber = (bank.account_number || '').toLowerCase()
      
      return bankName.includes(searchLower) || 
             accountHolder.includes(searchLower) || 
             accountNumber.includes(searchLower)
    })
    
    setFilteredBanks(filtered)
  }

  const fetchPgPartners = async () => {
    try {
      setLoadingPartners(true)
      // Fetch admin payout gateways (hardcoded list of ONLY payout services)
      const response = await adminAPI.getAdminPayoutGateways()
      if (response.success) {
        const gateways = response.gateways || []
        // Map to partner format
        const partners = gateways.map(gateway => ({
          value: gateway.id,
          label: gateway.name
        }))
        
        setPgPartners(partners)
        
        // Set first partner as default if available
        if (partners.length > 0) {
          setPgPartner(partners[0].value)
        }
      }
    } catch (error) {
      console.error('Error fetching PG partners:', error)
      toast.error('Failed to load payment gateways')
      setPgPartners([])
    } finally {
      setLoadingPartners(false)
    }
  }

  const handlePayout = async (e) => {
    e.preventDefault()
    
    if (!selectedBank) {
      toast.error('Please select a bank account')
      return
    }
    
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }
    
    if (!tpin || tpin.length !== 6) {
      toast.error('Please enter a valid 6-digit TPIN')
      return
    }
    
    setLoading(true)
    
    try {
      const response = await adminAPI.personalPayout({
        bank_id: selectedBank,
        amount: parseFloat(amount),
        tpin: tpin,
        pg_partner: pgPartner  // Use selected payment gateway
      })
      
      if (response.success) {
        toast.success('Payout processed successfully!')
        // Reset form
        setSelectedBank('')
        setAmount('')
        setTpin('')
      } else {
        toast.error(response.message || 'Payout failed')
      }
    } catch (error) {
      toast.error(error.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setSelectedBank('')
    setAmount('')
    setTpin('')
    setSearchQuery('')
    setFilteredBanks(banks)
    // Reset to first available partner
    if (pgPartners.length > 0) {
      setPgPartner(pgPartners[0].value)
    }
    toast.info('Form reset')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Wallet className="h-8 w-8 text-purple-600" />
        <h1 className="text-3xl font-bold">Personal Payout</h1>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handlePayout} className="space-y-6">
            {/* Search Bar */}
            <div>
              <Label className="text-base font-medium mb-2 block">Search Bank Account</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search by bank name, account holder, or account number..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="h-12 text-base pl-10"
                />
              </div>
              {searchQuery && (
                <p className="text-sm text-gray-600 mt-1">
                  Found {filteredBanks.length} account{filteredBanks.length !== 1 ? 's' : ''}
                </p>
              )}
            </div>

            {/* First Row - Bank Account and Amount */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label className="text-base font-medium mb-2 block">Select Bank Account</Label>
                <select
                  value={selectedBank}
                  onChange={(e) => setSelectedBank(e.target.value)}
                  className="flex h-12 w-full rounded-md border-2 border-gray-300 bg-white px-4 py-2 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                >
                  <option value="">Select Bank Account</option>
                  {filteredBanks.map((bank) => (
                    <option key={bank.id} value={bank.id}>
                      {bank.bank_name} - {bank.account_holder_name} - {bank.account_number.slice(-4).padStart(bank.account_number.length, '*')}
                    </option>
                  ))}
                </select>
                {filteredBanks.length === 0 && searchQuery && (
                  <p className="text-sm text-red-600 mt-1">
                    No bank accounts found matching your search
                  </p>
                )}
              </div>
              <div>
                <Label className="text-base font-medium mb-2 block">Amount</Label>
                <Input
                  type="number"
                  placeholder="Enter amount"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="h-12 text-base"
                  required
                  min="1"
                  step="0.01"
                />
              </div>

              <div>
                <Label className="text-base font-medium mb-2 block">Payment Gateway</Label>
                <select
                  value={pgPartner}
                  onChange={(e) => setPgPartner(e.target.value)}
                  className="flex h-12 w-full rounded-md border-2 border-gray-300 bg-white px-4 py-2 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                  disabled={loadingPartners || pgPartners.length === 0}
                >
                  {loadingPartners ? (
                    <option value="">Loading payment gateways...</option>
                  ) : pgPartners.length === 0 ? (
                    <option value="">No payment gateways configured</option>
                  ) : (
                    <>
                      <option value="">Select Payment Gateway</option>
                      {pgPartners.map((partner) => (
                        <option key={partner.value} value={partner.value}>
                          {partner.label}
                        </option>
                      ))}
                    </>
                  )}
                </select>
                {!loadingPartners && pgPartners.length === 0 && (
                  <p className="text-xs text-red-600 mt-1">
                    Please configure payout service routing in Settings
                  </p>
                )}
              </div>

              <div>
                <Label className="text-base font-medium mb-2 block">TPIN</Label>
                <div className="relative">
                  <Input
                    type={showTpin ? 'text' : 'password'}
                    placeholder="Enter 6-digit TPIN"
                    value={tpin}
                    onChange={(e) => setTpin(e.target.value)}
                    className="h-12 text-base pr-12"
                    required
                    maxLength="6"
                    pattern="[0-9]{6}"
                  />
                  <button
                    type="button"
                    onClick={() => setShowTpin(!showTpin)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                  >
                    {showTpin ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-4 pt-4">
              <Button
                type="submit"
                disabled={loading}
                className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white px-8 h-11"
              >
                {loading ? 'Processing...' : 'Process Payout'}
              </Button>
              <Button
                type="button"
                onClick={handleReset}
                variant="outline"
                className="bg-gray-400 hover:bg-gray-500 text-white px-8 h-11 border-0"
              >
                Reset
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Information Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h3 className="font-semibold text-blue-900 mb-2">Important Information</h3>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Payout charges will be deducted as per your scheme</li>
            <li>Ensure sufficient balance in your wallet</li>
            <li>TPIN is required for security verification</li>
            <li>Transaction will be processed through the selected payment gateway</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
