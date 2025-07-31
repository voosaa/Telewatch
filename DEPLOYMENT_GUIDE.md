# 🚀 TELEGRAM MONITOR - DEPLOYMENT GUIDE
## Vercel + Railway + MongoDB Atlas

### 📋 OVERVIEW
- **Frontend**: Vercel (React)
- **Backend**: Railway (FastAPI)  
- **Database**: MongoDB Atlas
- **Cost**: $0-5/month

---

## 🗂️ STEP 1: PREPARE FOR DEPLOYMENT

✅ **Code is Ready!** All deployment files have been created:
```
/app/
├── backend/
│   ├── server.py                 ✅ FastAPI app with CORS
│   ├── requirements.txt          ✅ Dependencies  
│   ├── Procfile                 ✅ Railway start command
│   ├── railway.toml             ✅ Railway configuration
│   └── .env.production          ✅ Environment template
├── frontend/
│   ├── package.json             ✅ Build scripts
│   └── public/index.html        ✅ React app
├── .gitignore                   ✅ Git ignore rules
└── deployment_check.py          ✅ Deployment checker
```

---

## 🗄️ STEP 2: SET UP MONGODB ATLAS (FREE DATABASE)

### 2.1 Create MongoDB Atlas Account
1. Go to **https://www.mongodb.com/atlas**
2. Click **"Try Free"**
3. Sign up with email
4. Choose **"Build a database"**

### 2.2 Create Free Cluster
1. Select **"Shared"** (FREE tier)
2. Choose **AWS** + **us-east-1** (recommended)
3. Cluster Name: **"telegram-monitor"**
4. Click **"Create Cluster"** (takes 1-3 minutes)

### 2.3 Configure Database Access
1. **Database Access** → **"Add New Database User"**
   - Username: `telegram_admin`
   - Password: Generate secure password (save it!)
   - Role: **Atlas admin**

2. **Network Access** → **"Add IP Address"**
   - Click **"Allow access from anywhere"** (0.0.0.0/0)
   - Confirm

### 2.4 Get Connection String
1. Click **"Connect"** on your cluster
2. Choose **"Connect your application"**
3. Copy the connection string:
   ```
   mongodb+srv://telegram_admin:<password>@telegram-monitor.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
4. Replace `<password>` with your actual password
5. **Save this connection string!** 📝

---

## 🚄 STEP 3: DEPLOY BACKEND TO RAILWAY

### 3.1 Create Railway Account
1. Go to **https://railway.app**
2. Sign up with GitHub
3. Authorize Railway to access your repositories

### 3.2 Deploy Backend
1. Click **"New Project"**
2. Choose **"Deploy from GitHub repo"**
3. Select your repository
4. Railway will detect FastAPI and deploy automatically!

### 3.3 Configure Environment Variables
In Railway dashboard, go to **Variables** tab and add:

```bash
# Database
MONGO_URL=mongodb+srv://telegram_admin:your_password@telegram-monitor.xxxxx.mongodb.net/telegram_bot_db?retryWrites=true&w=majority
DB_NAME=telegram_bot_db

# Telegram Bot
TELEGRAM_TOKEN=8342094196:AAE-E8jIYLjYflUPtY0G02NLbogbDpN_FE8
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
WEBHOOK_SECRET=telegram_bot_webhook_secret_2025

# JWT
JWT_SECRET=telegram_monitor_jwt_secret_key_2025_super_secure_random_string
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# NOWPayments (LIVE)
NOWPAYMENTS_API_KEY=N9BG2RQ-TSX4PCC-J6PNTQP-MRPM6NF
NOWPAYMENTS_IPN_SECRET=6fde78fb-814c-407f-b456-a4717dbc1a29
NOWPAYMENTS_SANDBOX=false
SUBSCRIPTION_PLANS={"pro": 9.99, "enterprise": 19.99}

# Wallets (Add your real addresses)
BTC_WALLET_ADDRESS=your_btc_wallet_address
ETH_WALLET_ADDRESS=your_eth_wallet_address
USDC_WALLET_ADDRESS=your_usdc_wallet_address
SOL_WALLET_ADDRESS=your_sol_wallet_address
```

### 3.4 Get Backend URL
After deployment, Railway will give you a URL like:
```
https://your-app-name-production.railway.app
```
**Save this URL!** 📝

---

## 🌐 STEP 4: DEPLOY FRONTEND TO VERCEL

### 4.1 Create Vercel Account
1. Go to **https://vercel.com**
2. Sign up with GitHub
3. Import your repository

### 4.2 Configure Build Settings
1. **Framework Preset**: React
2. **Root Directory**: `frontend`
3. **Build Command**: `npm run build`
4. **Output Directory**: `build`

### 4.3 Add Environment Variable
In Vercel dashboard, add:
```bash
REACT_APP_BACKEND_URL=https://your-app-name-production.railway.app
```

### 4.4 Deploy
Click **"Deploy"** - Vercel will build and deploy your React app!

---

## ⚙️ STEP 5: FINAL CONFIGURATION

### 5.1 Update NOWPayments Webhook
1. Go to your NOWPayments dashboard
2. **Settings** → **IPN Settings**
3. Update IPN URL to:
   ```
   https://your-app-name-production.railway.app/api/crypto/ipn
   ```

### 5.2 Update Telegram Bot Webhook
1. Your bot webhook will be:
   ```
   https://your-app-name-production.railway.app/api/telegram/webhook/telegram_bot_webhook_secret_2025
   ```

### 5.3 Test Deployment
1. Visit your Vercel app URL
2. Try creating an account
3. Test crypto payments
4. Check Railway logs for any issues

---

## 🎯 FINAL CHECKLIST

- [ ] MongoDB Atlas cluster created and accessible
- [ ] Railway backend deployed with all environment variables
- [ ] Vercel frontend deployed with backend URL
- [ ] NOWPayments webhook updated
- [ ] Telegram bot webhook configured
- [ ] Test user registration and payments

---

## 📞 TROUBLESHOOTING

### Backend Issues (Railway)
- Check **Deploy Logs** in Railway dashboard
- Verify all environment variables are set
- Test MongoDB connection string

### Frontend Issues (Vercel)
- Check **Build Logs** in Vercel dashboard
- Verify `REACT_APP_BACKEND_URL` is set correctly
- Test API calls in browser network tab

### Database Issues (MongoDB Atlas)
- Check IP whitelist (allow 0.0.0.0/0)
- Verify username/password in connection string
- Test connection from Railway logs

---

## 💰 MONTHLY COSTS

**Free Tier (Small Usage):**
- MongoDB Atlas: $0 (512MB)
- Railway: $0 (500 hours)
- Vercel: $0 (100GB bandwidth)
- **Total: $0/month**

**Production (Paid Tier):**
- MongoDB Atlas: $0 (free tier sufficient)
- Railway: $5/month
- Vercel: $0 (usually sufficient)
- **Total: $5/month**

---

## 🚀 READY TO DEPLOY!

Your Telegram Monitor app is production-ready! Follow the steps above and you'll have a scalable, professional deployment within 30 minutes.

**Need help? I'm here to assist with any step!** 🎉