# Deployment Guide - Vercel

This project is configured for deployment on Vercel. Follow these steps to deploy your motorcycle routing application.

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com) (free)
2. **GitHub Repository**: Push your code to GitHub (required for Vercel integration)
3. **Git**: Installed on your machine

## Step-by-Step Deployment

### 1. Initialize Git Repository (if not already done)

```bash
cd Motorcycle_Routing
git init
git add .
git commit -m "Initial commit: Motorcycle routing app"
```

### 2. Create a `.gitignore` File

Make sure sensitive files aren't committed:

```bash
# Already configured if .gitignore exists
# Key exclusions: .venv, __pycache__, .env.local
```

### 3. Push to GitHub

```bash
# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/Motorcycle_Routing.git
git branch -M main
git push -u origin main
```

### 4. Deploy on Vercel

**Option A: Via Vercel Web Dashboard**

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click "Add New" → "Project"
3. Select your GitHub repository
4. Configure project settings:
   - **Framework**: Other
   - **Root Directory**: `./` (current directory)
   - **Build Command**: `pip install -r requirements.txt`
   - **Output Directory**: `web/templates`
5. Add Environment Variables (if needed):
   - `GOOGLE_MAPS_API_KEY`: Your API key
   - `FLASK_ENV`: `production`
6. Click "Deploy"

**Option B: Via Vercel CLI**

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Follow the prompts and authenticate with GitHub
```

### 5. Configure Environment Variables

1. In Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add:
   - `GOOGLE_MAPS_API_KEY`: Your Google Maps API key
   - `FLASK_ENV`: `production`

### 6. Update CORS (if needed)

If frontend and backend are on different domains, you may need to update `app.py`:

```python
from flask_cors import CORS
CORS(app)
```

Add `flask-cors` to `requirements.txt`:

```bash
echo "flask-cors==4.0.0" >> requirements.txt
```

## Project Structure for Vercel

```
Motorcycle_Routing/
├── vercel.json           ← Deployment config
├── .vercelignore         ← Files to exclude
├── requirements.txt      ← Python dependencies
├── config.py             ← Configuration
├── web/
│   ├── app.py            ← Flask app (main entry point)
│   ├── templates/
│   │   └── index.html    ← Frontend
│   └── static/           ← Static assets
├── src/
│   ├── data_loader.py
│   ├── algorithms/
│   └── api/
├── data/
│   └── osm/              ← Network graph files
└── cache/                ← Cached data
```

## After Deployment

✅ Your app will be available at: `https://YOUR_PROJECT.vercel.app`

### Updating Your App

Any changes pushed to GitHub will automatically trigger a new deployment on Vercel.

```bash
git add .
git commit -m "Update: New feature"
git push origin main
```

## Troubleshooting

### Build Failures

- Check the Vercel logs: Dashboard → Your Project → Deployments → Latest → Logs
- Ensure all dependencies are in `requirements.txt`
- Verify file paths work on Linux (Vercel uses Linux servers)

### Cold Starts

- Flask apps may have slower first requests (normal for serverless)
- Subsequent requests will be faster

### Data Loading Issues

- Ensure `data/osm/` files are included in the deployment
- Check `.vercelignore` — it should NOT exclude `data/` or `cache/`

### API Key Issues

- Ensure `GOOGLE_MAPS_API_KEY` is set in Vercel environment variables
- Verify the key has proper permissions in Google Cloud Console

## Support

- Vercel Docs: [vercel.com/docs](https://vercel.com/docs)
- Flask on Vercel: [vercel.com/guides/deploying-python](https://vercel.com/guides/deploying-python)

---

**Deployed by**: Motorcycle Routing Team  
**Last Updated**: April 21, 2026
