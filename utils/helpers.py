import uuid
import qrcode
import base64
from io import BytesIO
from datetime import datetime, timedelta
from typing import Dict, Any
import time


def generate_uuid() -> str:
    """Generate a unique UUID string"""
    return str(uuid.uuid4())


def generate_qr_code(data: Dict[Any, Any]) -> str:
    """Generate QR code and return as base64 string"""
    # Convert data to string for QR code
    qr_string = f"{data['dia_aula_id']}|{data['timestamp']}|{data['action']}"
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_string)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def parse_qr_data(qr_string: str) -> Dict[str, Any]:
    """Parse QR code string back to data"""
    try:
        parts = qr_string.split('|')
        if len(parts) != 3:
            raise ValueError("Invalid QR code format")
        
        return {
            "dia_aula_id": parts[0],
            "timestamp": int(parts[1]),
            "action": parts[2]
        }
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid QR code data: {str(e)}")


def validate_qr_timestamp(timestamp: int, max_age_minutes: int = 30) -> bool:
    """Validate QR code timestamp (check if not too old)"""
    current_time = int(time.time())
    max_age_seconds = max_age_minutes * 60
    
    return (current_time - timestamp) <= max_age_seconds


def combine_date_time(date_str: str, time_str: str) -> datetime:
    """Combine date and time strings into datetime object"""
    try:
        # Parse date (YYYY-MM-DD)
        date_part = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Parse time (HH:MM)
        time_part = datetime.strptime(time_str, "%H:%M").time()
        
        # Combine
        return datetime.combine(date_part, time_part)
    except ValueError as e:
        raise ValueError(f"Invalid date/time format: {str(e)}")


def calculate_attendance_percentage(present: int, total: int) -> float:
    """Calculate attendance percentage"""
    if total == 0:
        return 0.0
    return round((present / total) * 100, 2)
