#!/bin/bash
echo "👑 AI Trading Empire is waking up..."

# Run python engine
python3 main.py --mode paper & 

# Start Node server
node server.js
