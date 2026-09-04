import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatDate(date) {
  if (!date) return '-'
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    if (isNaN(dateObj.getTime())) return '-'
    
    const day = dateObj.getDate().toString().padStart(2, '0')
    const month = dateObj.toLocaleString('en-IN', { month: 'short' })
    const year = dateObj.getFullYear()
    
    return `${day} ${month} ${year}`
  } catch (error) {
    console.error('Date formatting error:', error)
    return '-'
  }
}

export function formatDateTime(date) {
  if (!date) return '-'
  try {
    // Parse the date string (should be ISO format from backend in IST)
    const dateObj = new Date(date)
    if (isNaN(dateObj.getTime())) return '-'
    
    // Format the date components
    const options = {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }
    
    const formatter = new Intl.DateTimeFormat('en-IN', options)
    const formatted = formatter.format(dateObj)
    
    return `${formatted} IST`
  } catch (error) {
    console.error('Date formatting error:', error)
    return '-'
  }
}
