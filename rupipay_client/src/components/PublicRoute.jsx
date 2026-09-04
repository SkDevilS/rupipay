import { Navigate } from 'react-router-dom'
import clientAPI from '@/api/client_api'

export default function PublicRoute({ children }) {
  const isAuthenticated = clientAPI.isAuthenticated()
  
  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }
  
  return children
}
