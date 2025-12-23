# Stage 3: Frontend Integration

## Overview
Stage 3 focuses on integrating the backend API (Stage 2) with the frontend application deployed on Vercel. This document covers backend changes required for frontend integration.

**Frontend Repository**: Separate repo at [frontend-repo-url]  
**Frontend Deployment**: Vercel at https://medical-extraction.vercel.app  
**Backend API**: EC2 at http://<ec2-ip>:8080

## Backend Changes for Stage 3

### CORS Configuration

**Date**: December 22, 2025  
**Commit**: 123665e

#### Changes Made
Updated CORS origins from wildcard (`*`) to specific Vercel domains:

**Production Domain**:
```
https://medical-extraction.vercel.app
```

**Preview Deployments**:
```
https://*.vercel.app
```

#### Files Updated

**1. config/deployment.yml**
```yaml
gateway:
  api_port: 8080
  # CORS origins: Comma-separated list for production + preview deployments
  cors_origins: "https://medical-extraction.vercel.app,https://*.vercel.app"
```

**2. docker-compose.yml** 
```yaml
environment:
  # CORS configuration (restricted to Vercel domains for Stage 3)
  - CORS_ORIGINS=${CORS_ORIGINS:-*}
```

#### Implementation Details

The FastAPI gateway (`gateway/main.py`) handles CORS via comma-separated environment variable:

```python
allowed_origins = os.getenv("CORS_ORIGINS", "*")
origins_list = [allowed_origins] if allowed_origins == "*" else allowed_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

**Behavior**:
- If `CORS_ORIGINS="*"`: Allow all origins (development only)
- If `CORS_ORIGINS="domain1,domain2"`: Allow only specified origins
- Supports wildcard patterns like `https://*.vercel.app`

### Deployment

To apply CORS changes:

```bash
# 1. Commit changes to config files
git add config/deployment.yml docker-compose.yml
git commit -m "config: restrict CORS to Vercel domains"
git push

# 2. Redeploy gateway (no need to rebuild image)
poetry run python scripts/deploy.py --skip-start
```

**Note**: CORS configuration is applied via environment variables, so no Docker image rebuild is required. The `deploy.py` script will:
1. Pull latest docker-compose.yml from repo
2. Set `CORS_ORIGINS` environment variable from config
3. Restart containers with new configuration

### Verification

#### Test CORS Preflight
```bash
# Test from production domain
curl -X OPTIONS http://<ec2-ip>:8080/api/v1/extract \
  -H "Origin: https://medical-extraction.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -v

# Expected: HTTP 200 with CORS headers
# Access-Control-Allow-Origin: https://medical-extraction.vercel.app
# Access-Control-Allow-Methods: *
# Access-Control-Allow-Headers: *
```

#### Test from Frontend
1. Open https://medical-extraction.vercel.app
2. Submit a medical text for extraction
3. Check browser console for CORS errors
4. Verify API response is received

#### Test Preview Deployments
```bash
# Test from preview deployment
curl -X OPTIONS http://<ec2-ip>:8080/api/v1/extract \
  -H "Origin: https://my-branch-username.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

### Adding More Origins

To add additional allowed origins (e.g., local development):

**Option 1: Update config/deployment.yml**
```yaml
cors_origins: "https://medical-extraction.vercel.app,https://*.vercel.app,http://localhost:3000"
```

**Option 2: Environment variable override (temporary)**
```bash
# On EC2 instance via SSM
export CORS_ORIGINS="https://medical-extraction.vercel.app,http://localhost:3000"
docker compose restart gateway
```

### Security Considerations

**Current Configuration**:
- ✅ Production domain whitelisted
- ✅ Preview deployments supported (via wildcard)
- ✅ Credentials allowed for cookies/auth
- ⚠️ All HTTP methods allowed (`*`)
- ⚠️ All headers allowed (`*`)

**Future Hardening** (Post-Stage 3):
- Restrict `allow_methods` to `["GET", "POST", "OPTIONS"]`
- Restrict `allow_headers` to specific headers
- Remove wildcard for preview deployments if not needed
- Add rate limiting per origin

## Stage 3 Status

### Completed ✅
- CORS configuration updated for Vercel domains
- Backend changes committed and pushed
- Documentation created

### In Progress ⏳
- Frontend integration testing
- End-to-end workflow validation

### Pending 📋
- Performance monitoring (response times)
- Error tracking integration (Sentry)
- CORS hardening (restrict methods/headers)

## Related Documentation

- [STAGE-2-TESTING.md](./STAGE-2-TESTING.md) - Backend API testing guide
- [Frontend Repo README](frontend-repo-url) - Frontend setup and deployment
- [API Documentation](http://<ec2-ip>:8080/docs) - Interactive API docs

## Troubleshooting

### CORS Error in Browser
**Symptom**: `Access to fetch at 'http://<ec2-ip>:8080/api/v1/extract' from origin 'https://medical-extraction.vercel.app' has been blocked by CORS policy`

**Solution**:
1. Check if CORS_ORIGINS includes the frontend domain
2. Verify gateway container has restarted with new config:
   ```bash
   docker logs fastapi-gateway --tail 50 | grep CORS
   ```
3. Test CORS preflight (see Verification section above)

### Preview Deployment Not Working
**Symptom**: Production works, but preview deployments get CORS errors

**Solution**:
1. Verify wildcard pattern is configured: `https://*.vercel.app`
2. Check if preview URL matches pattern:
   - ✅ Valid: `https://my-branch-user.vercel.app`
   - ❌ Invalid: Custom domain not on vercel.app
3. Test with specific preview URL in CORS_ORIGINS temporarily

### CORS Working in curl but Not Browser
**Symptom**: curl preflight succeeds, but browser still blocks

**Possible Causes**:
1. Browser cached old CORS response (clear cache)
2. Frontend making request to wrong endpoint
3. Frontend not including required headers
4. Mixed content (HTTPS frontend → HTTP backend)
   - Use HTTPS for backend or proxy through Vercel API routes

## Next Steps

1. **Monitor Frontend Integration**
   - Track API response times from frontend
   - Monitor CORS-related errors in browser console
   - Collect user feedback on functionality

2. **Performance Optimization**
   - Consider CDN/caching for static responses
   - Implement response compression
   - Add request/response logging

3. **Security Hardening**
   - Restrict CORS methods and headers
   - Implement rate limiting by origin
   - Add API key authentication if needed

4. **Move to Stage 4: Monitoring**
   - Set up CloudWatch dashboards
   - Configure alerts for API errors
   - Track GPU utilization and costs
