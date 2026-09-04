import { Navigate } from 'react-router-dom'
import adminAPI from '@/api/admin_api'

export default function PublicRoute({ children }) {
  // If user is already authenticated, redirect to dashboard
  if (adminAPI.isAuthenticated()) {
    return <Navigate to="/" replace />
  }

  return children
}
