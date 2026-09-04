import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { 
  List, Search, Eye, Edit, Trash2, Lock, 
  Download, UserX, UserCheck, Loader2, FileText 
} from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'

export default function UserList() {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [merchantTypeFilter, setMerchantTypeFilter] = useState('All')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showSearch, setShowSearch] = useState(false)
  const [schemes, setSchemes] = useState([])
  
  // Modal states
  const [viewModalOpen, setViewModalOpen] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [resetPasswordModalOpen, setResetPasswordModalOpen] = useState(false)
  const [documentsModalOpen, setDocumentsModalOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState(null)
  const [editFormData, setEditFormData] = useState({})
  const [newPassword, setNewPassword] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadUsers()
    loadSchemes()
  }, [])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const response = await adminAPI.getUsers()
      if (response.success) {
        setUsers(response.users)
      }
    } catch (error) {
      toast.error(error.message || 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  const loadSchemes = async () => {
    try {
      const response = await adminAPI.getSchemes()
      if (response.success) {
        setSchemes(response.schemes || [])
      }
    } catch (error) {
      console.error('Failed to load schemes:', error)
    }
  }

  // Filter users
  const filteredUsers = users.filter(user => {
    const matchesSearch = 
      user.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.mobile?.includes(searchTerm) ||
      user.merchant_id?.includes(searchTerm)
    
    const matchesStatus = statusFilter === 'All' || 
      (statusFilter === 'Active' && user.is_active) ||
      (statusFilter === 'Inactive' && !user.is_active)
    
    const matchesMerchantType = merchantTypeFilter === 'All' || user.merchant_type === merchantTypeFilter
    
    // Date filter
    let matchesDate = true
    if (fromDate || toDate) {
      const userDate = new Date(user.created_at)
      if (fromDate) {
        matchesDate = matchesDate && userDate >= new Date(fromDate)
      }
      if (toDate) {
        matchesDate = matchesDate && userDate <= new Date(toDate)
      }
    }
    
    return matchesSearch && matchesStatus && matchesMerchantType && matchesDate
  })

  // View user
  const handleView = async (user) => {
    try {
      const response = await adminAPI.getUserDetails(user.merchant_id)
      if (response.success) {
        setSelectedUser(response.user)
        setViewModalOpen(true)
      }
    } catch (error) {
      toast.error(error.message || 'Failed to load user details')
    }
  }

  // Edit user
  const handleEdit = async (user) => {
    try {
      const response = await adminAPI.getUserDetails(user.merchant_id)
      if (response.success) {
        setSelectedUser(response.user)
        setEditFormData(response.user)
        setEditModalOpen(true)
      }
    } catch (error) {
      toast.error(error.message || 'Failed to load user details')
    }
  }

  const handleEditSave = async () => {
    try {
      setSaving(true)
      const response = await adminAPI.updateUser(selectedUser.merchant_id, editFormData)
      if (response.success) {
        toast.success('User updated successfully!')
        setEditModalOpen(false)
        await loadUsers()
      }
    } catch (error) {
      toast.error(error.message || 'Failed to update user')
    } finally {
      setSaving(false)
    }
  }

  // Toggle status
  const handleToggleStatus = async (user) => {
    try {
      const response = await adminAPI.toggleUserStatus(user.merchant_id)
      if (response.success) {
        toast.success(response.message)
        await loadUsers()
      }
    } catch (error) {
      toast.error(error.message || 'Failed to toggle user status')
    }
  }

  // Reset password
  const handleResetPassword = (user) => {
    setSelectedUser(user)
    setNewPassword('')
    setResetPasswordModalOpen(true)
  }

  const handleResetPasswordConfirm = async () => {
    if (!newPassword || newPassword.length < 8) {
      toast.error('Password must be at least 8 characters long')
      return
    }

    try {
      setSaving(true)
      const response = await adminAPI.resetUserPassword(selectedUser.merchant_id, newPassword)
      if (response.success) {
        toast.success('Password reset successfully!')
        setResetPasswordModalOpen(false)
        setNewPassword('')
      }
    } catch (error) {
      toast.error(error.message || 'Failed to reset password')
    } finally {
      setSaving(false)
    }
  }

  // Delete user
  const handleDelete = (user) => {
    setSelectedUser(user)
    setDeleteModalOpen(true)
  }

  const handleDeleteConfirm = async () => {
    try {
      setSaving(true)
      const response = await adminAPI.deleteUser(selectedUser.merchant_id)
      if (response.success) {
        toast.success('User deleted successfully!')
        setDeleteModalOpen(false)
        await loadUsers()
      }
    } catch (error) {
      toast.error(error.message || 'Failed to delete user')
    } finally {
      setSaving(false)
    }
  }

  // View documents
  const handleViewDocuments = async (user) => {
    try {
      const response = await adminAPI.getUserDetails(user.merchant_id)
      if (response.success) {
        setSelectedUser(response.user)
        setDocumentsModalOpen(true)
      }
    } catch (error) {
      toast.error(error.message || 'Failed to load documents')
    }
  }

  // Download document
  const handleDownloadDocument = async (docType, docName) => {
    try {
      toast.loading(`Downloading ${docName}...`)
      const response = await adminAPI.downloadDocument(selectedUser.merchant_id, docType)
      
      if (response.success && response.document_url) {
        // Create a temporary link and trigger download
        const link = document.createElement('a')
        link.href = response.document_url
        link.download = `${selectedUser.merchant_id}_${docType}`
        link.target = '_blank'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        
        toast.dismiss()
        toast.success(`${docName} downloaded successfully`)
      } else {
        toast.dismiss()
        toast.error('Document not available')
      }
    } catch (error) {
      toast.dismiss()
      toast.error(error.message || 'Failed to download document')
    }
  }

  // Reset filters
  const handleResetFilters = () => {
    setSearchTerm('')
    setStatusFilter('All')
    setMerchantTypeFilter('All')
    setFromDate('')
    setToDate('')
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-orange-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <List className="h-8 w-8 text-orange-600" />
          <h1 className="text-3xl font-bold">User List</h1>
        </div>
        <Button
          onClick={() => setShowSearch(!showSearch)}
          className="bg-gradient-to-r from-orange-500 to-yellow-400 hover:from-orange-600 hover:to-yellow-500"
        >
          <Search className="h-4 w-4 mr-2" />
          {showSearch ? 'Hide Search' : 'Search'}
        </Button>
      </div>

      {/* Search and Filters */}
      {showSearch && (
        <Card>
          <CardHeader>
            <CardTitle>Search & Filter</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search by name, email, phone, or merchant ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4 border-t">
              <div>
                <Label>Status</Label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                >
                  <option value="All">All Status</option>
                  <option value="Active">Active</option>
                  <option value="Inactive">Inactive</option>
                </select>
              </div>
              <div>
                <Label>Merchant Type</Label>
                <select
                  value={merchantTypeFilter}
                  onChange={(e) => setMerchantTypeFilter(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                >
                  <option value="All">All Types</option>
                  <option value="PAYIN">Payin</option>
                  <option value="PAYOUT">Payout</option>
                  <option value="BOTH">Both</option>
                </select>
              </div>
              <div>
                <Label>From Date</Label>
                <Input
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                />
              </div>
              <div>
                <Label>To Date</Label>
                <Input
                  type="date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button onClick={handleResetFilters} variant="outline">
                Reset Filters
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Users Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Users ({filteredUsers.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Merchant ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Scheme</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                      No users found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUsers.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-mono">{user.merchant_id}</TableCell>
                      <TableCell className="font-medium">{user.full_name}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>{user.mobile}</TableCell>
                      <TableCell>
                        <span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-700">
                          {user.merchant_type}
                        </span>
                      </TableCell>
                      <TableCell>{user.scheme_name || 'N/A'}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          user.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                        }`}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs">
                        {user.created_at_ist || formatDate(user.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => handleView(user)}
                            title="View Details"
                          >
                            <Eye className="h-4 w-4 text-blue-600" />
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => handleEdit(user)}
                            title="Edit User"
                          >
                            <Edit className="h-4 w-4 text-orange-600" />
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => handleToggleStatus(user)}
                            title={user.is_active ? 'Deactivate' : 'Activate'}
                          >
                            {user.is_active ? (
                              <UserX className="h-4 w-4 text-yellow-600" />
                            ) : (
                              <UserCheck className="h-4 w-4 text-green-600" />
                            )}
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => handleResetPassword(user)}
                            title="Reset Password"
                          >
                            <Lock className="h-4 w-4 text-purple-600" />
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => handleViewDocuments(user)}
                            title="View Documents"
                          >
                            <FileText className="h-4 w-4 text-indigo-600" />
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => handleDelete(user)}
                            title="Delete User"
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* View Modal */}
      <Dialog open={viewModalOpen} onOpenChange={setViewModalOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>User Details</DialogTitle>
            <DialogDescription>Complete information about the user</DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="grid grid-cols-2 gap-4 py-4">
              <div>
                <Label className="text-gray-500">Merchant ID</Label>
                <p className="font-medium font-mono">{selectedUser.merchant_id}</p>
              </div>
              <div>
                <Label className="text-gray-500">Full Name</Label>
                <p className="font-medium">{selectedUser.full_name}</p>
              </div>
              <div>
                <Label className="text-gray-500">Email</Label>
                <p className="font-medium">{selectedUser.email}</p>
              </div>
              <div>
                <Label className="text-gray-500">Mobile</Label>
                <p className="font-medium">{selectedUser.mobile}</p>
              </div>
              <div>
                <Label className="text-gray-500">Date of Birth</Label>
                <p className="font-medium">{formatDate(selectedUser.dob)}</p>
              </div>
              <div>
                <Label className="text-gray-500">Status</Label>
                <p className="font-medium">{selectedUser.is_active ? 'Active' : 'Inactive'}</p>
              </div>
              <div>
                <Label className="text-gray-500">Merchant Type</Label>
                <p className="font-medium">{selectedUser.merchant_type}</p>
              </div>
              <div>
                <Label className="text-gray-500">Scheme</Label>
                <p className="font-medium">{selectedUser.scheme_name || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-gray-500">Account Number</Label>
                <p className="font-medium font-mono">{selectedUser.account_number}</p>
              </div>
              <div>
                <Label className="text-gray-500">IFSC Code</Label>
                <p className="font-medium font-mono">{selectedUser.ifsc_code}</p>
              </div>
              <div>
                <Label className="text-gray-500">PAN Number</Label>
                <p className="font-medium font-mono">{selectedUser.pan_no}</p>
              </div>
              <div>
                <Label className="text-gray-500">Aadhar Number</Label>
                <p className="font-medium font-mono">{selectedUser.aadhar_card}</p>
              </div>
              <div className="col-span-2">
                <Label className="text-gray-500">GST Number</Label>
                <p className="font-medium font-mono">{selectedUser.gst_no}</p>
              </div>
              <div className="col-span-2">
                <Label className="text-gray-500">Address</Label>
                <p className="font-medium">{selectedUser.address}</p>
              </div>
              <div>
                <Label className="text-gray-500">City</Label>
                <p className="font-medium">{selectedUser.city}</p>
              </div>
              <div>
                <Label className="text-gray-500">State</Label>
                <p className="font-medium">{selectedUser.state}</p>
              </div>
              <div>
                <Label className="text-gray-500">Pincode</Label>
                <p className="font-medium">{selectedUser.pincode}</p>
              </div>
              <div>
                <Label className="text-gray-500">Created At (IST)</Label>
                <p className="font-medium">{selectedUser.created_at_ist || formatDate(selectedUser.created_at)}</p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setViewModalOpen(false)} variant="outline">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
            <DialogDescription>Update user information</DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="grid grid-cols-2 gap-4 py-4">
              <div>
                <Label>Full Name *</Label>
                <Input
                  value={editFormData.full_name || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, full_name: e.target.value })}
                />
              </div>
              <div>
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={editFormData.email || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
                />
              </div>
              <div>
                <Label>Mobile *</Label>
                <Input
                  value={editFormData.mobile || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, mobile: e.target.value })}
                />
              </div>
              <div>
                <Label>Merchant Type *</Label>
                <select
                  value={editFormData.merchant_type || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, merchant_type: e.target.value })}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                >
                  <option value="PAYIN">Payin</option>
                  <option value="PAYOUT">Payout</option>
                  <option value="BOTH">Both</option>
                </select>
              </div>
              <div>
                <Label>Scheme *</Label>
                <select
                  value={editFormData.scheme_id || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, scheme_id: e.target.value })}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                >
                  <option value="">Select Scheme</option>
                  {schemes.map((scheme) => (
                    <option key={scheme.id} value={scheme.id}>
                      {scheme.scheme_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label>Account Number *</Label>
                <Input
                  value={editFormData.account_number || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, account_number: e.target.value })}
                />
              </div>
              <div>
                <Label>IFSC Code *</Label>
                <Input
                  value={editFormData.ifsc_code || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, ifsc_code: e.target.value })}
                />
              </div>
              <div className="col-span-2">
                <Label>GST Number *</Label>
                <Input
                  value={editFormData.gst_no || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, gst_no: e.target.value })}
                />
              </div>
              <div className="col-span-2">
                <Label>Address *</Label>
                <Input
                  value={editFormData.address || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, address: e.target.value })}
                />
              </div>
              <div>
                <Label>City *</Label>
                <Input
                  value={editFormData.city || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, city: e.target.value })}
                />
              </div>
              <div>
                <Label>State *</Label>
                <Input
                  value={editFormData.state || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, state: e.target.value })}
                />
              </div>
              <div>
                <Label>Pincode *</Label>
                <Input
                  value={editFormData.pincode || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, pincode: e.target.value })}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setEditModalOpen(false)} variant="outline">
              Cancel
            </Button>
            <Button 
              onClick={handleEditSave}
              disabled={saving}
              className="bg-gradient-to-r from-orange-500 to-yellow-400 hover:from-orange-600 hover:to-yellow-500"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Modal */}
      <Dialog open={resetPasswordModalOpen} onOpenChange={setResetPasswordModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset User Password</DialogTitle>
            <DialogDescription>
              Enter a new password for this user
            </DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-4 py-4">
              <div>
                <p className="text-sm mb-2">
                  <span className="font-semibold">User:</span> {selectedUser.full_name}
                </p>
                <p className="text-sm mb-4">
                  <span className="font-semibold">Merchant ID:</span> {selectedUser.merchant_id}
                </p>
              </div>
              <div>
                <Label>New Password *</Label>
                <Input
                  type="password"
                  placeholder="Enter new password (min 8 characters)"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setResetPasswordModalOpen(false)} variant="outline">
              Cancel
            </Button>
            <Button 
              onClick={handleResetPasswordConfirm}
              disabled={saving}
              className="bg-purple-600 hover:bg-purple-700 text-white"
            >
              {saving ? 'Resetting...' : 'Reset Password'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Documents Modal */}
      <Dialog open={documentsModalOpen} onOpenChange={setDocumentsModalOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>User Documents</DialogTitle>
            <DialogDescription>
              Download uploaded documents
            </DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-3 py-4">
              <div className="grid grid-cols-2 gap-3">
                <Button
                  variant="outline"
                  className="justify-start"
                  onClick={() => handleDownloadDocument('aadhar_front', 'Aadhar Front')}
                  disabled={!selectedUser.aadhar_front_path}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Aadhar Front
                </Button>
                <Button
                  variant="outline"
                  className="justify-start"
                  onClick={() => handleDownloadDocument('aadhar_back', 'Aadhar Back')}
                  disabled={!selectedUser.aadhar_back_path}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Aadhar Back
                </Button>
                <Button
                  variant="outline"
                  className="justify-start"
                  onClick={() => handleDownloadDocument('pan_card', 'PAN Card')}
                  disabled={!selectedUser.pan_card_path}
                >
                  <Download className="h-4 w-4 mr-2" />
                  PAN Card
                </Button>
                <Button
                  variant="outline"
                  className="justify-start"
                  onClick={() => handleDownloadDocument('gst_certificate', 'GST Certificate')}
                  disabled={!selectedUser.gst_certificate_path}
                >
                  <Download className="h-4 w-4 mr-2" />
                  GST Certificate
                </Button>
                <Button
                  variant="outline"
                  className="justify-start"
                  onClick={() => handleDownloadDocument('cancelled_cheque', 'Cancelled Cheque')}
                  disabled={!selectedUser.cancelled_cheque_path}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Cancelled Cheque
                </Button>
                <Button
                  variant="outline"
                  className="justify-start"
                  onClick={() => handleDownloadDocument('shop_photo', 'Shop Photo')}
                  disabled={!selectedUser.shop_photo_path}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Shop Photo
                </Button>
                <Button
                  variant="outline"
                  className="justify-start col-span-2"
                  onClick={() => handleDownloadDocument('profile_photo', 'Profile Photo')}
                  disabled={!selectedUser.profile_photo_path}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Profile Photo
                </Button>
              </div>
              <p className="text-sm text-gray-500 mt-4">
                Note: Disabled buttons indicate documents that haven't been uploaded yet.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setDocumentsModalOpen(false)} variant="outline">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete User</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this user? This action cannot be undone and will remove all associated data.
            </DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="py-4">
              <p className="text-sm">
                <span className="font-semibold">User:</span> {selectedUser.full_name}
              </p>
              <p className="text-sm">
                <span className="font-semibold">Merchant ID:</span> {selectedUser.merchant_id}
              </p>
              <p className="text-sm">
                <span className="font-semibold">Email:</span> {selectedUser.email}
              </p>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setDeleteModalOpen(false)} variant="outline">
              Cancel
            </Button>
            <Button 
              onClick={handleDeleteConfirm}
              disabled={saving}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {saving ? 'Deleting...' : 'Delete User'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
