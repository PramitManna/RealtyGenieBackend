# RealtyGenie Backend - Render Deployment Guide

## 🚀 Quick Deploy to Render

### Prerequisites
1. GitHub repository with this code
2. Render account (free tier works)
3. Google Cloud credentials JSON file
4. Environment variables ready

### Step 1: Environment Setup

In your Render dashboard, set these environment variables as **secrets**:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Google Cloud Configuration  
PROJECT_ID=your-google-cloud-project-id
LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/app/creds/realtygenie-55126509a168.json

# Mailgun Configuration
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=your-mailgun-domain

# Optional: Additional settings
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

### Step 2: Google Credentials Setup

**Option A: Environment Variable (Recommended)**
1. Copy your Google Cloud service account JSON content
2. In Render dashboard, create environment variable:
   - Key: `GOOGLE_CREDENTIALS_JSON`
   - Value: [paste entire JSON content]

**Option B: File Upload**
1. Ensure `creds/realtygenie-55126509a168.json` exists in your repo
2. ⚠️ **Security Warning**: Only use this for testing, not production

### Step 3: Deploy to Render

**Automatic Deployment:**
1. Fork/push this repo to GitHub
2. Connect your Render account to GitHub
3. Create new "Web Service" from dashboard
4. Select this repository
5. Use these settings:
   - **Environment**: `Docker`
   - **Dockerfile Path**: `./Dockerfile`
   - **Build Command**: *(leave empty - uses Dockerfile)*
   - **Start Command**: *(leave empty - uses Dockerfile CMD)*

**Manual Configuration:**
```yaml
# Service Settings
Name: realtygenie-backend
Environment: Docker  
Region: Oregon (recommended)
Branch: main
Root Directory: .
Build Command: (empty)
Start Command: (empty)
```

### Step 4: Health Check Configuration

Render will automatically use the health check defined in Dockerfile:
- **Path**: `/api/health`
- **Initial Delay**: 40 seconds
- **Interval**: 30 seconds

### Step 5: Verify Deployment

Once deployed, test these endpoints:
```bash
# Health check
GET https://your-app.onrender.com/api/health

# API documentation
GET https://your-app.onrender.com/docs

# Test trigger email (requires auth)
POST https://your-app.onrender.com/api/lead-nurture/trigger-email
```

## 🔧 Local Development

```bash
# Build and run with Docker
docker-compose up --build

# Or run locally
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn main:app --reload
```

## 📊 Monitoring & Logs

- **Render Logs**: Available in dashboard under "Logs" tab
- **Health Monitoring**: Built-in health checks every 30s
- **Metrics**: Available in Render dashboard

## 🔒 Security Notes

1. **Never commit `.env` files** - use Render environment variables
2. **Google Credentials**: Use environment variable method in production
3. **API Keys**: All sensitive data should be in Render secrets
4. **CORS**: Currently set to allow all origins - restrict in production

## 🚨 Troubleshooting

### Common Issues:

**Build Fails:**
- Check Python version compatibility (using 3.11)
- Verify all requirements.txt dependencies are available
- Review build logs for specific error messages

**Health Check Fails:**
- Ensure `/api/health` endpoint is accessible
- Check if PORT environment variable is properly set
- Verify all required environment variables are set

**Google API Errors:**
- Confirm `GOOGLE_CREDENTIALS_JSON` is properly set
- Verify `PROJECT_ID` and `LOCATION` are correct
- Check Google Cloud API quotas and billing

**Database Connection Issues:**
- Verify Supabase URL and key are correct
- Check Supabase project is active and accessible
- Confirm network connectivity from Render to Supabase

### Debug Commands:

```bash
# Check container status
docker ps

# View application logs  
docker logs realtygenie-backend

# Test health endpoint locally
curl http://localhost:8000/api/health
```

## 📈 Production Optimization

For production workloads, consider:

1. **Upgrade Render Plan**: Move from Starter to Standard for better performance
2. **Add Redis**: For caching and session management
3. **Configure CDN**: For static assets and API caching
4. **Set up Monitoring**: Use external monitoring services
5. **Database Optimization**: Configure connection pooling
6. **Error Tracking**: Integrate Sentry or similar service

## 🔄 CI/CD Pipeline

The deployment supports automatic updates:
- Push to `main` branch triggers automatic deployment
- Health checks ensure zero-downtime deployments
- Rollback available through Render dashboard

---

🎉 **Your RealtyGenie Backend should now be live and ready for production use!**

For support, check the logs in Render dashboard or review the troubleshooting section above.