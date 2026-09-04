import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Briefcase, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

export default function ManageServices() {
  const [activeTab, setActiveTab] = useState('all')
  const [services, setServices] = useState({
    payin: false,
    payout: false,
    transferToBank: false,
  })
  const [selectedUser, setSelectedUser] = useState('')

  const handleCheckboxChange = (service) => {
    setServices(prev => ({
      ...prev,
      [service]: !prev[service]
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    
    const selectedServices = Object.entries(services)
      .filter(([_, enabled]) => enabled)
      .map(([service]) => service)
    
    if (selectedServices.length === 0) {
      toast.error('Please select at least one service')
      return
    }
    
    if (activeTab === 'selected' && !selectedUser) {
      toast.error('Please select a user')
      return
    }
    
    const message = activeTab === 'selected' 
      ? `Services updated for ${selectedUser}!`
      : 'Services updated for all users!'
    
    toast.success(message)
  }

  const handleReload = () => {
    setServices({
      payin: false,
      payout: false,
      transferToBank: false,
    })
    toast.info('Services reloaded')
  }

  const handleSelectUser = () => {
    if (!selectedUser) {
      toast.error('Please select a user')
      return
    }
    toast.success(`User ${selectedUser} selected successfully!`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Briefcase className="h-8 w-8 text-orange-600" />
        <h1 className="text-3xl font-bold">Activate / Inactive Services</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-6 py-3 font-medium transition-colors relative ${
            activeTab === 'all'
              ? 'text-red-600 border-b-2 border-red-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          All User
        </button>
        <button
          onClick={() => setActiveTab('selected')}
          className={`px-6 py-3 font-medium transition-colors relative ${
            activeTab === 'selected'
              ? 'text-red-600 border-b-2 border-red-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Selected User
        </button>
      </div>

      {/* All User Tab Content */}
      {activeTab === 'all' && (
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Services Checkboxes in a Row */}
              <div className="flex items-center gap-12">
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="payin"
                    checked={services.payin}
                    onCheckedChange={() => handleCheckboxChange('payin')}
                  />
                  <label
                    htmlFor="payin"
                    className="text-base font-medium leading-none cursor-pointer select-none"
                  >
                    Payin
                  </label>
                </div>

                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="payout"
                    checked={services.payout}
                    onCheckedChange={() => handleCheckboxChange('payout')}
                  />
                  <label
                    htmlFor="payout"
                    className="text-base font-medium leading-none cursor-pointer select-none"
                  >
                    PayOut
                  </label>
                </div>

                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="transferToBank"
                    checked={services.transferToBank}
                    onCheckedChange={() => handleCheckboxChange('transferToBank')}
                  />
                  <label
                    htmlFor="transferToBank"
                    className="text-base font-medium leading-none cursor-pointer select-none"
                  >
                    Transfer to Bank
                  </label>
                </div>
              </div>

              {/* Buttons */}
              <div className="flex gap-4">
                <Button
                  type="submit"
                  className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white px-8 h-11"
                >
                  Submit
                </Button>
                <Button
                  type="button"
                  onClick={handleReload}
                  variant="outline"
                  className="bg-gray-400 hover:bg-gray-500 text-white px-8 h-11 border-0"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Reload
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Selected User Tab Content */}
      {activeTab === 'selected' && (
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Select Search User */}
              <div>
                <Label className="text-base font-medium mb-2 block">Select Search User</Label>
                <select
                  value={selectedUser}
                  onChange={(e) => setSelectedUser(e.target.value)}
                  className="flex h-12 w-full rounded-md border-2 border-gray-300 bg-white px-4 py-2 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select User</option>
                  <option value="user1">ABC Enterprises</option>
                  <option value="user2">XYZ Solutions</option>
                  <option value="user3">Tech Corp</option>
                  <option value="user4">Digital Services</option>
                  <option value="user5">Paymique Studios</option>
                </select>
              </div>

              {/* Show services checkboxes only when user is selected */}
              {selectedUser && (
                <>
                  {/* Services Checkboxes in a Row */}
                  <div className="flex items-center gap-12">
                    <div className="flex items-center space-x-3">
                      <Checkbox
                        id="payin-selected"
                        checked={services.payin}
                        onCheckedChange={() => handleCheckboxChange('payin')}
                      />
                      <label
                        htmlFor="payin-selected"
                        className="text-base font-medium leading-none cursor-pointer select-none"
                      >
                        Payin
                      </label>
                    </div>

                    <div className="flex items-center space-x-3">
                      <Checkbox
                        id="payout-selected"
                        checked={services.payout}
                        onCheckedChange={() => handleCheckboxChange('payout')}
                      />
                      <label
                        htmlFor="payout-selected"
                        className="text-base font-medium leading-none cursor-pointer select-none"
                      >
                        PayOut
                      </label>
                    </div>

                    <div className="flex items-center space-x-3">
                      <Checkbox
                        id="transferToBank-selected"
                        checked={services.transferToBank}
                        onCheckedChange={() => handleCheckboxChange('transferToBank')}
                      />
                      <label
                        htmlFor="transferToBank-selected"
                        className="text-base font-medium leading-none cursor-pointer select-none"
                      >
                        Transfer to Bank
                      </label>
                    </div>
                  </div>

                  {/* Update Button */}
                  <div className="flex gap-4">
                    <Button
                      type="submit"
                      className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white px-8 h-11"
                    >
                      Update
                    </Button>
                    <Button
                      type="button"
                      onClick={handleReload}
                      variant="outline"
                      className="bg-gray-400 hover:bg-gray-500 text-white px-8 h-11 border-0"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Reload
                    </Button>
                  </div>
                </>
              )}
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
