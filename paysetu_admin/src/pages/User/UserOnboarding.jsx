import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { UserPlus, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'

export default function UserOnboarding() {
  const [currentStep, setCurrentStep] = useState(1)
  const [schemes, setSchemes] = useState([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [formData, setFormData] = useState({
    // Step 1: User Details
    fullName: '',
    email: '',
    mobile: '',
    dob: '',
    aadharCard: '',
    panNo: '',
    pincode: '',
    state: '',
    city: '',
    houseNumber: '',
    address: '',
    landmark: '',
    // Step 2: Organization Details
    merchantType: 'PAYIN',
    accountNum: '',
    ifscCode: '',
    gstNo: '',
    // Step 3: Document Upload
    aadharFront: null,
    aadharBack: null,
    panCard: null,
    gstCertificate: null,
    shopPhoto: null,
    profilePhoto: null,
    schemeId: '',
  })

  useEffect(() => {
    loadSchemes()
  }, [])

  const loadSchemes = async () => {
    try {
      setLoading(true)
      const response = await adminAPI.getSchemes()
      if (response.success) {
        setSchemes(response.schemes.filter(s => s.is_active))
      }
    } catch (error) {
      toast.error('Failed to load schemes')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Validate all required fields
    if (!formData.fullName || !formData.email || !formData.mobile || !formData.aadharCard || 
        !formData.panNo || !formData.pincode || !formData.state || !formData.city || 
        !formData.address || !formData.accountNum || !formData.ifscCode || !formData.gstNo || 
        !formData.schemeId) {
      toast.error('Please fill all required fields')
      return
    }

    if (!formData.aadharFront || !formData.aadharBack || !formData.panCard || 
        !formData.gstCertificate || !formData.shopPhoto || !formData.profilePhoto) {
      toast.error('Please upload all required documents')
      return
    }

    try {
      setSubmitting(true)
      
      // Create FormData for file upload
      const submitData = new FormData()
      
      // Append all text fields
      Object.keys(formData).forEach(key => {
        if (formData[key] !== null && formData[key] !== '' && !(formData[key] instanceof File)) {
          submitData.append(key, formData[key])
        }
      })
      
      // Append files
      if (formData.aadharFront) submitData.append('aadharFront', formData.aadharFront)
      if (formData.aadharBack) submitData.append('aadharBack', formData.aadharBack)
      if (formData.panCard) submitData.append('panCard', formData.panCard)
      if (formData.gstCertificate) submitData.append('gstCertificate', formData.gstCertificate)
      if (formData.shopPhoto) submitData.append('shopPhoto', formData.shopPhoto)
      if (formData.profilePhoto) submitData.append('profilePhoto', formData.profilePhoto)
      
      const response = await adminAPI.onboardMerchant(submitData)
      
      if (response.success) {
        toast.success(`Merchant onboarded successfully! Merchant ID: ${response.merchantId}`)
        if (response.emailSent) {
          toast.success('Credentials sent to merchant email')
        } else {
          toast.warning('Failed to send email. Please share credentials manually.')
        }
        
        // Reset form
        setFormData({
          fullName: '',
          email: '',
          mobile: '',
          dob: '',
          aadharCard: '',
          panNo: '',
          pincode: '',
          state: '',
          city: '',
          houseNumber: '',
          address: '',
          landmark: '',
          merchantType: 'PAYIN',
          accountNum: '',
          ifscCode: '',
          gstNo: '',
          aadharFront: null,
          aadharBack: null,
          panCard: null,
          gstCertificate: null,
          shopPhoto: null,
          profilePhoto: null,
          schemeId: '',
        })
        setCurrentStep(1)
      }
    } catch (error) {
      toast.error(error.message || 'Failed to onboard merchant')
    } finally {
      setSubmitting(false)
    }
  }

  const steps = [
    { number: 1, title: 'User Details' },
    { number: 2, title: 'Org. Details' },
    { number: 3, title: 'Document Upload' },
  ]

  const canProceedToStep2 = () => {
    return formData.fullName && formData.email && formData.mobile && formData.aadharCard && 
           formData.panNo && formData.pincode && formData.state && formData.city && formData.address
  }

  const canProceedToStep3 = () => {
    return formData.merchantType && formData.accountNum && formData.ifscCode && formData.gstNo
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <UserPlus className="h-8 w-8 text-orange-600" />
          <h1 className="text-3xl font-bold">Add Wallet User</h1>
        </div>
      </div>

      {/* Steps Indicator */}
      <div className="flex items-center justify-center gap-8">
        {steps.map((step, index) => (
          <div key={step.number} className="flex items-center gap-2">
            <div className="flex flex-col items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                  currentStep === step.number
                    ? 'bg-gradient-to-r from-orange-500 to-yellow-400 text-white'
                    : currentStep > step.number
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-300 text-gray-600'
                }`}
              >
                {step.number}
              </div>
              <p className="text-sm mt-2 font-medium">{step.title}</p>
            </div>
            {index < steps.length - 1 && (
              <div className="w-24 h-0.5 bg-gray-300 mb-6"></div>
            )}
          </div>
        ))}
      </div>

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle>
            {currentStep === 1 && 'Basic Details :'}
            {currentStep === 2 && 'Organization Details :'}
            {currentStep === 3 && 'Document Upload :'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Step 1: User Details */}
            {currentStep === 1 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label>Merchant Name *</Label>
                  <Input
                    value={formData.fullName}
                    onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                    placeholder="Enter merchant name"
                    required
                  />
                </div>
                <div>
                  <Label>Email *</Label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="m@example.com"
                    required
                  />
                </div>
                <div>
                  <Label>Mobile Number *</Label>
                  <Input
                    value={formData.mobile}
                    onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                    placeholder="Enter mobile number"
                    maxLength={10}
                    required
                  />
                </div>
                <div>
                  <Label>Date of Birth</Label>
                  <Input
                    type="date"
                    value={formData.dob}
                    onChange={(e) => setFormData({ ...formData, dob: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Aadhar Card No *</Label>
                  <Input
                    value={formData.aadharCard}
                    onChange={(e) => setFormData({ ...formData, aadharCard: e.target.value })}
                    placeholder="Enter Aadhar Card No"
                    maxLength={12}
                    required
                  />
                </div>
                <div>
                  <Label>Pan No *</Label>
                  <Input
                    value={formData.panNo}
                    onChange={(e) => setFormData({ ...formData, panNo: e.target.value.toUpperCase() })}
                    placeholder="Enter Pan No"
                    maxLength={10}
                    required
                  />
                </div>
                <div>
                  <Label>Pincode *</Label>
                  <Input
                    value={formData.pincode}
                    onChange={(e) => setFormData({ ...formData, pincode: e.target.value })}
                    placeholder="Enter Pincode"
                    maxLength={6}
                    required
                  />
                </div>
                <div>
                  <Label>State *</Label>
                  <select
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    required
                  >
                    <option value="">--Select State--</option>
                    <option value="Andhra Pradesh">Andhra Pradesh</option>
                    <option value="Arunachal Pradesh">Arunachal Pradesh</option>
                    <option value="Assam">Assam</option>
                    <option value="Bihar">Bihar</option>
                    <option value="Chhattisgarh">Chhattisgarh</option>
                    <option value="Goa">Goa</option>
                    <option value="Gujarat">Gujarat</option>
                    <option value="Haryana">Haryana</option>
                    <option value="Himachal Pradesh">Himachal Pradesh</option>
                    <option value="Jharkhand">Jharkhand</option>
                    <option value="Karnataka">Karnataka</option>
                    <option value="Kerala">Kerala</option>
                    <option value="Madhya Pradesh">Madhya Pradesh</option>
                    <option value="Maharashtra">Maharashtra</option>
                    <option value="Manipur">Manipur</option>
                    <option value="Meghalaya">Meghalaya</option>
                    <option value="Mizoram">Mizoram</option>
                    <option value="Nagaland">Nagaland</option>
                    <option value="Odisha">Odisha</option>
                    <option value="Punjab">Punjab</option>
                    <option value="Rajasthan">Rajasthan</option>
                    <option value="Sikkim">Sikkim</option>
                    <option value="Tamil Nadu">Tamil Nadu</option>
                    <option value="Telangana">Telangana</option>
                    <option value="Tripura">Tripura</option>
                    <option value="Uttar Pradesh">Uttar Pradesh</option>
                    <option value="Uttarakhand">Uttarakhand</option>
                    <option value="West Bengal">West Bengal</option>
                    <option value="Delhi">Delhi</option>
                  </select>
                </div>
                <div>
                  <Label>City *</Label>
                  <Input
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="Enter city"
                    required
                  />
                </div>
                <div>
                  <Label>House Number</Label>
                  <Input
                    value={formData.houseNumber}
                    onChange={(e) => setFormData({ ...formData, houseNumber: e.target.value })}
                    placeholder="House Number"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label>Address *</Label>
                  <Input
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    placeholder="Enter address"
                    required
                  />
                </div>
                <div className="md:col-span-3">
                  <Label>Landmark</Label>
                  <Input
                    value={formData.landmark}
                    onChange={(e) => setFormData({ ...formData, landmark: e.target.value })}
                    placeholder="Landmark"
                  />
                </div>
              </div>
            )}

            {/* Step 2: Org Details */}
            {currentStep === 2 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label>Merchant Type *</Label>
                  <select
                    value={formData.merchantType}
                    onChange={(e) => setFormData({ ...formData, merchantType: e.target.value })}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    required
                  >
                    <option value="PAYIN">Payin</option>
                    <option value="PAYOUT">Payout</option>
                    <option value="BOTH">Both</option>
                  </select>
                </div>
                <div>
                  <Label>Account Number *</Label>
                  <Input
                    value={formData.accountNum}
                    onChange={(e) => setFormData({ ...formData, accountNum: e.target.value })}
                    placeholder="Enter account number"
                    required
                  />
                </div>
                <div>
                  <Label>IFSC Code *</Label>
                  <Input
                    value={formData.ifscCode}
                    onChange={(e) => setFormData({ ...formData, ifscCode: e.target.value.toUpperCase() })}
                    placeholder="Enter IFSC code"
                    maxLength={11}
                    required
                  />
                </div>
                <div className="md:col-span-3">
                  <Label>GST Number *</Label>
                  <Input
                    value={formData.gstNo}
                    onChange={(e) => setFormData({ ...formData, gstNo: e.target.value.toUpperCase() })}
                    placeholder="Enter GST number"
                    maxLength={15}
                    required
                  />
                </div>
              </div>
            )}

            {/* Step 3: Document Upload */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label>Aadhar Card Front *</Label>
                    <Input
                      type="file"
                      accept="image/*,.pdf"
                      onChange={(e) => setFormData({ ...formData, aadharFront: e.target.files[0] })}
                      className="cursor-pointer"
                      required
                    />
                    {formData.aadharFront && (
                      <p className="text-xs text-green-600 mt-1">✓ {formData.aadharFront.name}</p>
                    )}
                  </div>
                  <div>
                    <Label>Aadhar Card Back *</Label>
                    <Input
                      type="file"
                      accept="image/*,.pdf"
                      onChange={(e) => setFormData({ ...formData, aadharBack: e.target.files[0] })}
                      className="cursor-pointer"
                      required
                    />
                    {formData.aadharBack && (
                      <p className="text-xs text-green-600 mt-1">✓ {formData.aadharBack.name}</p>
                    )}
                  </div>
                  <div>
                    <Label>PAN Card *</Label>
                    <Input
                      type="file"
                      accept="image/*,.pdf"
                      onChange={(e) => setFormData({ ...formData, panCard: e.target.files[0] })}
                      className="cursor-pointer"
                      required
                    />
                    {formData.panCard && (
                      <p className="text-xs text-green-600 mt-1">✓ {formData.panCard.name}</p>
                    )}
                  </div>
                  <div>
                    <Label>GST Certificate *</Label>
                    <Input
                      type="file"
                      accept="image/*,.pdf"
                      onChange={(e) => setFormData({ ...formData, gstCertificate: e.target.files[0] })}
                      className="cursor-pointer"
                      required
                    />
                    {formData.gstCertificate && (
                      <p className="text-xs text-green-600 mt-1">✓ {formData.gstCertificate.name}</p>
                    )}
                  </div>
                  <div>
                    <Label>Shop Photo *</Label>
                    <Input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setFormData({ ...formData, shopPhoto: e.target.files[0] })}
                      className="cursor-pointer"
                      required
                    />
                    {formData.shopPhoto && (
                      <p className="text-xs text-green-600 mt-1">✓ {formData.shopPhoto.name}</p>
                    )}
                  </div>
                  <div>
                    <Label>Profile Photo *</Label>
                    <Input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setFormData({ ...formData, profilePhoto: e.target.files[0] })}
                      className="cursor-pointer"
                      required
                    />
                    {formData.profilePhoto && (
                      <p className="text-xs text-green-600 mt-1">✓ {formData.profilePhoto.name}</p>
                    )}
                  </div>
                </div>

                {/* Scheme Selection */}
                <div className="border-t pt-6 mt-6">
                  <h3 className="text-lg font-semibold mb-4">Select Scheme</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label>Choose Scheme *</Label>
                      <select
                        value={formData.schemeId}
                        onChange={(e) => setFormData({ ...formData, schemeId: e.target.value })}
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                        required
                        disabled={loading || schemes.length === 0}
                      >
                        <option value="">--Select Scheme--</option>
                        {schemes.map(scheme => (
                          <option key={scheme.id} value={scheme.id}>
                            {scheme.scheme_name}
                          </option>
                        ))}
                      </select>
                      <p className="text-xs text-gray-500 mt-1">Select the appropriate scheme for this merchant</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex justify-between pt-6 border-t">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
                disabled={currentStep === 1 || submitting}
              >
                Previous
              </Button>
              {currentStep < 3 ? (
                <Button
                  type="button"
                  onClick={() => {
                    if (currentStep === 1 && !canProceedToStep2()) {
                      toast.error('Please fill all required fields')
                      return
                    }
                    if (currentStep === 2 && !canProceedToStep3()) {
                      toast.error('Please fill all required fields')
                      return
                    }
                    setCurrentStep(Math.min(3, currentStep + 1))
                  }}
                  className="bg-gradient-to-r from-orange-500 to-yellow-400 hover:from-orange-600 hover:to-yellow-500"
                >
                  Next
                </Button>
              ) : (
                <Button
                  type="submit"
                  disabled={submitting}
                  className="bg-gradient-to-r from-orange-500 to-yellow-400 hover:from-orange-600 hover:to-yellow-500"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    'Submit'
                  )}
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
