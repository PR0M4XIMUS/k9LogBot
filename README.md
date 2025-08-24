# 🐕 K9LogBot - Smart Dog Walking Tracker

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Raspberry%20Pi-red.svg" alt="Platform">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Telegram-Bot-blue.svg" alt="Telegram Bot">
</p>

**K9LogBot** is an intelligent Telegram bot designed to track dog walks and manage payments for dog walking services. Perfect for professional dog walkers, pet sitters, or anyone who wants to gamify their dog walking routine! 

## ✨ Features

### 🚶‍♀️ Walk Tracking
- **One-tap walk logging** - Record walks instantly with a button press
- **Automatic balance calculation** - Each walk adds to your earning balance
- **Daily/Weekly statistics** - Track your walking activity over time
- **Detailed reports** - View comprehensive walk history with dates and earnings

### 💰 Payment Management  
- **Balance tracking** in MDL (Moldovan Leu) currency
- **Credit system** - Add credits/payments to balance
- **Cash-out functionality** - Full or partial balance withdrawals
- **Transaction history** - Complete record of all payments and walks

### 📊 Smart Reporting
- **Real-time balance display** - Always know your current earnings
- **Weekly automated reports** - Scheduled summary reports every Sunday
- **Admin dashboard** - Advanced management and cleanup tools
- **Export capabilities** - Detailed transaction reports

### 🖥️ Hardware Integration
- **OLED Display Support** - Live stats on 128x64 OLED screen
- **Raspberry Pi Optimized** - Runs efficiently on Pi Zero to Pi 4
- **I2C Integration** - Seamless hardware display connection
- **Performance Monitoring** - Real-time system stats on display

### 🔧 Technical Excellence
- **Docker containerized** - Easy deployment and updates
- **Database persistence** - SQLite with performance optimizations
- **Automated scheduling** - Built-in task scheduler
- **Error handling** - Robust error recovery and logging
- **Multi-user support** - Individual user tracking and admin controls

## 🛠️ Hardware Requirements

### Minimum Requirements
- **Raspberry Pi** (any model - Pi Zero W to Pi 4)
- **MicroSD Card** (8GB+ recommended, Class 10)
- **Internet Connection** (WiFi or Ethernet)

### Optional Hardware
- **OLED Display** (128x64, I2C interface)
  - Supported: SSD1306 chipset displays
  - Connection: I2C (GPIO pins 3 & 5)
  - Address: 0x3C (default)

### Supported Platforms
- ✅ Raspberry Pi OS (Bullseye/Bookworm)
- ✅ Ubuntu 20.04+ (ARM64)
- ✅ Docker environments
- ✅ Any Linux system with Docker

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

# Enable I2C (for OLED display - optional)
sudo raspi-config
# Navigate to: Interface Options > I2C > Enable
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

## 🎮 Usage Guide

### 🚀 Getting Started
1. Start a conversation with your bot on Telegram
2. Send `/start` to initialize
3. Use `/setinitial <amount>` to set starting balance (optional)
4. You're ready to track walks!

### 📱 Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot and show welcome message | `/start` |
| `/help` | Display help with all available commands | `/help` |
| `/addwalk` | Record a new walk (+1 to balance) | `/addwalk` |
| `/balance` | Show current balance | `/balance` |
| `/setinitial <amount>` | Set initial balance | `/setinitial 100` |
| `/report` | Generate detailed activity report | `/report` |

### 🎯 Interactive Buttons

The bot provides easy-to-use buttons for common actions:

- **➕ Add Walk** - Quick walk logging
- **💰 Current Balance** - View current earnings  
- **📊 Detailed Report** - Comprehensive activity report
- **❓ Help** - Show available commands
- **💳 Give Credit** - Add credit to balance
- **💸 Cash Out** - Withdraw earnings

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

#### Balance Information
- **Current Balance**: Shows your current earnings in MDL
- **Total Walks**: Cumulative walk count
- **Daily Stats**: Walks completed today
- **Transaction History**: All credits and payments

#### Detailed Reports
- Complete transaction history
- Walk timestamps and earnings
- Payment/credit records
- Balance calculations

## 👨‍💼 Admin Functions

### Admin Setup
Admins are configured in `config.py`:
```python
ADMIN_CHAT_IDS = [864342269]  # Add your chat ID here
```

### Admin-Only Features

#### 🗑️ Cleanup Reports
Admins can clean up transaction history:

1. Click **🗑️ Cleanup Detailed Report** (admin button)
2. Choose cleanup option:
   - **📅 Last Week** - Delete past 7 days
   - **📆 Last Month** - Delete past 30 days  
   - **📋 Last 10 Entries** - Delete recent 10 transactions
   - **🎯 Custom Date Range** - Specify custom dates
3. Preview and confirm deletion

#### Advanced Management
- View system statistics
- Monitor bot performance
- Access detailed logs
- Bulk operations

## ⚙️ Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | *Required* | Your Telegram bot token from BotFather |
| `YOUR_TELEGRAM_CHAT_ID` | *Required* | Chat ID for automated reports |
| `DISPLAY_UPDATE_INTERVAL` | `10` | OLED update interval (seconds) |
| `STATS_CACHE_DURATION` | `30` | Statistics cache duration (seconds) |

### Performance Tuning

#### For Raspberry Pi Zero/1:
```env
DISPLAY_UPDATE_INTERVAL=15
STATS_CACHE_DURATION=60
```

#### For Raspberry Pi 3/4:
```env
DISPLAY_UPDATE_INTERVAL=5
STATS_CACHE_DURATION=30
```

### Database Configuration
Database settings are automatically optimized:
- WAL journal mode for better concurrency
- Memory temp storage
- Optimized PRAGMA settings
- Automatic indexing

## 🖥️ OLED Display Setup

### Hardware Connection
Connect your 128x64 I2C OLED display:

| OLED Pin | Pi Pin | Description |
|----------|--------|-------------|
| VCC | Pin 1 (3.3V) | Power |
| GND | Pin 6 (GND) | Ground |
| SCL | Pin 5 (GPIO 3) | I2C Clock |
| SDA | Pin 3 (GPIO 2) | I2C Data |

### Display Features
- **Real-time stats**: Current balance, walks, activity
- **System info**: CPU usage, memory, uptime
- **Bot status**: Online/offline, message count
- **Notifications**: Walk added, payments, errors

### Testing Display
```bash
# Check I2C connection
sudo i2cdetect -y 1

# Should show device at address 3C:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- --
```

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

#### OLED Display Not Working
```bash
# Check I2C is enabled
sudo raspi-config

# Test I2C connection
sudo i2cdetect -y 1

# Check display address (usually 0x3C or 0x3D)
```

#### Permission Errors
```bash
# Fix container permissions
sudo chown -R $USER:$USER data/
docker-compose down && docker-compose up -d
```

### Performance Issues

#### High CPU Usage
- Increase `DISPLAY_UPDATE_INTERVAL` in .env
- Increase `STATS_CACHE_DURATION` in .env
- Consider disabling OLED display temporarily

#### Memory Issues  
- Ensure adequate swap space: `sudo fallocate -l 1G /swapfile`
- Monitor with: `docker stats k9logbot`

### Getting Help

1. **Check Logs**: `docker-compose logs -f`
2. **Test Deployment**: `./test_deployment.sh`
3. **Health Check**: `./health_check.sh`
4. **Create Issue**: [GitHub Issues](https://github.com/PR0M4XIMUS/k9LogBot/issues)

## 📈 Performance Optimization

K9LogBot is optimized for Raspberry Pi performance:

### Database Optimizations
- **95% fewer database queries** with intelligent caching
- **35% faster query execution** with optimized PRAGMA settings
- **Indexed columns** for frequently accessed data

### Display Optimizations  
- **50% fewer display updates** with configurable intervals
- **Simplified rendering** to reduce CPU load
- **Efficient memory usage** for graphics operations

### System Optimizations
- **74% overall CPU load reduction**
- **Memory-mapped database** access
- **Optimized threading** for concurrent operations

For detailed performance information, see [PERFORMANCE.md](PERFORMANCE.md).

## 🐳 Docker Commands

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
git pull && docker-compose up -d --build
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

## 🔄 Updates and Maintenance

### Automatic Updates
```bash
# Update script (create update.sh)
#!/bin/bash
cd /path/to/k9LogBot
git pull
docker-compose down
docker-compose up -d --build
echo "✅ K9LogBot updated successfully!"
```

### Backup Strategy
```bash
# Daily backup cron job
0 2 * * * cp /path/to/k9LogBot/data/k9_log.db /backups/k9_log_$(date +\%Y\%m\%d).db
```

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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram Bot API wrapper
- [luma.oled](https://github.com/rm-hull/luma.oled) - OLED display library  
- [APScheduler](https://github.com/agronholm/apscheduler) - Advanced Python Scheduler
- Raspberry Pi Foundation for creating amazing hardware

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