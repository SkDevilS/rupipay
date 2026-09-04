import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'

const SESSION_TIMEOUT = 30 * 60 * 1000 // 30 minutes
const WARNING_TIME = 5 * 60 * 1000 // Show warning 5 minutes before expiry

export default function SessionExpiryWarning() {
  const navigate = useNavigate()
  const [showWarning, setShowWarning] = useState(false)
  const [timeLeft, setTimeLeft] = useState(0)
  const [lastActivity, setLastActivity] = useState(Date.now())

  useEffect(() => {
    // Track user activity
    const updateActivity = () => {
      setLastActivity(Date.now())
      setShowWarning(false)
    }

    // Activity events
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click']
    events.forEach(event => {
      document.addEventListener(event, updateActivity)
    })

    // Check session expiry
    const checkInterval = setInterval(() => {
      const now = Date.now()
      const timeSinceActivity = now - lastActivity
      const remaining = SESSION_TIMEOUT - timeSinceActivity

      if (remaining <= 0) {
        // Session expired
        handleSessionExpired()
      } else if (remaining <= WARNING_TIME && !showWarning) {
        // Show warning
        setShowWarning(true)
        setTimeLeft(Math.floor(remaining / 1000))
      } else if (showWarning) {
        // Update countdown
        setTimeLeft(Math.floor(remaining / 1000))
      }
    }, 1000)

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity)
      })
      clearInterval(checkInterval)
    }
  }, [lastActivity, showWarning])

  const handleSessionExpired = () => {
    clientAPI.logout()
    toast.error('Session expired. Please login again.')
    navigate('/login', { replace: true })
  }

  const handleExtendSession = async () => {
    try {
      await clientAPI.verifyToken()
      setLastActivity(Date.now())
      setShowWarning(false)
      toast.success('Session extended successfully')
    } catch (error) {
      toast.error('Failed to extend session')
      handleSessionExpired()
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <Dialog open={showWarning} onOpenChange={setShowWarning}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 rounded-full">
              <AlertTriangle className="h-6 w-6 text-yellow-600" />
            </div>
            <DialogTitle>Session Expiring Soon</DialogTitle>
          </div>
          <DialogDescription className="pt-4">
            Your session will expire in <span className="font-bold text-red-600">{formatTime(timeLeft)}</span>.
            <br />
            Would you like to extend your session?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="flex gap-2 sm:gap-2">
          <Button
            onClick={handleSessionExpired}
            variant="outline"
            className="flex-1"
          >
            Logout
          </Button>
          <Button
            onClick={handleExtendSession}
            className="flex-1 bg-gradient-to-r from-orange-500 to-yellow-400 hover:from-orange-600 hover:to-yellow-500"
          >
            Extend Session
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
