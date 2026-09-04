import { useState, useEffect } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import adminAPI from '@/api/admin_api'

export default function PinNotification() {
  const [showNotification, setShowNotification] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    // Check if PIN status is stored in localStorage
    const storedPinStatus = localStorage.getItem('adminHasPinSet')
    
    if (storedPinStatus === null) {
      // First time or after logout - check PIN status
      checkPinStatus()
    } else {
      // Use stored status
      setShowNotification(storedPinStatus === 'false')
    }
  }, [])

  // Listen for custom events when PIN is set or deleted
  useEffect(() => {
    const handlePinDeleted = () => {
      setShowNotification(true)
      setDismissed(false)
      localStorage.setItem('adminHasPinSet', 'false')
    }

    const handlePinSet = () => {
      setShowNotification(false)
      localStorage.setItem('adminHasPinSet', 'true')
    }

    window.addEventListener('adminPinDeleted', handlePinDeleted)
    window.addEventListener('adminPinSet', handlePinSet)

    return () => {
      window.removeEventListener('adminPinDeleted', handlePinDeleted)
      window.removeEventListener('adminPinSet', handlePinSet)
    }
  }, [])

  const checkPinStatus = async () => {
    try {
      const response = await adminAPI.checkPinStatus()
      setShowNotification(!response.hasPinSet)
      localStorage.setItem('adminHasPinSet', response.hasPinSet.toString())
    } catch (error) {
      console.error('Error checking PIN status:', error)
      // Don't show notification if there's an error
      setShowNotification(false)
    }
  }

  const handleDismiss = () => {
    setDismissed(true)
  }

  if (!showNotification || dismissed) {
    return null
  }

  return (
    <div className="bg-red-600 text-white px-6 py-3 flex items-center justify-between shadow-lg animate-slide-down">
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-5 w-5 flex-shrink-0" />
        <p className="text-sm font-medium">
          Please set your TPIN to start transactions.{' '}
          <Link 
            to="/security/change-pin" 
            className="underline hover:text-red-100 font-semibold"
          >
            Set TPIN Now
          </Link>
        </p>
      </div>
      <button
        onClick={handleDismiss}
        className="p-1 hover:bg-red-700 rounded transition-colors"
        aria-label="Dismiss notification"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}
