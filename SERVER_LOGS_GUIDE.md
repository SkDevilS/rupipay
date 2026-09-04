# Server Logs Guide - Payin & Payout Monitoring

## Quick Commands

### View Real-Time Logs (Follow Mode)
```bash
# All API logs (payin + payout + everything)
sudo journalctl -u moneyone-api -f

# Last 100 lines + follow
sudo journalctl -u moneyone-api -n 100 -f

# Filter by time (last 1 hour)
sudo journalctl -u moneyone-api --since "1 hour ago" -f
```

### View Recent Logs (Static)
```bash
# Last 50 lines
sudo journalctl -u moneyone-api -n 50

# Last 200 lines
sudo journalctl -u moneyone-api -n 200

# Today's logs
sudo journalctl -u moneyone-api --since today

# Yesterday's logs
sudo journalctl -u moneyone-api --since yesterday --until today
```

### Search Logs

#### Payin Logs
```bash
# All payin activity
sudo journalctl -u moneyone-api | grep -i payin

# Payin callbacks
sudo journalctl -u moneyone-api | grep -i "Payin Callback"

# Mudrape payin
sudo journalctl -u moneyone-api | grep -i "mudrape.*payin"

# QR code generation
sudo journalctl -u moneyone-api | grep -i "Creating Mudrape order"

# Status checks
sudo journalctl -u moneyone-api | grep -i "Checking.*status"
```

#### Payout Logs
```bash
# All payout activity
sudo journalctl -u moneyone-api | grep -i payout

# Payout callbacks
sudo journalctl -u moneyone-api | grep -i "Payout Callback"

# Mudrape payout
sudo journalctl -u moneyone-api | grep -i "mudrape.*payout"

# UPI payouts
sudo journalctl -u moneyone-api | grep -i "UPI payout"

# IMPS payouts
sudo journalctl -u moneyone-api | grep -i "IMPS payout"
```

sudo journalctl -u moneyone-api | grep -A 50 "PayTouch Payout Callback Received" | tail -200


#### Specific Transaction
```bash
# Search by order ID
sudo journalctl -u moneyone-api | grep "20260222215354239243"

# Search by transaction ID
sudo journalctl -u moneyone-api | grep "MUDRAPE_7679022140"

# Search by UTR
sudo journalctl -u moneyone-api | grep "701297876154"
```

#### Errors Only
```bash
# All errors
sudo journalctl -u moneyone-api | grep -i error

# Payin errors
sudo journalctl -u moneyone-api | grep -i "payin.*error"

# Payout errors
sudo journalctl -u moneyone-api | grep -i "payout.*error"

# Callback errors
sudo journalctl -u moneyone-api | grep -i "callback.*error"
```

### Time-Based Filtering

```bash
# Specific date
sudo journalctl -u moneyone-api --since "2026-02-22" --until "2026-02-23"

# Specific time range
sudo journalctl -u moneyone-api --since "2026-02-22 22:00:00" --until "2026-02-22 23:00:00"

# Last 30 minutes
sudo journalctl -u moneyone-api --since "30 minutes ago"

# Last 2 hours
sudo journalctl -u moneyone-api --since "2 hours ago"
```

## Log Patterns to Look For

### Successful Payin Flow
```
Creating Mudrape order with payload: {...}
Mudrape API Response Status: 200
Mudrape Response JSON: {"success": true, ...}
```

### Payin Callback Received
```
================================================================================
Mudrape Payin Callback Received
================================================================================
Callback Data: {
  "ref_id": "...",
  "txn_id": "...",
  "status": "SUCCESS",
  ...
}
Found Transaction: ...
✓ Wallet credited: ...
Payin callback processed successfully
```

### Payin Status Check
```
Admin checking Mudrape status for ...
Checking Mudrape with identifier: ...
Mudrape returned status: SUCCESS
✓ Updated ... to SUCCESS and credited wallet
```

### Successful Payout Flow
```
Calling Mudrape UPI payout API: {...}
Mudrape UPI Payout Response: 200 - {...}
Parsed - Status Code: 10000, Payout Status: SUCCESS
✓ Wallet debited: ...
```

### Payout Callback Received
```
================================================================================
Mudrape Payout Callback Received
================================================================================
Callback Data: {
  "clientTxnId": "...",
  "statusCode": 10000,
  "payoutStatus": "SUCCESS",
  ...
}
✓ Updated with completed_at from Mudrape: ...
Callback processed successfully
```

## Advanced Log Analysis

### Count Transactions by Status
```bash
# Count SUCCESS payins today
sudo journalctl -u moneyone-api --since today | grep -i "payin.*success" | wc -l

# Count FAILED payouts today
sudo journalctl -u moneyone-api --since today | grep -i "payout.*failed" | wc -l
```

### Export Logs to File
```bash
# Export today's logs
sudo journalctl -u moneyone-api --since today > /tmp/api_logs_today.txt

# Export specific time range
sudo journalctl -u moneyone-api --since "2026-02-22 20:00" --until "2026-02-22 23:00" > /tmp/api_logs_evening.txt

# Export payin logs only
sudo journalctl -u moneyone-api | grep -i payin > /tmp/payin_logs.txt
```

### Monitor Specific Merchant
```bash
# Replace with actual merchant ID
sudo journalctl -u moneyone-api -f | grep "7679022140"
```

### Watch for Callbacks
```bash
# Watch for any callbacks
sudo journalctl -u moneyone-api -f | grep -i "callback received"

# Watch for successful callbacks
sudo journalctl -u moneyone-api -f | grep -i "callback processed successfully"
```

## Service Management

### Check Service Status
```bash
sudo systemctl status moneyone-api
```

### Restart Service
```bash
sudo systemctl restart moneyone-api
```

### Stop Service
```bash
sudo systemctl stop moneyone-api
```

### Start Service
```bash
sudo systemctl start moneyone-api
```

### View Service Configuration
```bash
sudo systemctl cat moneyone-api
```

## Log Rotation

### Check Log Size
```bash
sudo journalctl -u moneyone-api --disk-usage
```

### Clear Old Logs
```bash
# Keep only last 3 days
sudo journalctl --vacuum-time=3d

# Keep only 500MB
sudo journalctl --vacuum-size=500M
```

## Useful Aliases (Add to ~/.bashrc)

```bash
# Add these to your ~/.bashrc file
alias api-logs='sudo journalctl -u moneyone-api -f'
alias api-logs-100='sudo journalctl -u moneyone-api -n 100'
alias api-logs-today='sudo journalctl -u moneyone-api --since today'
alias api-logs-payin='sudo journalctl -u moneyone-api | grep -i payin'
alias api-logs-payout='sudo journalctl -u moneyone-api | grep -i payout'
alias api-logs-error='sudo journalctl -u moneyone-api | grep -i error'
alias api-status='sudo systemctl status moneyone-api'
alias api-restart='sudo systemctl restart moneyone-api'
```

After adding, reload:
```bash
source ~/.bashrc
```

Then use:
```bash
api-logs          # Follow logs in real-time
api-logs-payin    # View all payin logs
api-logs-error    # View all errors
```

## Common Troubleshooting Scenarios

### Payin Not Updating to SUCCESS
```bash
# Check if callback was received
sudo journalctl -u moneyone-api | grep -i "payin callback received"

# Check for callback errors
sudo journalctl -u moneyone-api | grep -i "callback.*error"

# Check status check attempts
sudo journalctl -u moneyone-api | grep -i "checking.*status"
```

### Payout Stuck in INITIATED
```bash
# Check if payout was sent to Mudrape
sudo journalctl -u moneyone-api | grep -i "calling mudrape.*payout"

# Check Mudrape response
sudo journalctl -u moneyone-api | grep -i "mudrape.*payout response"

# Check for callback
sudo journalctl -u moneyone-api | grep -i "payout callback received"
```

### Wallet Not Credited
```bash
# Check for wallet credit logs
sudo journalctl -u moneyone-api | grep -i "wallet credited"

# Check for wallet errors
sudo journalctl -u moneyone-api | grep -i "wallet.*error"
```

### Service Crashes
```bash
# Check for crash logs
sudo journalctl -u moneyone-api --since "1 hour ago" | grep -i "error\|exception\|traceback"

# Check service status
sudo systemctl status moneyone-api

# View last crash
sudo journalctl -u moneyone-api -n 200 | grep -A 20 "error"
```

## Real-Time Monitoring Dashboard

### Monitor Everything at Once
```bash
# Open multiple terminal windows/tabs:

# Terminal 1: All logs
sudo journalctl -u moneyone-api -f

# Terminal 2: Payin only
sudo journalctl -u moneyone-api -f | grep -i payin

# Terminal 3: Payout only
sudo journalctl -u moneyone-api -f | grep -i payout

# Terminal 4: Errors only
sudo journalctl -u moneyone-api -f | grep -i error
```

### Using tmux (Split Screen)
```bash
# Install tmux if not installed
sudo apt install tmux

# Start tmux session
tmux

# Split horizontally: Ctrl+b then "
# Split vertically: Ctrl+b then %
# Switch panes: Ctrl+b then arrow keys

# In each pane, run different log commands
```

## Log Format Examples

### Payin Transaction Log
```
Feb 22 22:15:30 ip-172-31-34-229 gunicorn[19473]: Creating Mudrape order for merchant 7679022140 using MUDRAPE
Feb 22 22:15:30 ip-172-31-34-229 gunicorn[19473]: Creating Mudrape order with payload: {'userId': '...', 'RefID': '20260222215354239243', ...}
Feb 22 22:15:31 ip-172-31-34-229 gunicorn[19473]: Mudrape API Response Status: 200
Feb 22 22:15:31 ip-172-31-34-229 gunicorn[19473]: Mudrape Response JSON: {"success": true, "data": {...}}
```

### Callback Log
```
Feb 22 22:17:04 ip-172-31-34-229 gunicorn[19473]: ================================================================================
Feb 22 22:17:04 ip-172-31-34-229 gunicorn[19473]: Mudrape Payin Callback Received
Feb 22 22:17:04 ip-172-31-34-229 gunicorn[19473]: ================================================================================
Feb 22 22:17:04 ip-172-31-34-229 gunicorn[19473]: Callback Data: {"ref_id": "20260222215354239243", "txn_id": "TPAY202602221623544914675", "status": "SUCCESS", ...}
Feb 22 22:17:04 ip-172-31-34-229 gunicorn[19473]: Found Transaction: MUDRAPE_7679022140_ORD1771777434132674_20260222215354, Current Status: INITIATED
Feb 22 22:17:04 ip-172-31-34-229 gunicorn[19473]: ✓ Wallet credited: 290.46
Feb 22 22:17:04 ip-172-31-34-229 gunicorn[19473]: Payin callback processed successfully
```

## Quick Reference Card

```
COMMAND                                          PURPOSE
─────────────────────────────────────────────────────────────────────
sudo journalctl -u moneyone-api -f              Follow logs in real-time
sudo journalctl -u moneyone-api -n 100          Last 100 lines
sudo journalctl -u moneyone-api --since today   Today's logs
sudo journalctl -u moneyone-api | grep payin    Payin logs
sudo journalctl -u moneyone-api | grep payout   Payout logs
sudo journalctl -u moneyone-api | grep error    Error logs
sudo systemctl status moneyone-api              Service status
sudo systemctl restart moneyone-api             Restart service
```

## Save This Guide

Save this file to your server:
```bash
# Copy to server
scp SERVER_LOGS_GUIDE.md ubuntu@your-server:/home/ubuntu/

# Or create directly on server
nano ~/SERVER_LOGS_GUIDE.md
# Paste content and save (Ctrl+X, Y, Enter)
```

View anytime:
```bash
cat ~/SERVER_LOGS_GUIDE.md
# or
less ~/SERVER_LOGS_GUIDE.md
```

