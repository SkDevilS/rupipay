import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import adminAPI from '@/api/admin_api'

export default function ProtectedRoute({ children }) {
  const [isChecking, setIsChecking] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = () => {
    // Simple check - just verify token exists in localStorage
    const hasToken = adminAPI.isAuthenticated()
    console.log('🔐 ProtectedRoute - Token exists:', hasToken)
    
    setIsAuthenticated(hasToken)
    setIsChecking(false)
  }

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    console.log('❌ Not authenticated - redirecting to login')
    return <Navigate to="/login" replace />
  }

  return children
}
