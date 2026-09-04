"""
Timezone Utility Functions
Ensures all timestamps are in IST (Asia/Kolkata) timezone
"""

from datetime import datetime
import pytz

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    """Get current datetime in IST"""
    return datetime.now(IST)

def utc_to_ist(utc_dt):
    """
    Convert UTC datetime to IST
    Args:
        utc_dt: datetime object or ISO format string
    Returns:
        datetime object in IST or formatted string
    """
    if utc_dt is None:
        return None
    
    try:
        # If it's a string, parse it
        if isinstance(utc_dt, str):
            # Handle ISO format with Z or +00:00
            utc_dt_str = utc_dt.replace('Z', '+00:00')
            dt = datetime.fromisoformat(utc_dt_str)
        else:
            dt = utc_dt
        
        # If datetime is naive, assume it's UTC
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        # Convert to IST
        ist_dt = dt.astimezone(IST)
        return ist_dt
    except Exception as e:
        print(f"Error converting UTC to IST: {e}")
        return None

def ist_to_mysql_format(ist_dt):
    """
    Convert IST datetime to MySQL format string
    Args:
        ist_dt: datetime object in IST
    Returns:
        String in format 'YYYY-MM-DD HH:MM:SS'
    """
    if ist_dt is None:
        return None
    
    try:
        return ist_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error formatting IST datetime: {e}")
        return None

def utc_to_ist_string(utc_dt):
    """
    Convert UTC datetime to IST formatted string
    Args:
        utc_dt: datetime object or ISO format string
    Returns:
        String in format 'YYYY-MM-DD HH:MM:SS' in IST
    """
    ist_dt = utc_to_ist(utc_dt)
    if ist_dt:
        return ist_to_mysql_format(ist_dt)
    return None

def format_ist_datetime(dt):
    """
    Format datetime for display (IST)
    Args:
        dt: datetime object
    Returns:
        String in format 'DD-MM-YYYY HH:MM:SS'
    """
    if dt is None:
        return None
    
    try:
        # If datetime is naive, assume it's already in IST (from database)
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            # Convert to IST if it's in another timezone
            dt = dt.astimezone(IST)
        
        return dt.strftime('%d-%m-%Y %H:%M:%S')
    except Exception as e:
        print(f"Error formatting datetime: {e}")
        return None

def parse_mudrape_timestamp(timestamp_str):
    """
    Parse Mudrape API timestamp (UTC) and convert to IST
    Args:
        timestamp_str: ISO format string from Mudrape (e.g., "2026-02-22T06:51:35.952Z")
    Returns:
        String in MySQL format 'YYYY-MM-DD HH:MM:SS' in IST
    """
    if not timestamp_str:
        return None
    
    try:
        # Parse ISO format
        timestamp_str = timestamp_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(timestamp_str)
        
        # Convert to IST
        ist_dt = dt.astimezone(IST)
        
        # Return in MySQL format
        return ist_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error parsing Mudrape timestamp: {e}")
        return None

def get_ist_timestamp_for_display(dt):
    """
    Get IST timestamp for API response (ISO format)
    Args:
        dt: datetime object from database
    Returns:
        String in ISO format with IST timezone
    """
    if dt is None:
        return None
    
    try:
        # If datetime is naive, assume it's already in IST (from database)
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            # Convert to IST if it's in another timezone
            dt = dt.astimezone(IST)
        
        # Return in ISO format
        return dt.isoformat()
    except Exception as e:
        print(f"Error getting IST timestamp: {e}")
        return None

# Example usage:
if __name__ == '__main__':
    # Current IST time
    now_ist = get_ist_now()
    print(f"Current IST: {now_ist}")
    print(f"Formatted: {format_ist_datetime(now_ist)}")
    print(f"MySQL format: {ist_to_mysql_format(now_ist)}")
    
    # Convert UTC to IST
    utc_time = "2026-02-22T06:51:35.952Z"
    ist_time = utc_to_ist_string(utc_time)
    print(f"\nUTC: {utc_time}")
    print(f"IST: {ist_time}")
    
    # Parse Mudrape timestamp
    mudrape_ts = "2026-02-22T06:51:35.952Z"
    ist_ts = parse_mudrape_timestamp(mudrape_ts)
    print(f"\nMudrape UTC: {mudrape_ts}")
    print(f"IST MySQL: {ist_ts}")
