import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Key, CheckCircle2, XCircle, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'

export default function ChangePin() {
  const [tpins, setTpins] = useState({
    current: '',
    new: '',
    confirm: '',
  })
  const [loading, setLoading] = useState(false)
  const [hasPinSet, setHasPinSet] = useState(false)
  const [checkingPin, setCheckingPin] = useState(true)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [deletingPin, setDeletingPin] = useState(false)
  const [validations, setValidations] = useState({
    length: false,
    numeric: false,
    notSequential: false,
    notRepeated: false,
  })

  useEffect(() => {
    checkPinStatus()
  }, [])

  const checkPinStatus = async () => {
    setCheckingPin(true)
    try {
      const response = await clientAPI.checkPinStatus()
      setHasPinSet(response.hasPinSet)
    } catch (error) {
      console.error('Error checking PIN status:', error)
      setHasPinSet(false)
    } finally {
      setCheckingPin(false)
    }
  }

  const validatePin = (pin) => {
    const isSequential = ['012345', '123456', '234567', '345678', '456789', '567890'].includes(pin)
    const isRepeated = pin.length === 6 && new Set(pin).size === 1
    
    setValidations({
      length: pin.length === 6,
      numeric: /^\d+$/.test(pin),
      notSequential: !isSequential,
      notRepeated: !isRepeated,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (tpins.new !== tpins.confirm) {
      toast.error('New PINs do not match!')
      return
    }

    const allValid = Object.values(validations).every(v => v)
    if (!allValid) {
      toast.error('Please meet all PIN requirements')
      return
    }

    setLoading(true)
    try {
      const response = await clientAPI.changePin(
        hasPinSet ? tpins.current : null,
        tpins.new,
        tpins.confirm
      )

      if (response.success) {
        toast.success(response.message || (hasPinSet ? 'PIN changed successfully!' : 'PIN set successfully!'))
        setTpins({ current: '', new: '', confirm: '' })
        setValidations({
          length: false,
          numeric: false,
          notSequential: false,
          notRepeated: false,
        })
        setHasPinSet(true)
        
        // Store PIN status and dispatch event
        localStorage.setItem('hasPinSet', 'true')
        window.dispatchEvent(new Event('pinSet'))
      }
    } catch (error) {
      toast.error(error.message || 'Failed to change PIN')
    } finally {
      setLoading(false)
    }
  }

  const handleDeletePin = async () => {
    setDeletingPin(true)
    try {
      const response = await clientAPI.deletePin()
      if (response.success) {
        toast.success('PIN deleted successfully!')
        setShowDeleteDialog(false)
        setHasPinSet(false)
        setTpins({ current: '', new: '', confirm: '' })
        
        // Store PIN status and dispatch event
        localStorage.setItem('hasPinSet', 'false')
        window.dispatchEvent(new Event('pinDeleted'))
      }
    } catch (error) {
      toast.error(error.message || 'Failed to delete PIN')
    } finally {
      setDeletingPin(false)
    }
  }

  const handleTpinInput = (field, value) => {
    const numericValue = value.replace(/\D/g, '').slice(0, 6)
    setTpins({ ...tpins, [field]: numericValue })
    
    if (field === 'new') {
      validatePin(numericValue)
    }
  }

  if (checkingPin) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Checking PIN status...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Transaction PIN</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete your transaction PIN? You will need to set a new PIN before viewing credentials again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)} disabled={deletingPin}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeletePin} disabled={deletingPin}>
              {deletingPin ? 'Deleting...' : 'Delete PIN'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Key className="h-8 w-8 text-orange-600" />
            <div>
              <h1 className="text-3xl font-bold">{hasPinSet ? 'Change' : 'Set'} TPIN</h1>
              <p className="text-sm text-gray-600 mt-1">
                {hasPinSet ? 'Update your transaction PIN' : 'Set up your transaction PIN to start making transactions'}
              </p>
            </div>
          </div>
          {hasPinSet && (
            <Button
              variant="destructive"
              onClick={() => setShowDeleteDialog(true)}
              className="flex items-center gap-2"
            >
              <Trash2 size={16} />
              Delete PIN
            </Button>
          )}
        </div>

        <div className="max-w-2xl">
          <Card>
            <CardHeader>
              <CardTitle>{hasPinSet ? 'Update Your Transaction TPIN' : 'Set Your Transaction TPIN'}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
              {hasPinSet && (
                <div>
                  <Label>Current TPIN *</Label>
                  <Input
                    type="password"
                    maxLength={6}
                    value={tpins.current}
                    onChange={(e) => handleTpinInput('current', e.target.value)}
                    placeholder="Enter 6-digit TPIN"
                    required
                    disabled={loading}
                  />
                </div>
              )}

              <div>
                <Label>New TPIN *</Label>
                <Input
                  type="password"
                  maxLength={6}
                  value={tpins.new}
                  onChange={(e) => handleTpinInput('new', e.target.value)}
                  placeholder="Enter 6-digit TPIN"
                  required
                  disabled={loading}
                />
              </div>

              <div>
                <Label>Confirm New TPIN *</Label>
                <Input
                  type="password"
                  maxLength={6}
                  value={tpins.confirm}
                  onChange={(e) => handleTpinInput('confirm', e.target.value)}
                  placeholder="Re-enter 6-digit TPIN"
                  required
                  disabled={loading}
                />
                {tpins.confirm && tpins.new !== tpins.confirm && (
                  <p className="text-sm text-red-600 mt-1">PINs do not match</p>
                )}
              </div>

              <div className="p-4 bg-blue-50 rounded-lg text-sm">
                <p className="font-medium mb-3 text-blue-900">PIN Requirements:</p>
                <div className="space-y-2">
                  <div className={`flex items-center gap-2 ${validations.length ? 'text-green-700' : 'text-gray-600'}`}>
                    {validations.length ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    <span>Must be exactly 6 digits</span>
                  </div>
                  <div className={`flex items-center gap-2 ${validations.numeric ? 'text-green-700' : 'text-gray-600'}`}>
                    {validations.numeric ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    <span>Only numeric characters allowed</span>
                  </div>
                  <div className={`flex items-center gap-2 ${validations.notSequential ? 'text-green-700' : 'text-gray-600'}`}>
                    {validations.notSequential ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    <span>Avoid sequential numbers (123456)</span>
                  </div>
                  <div className={`flex items-center gap-2 ${validations.notRepeated ? 'text-green-700' : 'text-gray-600'}`}>
                    {validations.notRepeated ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    <span>Avoid repeated numbers (111111)</span>
                  </div>
                </div>
              </div>

              <Button 
                type="submit" 
                className="w-full bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800"
                disabled={loading}
              >
                {loading ? (hasPinSet ? 'Changing PIN...' : 'Setting PIN...') : (hasPinSet ? 'Change TPIN' : 'Set TPIN')}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
    </>
  )
}
