# Streamlit Deployment Guide

## Deploying to Streamlit Community Cloud

### Prerequisites
- GitHub account
- Streamlit Community Cloud account (free at [share.streamlit.io](https://share.streamlit.io))
- Your code in a GitHub repository

### Step 1: Prepare Your Repository

1. **Replace app.py with the updated version:**
```bash
mv app.py app_old.py
mv app_streamlit.py app.py
```

2. **Ensure .gitignore is configured:**
```bash
# Add these to .gitignore if not already present
echo ".env" >> .gitignore
echo "storage.json" >> .gitignore
echo ".streamlit/secrets.toml" >> .gitignore
```

3. **Commit and push to GitHub:**
```bash
git add .
git commit -m "Update for Streamlit Cloud deployment"
git push origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **"New app"**
4. Configure:
   - **Repository**: `gauravkhati/multi-doc-tagging`
   - **Branch**: `temp` (or `main`)
   - **Main file path**: `app.py`
5. Click **"Advanced settings"**

### Step 3: Configure Secrets

Choose **ONE** authentication method:

#### Option A: Google AI Studio API Key (Recommended - Simpler)

In the "Secrets" section, paste:

```toml
MISTRAL_API_KEY = "UBcLe7zIA91i6M3SvoYqCrde0UN74urB"
GOOGLE_API_KEY = "AIzaSy...your_actual_google_ai_studio_key"
```

**Get Google AI Studio API Key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy and paste it above (starts with `AIzaSy`)

#### Option B: Google Cloud Service Account (For Vertex AI)

In the "Secrets" section, paste:

```toml
MISTRAL_API_KEY = "UBcLe7zIA91i6M3SvoYqCrde0UN74urB"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

**To get service account details:**
1. Open your `storage.json` file
2. Copy all the JSON content
3. Convert it to TOML format above
4. Make sure the `private_key` has `\n` for newlines

### Step 4: Deploy

1. Click **"Deploy"**
2. Wait 2-5 minutes for the build to complete
3. Your app will be live at: `https://your-app-name.streamlit.app`

### Step 5: Verify

1. Open your app URL
2. Upload a test PDF
3. Click "Process Document"
4. Verify the results and downloads

---

## Local Testing Before Deployment

Test the Streamlit Cloud version locally:

1. **Create a local secrets file:**
```bash
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

2. **Edit `.streamlit/secrets.toml` with your actual keys**

3. **Run locally:**
```bash
streamlit run app.py
```

4. **Test the app** at http://localhost:8501

---

## Troubleshooting

### "MISTRAL_API_KEY not found"
- Ensure you added the secret in Streamlit Cloud settings
- Key name must be exactly `MISTRAL_API_KEY`

### "Failed to initialize Gemini model"
- Verify your Google credentials are correct
- For Option A: Check your `GOOGLE_API_KEY` starts with `AIzaSy`
- For Option B: Verify all `gcp_service_account` fields are filled

### "Import errors" or "Module not found"
- Streamlit Cloud automatically installs from `requirements.txt`
- Verify `requirements.txt` has all dependencies
- Check build logs in Streamlit Cloud dashboard

### App runs out of memory
- Free tier has 1GB RAM limit
- Try processing smaller PDFs (< 10 pages)
- Consider upgrading to Streamlit Cloud paid tier

---

## Updating Your Deployed App

1. Make code changes locally
2. Commit and push to GitHub:
```bash
git add .
git commit -m "Update app"
git push
```
3. Streamlit Cloud auto-deploys on push
4. Watch the deployment in the dashboard

---

## Managing Secrets

### Update secrets:
1. Go to your app dashboard on Streamlit Cloud
2. Click **"⋯" → "Settings" → "Secrets"**
3. Edit and save
4. App will automatically restart

### Rotate API keys:
1. Generate new API key
2. Update in Streamlit secrets
3. Save (app auto-restarts)
4. Revoke old key

---

## Best Practices

✅ **DO:**
- Use `.gitignore` to exclude secrets
- Test locally before deploying
- Monitor app usage and logs
- Use environment-specific configs

❌ **DON'T:**
- Commit `.env` or `storage.json` to git
- Hardcode API keys in code
- Deploy without testing
- Share your secrets publicly

---

## Resources

- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Mistral API Docs](https://docs.mistral.ai/)
- [Google AI Studio](https://makersuite.google.com/)
