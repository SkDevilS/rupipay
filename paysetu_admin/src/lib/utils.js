import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount) {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '₹0.00'
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(Number(amount))
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
    // If date is already in 'YYYY-MM-DD HH:MM:SS' format (IST from backend)
    // Parse it directly without timezone conversion
    if (typeof date === 'string' && date.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)) {
      const [datePart, timePart] = date.split(' ')
      const [year, month, day] = datePart.split('-')
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      const monthName = monthNames[parseInt(month) - 1]
      
      return `${day} ${monthName} ${year}, ${timePart} IST`
    }
    
    // Fallback for other date formats
    const dateObj = new Date(date)
    if (isNaN(dateObj.getTime())) return '-'
    
    const options = {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata'
    }
    
    const formatter = new Intl.DateTimeFormat('en-IN', options)
    const formatted = formatter.format(dateObj)
    
    return `${formatted} IST`
  } catch (error) {
    console.error('Date formatting error:', error)
    return '-'
  }
}
