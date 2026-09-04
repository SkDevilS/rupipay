import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { 
  Shield, 
  Plus, 
  Trash2, 
  Search, 
  AlertCircle, 
  CheckCircle, 
  XCircle,
  Eye,
  Power,
  PowerOff
} from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'
import { formatDateTime } from '@/lib/utils'

export default function IPSecurity() {
  const [merchants, setMerchants] = useState([])
  const [selectedMerchant, setSelectedMerchant] = useState(null)
  const [ipList, setIpList] = useState([])
  const [logs, setLogs] = useState([])
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 20,
    total_records: 0,
    total_pages: 0,
    has_next: false,
    has_prev: false
  })
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newIP, setNewIP] = useState({ ip_address: '', description: '' })

  useEffect(() => {
    loadMerchants()
  }, [])

  const loadMerchants = async () => {
    try {
      setLoading(true)
      const response = await adminAPI.getIPSecurityMerchants()
      if (response.success) {
        setMerchants(response.merchants || [])
      }
    } catch (error) {
      console.error('Error loading merchants:', error)
      toast.error('Failed to load merchants')
    } finally {
      setLoading(false)
    }
  }

  const loadMerchantIPSecurity = async (merchantId, page = 1) => {
    try {
      setLoading(true)
      const response = await adminAPI.getMerchantIPSecurity(merchantId)
      if (response.success) {
        setSelectedMerchant(response.merchant)
        setIpList(response.ip_list || [])
        
        // Load logs with pagination
        const logsResponse = await adminAPI.getIPSecurityLogs({
          merchant_id: merchantId,
          page: page,
          per_page: 20
        })
        
        if (logsResponse.success) {
          setLogs(logsResponse.logs || [])
          setPagination(logsResponse.pagination || {
            page: 1,
            per_page: 20,
            total_records: 0,
            total_pages: 0,
            has_next: false,
            has_prev: false
          })
        }
      }
    } catch (error) {
      console.error('Error loading IP security:', error)
      toast.error('Failed to load IP security configuration')
    } finally {
      setLoading(false)
    }
  }
  
  const handlePageChange = (newPage) => {
    if (selectedMerchant) {
      loadMerchantIPSecurity(selectedMerchant.merchant_id, newPage)
    }
  }

  const handleAddIP = async () => {
    if (!newIP.ip_address.trim()) {
      toast.error('IP address is required')
      return
    }

    // Basic IP validation
    const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
    if (!ipPattern.test(newIP.ip_address)) {
      toast.error('Invalid IP address format')
      return
    }

    try {
      setLoading(true)
      const response = await adminAPI.addMerchantIP(selectedMerchant.merchant_id, newIP)
      if (response.success) {
        toast.success('IP address added successfully')
        setShowAddModal(false)
        setNewIP({ ip_address: '', description: '' })
        loadMerchantIPSecurity(selectedMerchant.merchant_id)
      }
    } catch (error) {
      console.error('Error adding IP:', error)
      toast.error(error.message || 'Failed to add IP address')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleIP = async (ipId, currentStatus) => {
    try {
      setLoading(true)
      const response = await adminAPI.updateMerchantIP(
        selectedMerchant.merchant_id,
        ipId,
        { is_active: !currentStatus }
      )
      if (response.success) {
        toast.success(`IP ${!currentStatus ? 'enabled' : 'disabled'} successfully`)
        loadMerchantIPSecurity(selectedMerchant.merchant_id)
      }
    } catch (error) {
      console.error('Error toggling IP:', error)
      toast.error('Failed to update IP status')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteIP = async (ipId) => {
    if (!confirm('Are you sure you want to delete this IP address?')) {
      return
    }

    try {
      setLoading(true)
      const response = await adminAPI.deleteMerchantIP(selectedMerchant.merchant_id, ipId)
      if (response.success) {
        toast.success('IP address deleted successfully')
        loadMerchantIPSecurity(selectedMerchant.merchant_id)
      }
    } catch (error) {
      console.error('Error deleting IP:', error)
      toast.error('Failed to delete IP address')
    } finally {
      setLoading(false)
    }
  }

  const filteredMerchants = merchants.filter(m =>
    m.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.merchant_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.email.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="h-8 w-8 text-blue-600" />
            IP Security Management
          </h1>
          <p className="text-gray-600 mt-1">
            Configure IP whitelisting for merchant payout operations
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Merchant List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Select Merchant</CardTitle>
            <CardDescription>Choose a merchant to configure IP security</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search merchants..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>

              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {filteredMerchants.map((merchant) => (
                  <div
                    key={merchant.merchant_id}
                    onClick={() => loadMerchantIPSecurity(merchant.merchant_id)}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedMerchant?.merchant_id === merchant.merchant_id
                        ? 'bg-blue-50 border-blue-500'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="font-medium">{merchant.full_name}</div>
                    <div className="text-sm text-gray-600">{merchant.merchant_id}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-500">
                        {merchant.ip_count} IP{merchant.ip_count !== 1 ? 's' : ''} configured
                      </span>
                      {merchant.is_active ? (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                          Active
                        </span>
                      ) : (
                        <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                          Inactive
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* IP Configuration */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>IP Whitelist Configuration</CardTitle>
                {selectedMerchant && (
                  <CardDescription>
                    Managing IPs for {selectedMerchant.full_name} ({selectedMerchant.merchant_id})
                  </CardDescription>
                )}
              </div>
              {selectedMerchant && (
                <Button onClick={() => setShowAddModal(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add IP
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedMerchant ? (
              <div className="text-center py-12 text-gray-500">
                <Shield className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>Select a merchant to configure IP security</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* IP List */}
                <div>
                  <h3 className="font-semibold mb-3">Whitelisted IP Addresses</h3>
                  {ipList.length === 0 ? (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                        <div>
                          <p className="font-medium text-yellow-800">No IP Restrictions</p>
                          <p className="text-sm text-yellow-700 mt-1">
                            This merchant has no IP whitelist configured. All IPs are currently allowed for payout operations.
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {ipList.map((ip) => (
                        <div
                          key={ip.id}
                          className="flex items-center justify-between p-4 border rounded-lg"
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-medium">{ip.ip_address}</span>
                              {ip.is_active ? (
                                <CheckCircle className="h-4 w-4 text-green-600" />
                              ) : (
                                <XCircle className="h-4 w-4 text-red-600" />
                              )}
                            </div>
                            {ip.description && (
                              <p className="text-sm text-gray-600 mt-1">{ip.description}</p>
                            )}
                            <p className="text-xs text-gray-500 mt-1">
                              Added by {ip.created_by} on {formatDateTime(ip.created_at)}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleToggleIP(ip.id, ip.is_active)}
                            >
                              {ip.is_active ? (
                                <PowerOff className="h-4 w-4" />
                              ) : (
                                <Power className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDeleteIP(ip.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Recent Logs */}
                <div>
                  <h3 className="font-semibold mb-3">Recent Activity Logs</h3>
                  <div className="border rounded-lg overflow-hidden">
                    <div className="max-h-[300px] overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr>
                            <th className="px-4 py-2 text-left">IP Address</th>
                            <th className="px-4 py-2 text-left">Endpoint</th>
                            <th className="px-4 py-2 text-left">Action</th>
                            <th className="px-4 py-2 text-left">Status</th>
                            <th className="px-4 py-2 text-left">Time</th>
                          </tr>
                        </thead>
                        <tbody>
                          {logs.length === 0 ? (
                            <tr>
                              <td colSpan="5" className="px-4 py-8 text-center text-gray-500">
                                No activity logs yet
                              </td>
                            </tr>
                          ) : (
                            logs.map((log, index) => (
                              <tr key={index} className="border-t">
                                <td className="px-4 py-2 font-mono text-xs">{log.ip_address}</td>
                                <td className="px-4 py-2 text-xs">{log.endpoint}</td>
                                <td className="px-4 py-2 text-xs">{log.action}</td>
                                <td className="px-4 py-2">
                                  <span
                                    className={`text-xs px-2 py-1 rounded ${
                                      log.status === 'ALLOWED'
                                        ? 'bg-green-100 text-green-700'
                                        : 'bg-red-100 text-red-700'
                                    }`}
                                  >
                                    {log.status}
                                  </span>
                                </td>
                                <td className="px-4 py-2 text-xs text-gray-600">
                                  {formatDateTime(log.created_at)}
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                    
                    {/* Pagination */}
                    {pagination.total_pages > 1 && (
                      <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
                        <div className="text-sm text-gray-600">
                          Showing {((pagination.page - 1) * pagination.per_page) + 1} to{' '}
                          {Math.min(pagination.page * pagination.per_page, pagination.total_records)} of{' '}
                          {pagination.total_records} logs
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handlePageChange(pagination.page - 1)}
                            disabled={!pagination.has_prev || loading}
                          >
                            Previous
                          </Button>
                          <div className="flex items-center gap-1">
                            {[...Array(pagination.total_pages)].map((_, i) => {
                              const pageNum = i + 1
                              // Show first page, last page, current page, and pages around current
                              if (
                                pageNum === 1 ||
                                pageNum === pagination.total_pages ||
                                (pageNum >= pagination.page - 1 && pageNum <= pagination.page + 1)
                              ) {
                                return (
                                  <Button
                                    key={pageNum}
                                    size="sm"
                                    variant={pageNum === pagination.page ? 'default' : 'outline'}
                                    onClick={() => handlePageChange(pageNum)}
                                    disabled={loading}
                                    className="w-8"
                                  >
                                    {pageNum}
                                  </Button>
                                )
                              } else if (
                                pageNum === pagination.page - 2 ||
                                pageNum === pagination.page + 2
                              ) {
                                return <span key={pageNum} className="px-1">...</span>
                              }
                              return null
                            })}
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handlePageChange(pagination.page + 1)}
                            disabled={!pagination.has_next || loading}
                          >
                            Next
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Add IP Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Add IP Address</CardTitle>
              <CardDescription>
                Add a new IP address to the whitelist for {selectedMerchant?.full_name}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="ip_address">IP Address *</Label>
                  <Input
                    id="ip_address"
                    placeholder="e.g., 192.168.1.100"
                    value={newIP.ip_address}
                    onChange={(e) => setNewIP({ ...newIP, ip_address: e.target.value })}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Enter IPv4 address in format: xxx.xxx.xxx.xxx
                  </p>
                </div>
                <div>
                  <Label htmlFor="description">Description (Optional)</Label>
                  <Textarea
                    id="description"
                    placeholder="e.g., Office network, Production server"
                    value={newIP.description}
                    onChange={(e) => setNewIP({ ...newIP, description: e.target.value })}
                    rows={3}
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowAddModal(false)
                      setNewIP({ ip_address: '', description: '' })
                    }}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleAddIP} disabled={loading}>
                    {loading ? 'Adding...' : 'Add IP'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
