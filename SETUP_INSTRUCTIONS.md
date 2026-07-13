# Setup Instructions - AWS Cost Anomaly Detective

**Status**: ✅ **LIVE ON AWS-SAMPLES**  
**Repository**: https://github.com/aws-samples/sample-aws-cost-anomaly-detective

---

## For Contributors/Developers

### Step 1: Clone the Repository

```bash
# Clone from aws-samples
git clone https://github.com/aws-samples/sample-aws-cost-anomaly-detective.git
cd sample-aws-cost-anomaly-detective
```

### Step 2: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Configure AWS Credentials

```bash
# Set up AWS credentials (if not already configured)
aws configure

# Verify access to required services
aws bedrock list-foundation-models --region us-east-1
aws ce get-cost-and-usage --time-period Start=2026-01-01,End=2026-01-02 --granularity DAILY --metrics BlendedCost
```

### Step 4: Deploy to Your AWS Account

See deployment options in the main [README.md](README.md):
- **Quick Deploy**: 1-click CloudFormation
- **Manual Deploy**: Step-by-step Lambda setup
- **Multi-Account**: Organizations deployment

---

## For Contributors

### Making Changes

- ✅ Add GitHub repo URL to your internal wiki
- ✅ Share on internal #opensource Slack channel
- ✅ Draft blog post for AWS Architecture Blog
- ✅ Create workshop for re:Invent
- ✅ Add to SA enablement resources
- ✅ Demo to customers

---

## Quick Test (Local)

```bash
cd ~/aws-cost-anomaly-detective

# Install dependencies
pip install -r requirements.txt

# Test locally (will fail without AWS creds, but validates imports)
python src/lambda_function.py
```

---

## Project Statistics

- **Files Created**: 12
- **Lines of Code**: 860+ (Python)
- **Lines of Docs**: 1,500+
- **AWS Services**: 10+
- **Ready for**: aws-samples submission

---

## Quick Links

- 🌐 **Live Repository**: https://github.com/aws-samples/sample-aws-cost-anomaly-detective
- 📖 **Main README**: [README.md](README.md)
- 🏗️ **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 🎓 **Workshop**: [docs/WORKSHOP.md](docs/WORKSHOP.md)
- 🔐 **Security Review**: [SECURITY_ANONYMIZATION_CHECKLIST.md](SECURITY_ANONYMIZATION_CHECKLIST.md)

---

**Status**: ✅ **APPROVED AND PUBLIC** - Ready for promotion and customer use!
