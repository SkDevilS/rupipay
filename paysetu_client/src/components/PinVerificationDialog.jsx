import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { KeyRound, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'

export default function PinVerificationDialog({ open, onOpenChange, onVerified, title = "Verify PIN" }) {
  const [pin, setPin] = useState('')
  const [verifying, setVerifying] = useState(false)

  const handleVerify = async () => {
    if (!pin || pin.length !== 6) {
      toast.error('Please enter a 6-digit PIN')
      return
    }

    try {
      setVerifying(true)
      const response = await clientAPI.verifyPin(pin)
      
      if (response.success) {
        toast.success('PIN verified successfully!')
        setPin('')
        onVerified()
        onOpenChange(false)
      }
    } catch (error) {
      toast.error(error.message || 'Incorrect PIN')
      setPin('')
    } finally {
      setVerifying(false)
    }
  }

  const handleClose = () => {
    setPin('')
    onOpenChange(false)
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && pin.length === 6) {
      handleVerify()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-purple-600" />
            {title}
          </DialogTitle>
          <DialogDescription>
            Enter your 6-digit transaction PIN to view sensitive credentials
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="pin">Transaction PIN</Label>
            <Input
              id="pin"
              type="password"
              maxLength={6}
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
              onKeyPress={handleKeyPress}
              placeholder="Enter 6-digit PIN"
              className="text-center text-2xl tracking-widest"
              autoFocus
            />
          </div>

          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
            <p className="text-xs text-purple-800">
              <strong>Security Notice:</strong> Your PIN is required to view sensitive API credentials. 
              Credentials will be hidden again when you navigate away from this page.
            </p>
          </div>
        </div>

        <DialogFooter className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={verifying}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleVerify}
            disabled={verifying || pin.length !== 6}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            {verifying ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Verifying...
              </>
            ) : (
              'Verify PIN'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
