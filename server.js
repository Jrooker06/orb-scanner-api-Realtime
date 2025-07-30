const express = require('express');
const WebSocket = require('ws');
const http = require('http');
const https = require('https');

const app = express();
const server = http.createServer(app);

// Your Polygon API key (keep this secure!)
const POLYGON_API_KEY = "la79AawZg0NOZJ3ldtFztVagVQ4hHBjM";

// Health endpoint
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        message: 'Server is running',
        timestamp: new Date().toISOString()
    });
});

// Root endpoint
app.get('/', (req, res) => {
    res.json({ 
        message: 'Polygon WebSocket Proxy Server',
        endpoints: {
            health: '/health',
            websocket: '/ws'
        }
    });
});

// WebSocket server
const wss = new WebSocket.Server({ server });

// Store Polygon WebSocket connection
let polygonWs = null;

wss.on('connection', (ws, req) => {
    console.log('Client connected');
    
    // Connect to Polygon WebSocket if not already connected
    if (!polygonWs) {
        console.log('Connecting to Polygon WebSocket...');
        polygonWs = new WebSocket('wss://socket.polygon.io/stocks');
        
        polygonWs.on('open', () => {
            console.log('Connected to Polygon WebSocket');
            // Authenticate with Polygon
            polygonWs.send(JSON.stringify({
                action: 'auth',
                params: POLYGON_API_KEY
            }));
        });
        
        polygonWs.on('message', (data) => {
            try {
                const message = JSON.parse(data);
                // Forward Polygon data to all connected clients
                wss.clients.forEach((client) => {
                    if (client.readyState === WebSocket.OPEN) {
                        client.send(data.toString());
                    }
                });
            } catch (error) {
                console.error('Error parsing Polygon message:', error);
            }
        });
        
        polygonWs.on('error', (error) => {
            console.error('Polygon WebSocket error:', error);
        });
        
        polygonWs.on('close', () => {
            console.log('Polygon WebSocket disconnected');
            polygonWs = null;
        });
    }
    
    // Handle messages from client
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            
            // Forward subscription requests to Polygon
            if (data.action === 'subscribe' && polygonWs && polygonWs.readyState === WebSocket.OPEN) {
                console.log('Forwarding subscription:', data.params);
                polygonWs.send(JSON.stringify(data));
            }
            
            // Forward authentication requests to Polygon
            if (data.action === 'auth' && polygonWs && polygonWs.readyState === WebSocket.OPEN) {
                console.log('Forwarding auth request');
                polygonWs.send(JSON.stringify({
                    action: 'auth',
                    params: POLYGON_API_KEY
                }));
            }
            
        } catch (error) {
            console.error('Error parsing client message:', error);
        }
    });
    
    ws.on('close', () => {
        console.log('Client disconnected');
    });
    
    ws.on('error', (error) => {
        console.error('Client WebSocket error:', error);
    });
});

// Start server
const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/health`);
    console.log(`WebSocket: ws://localhost:${PORT}/ws`);
}); 