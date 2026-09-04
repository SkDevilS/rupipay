import { Navigate, useLocation } from 'react-router-dom'
import clientAPI from '@/api/client_api'

export default function ProtectedRoute({ children }) {
  const location = useLocation()
  const isAuthenticated = clientAPI.isAuthenticated()
  
  if (!isAuthenticated) {
    // Redirect to login but save the location they were trying to access
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  
  return children
}
