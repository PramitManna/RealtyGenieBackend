# Lead Nurture Dashboard Backend - API Documentation

## Overview Endpoints

### 1. GET `/api/lead-nurture/dashboard/overview`
Returns the main dashboard overview with key stats.

**Query Parameters:**
- `email` (optional) - User email address

**Response:**
```json
{
  "total_leads": 2847,
  "active_campaigns": 24,
  "response_rate": 85.5,
  "conversion_rate": 12.3,
  "avg_response_time": 2,
  "leads_this_month": 347,
  "leads_this_week": 89,
  "campaigns_status": {
    "active": 18,
    "paused": 4,
    "completed": 2,
    "pending": 0
  },
  "recent_activities": [
    {
      "id": 1,
      "type": "email_sent",
      "title": "Sent campaign to 150 leads",
      "description": "Spring Market Update Campaign",
      "timestamp": "2025-12-03T10:30:00",
      "status": "success"
    }
  ],
  "metrics_trend": {
    "week_over_week": 12.5,
    "month_over_month": 34.2,
    "top_performing_campaign": "Spring Market Update",
    "weakest_campaign": "Seasonal Digest"
  }
}
```

---

### 2. GET `/api/lead-nurture/dashboard/metrics`
Returns detailed metrics for dashboard charts and graphs.

**Query Parameters:**
- `email` (optional) - User email address

**Response:**
```json
{
  "daily_leads": [
    {"date": "2025-11-27", "count": 45},
    {"date": "2025-11-28", "count": 52}
  ],
  "response_by_segment": [
    {"segment": "Luxury", "responses": 156, "rate": 88},
    {"segment": "Investment", "responses": 123, "rate": 82}
  ],
  "campaign_performance": [
    {
      "name": "Spring Market",
      "sent": 450,
      "opened": 302,
      "clicked": 85,
      "converted": 12
    }
  ]
}
```

---

### 3. POST `/api/lead-nurture/dashboard/campaign-stats`
Returns detailed stats for a specific campaign.

**Request Body:**
```json
{
  "campaign_id": "123"
}
```

**Response:**
```json
{
  "campaign_id": "123",
  "name": "Spring Market Update",
  "status": "active",
  "created_at": "2025-11-15T10:00:00Z",
  "total_sent": 1250,
  "total_opened": 1062,
  "total_clicked": 284,
  "total_converted": 45,
  "open_rate": 84.96,
  "click_rate": 22.72,
  "conversion_rate": 3.6,
  "bounce_rate": 2.4,
  "unsubscribe_rate": 0.8,
  "segments": [
    {
      "name": "Luxury Buyers",
      "sent": 450,
      "opened": 402,
      "converted": 18
    }
  ]
}
```

---

### 4. GET `/api/lead-nurture/status`
Returns the status of the lead nurture tool.

**Response:**
```json
{
  "status": "operational",
  "feature": "lead-nurture-tool",
  "version": "1.0.0"
}
```

---

## Usage in Frontend

### Fetching Dashboard Overview
```typescript
const fetchOverview = async (userEmail: string) => {
  const response = await fetch(`/api/lead-nurture/dashboard/overview?email=${userEmail}`);
  const data = await response.json();
  return data;
};
```

### Fetching Metrics
```typescript
const fetchMetrics = async (userEmail: string) => {
  const response = await fetch(`/api/lead-nurture/dashboard/metrics?email=${userEmail}`);
  const data = await response.json();
  return data;
};
```

### Fetching Campaign Stats
```typescript
const fetchCampaignStats = async (campaignId: string) => {
  const response = await fetch(`/api/lead-nurture/dashboard/campaign-stats`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ campaign_id: campaignId })
  });
  const data = await response.json();
  return data;
};
```

---

## Database Integration (TODO)

To connect to actual database:

1. **Replace mock data with Supabase queries:**
   - Query `lead_campaigns` table for active_campaigns count
   - Query `leads` table for total_leads count
   - Query `email_responses` table for response_rate calculation
   - Query `conversions` table for conversion_rate

2. **Example Supabase query:**
```python
from lib.supabase_client import get_supabase_client

async def get_user_leads(user_id: str):
    supabase = get_supabase_client()
    response = supabase.table('leads').select('*').eq('user_id', user_id).execute()
    return response.data
```

3. **Add this to `requirements.txt` if not already present:**
   - `supabase>=2.3.0`

---

## Notes

- All endpoints return JSON responses
- Mock data provided for immediate frontend testing
- Timestamps are in ISO 8601 format (UTC)
- Email parameter is optional but recommended for multi-user tracking
