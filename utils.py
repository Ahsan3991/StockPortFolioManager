from datetime import datetime

def normalize_date_format(date_str):
    """
    Convert various date formats to YYYY-MM-DD for consistent storage.
    
    Args:
        date_str: Date string in various formats, or datetime object
        
    Returns:
        str: Date in YYYY-MM-DD format, or original string if parsing fails
    """
    if not date_str:
        return date_str
        
    try:
        # If it's already a datetime object, just format it
        if isinstance(date_str, datetime):
            return date_str.strftime('%Y-%m-%d')
            
        # Try common date formats
        formats = [
            '%Y-%m-%d',  # 2025-03-12
            '%d-%m-%Y',  # 12-03-2025
            '%m-%d-%Y',  # 03-12-2025
            '%Y/%m/%d',  # 2025/03/12
            '%d/%m/%Y',  # 12/03/2025
            '%m/%d/%Y',  # 03/12/2025
            '%B %d, %Y', # March 12, 2025
            '%d %B %Y',  # 12 March 2025
            '%b %d, %Y', # Mar 12, 2025
            '%Y-%m-%dT%H:%M:%S',  # ISO format with time
            '%Y%m%d'     # 20250312
        ]
            
        # If it's a string, try different formats
        if isinstance(date_str, str):
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
                
        # If we get here, none of the formats worked
        # Return the original string instead of raising an error
        return str(date_str)
    except Exception:
        # If there's any error, return the original string
        return str(date_str)