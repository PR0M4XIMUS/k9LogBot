# 🐕 K9LogBot - Smart Dog Walking Tracker

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Raspberry%20Pi-red.svg" alt="Platform">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Telegram-Bot-blue.svg" alt="Telegram Bot">
</p>

**K9LogBot** is an intelligent Telegram bot designed to track dog walks and manage payments for dog walking services. Perfect for professional dog walkers, pet sitters, or anyone who wants to gamify their dog walking routine!

---

## 📋 Table of Contents

- [Features](#-features)
- [What's New](#-whats-new)
- [Hardware Requirements](#-hardware-requirements)
- [Quick Setup](#-quick-setup)
- [Usage Guide](#-usage-guide)
- [Admin Functions](#-admin-functions)
- [Configuration](#-configuration)
- [Performance](#-performance)
- [Docker & Deployment](#-docker--deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## ✨ Features

### 🚶‍♀️ Walk Tracking
- **One-tap walk logging** - Record walks instantly with button press
- **Configurable walk rate** - Admin can adjust per-walk payment (default 75 MDL)
- **Walk notes** - Add context to each walk (distance, dog name, conditions, etc.)
- **Automatic balance calculation** - Walk rate added to balance instantly
- **Streak tracking** - Consecutive days of walks displayed in balance
- **Daily/Weekly statistics** - Track activity with real-time progress
- **Detailed reports** - View comprehensive walk history with timestamps and notes

### 💰 Payment Management
- **Balance tracking** in MDL (Moldovan Leu)
- **Credit system** - Add credits/advance payments to balance
- **Cash-out functionality** - Full or partial balance withdrawals
- **Transaction history** - Complete record of all payments and walks
- **Individual transaction deletion** - Remove specific entries (admin only)

### 📊 Smart Reporting & Analytics
- **Real-time balance display** - Always know current earnings
- **Streak tracking** - 🔥 Display consecutive days with walks
- **Weekly goals** - 🎯 Set targets and see live progress bar
- **Earnings forecast** - 📈 Monthly projection based on current pace
- **Weekly automated reports** - Scheduled summary every Sunday at 20:00
- **Enhanced visual reports** - Better formatting with emoji indicators
- **Transaction preview** - See what will be deleted before confirming
- **Daily reminders** - 🔔 Optional reminder if no walk logged by your chosen time

### 👨‍💼 Admin Controls
- **Configurable walk rate** - Change payment per walk via `/setrate`
- **Broadcast messages** - Send announcements to all users
- **CSV export** - Download full transaction history for analysis
- **Individual transaction deletion** - Remove specific entries with balance auto-adjust
- **Flexible cleanup** - Delete by date range, count, or presets
- **User management** - Track registered users for broadcast

### 🗄️ Database Management
- **Automatic monthly cleanup** - Scheduled database maintenance
- **Manual cleanup tools** - Admin can delete by date range or count
- **Balance preservation** - Cleanup removes records without affecting balance
- **Optimized queries** - 35% faster with indexed columns

### 🔧 Technical Excellence
- **Docker containerized** - Easy deployment and updates
- **Database persistence** - SQLite with WAL mode and optimizations
- **Reliable scheduling** - Async JobQueue ensures reports and cleanup always run
- **Error handling** - Robust error recovery and logging
- **Multi-user support** - Individual tracking with admin controls
- **Performance optimized** - Runs efficiently on all Raspberry Pi models
- **Persistent settings** - User preferences and admin settings stored in database

---

## 🎉 What's New

### Latest Features (v2.0)

#### 🔹 Configurable Walk Rate (`/setrate`)
Admins can change the per-walk price without editing code:
- `/setrate 80` — New walks are worth 80 MDL
- Persisted in database, applies immediately
- Useful for seasonal adjustments or rate changes

#### 🔹 Broadcast Messages (`/broadcast`)
Send announcements to all registered users:
- `/broadcast Important: New rate is 80 MDL per walk!`
- Reaches everyone who has started the bot
- Perfect for policy updates and notifications

#### 📥 Export Transactions (`/export`)
Download full transaction history as CSV:
- Compatible with Excel, Google Sheets, databases
- Includes timestamp, amount, type, description, and notes
- Useful for bookkeeping and tax records

#### 📝 Walk Notes
Add context to each walk you log:
- After `/addwalk`, tap **✏️ Add Note**
- Type distance, dog name, conditions, or anything useful
- Notes are searchable and visible in detailed reports

#### 🔥 Streak Tracking
Automatic motivation system:
- Displays consecutive days of walks in `/balance`
- Resets if you skip a day
- Encourages consistent daily habits

#### 🎯 Weekly Goals
Set and track personal targets:
- `/setgoal 10` — Aim for 10 walks per week
- Visual progress bar in `/balance`
- Update your goal anytime with `/setgoal <n>`

#### 📈 Earnings Forecast
Automatic month projection:
- `📈 Month forecast: ~2,250 MDL` in `/balance`
- Based on pace so far, projects month earnings
- Updates daily as you walk

#### 🔔 Daily Reminders
Optional push notifications:
- `/reminder 09:00` — Get reminded at 9 AM if no walk logged yet
- `/reminder off` — Disable
- Per-user setting; everyone chooses their own time

#### ↩️ Undo (`/undo`)
Quickly delete your last transaction:
- Shows the last entry with confirmation
- One-tap reversal if you made a mistake
- Resets balance automatically

#### 🔹 Individual Transaction Deletion
Admins can delete specific transactions directly from reports using inline buttons. Balance is automatically adjusted.

#### 🔹 Enhanced Detailed Reports
- Better visual formatting with emoji indicators
- Transaction IDs displayed for easy reference
- Summary statistics at the top
- Notes displayed for each transaction

#### 🔹 Fixed Scheduled Jobs
Weekly reports and monthly cleanup now run reliably:
- Switched from broken BackgroundScheduler to async JobQueue
- All background tasks guaranteed to execute
- Weekly reports now arrive on time
- Monthly cleanup completes as configured

#### 🔹 Performance Optimizations
- 95% fewer database queries with caching
- 35% faster query execution
- WAL journal mode for concurrency
- Memory-mapped database access
- Indexed columns for frequent queries

---

## 🛠️ Hardware Requirements

### Minimum Requirements
- **Raspberry Pi** (any model - Pi Zero W to Pi 4)
- **MicroSD Card** (8GB+ recommended, Class 10)
- **Internet Connection** (WiFi or Ethernet)

### Supported Platforms
- ✅ Raspberry Pi OS (Bullseye/Bookworm)
- ✅ Ubuntu 20.04+ (ARM64)
- ✅ Docker environments
- ✅ Any Linux system with Docker

---

## 🚀 Quick Setup

### 1️⃣ Prerequisites

```bash
# Update your system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose (if not included)
sudo apt install docker-compose -y
```

### 2️⃣ Get Your Telegram Bot Token

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Choose a name (e.g., "My K9 Walker Bot")
4. Choose a username (e.g., "my_k9walker_bot")
5. Copy the bot token (looks like: `1234567890:ABCD...`)

### 3️⃣ Get Your Chat ID

1. Message your bot on Telegram
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":12345678}` - that's your chat ID

### 4️⃣ Clone and Configure

```bash
# Clone the repository
git clone https://github.com/PR0M4XIMUS/k9LogBot.git
cd k9LogBot

# Create configuration file
cp .env.example .env

# Edit configuration
nano .env
```

### 5️⃣ Configure Environment Variables

Edit your `.env` file:

```env
# Required - Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCD-your-bot-token-here
YOUR_TELEGRAM_CHAT_ID=your_chat_id_here

# Optional - Performance Settings
DISPLAY_UPDATE_INTERVAL=10
STATS_CACHE_DURATION=30

# Optional - Auto Cleanup Settings
AUTO_CLEANUP_DAY=10
AUTO_CLEANUP_MONTHS_TO_KEEP=1
AUTO_CLEANUP_ENABLED=true
```

### 6️⃣ Deploy

```bash
# Deploy with the provided script
chmod +x deploy.sh
./deploy.sh

# Or manually with docker-compose
docker-compose up -d --build
```

### 7️⃣ Verify Installation

```bash
# Check deployment
./test_deployment.sh

# View logs
docker-compose logs -f
```

---

## 🎮 Usage Guide

### 🚀 Getting Started

1. Start a conversation with your bot on Telegram
2. Send `/start` to initialize
3. Use `/setinitial <amount>` to set starting balance (optional)
4. You're ready to track walks!

### 📱 Available Commands

#### User Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot and show welcome message | `/start` |
| `/help` | Display help with all available commands | `/help` |
| `/addwalk` | Record a new walk | `/addwalk` |
| `/balance` | Show balance, streak, weekly progress & forecast | `/balance` |
| `/setinitial <amount>` | Set initial balance | `/setinitial 100` |
| `/report` | Generate detailed activity report | `/report` |
| `/undo` | Delete the last transaction | `/undo` |
| `/setgoal <n>` | Set weekly walk goal | `/setgoal 10` |
| `/reminder <HH:MM>` | Set daily reminder (or `/reminder off`) | `/reminder 09:00` |

#### Admin Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/setrate <amount>` | Change the per-walk rate | `/setrate 80` |
| `/broadcast <message>` | Send announcement to all users | `/broadcast Rate increased to 80 MDL` |
| `/export` | Download all transactions as CSV | `/export` |
| `/cleanup` | Access detailed cleanup options | `/cleanup` |

### 🎯 Interactive Buttons

The bot provides easy-to-use buttons for common actions:

- **➕ Add Walk** - Quick walk logging
- **💰 Current Balance** - View current earnings
- **📊 Detailed Report** - Comprehensive activity report
- **❓ Help** - Show available commands
- **💳 Give Credit** - Add credit to balance
- **💸 Cash Out** - Withdraw earnings
- **🗑️ Cleanup Detailed Report** - Admin only

### 💳 Payment Operations

#### Adding Credit
1. Click **💳 Give Credit** or use the payment flow
2. Enter amount in MDL
3. Amount is added to your balance

#### Cashing Out
1. Click **💸 Cash Out**
2. Choose:
   - **💸 Pay Out All** - Withdraw entire balance
   - **✏️ Manual Amount** - Specify amount to withdraw
3. Confirm transaction

### 📊 Reports and Analytics

#### Balance Display (`/balance`)
- **Current Balance**: Your total earnings in MDL
- **Streak**: 🔥 Shows consecutive days with walks
- **Weekly Progress**: 🎯 Visual progress bar toward your goal (if set)
- **Month Forecast**: 📈 Projected earnings for the month based on current pace
- **Weekly Walks**: Total walks this week

#### Detailed Reports (`/report`)
- Complete transaction history with IDs
- Walk timestamps, amounts, and notes
- Payment/credit records with dates
- Balance calculations
- Individual delete buttons (admin only)

### 📝 Walk Notes
After logging a walk with `/addwalk` or **➕ Add Walk**:
1. An **✏️ Add Note** button appears
2. Tap it and type your note (e.g., "2 miles", "Dog name", "Special conditions")
3. Note is saved to that transaction
4. View notes in `/report` for detailed context

---

## 👨‍💼 Admin Functions

### Admin Setup

Admins are configured in `config.py`:

```python
ADMIN_CHAT_IDS = [864342269]  # Add your chat ID here
```

### Admin-Only Features

#### 🔹 Configurable Walk Rate (`/setrate`)
Change the payment per walk without editing code:
- `/setrate 80` — sets the rate to 80 MDL per walk
- `/setrate` — displays the current rate
- New rate applies to all walks logged going forward
- Existing transactions are not affected
- Rate is persisted in the database

#### 📢 Broadcast Messages (`/broadcast`)
Send announcements to all registered users:
- `/broadcast New rate is now 80 MDL per walk!`
- Useful for policy changes, scheduled downtime, or important updates
- All users who've used `/start` will receive the message

#### 📥 Export Transactions (`/export`)
Download all transaction history as a CSV file:
- `/export` — sends a timestamped CSV file
- Useful for bookkeeping, tax records, or data analysis
- File includes: timestamp, amount, type, description, and notes
- Can open in Excel, Google Sheets, or any spreadsheet tool

#### ↩️ Undo Last Transaction (`/undo`)
Quickly delete the most recent transaction:
- `/undo` — shows the last transaction with a confirmation button
- Tap **✅ Yes, Undo** to delete, or **❌ Cancel** to keep it
- Balance is automatically adjusted
- Works for admins and users (everyone can undo their own mistakes)

#### 🔹 Individual Transaction Deletion
Delete specific transactions directly from the report:
1. View **📊 Detailed Report**
2. Admin sees inline buttons with transaction IDs
3. Tap any transaction to delete it
4. Balance is automatically adjusted

#### 🗑️ Cleanup Reports (`/cleanup`)
Clean up transaction history with multiple options:

1. Click **🗑️ Cleanup Detailed Report** (admin button)
2. Choose cleanup option:
   - **📅 Last Week** - Delete past 7 days
   - **📆 Last Month** - Delete past 30 days
   - **📋 Last 10 Entries** - Delete recent 10 transactions
   - **🎯 Custom Date Range** - Specify custom dates
3. Preview what will be deleted
4. Confirm deletion

#### Automatic Monthly Cleanup
Scheduled cleanup runs automatically (configurable):
- Runs on specified day of each month at 03:00
- Keeps N months of records (configurable)
- Sends notification when completed
- Preserves balance while removing old records

---

## 🎯 User Features & Tracking

### 🔥 Streak Tracking
Monitor your consistency with consecutive-day streaks:
- Automatically calculated based on daily walks
- Displayed in `/balance` (e.g., "🔥 Streak: *7 days*")
- Resets if you skip a day
- Motivates daily walk habits

### 🎯 Weekly Goals
Set and track a personal weekly walk target:
- `/setgoal 10` — Set a goal of 10 walks per week
- `/balance` — Shows progress bar: `🎯 This week: *6/10* `[██████░░░░]``
- `/setgoal` — View your current goal and progress
- Visual progress bar updates as you log walks
- Helps maintain consistency and accountability

### 📈 Earnings Forecast
Automatically projects your month earnings based on current pace:
- Displayed in `/balance` (e.g., "📈 Month forecast: *~2,250 MDL*")
- Calculated as: `(earnings so far / days elapsed) × total days in month`
- Updates daily to reflect your walking pace
- Useful for budgeting and planning

### 🔔 Daily Reminders
Get a reminder if you forget to log a walk:
- `/reminder 09:00` — Set reminder for 9:00 AM
- `/reminder off` — Disable reminders
- `/reminder` — View your current reminder setting
- Sends a message only if no walk has been logged by that time
- Optional and per-user (each person sets their own time)

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | *Required* | Your Telegram bot token from BotFather |
| `YOUR_TELEGRAM_CHAT_ID` | *Required* | Chat ID for automated reports |
| `STATS_CACHE_DURATION` | `30` | Statistics cache duration (seconds) |
| `AUTO_CLEANUP_DAY` | `10` | Day of month for auto cleanup (1-28) |
| `AUTO_CLEANUP_MONTHS_TO_KEEP` | `1` | Months of records to retain |
| `AUTO_CLEANUP_ENABLED` | `true` | Enable/disable auto cleanup |

### Database Configuration

Database settings are automatically optimized:
- WAL journal mode for better concurrency
- Memory temp storage
- Optimized PRAGMA settings
- Automatic indexing on frequently queried columns

### Runtime Settings

User and admin settings are stored in the database:
- **settings table**: Global settings like walk rate
- **users table**: Tracks registered users for broadcast
- **user_settings table**: Per-user goals, reminders, preferences
- All settings persist across bot restarts
- No configuration files needed — everything is configurable via commands

---

## 📈 Performance

K9LogBot is optimized for Raspberry Pi performance:

### Database Optimizations
- **95% fewer database queries** with intelligent caching
- **35% faster query execution** with optimized PRAGMA settings
- **Indexed columns** for frequently accessed data
- **WAL mode** for better concurrency

### System Optimizations
- **Memory-mapped database** access
- **Optimized threading** for concurrent operations
- Runs efficiently on all Raspberry Pi models (Pi Zero to Pi 4)

### Scheduled Jobs
Reliable background tasks using python-telegram-bot's async JobQueue:
- **Weekly report**: Every Sunday at 20:00 (configurable chat ID)
- **Monthly cleanup**: Configurable day of month at 03:00
- **Daily reminders**: Run every minute to check if reminders are due
- All jobs are fully async and guaranteed to execute

For detailed performance information, see [PERFORMANCE.md](PERFORMANCE.md).

---

## 🐳 Docker & Deployment

### Basic Operations

```bash
# Start the bot
docker-compose up -d

# Stop the bot
docker-compose down

# Restart the bot
docker-compose restart

# View logs
docker-compose logs -f

# Update to latest version
git pull && docker-compose down && docker-compose up -d --build
```

### Maintenance

```bash
# Clean up old images
docker image prune

# Backup database
cp data/k9_log.db data/k9_log_backup_$(date +%Y%m%d).db

# View container stats
docker stats k9logbot
```

### Update Script

Create `update.sh` for easy updates:

```bash
#!/bin/bash
cd /path/to/k9LogBot
git pull
docker-compose down
docker-compose up -d --build
echo "✅ K9LogBot updated successfully!"
```

### Backup Strategy

Daily backup cron job:

```bash
0 2 * * * cp /path/to/k9LogBot/data/k9_log.db /backups/k9_log_$(date +\%Y\%m\%d).db
```

---

## 🔧 Troubleshooting

### Common Issues

#### Bot Not Responding

```bash
# Check if container is running
docker ps

# View logs for errors
docker-compose logs -f

# Restart the bot
docker-compose restart
```

#### Database Issues

```bash
# Check database file
ls -la data/k9_log.db

# Reset database (⚠️ WARNING: This will delete all data!)
rm data/k9_log.db
docker-compose restart
```

#### Permission Errors

```bash
# Fix container permissions
sudo chown -R $USER:$USER data/
docker-compose down && docker-compose up -d
```

### Performance Issues

#### High CPU Usage
- Increase `STATS_CACHE_DURATION` in .env

#### Memory Issues
- Ensure adequate swap space: `sudo fallocate -l 1G /swapfile`
- Monitor with: `docker stats k9logbot`

### Getting Help

1. **Check Logs**: `docker-compose logs -f`
2. **Test Deployment**: `./test_deployment.sh`
3. **Health Check**: `./health_check.sh`
4. **Create Issue**: [GitHub Issues](https://github.com/PR0M4XIMUS/k9LogBot/issues)

---

## 📝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and test thoroughly
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/k9LogBot.git
cd k9LogBot

# Create development environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram Bot API wrapper
- [luma.oled](https://github.com/rm-hull/luma.oled) - OLED display library
- [APScheduler](https://github.com/agronholm/apscheduler) - Advanced Python Scheduler
- Raspberry Pi Foundation for creating amazing hardware

---

## 📞 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/PR0M4XIMUS/k9LogBot/issues)
- **Discussions**: [Community discussions and Q&A](https://github.com/PR0M4XIMUS/k9LogBot/discussions)
- **Documentation**: Check this README and [PERFORMANCE.md](PERFORMANCE.md)

---

<p align="center">
  Made with ❤️ for dog lovers and their furry friends!
</p>

<p align="center">
  <em>Happy walking! 🐕‍🦺</em>
</p>
