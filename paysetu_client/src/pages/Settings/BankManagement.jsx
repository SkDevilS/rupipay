import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Building, Eye, EyeOff, RefreshCw, Trash2, ToggleLeft, ToggleRight } from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'

export default function BankManagement() {
  const [loading, setLoading] = useState(false)
  const [loadingBanks, setLoadingBanks] = useState(true)
  const [banks, setBanks] = useState([])
  
  // Form states
  const [bankName, setBankName] = useState('')
  const [accountNo, setAccountNo] = useState('')
  const [reAccountNo, setReAccountNo] = useState('')
  const [ifscCode, setIfscCode] = useState('')
  const [branchName, setBranchName] = useState('')
  const [accountHolderName, setAccountHolderName] = useState('')
  const [tpin, setTpin] = useState('')
  const [showTpin, setShowTpin] = useState(false)
  
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [deletingBank, setDeletingBank] = useState(null)
  const [deleteTpin, setDeleteTpin] = useState('')
  const [showDeleteTpin, setShowDeleteTpin] = useState(false)

  useEffect(() => {
    loadBanks()
  }, [])

  const loadBanks = async () => {
    try {
      setLoadingBanks(true)
      const response = await clientAPI.getBanks()
      if (response.success) {
        setBanks(response.banks || [])
      }
    } catch (error) {
      toast.error('Failed to load banks')
      console.error('Load banks error:', error)
    } finally {
      setLoadingBanks(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Check bank limit
    if (banks.length >= 5) {
      toast.error('Maximum 5 banks allowed')
      return
    }
    
    if (!bankName) {
      toast.error('Please select a bank name')
      return
    }
    
    if (!accountNo) {
      toast.error('Please enter account number')
      return
    }
    
    if (accountNo !== reAccountNo) {
      toast.error('Account numbers do not match')
      return
    }
    
    if (!ifscCode) {
      toast.error('Please enter IFSC code')
      return
    }
    
    if (!branchName) {
      toast.error('Please enter branch name')
      return
    }
    
    if (!accountHolderName) {
      toast.error('Please enter account holder name')
      return
    }
    
    if (!tpin || tpin.length !== 6) {
      toast.error('Please enter valid 6-digit TPIN')
      return
    }
    
    setLoading(true)
    try {
      const response = await clientAPI.addBank({
        bankName,
        accountNumber: accountNo,
        reAccountNumber: reAccountNo,
        ifscCode,
        branchName,
        accountHolderName,
        tpin
      })
      
      if (response.success) {
        toast.success('Bank account added successfully!')
        handleReset()
        loadBanks()
      }
    } catch (error) {
      toast.error(error.message || 'Failed to add bank account')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setBankName('')
    setAccountNo('')
    setReAccountNo('')
    setIfscCode('')
    setBranchName('')
    setAccountHolderName('')
    setTpin('')
  }

  const handleDeleteClick = (bank) => {
    setDeletingBank(bank)
    setDeleteTpin('')
    setShowDeleteDialog(true)
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTpin || deleteTpin.length !== 6) {
      toast.error('Please enter valid 6-digit TPIN')
      return
    }
    
    try {
      const response = await clientAPI.deleteBank(deletingBank.id, deleteTpin)
      if (response.success) {
        toast.success('Bank deleted successfully!')
        setShowDeleteDialog(false)
        setDeletingBank(null)
        setDeleteTpin('')
        loadBanks()
      }
    } catch (error) {
      toast.error(error.message || 'Failed to delete bank')
    }
  }

  const handleToggleStatus = async (bank) => {
    try {
      const response = await clientAPI.toggleBankStatus(bank.id)
      if (response.success) {
        toast.success(response.message)
        loadBanks()
      }
    } catch (error) {
      toast.error(error.message || 'Failed to toggle bank status')
    }
  }

  const getStatusBadge = (isActive) => {
    return isActive ? (
      <Badge className="bg-green-100 text-green-700 hover:bg-green-100">Active</Badge>
    ) : (
      <Badge className="bg-gray-100 text-gray-700 hover:bg-gray-100">Inactive</Badge>
    )
  }

  const getSettlementStatusBadge = (status) => {
    const statusConfig = {
      'PENDING': { bg: 'bg-yellow-100', text: 'text-yellow-700' },
      'APPROVED': { bg: 'bg-green-100', text: 'text-green-700' },
      'REJECTED': { bg: 'bg-red-100', text: 'text-red-700' }
    }
    
    const config = statusConfig[status] || statusConfig['PENDING']
    return (
      <Badge className={`${config.bg} ${config.text} hover:${config.bg}`}>
        {status}
      </Badge>
    )
  }

  return (
    <>
      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Bank Account</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this bank account? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label>Enter TPIN to confirm</Label>
            <div className="relative mt-2">
              <Input
                type={showDeleteTpin ? 'text' : 'password'}
                placeholder="Enter 6-digit TPIN"
                value={deleteTpin}
                onChange={(e) => setDeleteTpin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength="6"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowDeleteTpin(!showDeleteTpin)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
              >
                {showDeleteTpin ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Building className="h-8 w-8 text-orange-600" />
          <h1 className="text-3xl font-bold">Add Bank</h1>
        </div>

        {/* Add Bank Form */}
        <Card>
          <CardContent className="pt-6">
            {banks.length >= 5 && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  You have reached the maximum limit of 5 banks. Please delete a bank to add a new one.
                </p>
              </div>
            )}
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* First Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <Label className="text-base font-medium mb-2 block">Select Bank Name</Label>
                  <Input
                    type="text"
                    placeholder="Enter Bank Name"
                    value={bankName}
                    onChange={(e) => setBankName(e.target.value)}
                    className="h-12 text-base"
                    required
                    disabled={loading}
                  />
                </div>

                <div>
                  <Label className="text-base font-medium mb-2 block">Enter Account No</Label>
                  <Input
                    type="text"
                    placeholder="Enter Account No"
                    value={accountNo}
                    onChange={(e) => setAccountNo(e.target.value)}
                    className="h-12 text-base"
                    required
                    disabled={loading}
                  />
                </div>

                <div>
                  <Label className="text-base font-medium mb-2 block">Re-Enter Account No</Label>
                  <Input
                    type="text"
                    placeholder="Re-Enter Account No"
                    value={reAccountNo}
                    onChange={(e) => setReAccountNo(e.target.value)}
                    className="h-12 text-base"
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Second Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <Label className="text-base font-medium mb-2 block">Enter IFSC Code</Label>
                  <Input
                    type="text"
                    placeholder="Enter IFSC Code"
                    value={ifscCode}
                    onChange={(e) => setIfscCode(e.target.value.toUpperCase())}
                    className="h-12 text-base"
                    required
                    disabled={loading}
                  />
                </div>

                <div>
                  <Label className="text-base font-medium mb-2 block">Branch Name</Label>
                  <Input
                    type="text"
                    placeholder="Branch Name"
                    value={branchName}
                    onChange={(e) => setBranchName(e.target.value)}
                    className="h-12 text-base"
                    required
                    disabled={loading}
                  />
                </div>

                <div>
                  <Label className="text-base font-medium mb-2 block">Enter Account Holder Name</Label>
                  <Input
                    type="text"
                    placeholder="Enter Account Holder Name"
                    value={accountHolderName}
                    onChange={(e) => setAccountHolderName(e.target.value)}
                    className="h-12 text-base"
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Third Row - TPIN */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <Label className="text-base font-medium mb-2 block">TPIN</Label>
                  <div className="relative">
                    <Input
                      type={showTpin ? 'text' : 'password'}
                      placeholder="TPIN"
                      value={tpin}
                      onChange={(e) => setTpin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      className="h-12 text-base pr-12"
                      required
                      maxLength="6"
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowTpin(!showTpin)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                    >
                      {showTpin ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Buttons */}
              <div className="flex gap-4">
                <Button
                  type="submit"
                  className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white px-8 h-11"
                  disabled={loading || banks.length >= 5}
                >
                  {loading ? 'Submitting...' : 'Submit'}
                </Button>
                <Button
                  type="button"
                  onClick={handleReset}
                  variant="outline"
                  className="bg-gray-400 hover:bg-gray-500 text-white px-8 h-11 border-0"
                  disabled={loading}
                >
                  Reset
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Bank List Section */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Bank List</h2>
              <Button
                variant="ghost"
                size="sm"
                className="text-gray-600 hover:text-gray-900"
                onClick={loadBanks}
                disabled={loadingBanks}
              >
                <RefreshCw className={`h-4 w-4 ${loadingBanks ? 'animate-spin' : ''}`} />
              </Button>
            </div>

            {/* Note */}
            <div className="mb-4 space-y-1">
              <p className="text-sm text-gray-700"><span className="font-semibold">Note:</span></p>
              <p className="text-sm text-gray-600">1. Maximum 5 banks allowed to add.</p>
              <p className="text-sm text-gray-600">2. You can activate or deactivate your bank accounts.</p>
            </div>

            {loadingBanks ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
                  <p className="mt-4 text-gray-600">Loading banks...</p>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto border rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead className="whitespace-nowrap font-semibold">SR. NO.</TableHead>
                      <TableHead className="whitespace-nowrap font-semibold">NAME</TableHead>
                      <TableHead className="whitespace-nowrap font-semibold">ACCOUNT NO</TableHead>
                      <TableHead className="whitespace-nowrap font-semibold">IFSC</TableHead>
                      <TableHead className="whitespace-nowrap font-semibold">BANK NAME</TableHead>
                      <TableHead className="whitespace-nowrap font-semibold">BRANCH NAME</TableHead>
                      <TableHead className="whitespace-nowrap font-semibold">STATUS</TableHead>
                      <TableHead className="whitespace-nowrap font-semibold">ACTIONS</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {banks.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                          No bank accounts found
                        </TableCell>
                      </TableRow>
                    ) : (
                      banks.map((bank, index) => (
                        <TableRow key={bank.id} className="hover:bg-gray-50">
                          <TableCell>{index + 1}</TableCell>
                          <TableCell className="font-medium">{bank.account_holder_name}</TableCell>
                          <TableCell>{bank.account_number}</TableCell>
                          <TableCell>{bank.ifsc_code}</TableCell>
                          <TableCell className="max-w-xs">{bank.bank_name}</TableCell>
                          <TableCell>{bank.branch_name}</TableCell>
                          <TableCell>{getStatusBadge(bank.is_active)}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Button
                                onClick={() => handleToggleStatus(bank)}
                                variant="ghost"
                                size="sm"
                                className={bank.is_active 
                                  ? "text-red-600 hover:text-red-700 hover:bg-red-50" 
                                  : "text-green-600 hover:text-green-700 hover:bg-green-50"}
                                title={bank.is_active ? 'Deactivate' : 'Activate'}
                              >
                                {bank.is_active ? (
                                  <ToggleRight className="h-5 w-5" />
                                ) : (
                                  <ToggleLeft className="h-5 w-5" />
                                )}
                              </Button>
                              <Button
                                onClick={() => handleDeleteClick(bank)}
                                variant="ghost"
                                size="sm"
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}
