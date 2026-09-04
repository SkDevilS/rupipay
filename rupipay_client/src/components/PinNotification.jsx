import { useState, useEffect } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'
import clientAPI from '@/api/client_api'

export default function PinNotification() {
  const [hasPinSet, setHasPinSet] = useState(true)
  const [isVisible, setIsVisible] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    // Check if PIN status is stored in localStorage
    const storedPinStatus = localStorage.getItem('hasPinSet')
    
    if (storedPinStatus === null) {
      // First time or after logout - check PIN status
      checkPinStatus()
    } else {
      // Use stored status
      setHasPinSet(storedPinStatus === 'true')
    }
  }, [])

  // Listen for custom event when PIN is deleted
  useEffect(() => {
    const handlePinDeleted = () => {
      setHasPinSet(false)
      setIsVisible(true)
      localStorage.setItem('hasPinSet', 'false')
    }

    const handlePinSet = () => {
      setHasPinSet(true)
      localStorage.setItem('hasPinSet', 'true')
    }

    window.addEventListener('pinDeleted', handlePinDeleted)
    window.addEventListener('pinSet', handlePinSet)

    return () => {
      window.removeEventListener('pinDeleted', handlePinDeleted)
      window.removeEventListener('pinSet', handlePinSet)
    }
  }, [])

  const checkPinStatus = async () => {
    try {
      const response = await clientAPI.checkPinStatus()
      if (response.success) {
        setHasPinSet(response.hasPinSet)
        localStorage.setItem('hasPinSet', response.hasPinSet.toString())
      }
    } catch (error) {
      console.error('Error checking PIN status:', error)
    }
  }

  if (hasPinSet || !isVisible) {
    return null
  }

  return (
    <div className="bg-red-600 text-white shadow-lg relative">
      <div className="flex items-center justify-between px-6 py-3">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 flex-shrink-0" />
          <div className="flex items-center gap-2">
            <span className="font-medium">Please set your TPIN to start transactions.</span>
            <button
              onClick={() => navigate('/security/change-pin')}
              className="underline hover:text-red-100 font-semibold transition-colors"
            >
              Set TPIN Now
            </button>
          </div>
        </div>
        <button
          onClick={() => setIsVisible(false)}
          className="text-white hover:text-red-100 transition-colors p-1"
          aria-label="Close notification"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}
