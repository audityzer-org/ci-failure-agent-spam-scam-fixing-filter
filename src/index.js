// Telegram Bot + ClickUp Integration Server
// Step 5: Express Server with Webhook Support

require('dotenv').config();
const express = require('express');
const { Client } = require('pg');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || 'localhost';

// Middleware
app.use(express.json());

// PostgreSQL Connection
const pool = new Client({
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
  ssl: process.env.DB_SSL === 'true' ? { rejectUnauthorized: false } : false,
});

// Database Connection
async function connectDatabase() {
  try {
    await pool.connect();
    console.log('\u2713 PostgreSQL database connected successfully');
    
    // Verify tables exist
    const res = await pool.query(
      `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'`
    );
    console.log(`\u2713 Found ${res.rows.length} tables in database`);
  } catch (error) {
    console.error('\u2717 Database connection failed:', error.message);
    process.exit(1);
  }
}

// Health Check Endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    service: 'Telegram-ClickUp Bot',
    uptime: process.uptime(),
  });
});

// Telegram Webhook Endpoint
app.post('/webhook/telegram', async (req, res) => {
  try {
    console.log('\ud83d\udce8 Telegram message received:', req.body);
    
    const { message, update_id } = req.body;
    
    if (message) {
      const { chat, text, from } = message;
      console.log(`Message from ${from.username}: ${text}`);
      
      // Store webhook event in database
      try {
        await pool.query(
          'INSERT INTO webhook_logs (service, event_type, payload) VALUES ($1, $2, $3)',
          ['telegram', 'message_received', JSON.stringify(req.body)]
        );
      } catch (dbError) {
        console.warn('Failed to log webhook:', dbError.message);
      }
    }
    
    res.json({ ok: true, update_id });
  } catch (error) {
    console.error('\u274c Telegram webhook error:', error.message);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ClickUp Webhook Endpoint
app.post('/webhook/clickup', async (req, res) => {
  try {
    console.log('\ud83d\udce8 ClickUp event received:', req.body);
    
    const { event, data } = req.body;
    
    if (event && data) {
      console.log(`ClickUp event: ${event}`);
      console.log(`Event data:`, JSON.stringify(data, null, 2));
      
      // Store webhook event in database
      try {
        await pool.query(
          'INSERT INTO webhook_logs (service, event_type, payload) VALUES ($1, $2, $3)',
          ['clickup', event, JSON.stringify(req.body)]
        );
      } catch (dbError) {
        console.warn('Failed to log webhook:', dbError.message);
      }
    }
    
    res.json({ ok: true });
  } catch (error) {
    console.error('\u274c ClickUp webhook error:', error.message);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Status Endpoint
app.get('/status', async (req, res) => {
  try {
    const dbStatus = await pool.query('SELECT NOW()');
    res.json({
      status: 'running',
      database: 'connected',
      timestamp: dbStatus.rows[0].now,
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      database: 'disconnected',
      error: error.message,
    });
  }
});

// Error Handling Middleware
app.use((err, req, res, next) => {
  console.error('\u274c Server error:', err.message);
  res.status(500).json({
    error: err.message,
    timestamp: new Date().toISOString(),
  });
});

// 404 Handling
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Server Startup
async function start() {
  try {
    console.log('\ud83d\ude80 Starting Telegram-ClickUp Integration Server...');
    console.log(`\ud83d\udd13 Environment: ${process.env.NODE_ENV || 'development'}`);
    
    // Connect to database
    await connectDatabase();
    
    // Start server
    const server = app.listen(PORT, HOST, () => {
      console.log('\ud83d\ude80 Server running!');
      console.log(`\ud83c\udf10 Host: ${HOST}`);
      console.log(`\ud83d\udcc2 Port: ${PORT}`);
      console.log(`\ud83d\udc93 Health check: http://${HOST}:${PORT}/health`);
      console.log(`\ud83d\udce1 Telegram webhook: http://${HOST}:${PORT}/webhook/telegram`);
      console.log(`\ud83d\udce1 ClickUp webhook: http://${HOST}:${PORT}/webhook/clickup`);
      console.log(`\ud83d\udcc4 Status: http://${HOST}:${PORT}/status`);
      console.log('\n\u2705 Ready to receive webhooks!');
    });
    
    // Graceful Shutdown
    process.on('SIGTERM', () => {
      console.log('SIGTERM received, closing server...');
      server.close(() => {
        console.log('Server closed');
        pool.end(() => {
          console.log('Database connection closed');
          process.exit(0);
        });
      });
    });
  } catch (error) {
    console.error('\u274c Failed to start server:', error);
    process.exit(1);
  }
}

// Start the server
start();

module.exports = app;
