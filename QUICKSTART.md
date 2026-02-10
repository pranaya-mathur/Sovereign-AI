# Phase 5 Quick Start ⚡

**Get Phase 5 running in 3 commands!**

## Option 1: Automated Startup (Recommended)

```bash
# 1. Clone and setup
git clone https://github.com/pranaya-mathur/LLM-Observability.git
cd LLM-Observability
git checkout phase5-security-dashboard

# 2. Install dependencies
pip install -r requirements_phase5.txt

# 3. Start everything!
chmod +x start_phase5.sh
./start_phase5.sh
```

That's it! 🎉

**What you get:**
- 📊 API running on http://localhost:8000
- 🎨 Dashboard on http://localhost:8501
- 📚 Docs at http://localhost:8000/docs

**Default Login:**
- Username: `admin`
- Password: `admin123`

**To stop:**
```bash
./stop_phase5.sh
```

---

## Option 2: Manual Startup

### Terminal 1: Start API
```bash
python -m uvicorn api.app_complete:app --reload --port 8000
```

### Terminal 2: Start Dashboard
```bash
streamlit run dashboard/admin_dashboard.py
```

### Terminal 3: Run Tests
```bash
python scripts/test_phase5_complete.py
```

---

## What to Test

### 1. Dashboard
Open http://localhost:8501
- ✅ Login with `admin / admin123`
- ✅ Check Overview page (tier charts)
- ✅ User Management (update roles/tiers)
- ✅ Detection Monitor (test responses)

### 2. API (via Browser)
Open http://localhost:8000/docs
- ✅ Click "Authorize"
- ✅ Login to get token
- ✅ Try `/api/detect` endpoint
- ✅ Test other endpoints

### 3. Automated Tests
```bash
python scripts/test_phase5_complete.py
```

Should see:
```
🎉 All tests passed! Phase 5 is fully functional.
```

---

## Quick API Test (curl)

```bash
# 1. Get token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login?username=admin&password=admin123" | jq -r '.access_token')

# 2. Test detection
curl -X POST "http://localhost:8000/api/detect" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "RAG stands for Ruthenium-Arsenic Growth"
  }' | jq

# 3. Check health
curl http://localhost:8000/api/monitoring/health | jq

# 4. List users (admin only)
curl -X GET "http://localhost:8000/api/admin/users" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Features to Explore

### 🔐 Authentication
- JWT tokens with 24-hour expiration
- Role-based access (admin/user/viewer)
- Secure password hashing (bcrypt)

### 🚦 Rate Limiting
- **Free:** 100 requests/hour
- **Pro:** 1,000 requests/hour
- **Enterprise:** 10,000 requests/hour

### 🛡️ 3-Tier Detection
1. **Tier 1:** Regex patterns (<1ms)
2. **Tier 2:** Semantic embeddings (5-10ms)
3. **Tier 3:** LLM agent reasoning (50-100ms)

### 👥 User Management
- Create/update/delete users
- Change roles and tiers
- Enable/disable accounts

### 📊 Monitoring
- Real-time tier statistics
- System health checks
- Detection logs

---

## Troubleshooting

### API won't start?
```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
kill -9 $(lsof -ti:8000)
```

### Dashboard won't connect?
```bash
# Verify API is running
curl http://localhost:8000/

# Should return service info
```

### Database issues?
```bash
# Reset database
rm llm_observability.db
python -m uvicorn api.app_complete:app --reload
```

---

## Next Steps

1. ✅ **Test locally** (you are here!)
2. 📦 **Review code** in your IDE
3. 🔀 **Merge to main** when ready
4. 🚀 **Deploy** to production

---

## Documentation

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Complete testing instructions
- **[PHASE5_COMPLETE.md](PHASE5_COMPLETE.md)** - Full documentation
- **API Docs:** http://localhost:8000/docs

---

## Default Accounts

| User | Username | Password | Role | Tier |
|------|----------|----------|------|------|
| Admin | `admin` | `admin123` | admin | enterprise |
| Test User | `testuser` | `test123` | user | free |

**⚠️ Change these passwords in production!**

---

## Support

For issues:
1. Check logs: `tail -f logs/api.log`
2. Review [TESTING_GUIDE.md](TESTING_GUIDE.md)
3. Open GitHub issue

---

**Happy Testing! 🎉**

Phase 5 is production-ready and fully functional.
