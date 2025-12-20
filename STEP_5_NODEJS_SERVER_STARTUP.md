# STEP 5: Node.js Server Startup & Log Verification

## Objective
Initialize and verify the Express server is running correctly with all required connections established.

## Key Tasks
1. Create src/index.js (main entry point)
2. Implement Express server with webhook routes
3. Connect to PostgreSQL
4. Setup error handling and logging
5. Start server on port 3000
6. Verify logs show successful startup
7. Test health check endpoint

## Prerequisites Completed
✅ Step 1: Telegram Bot Token acquired
✅ Step 2: NPM dependencies installed
✅ Step 3: .env file configured
✅ Step 4: PostgreSQL initialized

## Step 5.1: Create Express Server Entry Point

### Create src/index.js
```javascript
require('dotenv').config();
const express = require('express');
const pg = require('pg');
const axios = require('axios');
const { Client } = pg;

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// PostgreSQL Connection Pool
const pool = new Client({
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
});

// Connect to Database
async function connectDatabase() {
  try {
    await pool.connect();
    console.log('✓ PostgreSQL database connected successfully');
  } catch (error) {
    console.error('✗ Database connection failed:', error.message);
    process.exit(1);
  }
}

// Health Check Endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Telegram Webhook Endpoint
app.post('/webhook/telegram', (req, res) => {
  console.log('📨 Telegram message received:', req.body);
  res.json({ ok: true });
});

// ClickUp Webhook Endpoint
app.post('/webhook/clickup', (req, res) => {
  console.log('📨 ClickUp event received:', req.body);
  res.json({ ok: true });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('❌ Error:', err.message);
  res.status(500).json({ error: err.message });
});

// Server startup
async function start() {
  try {
    await connectDatabase();
    app.listen(PORT, () => {
      console.log(`🚀 Server running on port ${PORT}`);
      console.log(`📡 Telegram webhook: http://localhost:${PORT}/webhook/telegram`);
      console.log(`📡 ClickUp webhook: http://localhost:${PORT}/webhook/clickup`);
      console.log(`💓 Health check: http://localhost:${PORT}/health`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

start();
```

## Step 5.2: Update package.json Scripts

Add to package.json:
```json
{
  "scripts": {
    "dev": "nodemon src/index.js",
    "start": "node src/index.js",
    "test": "jest"
  }
}
```

## Step 5.3: Start the Server

### Development (with auto-reload)
```bash
npm run dev
```

### Production
```bash
npm start
```

## Step 5.4: Verify Server is Running

Expected console output:
```
✓ PostgreSQL database connected successfully
🚀 Server running on port 3000
📡 Telegram webhook: http://localhost:3000/webhook/telegram
📡 ClickUp webhook: http://localhost:3000/webhook/clickup
💓 Health check: http://localhost:3000/health
```

## Step 5.5: Test Health Check

### Using curl
```bash
curl http://localhost:3000/health
```

### Expected response
```json
{
  "status": "OK",
  "timestamp": "2024-12-20T10:30:45.123Z"
}
```

## Testing Checklist
- [ ] Server starts without errors
- [ ] Database connection established
- [ ] Health check endpoint responds
- [ ] Logs show "Server running on port 3000"
- [ ] All webhook routes registered
- [ ] No port conflicts
- [ ] Error handling working

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### Database Connection Error
- Verify .env variables
- Check PostgreSQL is running
- Confirm database exists
- Verify credentials

### Missing Dependencies
```bash
npm install express pg dotenv nodemon
```

## Next Steps
→ Step 6: ClickUp Webhook Configuration

Estimated Time: 20 minutes
Difficulty: Medium
Status: In Progress ⏳
