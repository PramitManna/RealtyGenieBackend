# 🏠 RealtyGenie Backend API

AI-powered email automation system for real estate professionals. Generate personalized, professional emails for lead nurturing campaigns with Google Gemini AI and automated delivery via Mailgun.

## 🚀 Quick Start

### Local Development
```bash
# 1. Clone and setup
git clone <your-repo>
cd realtygeniebackend2

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 5. Run the server
uvicorn main:app --reload
```

### Docker Development
```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build Docker image only
docker build -t realtygenie-backend .
docker run -p 8000:8000 --env-file .env realtygenie-backend
```

## 🌐 Production Deployment (Render)

**One-Click Deploy:** See [RENDER_DEPLOY.md](./RENDER_DEPLOY.md) for detailed instructions.

**Quick Deploy Steps:**
1. Push code to GitHub
2. Create Render Web Service
3. Set environment variables in Render dashboard
4. Deploy with Docker environment

**Test Deployment:**
```bash
python test_deployment.py https://your-app.onrender.com
```

## 📋 API Endpoints

### Core Endpoints
- `GET /api/health` - Health check
- `GET /api/` - API documentation  
- `GET /docs` - Interactive Swagger UI
- `GET /redoc` - Alternative API docs

### Email Automation
- `POST /api/lead-nurture/trigger-email` - Send AI-generated emails

### Lead Management  
- `POST /api/leads/clean` - Clean and validate lead data
- `POST /api/leads/validate-single` - Validate single lead
- `POST /api/leads/validate-batch` - Validate multiple leads

### Campaign Management
- `GET /api/campaigns/` - List campaigns
- `POST /api/campaigns/` - Create campaign
- `GET /api/batches/` - List lead batches

## 🔧 Configuration

### Required Environment Variables

```bash
# Supabase Database
SUPABASE_URL=https://your-project.supabase.co  
SUPABASE_KEY=your-supabase-anon-key

# Google Cloud (Gemini AI + Vision)
PROJECT_ID=your-google-cloud-project
LOCATION=us-central1

# Mailgun Email Delivery
MAILGUN_API_KEY=your-mailgun-key
MAILGUN_DOMAIN=your-domain.mailgun.org
```

### Google Credentials Setup

**For Local Development:**
```bash
GOOGLE_APPLICATION_CREDENTIALS=./creds/service-account.json
```

**For Production (Render):**
```bash
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
```

## 🎯 Key Features

### ✨ AI Email Generation
- **Google Gemini Integration**: Generates personalized, professional email content
- **Smart Placeholders**: Automatically replaces `{name}` with lead names
- **Tone Control**: Professional, friendly, informative, and urgent tones
- **Purpose-Driven**: Market updates, property showcases, follow-ups, etc.

### 📧 Email Automation  
- **Mailgun Delivery**: Reliable email delivery with tracking
- **Batch Processing**: Send to multiple leads simultaneously  
- **CC to Realtor**: Automatic copy to realtor for transparency
- **Error Handling**: Robust failure handling and reporting

### 🎨 Professional Templates
- **Premium Design**: Professional color scheme and layout
- **Responsive**: Works on desktop and mobile clients
- **Branding**: Consistent realtor branding and signature

### 📊 Lead Management
- **Data Cleaning**: Automated lead data validation and cleaning
- **Batch Organization**: Group leads by campaigns and criteria  
- **Integration Ready**: Works with existing CRM systems

## 🛠️ Tech Stack

- **FastAPI**: Modern Python web framework
- **Google Vertex AI**: Gemini 2.5 Flash for content generation
- **Google Cloud Vision**: OCR and document processing
- **Supabase**: Database and authentication
- **Mailgun**: Email delivery service
- **Docker**: Containerization and deployment
- **Render**: Cloud hosting platform

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`  
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI**: `http://localhost:8000/openapi.json`

## 🧪 Testing

```bash
# Run local tests
python test_deployment.py http://localhost:8000

# Test production deployment  
python test_deployment.py https://your-app.onrender.com

# Manual API testing
curl http://localhost:8000/api/health
```

## 🔒 Security

- **Environment Variables**: All secrets stored as env vars
- **CORS Configuration**: Configurable cross-origin settings
- **Input Validation**: Pydantic models for request validation
- **Error Handling**: Secure error responses without data leaks

## 📝 Development

### Project Structure
```
realtygeniebackend2/
├── main.py                 # FastAPI application entry
├── routers/                # API route definitions
│   ├── health.py          # Health and status endpoints  
│   ├── lead_nurture.py    # Email automation endpoints
│   ├── leads.py           # Lead management endpoints
│   └── campaigns.py       # Campaign management
├── services/               # Business logic services
│   ├── gemini_service.py  # AI email generation
│   ├── mailgun_service.py # Email delivery
│   └── supabase_service.py # Database operations
├── utils/                  # Utility functions
├── creds/                  # Google Cloud credentials (local only)
└── requirements.txt        # Python dependencies
```

### Adding New Features

1. **Create Router**: Add new endpoint in `routers/`
2. **Business Logic**: Implement in appropriate service  
3. **Models**: Define Pydantic models for validation
4. **Register**: Add router to `main.py`
5. **Test**: Update `test_deployment.py`

## 🐛 Troubleshooting

### Common Issues

**Google API Errors:**
- Verify credentials are properly configured
- Check PROJECT_ID and LOCATION settings
- Ensure APIs are enabled in Google Cloud Console

**Email Delivery Issues:**  
- Verify Mailgun API key and domain
- Check domain DNS configuration
- Review Mailgun dashboard for delivery status

**Database Connection:**
- Confirm Supabase URL and key are correct
- Verify Supabase project is active
- Check network connectivity

### Debug Commands

```bash  
# Check container logs
docker logs realtygenie-backend

# Test individual services
python -c "from services.gemini_service import GeminiService; g=GeminiService()"
python -c "from services.mailgun_service import MailgunService; m=MailgunService()"

# Validate environment
python -c "import os; print('✅' if os.getenv('SUPABASE_URL') else '❌', 'SUPABASE_URL')"
```

## 📞 Support

- **Documentation**: [RENDER_DEPLOY.md](./RENDER_DEPLOY.md)
- **API Reference**: `GET /docs` endpoint
- **Test Suite**: `python test_deployment.py`

---

🎉 **Ready to revolutionize real estate lead nurturing with AI-powered automation!**