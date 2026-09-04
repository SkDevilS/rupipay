import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Lock, Eye, EyeOff, CheckCircle2, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'

export default function ChangePassword() {
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  })
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: '',
  })
  const [loading, setLoading] = useState(false)
  const [validations, setValidations] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  })

  const validatePassword = (password) => {
    setValidations({
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password),
    })
  }

  const handlePasswordChange = (field, value) => {
    setPasswords({ ...passwords, [field]: value })
    if (field === 'new') {
      validatePassword(value)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (passwords.new !== passwords.confirm) {
      toast.error('New passwords do not match!')
      return
    }

    const allValid = Object.values(validations).every(v => v)
    if (!allValid) {
      toast.error('Please meet all password requirements')
      return
    }

    setLoading(true)
    try {
      const response = await adminAPI.changePassword(
        passwords.current,
        passwords.new,
        passwords.confirm
      )

      if (response.success) {
        toast.success(response.message || 'Password changed successfully!')
        setPasswords({ current: '', new: '', confirm: '' })
        setValidations({
          length: false,
          uppercase: false,
          lowercase: false,
          number: false,
          special: false,
        })
      }
    } catch (error) {
      toast.error(error.message || 'Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  const toggleShow = (field) => {
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Lock className="h-8 w-8 text-blue-600" />
        <h1 className="text-3xl font-bold">Change Password</h1>
      </div>

      <div className="max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Update Your Password</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Current Password *</Label>
                <div className="relative">
                  <Input
                    type={showPasswords.current ? 'text' : 'password'}
                    value={passwords.current}
                    onChange={(e) => handlePasswordChange('current', e.target.value)}
                    required
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={() => toggleShow('current')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                    disabled={loading}
                  >
                    {showPasswords.current ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div>
                <Label>New Password *</Label>
                <div className="relative">
                  <Input
                    type={showPasswords.new ? 'text' : 'password'}
                    value={passwords.new}
                    onChange={(e) => handlePasswordChange('new', e.target.value)}
                    required
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={() => toggleShow('new')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                    disabled={loading}
                  >
                    {showPasswords.new ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div>
                <Label>Confirm New Password *</Label>
                <div className="relative">
                  <Input
                    type={showPasswords.confirm ? 'text' : 'password'}
                    value={passwords.confirm}
                    onChange={(e) => handlePasswordChange('confirm', e.target.value)}
                    required
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={() => toggleShow('confirm')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                    disabled={loading}
                  >
                    {showPasswords.confirm ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {passwords.confirm && passwords.new !== passwords.confirm && (
                  <p className="text-sm text-red-600 mt-1">Passwords do not match</p>
                )}
              </div>

              <div className="p-4 bg-blue-50 rounded-lg text-sm">
                <p className="font-medium mb-3 text-blue-900">Password Requirements:</p>
                <div className="space-y-2">
                  <div className={`flex items-center gap-2 ${validations.length ? 'text-green-700' : 'text-gray-600'}`}>
                    {validations.length ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    <span>At least 8 characters long</span>
                  </div>
                  <div className={`flex items-center gap-2 ${validations.uppercase ? 'text-green-700' : 'text-gray-600'}`}>
                    {validations.uppercase ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    <span>Contains uppercase letter (A-Z)</span>
                  </div>
                  <div className={`flex items-center gap-2 ${validations.lowercase ? 'text-green-700' : 'text-gray-600'}`}>
                    {validations.lowercase ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    <span>Contains lowercase letter (a-z)</span>
                  </div>
                  <div className={`flex items-center gap-2 ${validations.number ? 'text-green-700' : 'text-gray-600'}`}>
                    {validations.number ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    <span>Contains at least one number (0-9)</span>
                  </div>
                  <div className={`flex items-center gap-2 ${validations.special ? 'text-green-700' : 'text-gray-600'}`}>
                    {validations.special ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    <span>Contains special character (!@#$%^&*...)</span>
                  </div>
                </div>
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Changing Password...' : 'Change Password'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
