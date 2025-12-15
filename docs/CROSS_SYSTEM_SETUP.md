# 🔄 Cross-System Setup Guide

This guide helps you seamlessly continue your NEJM Research System setup across your Windows desktop and macOS laptop.

## 🎯 Quick Start

### On Any System (First Time)
```bash
# Check current setup status
python setup_manager.py status

# Update system information
python setup_manager.py system-info

# See what to do next
python setup_manager.py next
```

## 📋 Workflow Between Systems

### 1. Starting Setup (Windows Desktop)
```bash
# Initialize and check status
python setup_manager.py status

# Mark steps as you complete them
python setup_manager.py complete "AWS CLI configured"
python setup_manager.py complete "Python 3.12 installed"

# Record AWS resources as you create them
python setup_manager.py aws-resource opensearch_domain "search-nejm-research-abc123"
python setup_manager.py aws-resource s3_bucket "nejm-research-1734123456-jbsmith"

# Add notes for context
python setup_manager.py note "Started OpenSearch domain creation, will take 15 minutes"

# Commit and push progress
git add setup_state.json
git commit -m "Update setup progress: AWS CLI configured, OpenSearch domain creating"
git push
```

### 2. Continuing Setup (macOS Laptop)
```bash
# Pull latest changes
git pull

# Check what was done and what's next
python setup_manager.py status
python setup_manager.py next

# Update system info for macOS
python setup_manager.py system-info

# Continue with macOS-specific steps
python setup_manager.py complete "Homebrew installed"
python setup_manager.py complete "AWS CLI configured on macOS"

# Push progress back
git add setup_state.json
git commit -m "Continued setup on macOS: AWS CLI configured"
git push
```

### 3. Back to Windows (Later)
```bash
# Pull latest progress
git pull

# Check status and continue
python setup_manager.py status
python setup_manager.py complete "Lambda function deployed"
python setup_manager.py aws-resource lambda_function "nejm-research-assistant"

# Push final progress
git add setup_state.json
git commit -m "Completed Lambda deployment"
git push
```

## 🔧 Setup State Tracking

The `setup_manager.py` script tracks:

### ✅ Completed Steps
- AWS CLI configuration
- Python installation
- Service deployments
- Testing and verification

### ☁️ AWS Resources
- OpenSearch domain IDs
- S3 bucket names
- Lambda function names
- API Gateway endpoints
- Secrets Manager ARNs

### 💻 System Status
- **Windows Desktop**: AWS CLI, Python version, Git config
- **macOS Laptop**: Homebrew, AWS CLI, Python version

### 📝 Notes & Context
- Timestamped notes with system info
- Progress context for handoffs
- Error messages and solutions

## 🚀 Common Commands

### Check Status
```bash
python setup_manager.py status
```

### Mark Progress
```bash
# Mark a step complete
python setup_manager.py complete "OpenSearch domain created"

# Record AWS resource
python setup_manager.py aws-resource api_gateway "abc123def456"

# Add contextual note
python setup_manager.py note "API Gateway created, testing endpoints next"
```

### Get Next Steps
```bash
python setup_manager.py next
```

## 📊 Example Status Output

```
🔧 NEJM Research System Setup Status
=====================================

Current System: windows-desktop
Setup Phase: aws-deployment
Last Updated: 2024-12-14T15:30:00Z

✅ Completed Steps (4):
   • AWS CLI configured
   • Python 3.12 installed
   • OpenSearch domain created
   • S3 bucket created

📋 Next Steps (3):
   1. Deploy Lambda function
   2. Configure API Gateway
   3. Test end-to-end functionality

☁️ AWS Resources:
   ✅ opensearch_domain: search-nejm-research-abc123
   ✅ s3_bucket: nejm-research-1734123456-jbsmith
   ⏳ lambda_function: Not created
   ⏳ api_gateway: Not created
   ✅ secrets_manager: nejm-api-credentials

💻 System Status:
   🟢 windows-desktop:
      AWS CLI: ✅
      Python: Python 3.12.1
      Git: ✅
      Last Active: 2024-12-14T15:30:00Z
   ⚪ macos-laptop:
      AWS CLI: ✅
      Python: Python 3.12.0
      Git: ✅
      Last Active: 2024-12-14T10:15:00Z

📝 Recent Notes:
   • [windows-desktop] Started OpenSearch domain creation, will take 15 minutes
   • [windows-desktop] OpenSearch domain is now active and ready
   • [macos-laptop] Configured AWS CLI with same credentials
   • [windows-desktop] S3 bucket created with versioning enabled
```

## 🔄 Git Workflow Integration

### Automatic State Sync
```bash
# Add to your .gitignore (already done)
# setup_state.json is tracked for cross-system coordination

# Always pull before starting work
git pull

# Always push after making progress
git add setup_state.json
git commit -m "Setup progress: [describe what you did]"
git push
```

### Branch Strategy (Optional)
```bash
# Create setup branch for major changes
git checkout -b aws-setup-phase1
# ... do setup work ...
git add setup_state.json
git commit -m "Phase 1: Core AWS services deployed"
git push -u origin aws-setup-phase1

# Merge when phase complete
git checkout main
git merge aws-setup-phase1
git push
```

## 🛠️ Troubleshooting

### State File Conflicts
```bash
# If you get merge conflicts in setup_state.json
git pull
# Manually resolve conflicts, keeping the most recent progress
git add setup_state.json
git commit -m "Resolved setup state merge conflict"
```

### Lost Progress
```bash
# Check git history
git log --oneline setup_state.json

# Restore from previous commit if needed
git checkout HEAD~1 setup_state.json
```

### System Detection Issues
```bash
# Manually update system info
python setup_manager.py system-info

# Check detected system
python -c "import platform; print(platform.system())"
```

## 🎯 Best Practices

1. **Always pull first**: `git pull` before starting work
2. **Frequent commits**: Commit progress after each major step
3. **Descriptive notes**: Add context for your future self
4. **Resource tracking**: Record all AWS resource IDs immediately
5. **Status checks**: Run `python setup_manager.py status` regularly

This system ensures you can seamlessly switch between your Windows desktop and macOS laptop while maintaining complete context of your setup progress!