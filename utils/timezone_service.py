"""
Timezone Utility Service
Handles timezone calculations for recipient-aware email scheduling
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import pytz
from zoneinfo import ZoneInfo


def get_recipient_timezone(lead_data: dict) -> str:
    """
    Determine recipient's timezone from lead data.
    Priority: lead.timezone > lead.city > default 'America/Toronto'
    
    Args:
        lead_data: Dictionary with lead information (should include timezone and/or city)
    
    Returns:
        Timezone string (e.g., 'America/New_York')
    """
    # If lead has explicit timezone, use it
    if lead_data.get("timezone"):
        return lead_data["timezone"]
    
    # Otherwise, map city to timezone if available
    city_timezone_map = {
        "Toronto": "America/Toronto",
        "Vancouver": "America/Vancouver",
        "Montreal": "America/Toronto",
        "Calgary": "America/Denver",
        "Edmonton": "America/Denver",
        "Ottawa": "America/Toronto",
        "Winnipeg": "America/Chicago",
        "Quebec": "America/Toronto",
        "Hamilton": "America/Toronto",
        "Kitchener": "America/Toronto",
        "London": "America/Toronto",
        "Victoria": "America/Vancouver",
        "Halifax": "America/Halifax",
        "St. John's": "America/St_Johns",
        "Saskatoon": "America/Chicago",
        "Regina": "America/Chicago",
    }
    
    city = lead_data.get("city", "")
    if city in city_timezone_map:
        return city_timezone_map[city]
    
    # Default to Toronto timezone
    return "America/Toronto"


def calculate_send_time_in_timezone(
    base_utc_time: datetime,
    target_timezone: str,
    target_hour: int = 8,
    target_minute: int = 0,
) -> datetime:
    """
    Calculate send time in UTC for a specific local time in recipient's timezone.
    If the calculated time is in the past, move to the next day.
    
    Args:
        base_utc_time: Base UTC time (campaign creation or send day offset)
        target_timezone: Recipient's timezone string (e.g., 'America/New_York')
        target_hour: Hour in recipient's local time (0-23, default 8 for 8 AM)
        target_minute: Minute in recipient's local time (0-59, default 0)
    
    Returns:
        datetime in UTC when email should be sent (targeting recipient's local time)
    
    Example:
        # Schedule email for 8 AM on day 10 in recipient's Toronto time
        base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # Jan 1 noon UTC
        send_utc = calculate_send_time_in_timezone(base, "America/Toronto", 8, 0)
        # Returns approximately 2024-01-11 13:00:00 UTC (8 AM Toronto time on Jan 11)
    """
    if not base_utc_time.tzinfo:
        base_utc_time = base_utc_time.replace(tzinfo=pytz.UTC)
    
    # Get timezone object
    tz = pytz.timezone(target_timezone)
    
    # Convert base UTC time to recipient's local time
    local_time = base_utc_time.astimezone(tz)
    
    # Create target local time (same date, but at target_hour:target_minute)
    target_local = local_time.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    # If target time is in the past, move to next day
    if target_local < local_time:
        target_local = target_local + timedelta(days=1)
    
    # Convert back to UTC
    send_utc = target_local.astimezone(pytz.UTC)
    
    return send_utc


def is_within_send_window(
    recipient_utc_time: datetime,
    recipient_timezone: str,
    start_hour: int = 8,
    end_hour: int = 20,
) -> bool:
    """
    Check if a UTC time falls within the recipient's send window (e.g., 8 AM - 8 PM).
    
    Args:
        recipient_utc_time: Time in UTC
        recipient_timezone: Recipient's timezone
        start_hour: Start of send window in local time (default 8 for 8 AM)
        end_hour: End of send window in local time (default 20 for 8 PM)
    
    Returns:
        True if time is within send window, False otherwise
    """
    if not recipient_utc_time.tzinfo:
        recipient_utc_time = recipient_utc_time.replace(tzinfo=pytz.UTC)
    
    tz = pytz.timezone(recipient_timezone)
    local_time = recipient_utc_time.astimezone(tz)
    
    return start_hour <= local_time.hour < end_hour


def get_next_valid_send_time(
    current_utc_time: datetime,
    recipient_timezone: str,
    start_hour: int = 8,
    end_hour: int = 20,
) -> datetime:
    """
    Get the next valid send time if current time is outside the send window.
    If current time is after end_hour, moves to start_hour next day.
    If current time is before start_hour, moves to start_hour same day.
    
    Args:
        current_utc_time: Current UTC time
        recipient_timezone: Recipient's timezone
        start_hour: Start of send window (default 8)
        end_hour: End of send window (default 20)
    
    Returns:
        Next valid send time in UTC
    """
    if not current_utc_time.tzinfo:
        current_utc_time = current_utc_time.replace(tzinfo=pytz.UTC)
    
    tz = pytz.timezone(recipient_timezone)
    local_time = current_utc_time.astimezone(tz)
    
    # If before start window, move to start_hour today
    if local_time.hour < start_hour:
        target_local = local_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    # If after end window, move to start_hour tomorrow
    elif local_time.hour >= end_hour:
        target_local = (local_time + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
    else:
        # Already within window
        return current_utc_time
    
    # Convert back to UTC
    return target_local.astimezone(pytz.UTC)


def get_local_time_display(
    utc_time: datetime,
    timezone_str: str,
    format_str: str = "%I:%M %p %Z",
) -> str:
    """
    Convert UTC time to recipient's local time for display.
    
    Args:
        utc_time: Time in UTC
        timezone_str: Recipient's timezone
        format_str: Format string for display (default: "08:30 AM EST")
    
    Returns:
        Formatted time string in recipient's timezone
    """
    if not utc_time.tzinfo:
        utc_time = utc_time.replace(tzinfo=pytz.UTC)
    
    tz = pytz.timezone(timezone_str)
    local_time = utc_time.astimezone(tz)
    
    return local_time.strftime(format_str)


def calculate_campaign_queue_times(
    campaign_created_at: datetime,
    recipient_timezone: str,
    send_window_start: int = 8,
    send_window_end: int = 20,
) -> dict:
    """
    Calculate all send times (D0, D10, D20, D30) for a campaign in recipient's timezone.
    
    Args:
        campaign_created_at: Campaign creation time (UTC)
        recipient_timezone: Recipient's timezone
        send_window_start: Start of send window (default 8 AM)
        send_window_end: End of send window (default 8 PM)
    
    Returns:
        Dict with send times for each day:
        {
            "day_0": {"utc": datetime, "local": str, "timezone": str},
            "day_10": {"utc": datetime, "local": str, "timezone": str},
            "day_20": {"utc": datetime, "local": str, "timezone": str},
            "day_30": {"utc": datetime, "local": str, "timezone": str},
        }
    """
    if not campaign_created_at.tzinfo:
        campaign_created_at = campaign_created_at.replace(tzinfo=pytz.UTC)
    
    schedule = {}
    
    for day_offset in [0, 10, 20, 30]:
        # Calculate base time (day offset from campaign creation)
        base_utc = campaign_created_at + timedelta(days=day_offset)
        
        # Calculate send time in recipient's send window
        send_utc = calculate_send_time_in_timezone(
            base_utc,
            recipient_timezone,
            target_hour=send_window_start,
            target_minute=0,
        )
        
        # If outside window, get next valid time
        if not is_within_send_window(send_utc, recipient_timezone, send_window_start, send_window_end):
            send_utc = get_next_valid_send_time(send_utc, recipient_timezone, send_window_start, send_window_end)
        
        local_display = get_local_time_display(send_utc, recipient_timezone)
        
        schedule[f"day_{day_offset}"] = {
            "utc": send_utc.isoformat(),
            "local": local_display,
            "timezone": recipient_timezone,
        }
    
    return schedule