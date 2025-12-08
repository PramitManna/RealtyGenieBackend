# Festive Email Automation Feature

## Overview
The festive email automation feature allows real estate agents to automatically send personalized greeting emails to their leads on major festivals and celebrations throughout the year.

## Features

### 🎯 Automated Sending
- Emails are sent automatically on the festival day at 9:00 AM local time
- One email per lead per festival
- Sent to all leads across all batches for enabled festivals

### 🎉 Supported Festivals
The system includes 12 major festivals celebrated in Vancouver:

1. **Christmas** (Dec 25) 🎄
2. **New Year** (Jan 1) 🎉
3. **Valentine's Day** (Feb 14) 💝
4. **Easter** (Variable) 🐰
5. **Mother's Day** (2nd Sunday in May) 🌸
6. **Father's Day** (3rd Sunday in June) 👔
7. **Canada Day** (Jul 1) 🇨🇦
8. **Halloween** (Oct 31) 🎃
9. **Thanksgiving** (2nd Monday in October) 🦃
10. **Diwali** (Variable) 🪔
11. **Hanukkah** (Variable) 🕎
12. **Chinese New Year** (Variable) 🧧

### ⚙️ User Control
- Toggle each festival on/off individually
- Settings are saved per user
- Changes take effect immediately
- Can be updated anytime before the festival date

## Usage

### For Users (Frontend)

1. **Access the Feature**
   - Navigate to the Lead Nurture Dashboard
   - Click "Trigger Email" button
   - Select the "Festive Emails" tab

2. **Enable/Disable Festivals**
   - Browse through the list of festivals
   - Toggle the switch ON for festivals you want to participate in
   - Toggle OFF to disable automatic sending
   - Settings are saved automatically

3. **Email Delivery**
   - Emails are sent automatically on the festival day
   - All active leads receive the greeting
   - Emails are personalized with lead names and agent information

### For Developers

#### Database Schema

**Table: `festive_email_settings`**
```sql
CREATE TABLE festive_email_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    festive_id VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, festive_id)
);
```

#### API Endpoints

**1. Get Festive Settings**
```http
GET /api/lead-nurture/festive-settings?user_id={user_id}
```

Response:
```json
{
  "settings": {
    "christmas": true,
    "new_year": false,
    "canada_day": true
  }
}
```

**2. Update Festive Setting**
```http
POST /api/lead-nurture/festive-settings
Content-Type: application/json

{
  "user_id": "uuid",
  "festive_id": "christmas",
  "enabled": true
}
```

Response:
```json
{
  "success": true,
  "message": "Festive email enabled"
}
```

**3. Manual Trigger (Testing)**
```http
POST /api/cron/send-festive-emails
```

Response:
```json
{
  "success": true,
  "message": "Festive email job executed",
  "stats": {
    "checked_festivals": ["Christmas"],
    "emails_sent": 150,
    "emails_failed": 2,
    "errors": []
  }
}
```

#### Cron Job Setup

The festive email system requires a daily cron job:

**Recommended Schedule:** Daily at 9:00 AM local time

**Cron Expression:**
```bash
0 9 * * * /path/to/python /path/to/project/trigger_festive_emails.py
```

**Using Render.com:**
```yaml
# render.yaml
jobs:
  - type: cron
    name: festive-email-sender
    schedule: "0 9 * * *"  # Daily at 9 AM UTC
    buildCommand: pip install -r requirements.txt
    startCommand: python -c "from services.cron_service import send_festive_emails; import asyncio; asyncio.run(send_festive_emails())"
```

**Using GitHub Actions:**
```yaml
# .github/workflows/festive-emails.yml
name: Send Festive Emails
on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM UTC
  workflow_dispatch:  # Allow manual trigger

jobs:
  send-festive-emails:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Send festive emails
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          MAILGUN_API_KEY: ${{ secrets.MAILGUN_API_KEY }}
        run: |
          python -c "from services.cron_service import send_festive_emails; import asyncio; asyncio.run(send_festive_emails())"
```

## Email Personalization

Each festive email includes the following personalized elements:

- `{{recipient_name}}` - Lead's name
- `{{agent_name}}` - Agent's full name
- `{{company}}` - Agent's brokerage/company
- `{{city}}` - Agent's primary market
- `{{year}}` - Current year

### Example Template (Christmas)

**Subject:** 🎄 Warm Holiday Wishes from John Smith

**Body:**
```
Dear Sarah Johnson,

Wishing you and your loved ones a wonderful Christmas filled with joy, warmth, and cherished moments!

As we celebrate this special season, I want to take a moment to thank you for being part of our real estate community in Vancouver. Your trust and support mean the world to us.

May the new year bring you prosperity, happiness, and perhaps the perfect home you've been dreaming of!

Warmest holiday wishes,
John Smith
Century 21 Realty
```

## Testing

### 1. Manual Testing (Development)

Test the festive email system without waiting for the actual date:

```python
# In your Python shell or test script
from services.cron_service import send_festive_emails
import asyncio

# This will check today's date and send emails if it matches any festival
stats = asyncio.run(send_festive_emails())
print(stats)
```

### 2. API Testing

```bash
# Test getting settings
curl -X GET "http://localhost:8000/api/lead-nurture/festive-settings?user_id=YOUR_USER_ID"

# Test enabling a festival
curl -X POST "http://localhost:8000/api/lead-nurture/festive-settings" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID",
    "festive_id": "christmas",
    "enabled": true
  }'

# Test manual trigger
curl -X POST "http://localhost:8000/api/cron/send-festive-emails"
```

### 3. Frontend Testing

1. Open the Email Trigger Modal
2. Switch to "Festive Emails" tab
3. Toggle festivals on/off
4. Verify settings persist after page reload

## Migration

To set up the database:

```bash
# Run the migration
psql $DATABASE_URL -f migrations/008_add_festive_email_settings.sql

# Or via Supabase dashboard SQL editor
# Copy and paste the contents of 008_add_festive_email_settings.sql
```

## Monitoring

### Check Queue Health
```bash
curl http://localhost:8000/api/queue-health
```

### View Logs
```bash
# Check festive email sending logs
grep "Festive" logs/app.log

# Check for errors
grep "ERROR.*festive" logs/app.log -i
```

## Best Practices

1. **Test Before Major Holidays**
   - Run manual trigger test 1 week before
   - Verify email templates render correctly
   - Check personalization works for all leads

2. **Monitor Email Deliverability**
   - Check Mailgun dashboard for bounces
   - Monitor spam complaints
   - Keep templates warm and friendly

3. **User Communication**
   - Notify users about new festivals added
   - Provide preview of email templates
   - Allow customization in future versions

4. **Performance**
   - Batch email sending for large lead lists
   - Implement rate limiting if needed
   - Monitor API response times

## Future Enhancements

- [ ] Allow users to customize email templates
- [ ] Add more regional festivals
- [ ] Support multiple languages
- [ ] Add email preview before sending
- [ ] Include unsubscribe option
- [ ] Track open rates and engagement
- [ ] A/B testing for email content
- [ ] Schedule emails at optimal send times

## Troubleshooting

### Emails Not Sending

1. Check cron job is running:
   ```bash
   # View cron logs
   tail -f /var/log/cron.log
   ```

2. Verify Mailgun credentials:
   ```python
   from services.mailgun_service import mailgun_service
   print(mailgun_service is not None)
   ```

3. Check user has enabled the festival:
   ```sql
   SELECT * FROM festive_email_settings 
   WHERE user_id = 'USER_ID' AND festive_id = 'christmas';
   ```

### Database Issues

```sql
-- Check table exists
\dt festive_email_settings

-- View all settings
SELECT * FROM festive_email_settings;

-- Reset settings for testing
DELETE FROM festive_email_settings WHERE user_id = 'TEST_USER_ID';
```

## Support

For issues or questions:
- Check backend logs: `tail -f logs/app.log`
- Review Mailgun dashboard for delivery issues
- Test with manual trigger endpoint
- Verify database migrations ran successfully
