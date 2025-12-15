# 🔐 Secure API Key Setup Guide

**NEVER share your API key in plain text or commit it to version control!**

## 📋 Step-by-Step Setup

### Step 1: Get Your API Key
Contact NEJM to obtain your API key for the QA environment.

### Step 2: Choose Your Security Method

#### Option A: Environment Variable (Recommended for Development)
```bash
# Set for current session (format: userid|apikey)
export NEJM_API_KEY='your-userid|your-actual-api-key'

# Make it permanent (add to ~/.zshrc or ~/.bashrc)
echo 'export NEJM_API_KEY="your-userid|your-actual-api-key"' >> ~/.zshrc
source ~/.zshrc
```

#### Option B: Secure Config File (Recommended for Production)
```bash
# Save credentials securely (format: userid|apikey)
python config_manager.py --set-key 'your-userid|your-actual-api-key' --environment qa

# For production environment
python config_manager.py --set-key 'your-userid|your-prod-api-key' --environment production

# List configured environments
python config_manager.py --list
```

#### Option C: Command Line (Testing Only)
```bash
# Only for quick testing - credentials visible in command history
python nejm_api_client.py --api-key 'your-userid|your-key' --dry-run --limit 3
```

## 🧪 Test Your Setup

### Test QA Environment
```bash
# Using environment variable or config file
python nejm_api_client.py --dry-run --limit 3

# Using command line
python nejm_api_client.py --api-key 'your-key' --dry-run --limit 3
```

### Test Production Environment
```bash
# Using config file
python nejm_api_client.py --environment production --dry-run --limit 3

# Using environment variable
export NEJM_API_KEY_PRODUCTION='your-prod-key'
python nejm_api_client.py --environment production --dry-run --limit 3
```

## 🔒 Security Features

### Config File Security
- Stored in `~/.nejm_api/config.json`
- File permissions set to `600` (owner read/write only)
- Directory permissions set to `700` (owner access only)

### Priority Order
The system checks for API keys in this order:
1. `--api-key` command line argument
2. Environment variable (`NEJM_API_KEY` or `NEJM_API_KEY_PRODUCTION`)
3. Config file (`~/.nejm_api/config.json`)

## 🚀 Ready to Use

Once configured, you can run commands without exposing your key:

```bash
# Test connection
python nejm_api_client.py --dry-run --limit 3

# Start ingesting
python nejm_api_client.py --limit 10

# Automated ingestion
python automated_ingestion.py

# Compare environments
python compare_environments.py
```

## ⚠️ Security Best Practices

1. **Never commit API keys to git**
2. **Use environment variables for CI/CD**
3. **Use config files for local development**
4. **Rotate keys regularly**
5. **Use different keys for QA vs Production**

## 🔧 Troubleshooting

### Check if key is configured:
```bash
python config_manager.py --list
```

### Test credentials manually:
```bash
curl -H "apiuser: your-userid" -H "apikey: your-key" \
  "https://onesearch-api.nejmgroup-qa.org/api/v1/simple?context=nejm&objectType=nejm-article&pageLength=1"
```

### Reset configuration:
```bash
rm -rf ~/.nejm_api/
```