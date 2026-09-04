import { useState, useEffect, useRef } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { AlertTriangle, RefreshCw, X } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'
import { useNavigate } from 'react-router-dom'

export default function SessionExpiryWarning() {
  const navigate = useNavigate()
  const [showWarning, setShowWarning] = useState(false)
  const [countdown, setCountdown] = useState(20)
  const [refreshing, setRefreshing] = useState(false)
  
  // Session timeout: 15 minutes - PRODUCTION
  const SESSION_TIMEOUT = 15 * 60 * 1000 // 15 minutes in milliseconds
  const WARNING_TIME = 14 * 60 * 1000 + 40 * 1000 // Show warning at 14:40 (20 seconds before expiry)
  const COUNTDOWN_DURATION = 20 // 20 seconds countdown
  
  const warningTimerRef = useRef(null)
  const logoutTimerRef = useRef(null)
  const countdownIntervalRef = useRef(null)
  const lastActivityRef = useRef(Date.now())

  useEffect(() => {
    console.log('SessionExpiryWarning mounted')
    
    const checkInactivity = () => {
      const now = Date.now()
      const timeSinceLastActivity = now - lastActivityRef.current
      
      // If warning should be shown
      if (timeSinceLastActivity >= WARNING_TIME && !showWarning) {
        console.log('Showing warning - inactive for', timeSinceLastActivity / 1000, 'seconds')
        setShowWarning(true)
        startCountdown()
      }
      
      // If session should expire
      if (timeSinceLastActivity >= SESSION_TIMEOUT) {
        console.log('Session expired - logging out')
        handleSessionExpired()
      }
    }

    const startCountdown = () => {
      let timeLeft = COUNTDOWN_DURATION
      setCountdown(timeLeft)
      
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current)
      }
      
      countdownIntervalRef.current = setInterval(() => {
        timeLeft -= 1
        setCountdown(timeLeft)
        console.log('Countdown:', timeLeft)
        
        if (timeLeft <= 0) {
          clearInterval(countdownIntervalRef.current)
          handleSessionExpired()
        }
      }, 1000)
    }

    const handleSessionExpired = async () => {
      console.log('Handling session expiry')
      setShowWarning(false)
      clearAllTimers()
      
      try {
        await adminAPI.logout()
      } catch (error) {
        console.error('Logout error:', error)
      }
      
      toast.error('Session expired. Please login again.')
      navigate('/login')
    }

    const handleActivity = () => {
      if (!showWarning) {
        const now = Date.now()
        lastActivityRef.current = now
        console.log('Activity detected - timer reset')
      }
    }

    const clearAllTimers = () => {
      if (warningTimerRef.current) clearInterval(warningTimerRef.current)
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current)
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current)
    }

    // Activity listeners
    const activityEvents = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click']
    
    // Initialize
    if (adminAPI.isAuthenticated()) {
      console.log('Starting session monitoring - timeout:', SESSION_TIMEOUT / 1000, 'seconds')
      lastActivityRef.current = Date.now()
      
      // Check inactivity every second
      warningTimerRef.current = setInterval(checkInactivity, 1000)
      
      // Add activity listeners
      activityEvents.forEach(event => {
        window.addEventListener(event, handleActivity, { passive: true })
      })
    }

    // Cleanup
    return () => {
      console.log('SessionExpiryWarning unmounted - cleaning up')
      clearAllTimers()
      
      activityEvents.forEach(event => {
        window.removeEventListener(event, handleActivity)
      })
    }
  }, [navigate, showWarning])

  const handleRefresh = async () => {
    console.log('Refreshing session')
    setRefreshing(true)
    
    try {
      // Verify token to refresh session
      await adminAPI.verifyToken()
      
      // Reset everything
      lastActivityRef.current = Date.now()
      setShowWarning(false)
      setCountdown(COUNTDOWN_DURATION)
      
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current)
      }
      
      toast.success('Session refreshed successfully!')
      console.log('Session refreshed - timer reset')
    } catch (error) {
      console.error('Refresh error:', error)
      toast.error('Failed to refresh session. Please login again.')
      await adminAPI.logout()
      navigate('/login')
    } finally {
      setRefreshing(false)
    }
  }

  const handleClose = async () => {
    console.log('Closing session manually')
    setShowWarning(false)
    
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current)
    }
    
    await adminAPI.logout()
    toast.info('Session closed. Please login again.')
    navigate('/login')
  }

  if (!showWarning) return null

  return (
    <Dialog open={showWarning} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-md" hideClose>
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-3 bg-orange-100 rounded-full">
              <AlertTriangle className="h-6 w-6 text-orange-600" />
            </div>
            <DialogTitle className="text-xl">Session Expiring Soon</DialogTitle>
          </div>
          <DialogDescription className="text-base pt-2">
            Your session is about to expire. Please Refresh or You will be automatically logged out in:
          </DialogDescription>
        </DialogHeader>

        {/* Countdown Timer */}
        <div className="flex flex-col items-center justify-center py-6">
          <div className="relative">
            <svg className="transform -rotate-90 w-32 h-32">
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="currentColor"
                strokeWidth="8"
                fill="transparent"
                className="text-gray-200"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="currentColor"
                strokeWidth="8"
                fill="transparent"
                strokeDasharray={`${2 * Math.PI * 56}`}
                strokeDashoffset={`${2 * Math.PI * 56 * (1 - countdown / COUNTDOWN_DURATION)}`}
                className="text-orange-500 transition-all duration-1000 ease-linear"
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="text-4xl font-bold text-orange-600">{countdown}</div>
                <div className="text-sm text-gray-500">seconds</div>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="flex gap-2 sm:gap-2">
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={refreshing}
            className="flex-1 border-gray-300 hover:bg-gray-100"
          >
            <X className="h-4 w-4 mr-2" />
            Close Session
          </Button>
          <Button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex-1 bg-gradient-to-r from-orange-500 to-yellow-500 hover:from-orange-600 hover:to-yellow-600 text-white"
          >
            {refreshing ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Refreshing...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh Session
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
