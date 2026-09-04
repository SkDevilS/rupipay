import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { CreditCard, ChevronDown, ChevronUp, Save, Trash2, Plus } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'

// Default charge templates
const DEFAULT_PAYOUT_CHARGES = [
  { productName: 'PAYOUT 100-1000', minAmount: 100, maxAmount: 1000, chargeValue: 1.5, chargeType: 'PERCENTAGE' },
  { productName: 'PAYOUT 1001-25000', minAmount: 1001, maxAmount: 25000, chargeValue: 1.5, chargeType: 'PERCENTAGE' },
  { productName: 'PAYOUT 25001-50000', minAmount: 25001, maxAmount: 50000, chargeValue: 1.5, chargeType: 'PERCENTAGE' },
  { productName: 'PAYOUT 50001-200000', minAmount: 50001, maxAmount: 200000, chargeValue: 1.5, chargeType: 'PERCENTAGE' },
]

const DEFAULT_PAYIN_CHARGES = [
  { productName: 'PAYIN 100-500', minAmount: 100, maxAmount: 500, chargeValue: 3.5, chargeType: 'PERCENTAGE' },
  { productName: 'PAYIN 501-1000', minAmount: 501, maxAmount: 1000, chargeValue: 3.5, chargeType: 'PERCENTAGE' },
  { productName: 'PAYIN 1001-25000', minAmount: 1001, maxAmount: 25000, chargeValue: 3.5, chargeType: 'PERCENTAGE' },
  { productName: 'PAYIN 25001-50000', minAmount: 25001, maxAmount: 50000, chargeValue: 3.5, chargeType: 'PERCENTAGE' },
  { productName: 'PAYIN 50001-200000', minAmount: 50001, maxAmount: 200000, chargeValue: 3.5, chargeType: 'PERCENTAGE' },
]

export default function Commercials() {
  const [activeTab, setActiveTab] = useState('update')
  const [schemes, setSchemes] = useState([])
  const [selectedSchemeId, setSelectedSchemeId] = useState(null)
  const [payoutCharges, setPayoutCharges] = useState([])
  const [payinCharges, setPayinCharges] = useState([])
  const [payoutOpen, setPayoutOpen] = useState(true)
  const [paymentGatewayOpen, setPaymentGatewayOpen] = useState(true)
  const [schemeName, setSchemeName] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // Load schemes on mount
  useEffect(() => {
    loadSchemes()
  }, [])

  // Load charges when scheme is selected
  useEffect(() => {
    if (selectedSchemeId) {
      loadSchemeCharges(selectedSchemeId)
    }
  }, [selectedSchemeId])

  const loadSchemes = async () => {
    try {
      setLoading(true)
      const response = await adminAPI.getSchemes()
      if (response.success) {
        setSchemes(response.schemes)
        if (response.schemes.length > 0 && !selectedSchemeId) {
          setSelectedSchemeId(response.schemes[0].id)
        }
      }
    } catch (error) {
      toast.error(error.message || 'Failed to load schemes')
    } finally {
      setLoading(false)
    }
  }

  const loadSchemeCharges = async (schemeId) => {
    try {
      setLoading(true)
      const response = await adminAPI.getSchemeCharges(schemeId)
      if (response.success) {
        // Set charges or use defaults if empty
        setPayoutCharges(
          response.charges.payout.length > 0 
            ? response.charges.payout.map(c => ({
                id: c.id,
                productName: c.product_name,
                minAmount: parseFloat(c.min_amount),
                maxAmount: parseFloat(c.max_amount),
                chargeValue: parseFloat(c.charge_value),
                chargeType: c.charge_type
              }))
            : DEFAULT_PAYOUT_CHARGES
        )
        setPayinCharges(
          response.charges.payin.length > 0
            ? response.charges.payin.map(c => ({
                id: c.id,
                productName: c.product_name,
                minAmount: parseFloat(c.min_amount),
                maxAmount: parseFloat(c.max_amount),
                chargeValue: parseFloat(c.charge_value),
                chargeType: c.charge_type
              }))
            : DEFAULT_PAYIN_CHARGES
        )
      }
    } catch (error) {
      toast.error(error.message || 'Failed to load charges')
      // Set defaults on error
      setPayoutCharges(DEFAULT_PAYOUT_CHARGES)
      setPayinCharges(DEFAULT_PAYIN_CHARGES)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateScheme = async () => {
    if (!schemeName.trim()) {
      toast.error('Please enter scheme name')
      return
    }

    try {
      setSaving(true)
      const response = await adminAPI.createScheme(schemeName.trim())
      if (response.success) {
        toast.success(`Scheme "${schemeName}" created successfully!`)
        setSchemeName('')
        await loadSchemes()
        setActiveTab('update')
        setSelectedSchemeId(response.schemeId)
      }
    } catch (error) {
      toast.error(error.message || 'Failed to create scheme')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveCharges = async () => {
    if (!selectedSchemeId) {
      toast.error('Please select a scheme')
      return
    }

    try {
      setSaving(true)
      
      // Prepare charges data
      const charges = [
        ...payoutCharges.map(c => ({
          serviceType: 'PAYOUT',
          productName: c.productName,
          minAmount: c.minAmount,
          maxAmount: c.maxAmount,
          chargeValue: c.chargeValue,
          chargeType: c.chargeType
        })),
        ...payinCharges.map(c => ({
          serviceType: 'PAYIN',
          productName: c.productName,
          minAmount: c.minAmount,
          maxAmount: c.maxAmount,
          chargeValue: c.chargeValue,
          chargeType: c.chargeType
        }))
      ]

      const response = await adminAPI.updateCharges(selectedSchemeId, charges)
      if (response.success) {
        toast.success('Charges saved successfully!')
        await loadSchemeCharges(selectedSchemeId)
      }
    } catch (error) {
      toast.error(error.message || 'Failed to save charges')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteScheme = async () => {
    if (!selectedSchemeId) {
      toast.error('Please select a scheme')
      return
    }

    const selectedScheme = schemes.find(s => s.id === selectedSchemeId)
    if (!selectedScheme) return

    if (!confirm(`Are you sure you want to delete scheme "${selectedScheme.scheme_name}"? This will also delete all associated charges.`)) {
      return
    }

    try {
      setSaving(true)
      const response = await adminAPI.deleteScheme(selectedSchemeId)
      if (response.success) {
        toast.success('Scheme deleted successfully!')
        await loadSchemes()
        setSelectedSchemeId(null)
        setPayoutCharges([])
        setPayinCharges([])
      }
    } catch (error) {
      toast.error(error.message || 'Failed to delete scheme')
    } finally {
      setSaving(false)
    }
  }

  const updatePayoutCharge = (index, field, value) => {
    const updated = [...payoutCharges]
    updated[index] = { ...updated[index], [field]: value }
    setPayoutCharges(updated)
  }

  const updatePayinCharge = (index, field, value) => {
    const updated = [...payinCharges]
    updated[index] = { ...updated[index], [field]: value }
    setPayinCharges(updated)
  }

  const addPayoutCharge = () => {
    setPayoutCharges([...payoutCharges, {
      productName: `PAYOUT ${payoutCharges.length + 1}`,
      minAmount: 0,
      maxAmount: 0,
      chargeValue: 0,
      chargeType: 'PERCENTAGE'
    }])
  }

  const addPayinCharge = () => {
    setPayinCharges([...payinCharges, {
      productName: `PAYIN ${payinCharges.length + 1}`,
      minAmount: 0,
      maxAmount: 0,
      chargeValue: 0,
      chargeType: 'PERCENTAGE'
    }])
  }

  const removePayoutCharge = (index) => {
    setPayoutCharges(payoutCharges.filter((_, i) => i !== index))
  }

  const removePayinCharge = (index) => {
    setPayinCharges(payinCharges.filter((_, i) => i !== index))
  }

  const handleReset = () => {
    setSchemeName('')
    toast.info('Form reset')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <CreditCard className="h-8 w-8 text-orange-600" />
        <h1 className="text-3xl font-bold">Commercials</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('update')}
          className={`px-6 py-3 font-medium transition-colors relative ${
            activeTab === 'update'
              ? 'text-red-600 border-b-2 border-red-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Update Scheme
        </button>
        <button
          onClick={() => setActiveTab('add')}
          className={`px-6 py-3 font-medium transition-colors relative ${
            activeTab === 'add'
              ? 'text-red-600 border-b-2 border-red-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Add Scheme
        </button>
      </div>

      {/* Update Scheme Tab */}
      {activeTab === 'update' && (
        <div className="space-y-4">
          {/* Select Scheme */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <Label className="text-base font-medium mb-2 block">Select Scheme</Label>
                  <select
                    value={selectedSchemeId || ''}
                    onChange={(e) => setSelectedSchemeId(parseInt(e.target.value))}
                    disabled={loading || schemes.length === 0}
                    className="flex h-12 w-full rounded-md border-2 border-gray-300 bg-white px-4 py-2 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  >
                    {schemes.length === 0 ? (
                      <option value="">No schemes available</option>
                    ) : (
                      schemes.map(scheme => (
                        <option key={scheme.id} value={scheme.id}>
                          {scheme.scheme_name}
                        </option>
                      ))
                    )}
                  </select>
                </div>
                <Button
                  onClick={handleDeleteScheme}
                  disabled={!selectedSchemeId || saving}
                  variant="outline"
                  className="bg-red-500 hover:bg-red-600 text-white border-0 h-12 px-6"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Scheme
                </Button>
              </div>
            </CardContent>
          </Card>

          {selectedSchemeId && (
            <>
              {/* Payout Collapsible Section */}
              <div className="border-2 border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => setPayoutOpen(!payoutOpen)}
                  className="flex items-center justify-between w-full p-4 bg-blue-100 hover:bg-blue-200 transition-colors"
                >
                  <span className="font-semibold text-gray-800 text-lg">Payout</span>
                  {payoutOpen ? (
                    <ChevronUp className="h-5 w-5 text-gray-600" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-600" />
                  )}
                </button>

                {payoutOpen && (
                  <div className="p-4 bg-white">
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>SR / NO</TableHead>
                            <TableHead>PRODUCT NAME</TableHead>
                            <TableHead>MIN AMOUNT</TableHead>
                            <TableHead>MAX AMOUNT</TableHead>
                            <TableHead>CHARGE VALUE</TableHead>
                            <TableHead>CHARGE TYPE</TableHead>
                            <TableHead>ACTION</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {payoutCharges.map((item, index) => (
                            <TableRow key={index}>
                              <TableCell>{index + 1}</TableCell>
                              <TableCell>
                                <Input
                                  type="text"
                                  value={item.productName}
                                  onChange={(e) => updatePayoutCharge(index, 'productName', e.target.value)}
                                  className="w-48 h-9"
                                />
                              </TableCell>
                              <TableCell>
                                <Input
                                  type="number"
                                  value={item.minAmount}
                                  onChange={(e) => updatePayoutCharge(index, 'minAmount', parseFloat(e.target.value) || 0)}
                                  className="w-32 h-9"
                                />
                              </TableCell>
                              <TableCell>
                                <Input
                                  type="number"
                                  value={item.maxAmount}
                                  onChange={(e) => updatePayoutCharge(index, 'maxAmount', parseFloat(e.target.value) || 0)}
                                  className="w-32 h-9"
                                />
                              </TableCell>
                              <TableCell>
                                <Input
                                  type="number"
                                  step="0.01"
                                  value={item.chargeValue}
                                  onChange={(e) => updatePayoutCharge(index, 'chargeValue', parseFloat(e.target.value) || 0)}
                                  className="w-32 h-9"
                                />
                              </TableCell>
                              <TableCell>
                                <select
                                  value={item.chargeType}
                                  onChange={(e) => updatePayoutCharge(index, 'chargeType', e.target.value)}
                                  className="flex h-9 w-full rounded-md border border-gray-300 bg-white px-3 py-1 text-sm"
                                >
                                  <option value="PERCENTAGE">% Percentage</option>
                                  <option value="FIXED">Fixed</option>
                                </select>
                              </TableCell>
                              <TableCell>
                                <Button
                                  onClick={() => removePayoutCharge(index)}
                                  variant="outline"
                                  size="sm"
                                  className="text-red-600 hover:text-red-700"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <Button
                      onClick={addPayoutCharge}
                      variant="outline"
                      className="mt-4"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add Payout Charge
                    </Button>
                  </div>
                )}
              </div>

              {/* Payment Gateway Collapsible Section */}
              <div className="border-2 border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => setPaymentGatewayOpen(!paymentGatewayOpen)}
                  className="flex items-center justify-between w-full p-4 bg-blue-100 hover:bg-blue-200 transition-colors"
                >
                  <span className="font-semibold text-gray-800 text-lg">Payment Gateway (Payin)</span>
                  {paymentGatewayOpen ? (
                    <ChevronUp className="h-5 w-5 text-gray-600" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-600" />
                  )}
                </button>

                {paymentGatewayOpen && (
                  <div className="p-4 bg-white">
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>SR / NO</TableHead>
                            <TableHead>PRODUCT NAME</TableHead>
                            <TableHead>MIN AMOUNT</TableHead>
                            <TableHead>MAX AMOUNT</TableHead>
                            <TableHead>CHARGE VALUE</TableHead>
                            <TableHead>CHARGE TYPE</TableHead>
                            <TableHead>ACTION</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {payinCharges.map((item, index) => (
                            <TableRow key={index}>
                              <TableCell>{index + 1}</TableCell>
                              <TableCell>
                                <Input
                                  type="text"
                                  value={item.productName}
                                  onChange={(e) => updatePayinCharge(index, 'productName', e.target.value)}
                                  className="w-48 h-9"
                                />
                              </TableCell>
                              <TableCell>
                                <Input
                                  type="number"
                                  value={item.minAmount}
                                  onChange={(e) => updatePayinCharge(index, 'minAmount', parseFloat(e.target.value) || 0)}
                                  className="w-32 h-9"
                                />
                              </TableCell>
                              <TableCell>
                                <Input
                                  type="number"
                                  value={item.maxAmount}
                                  onChange={(e) => updatePayinCharge(index, 'maxAmount', parseFloat(e.target.value) || 0)}
                                  className="w-32 h-9"
                                />
                              </TableCell>
                              <TableCell>
                                <Input
                                  type="number"
                                  step="0.01"
                                  value={item.chargeValue}
                                  onChange={(e) => updatePayinCharge(index, 'chargeValue', parseFloat(e.target.value) || 0)}
                                  className="w-32 h-9"
                                />
                              </TableCell>
                              <TableCell>
                                <select
                                  value={item.chargeType}
                                  onChange={(e) => updatePayinCharge(index, 'chargeType', e.target.value)}
                                  className="flex h-9 w-full rounded-md border border-gray-300 bg-white px-3 py-1 text-sm"
                                >
                                  <option value="PERCENTAGE">% Percentage</option>
                                  <option value="FIXED">Fixed</option>
                                </select>
                              </TableCell>
                              <TableCell>
                                <Button
                                  onClick={() => removePayinCharge(index)}
                                  variant="outline"
                                  size="sm"
                                  className="text-red-600 hover:text-red-700"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <Button
                      onClick={addPayinCharge}
                      variant="outline"
                      className="mt-4"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add Payin Charge
                    </Button>
                  </div>
                )}
              </div>

              {/* Save Button */}
              <div className="flex justify-end">
                <Button
                  onClick={handleSaveCharges}
                  disabled={saving}
                  className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white px-8 h-11"
                >
                  <Save className="h-4 w-4 mr-2" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Add Scheme Tab */}
      {activeTab === 'add' && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-6">
              <div>
                <Label className="text-base font-medium mb-2 block">Enter Scheme name*</Label>
                <Input
                  type="text"
                  placeholder="Enter Scheme name"
                  value={schemeName}
                  onChange={(e) => setSchemeName(e.target.value)}
                  className="h-12 text-base"
                />
              </div>

              <div className="flex gap-4">
                <Button
                  onClick={handleCreateScheme}
                  disabled={saving}
                  className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white px-8 h-11"
                >
                  {saving ? 'Creating...' : 'Create Scheme'}
                </Button>
                <Button
                  onClick={handleReset}
                  variant="outline"
                  className="bg-gray-400 hover:bg-gray-500 text-white px-8 h-11 border-0"
                >
                  Reset
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
