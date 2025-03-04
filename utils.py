from datetime import datetime
def normalize_date_format(date_str):
    """Convert various date formats to YYYY-MM-DD for consistent storage"""
    if not date_str:
        return date_str
        
    try:
        # Try common date formats
        formats = ['%Y/%m/%d', '%d-%m-%Y', '%Y-%m-%d', '%B %d, %Y']
        
        # If it's already a datetime object, just format it
        if isinstance(date_str, datetime):
            return date_str.strftime('%Y-%m-%d')
            
        # If it's a string, try different formats
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
                
        # If we get here, none of the formats worked
        return date_str
    except Exception:
        # If there's any error, return the original
        return date_str