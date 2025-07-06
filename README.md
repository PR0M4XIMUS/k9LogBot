# K9LogBot - Dog Walking Payment Tracker with OLED Display

A Telegram bot for tracking dog walking payments with integrated OLED display support for 24/7 monitoring on Raspberry Pi.

## Features

### Core Bot Features
- **Dog Walk Tracking**: Record walks and automatically update balance (75 MDL per walk)
- **Payment Management**: Track payments made and credits given
- **Balance Monitoring**: Real-time balance tracking with clear status indicators
- **Detailed Reports**: Comprehensive transaction history and weekly summaries
- **Automated Scheduling**: Weekly reports via APScheduler

### OLED Display Features (NEW!)
- **24/7 Monitoring**: Continuous display of bot status and statistics
- **4 Rotating Screens**: 
  1. Bot status and uptime
  2. Current balance with large text
  3. Statistics (total walks, walks today, total earned)
  4. Current date and time
- **Live Notifications**: Temporary notifications for actions (walks, payments, credits)
- **Thread-Safe Operation**: Concurrent display management with proper locking
- **Graceful Fallback**: Continues operation if OLED display is not connected

## Requirements

### Hardware
- Raspberry Pi (for OLED display functionality)
- I2C OLED Display (128x64 pixels) - Optional
- Common I2C addresses supported: 0x3C, 0x3D

### Software
- Python 3.11+
- Docker & Docker Compose
- Telegram Bot Token

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/PR0M4XIMUS/k9LogBot.git
cd k9LogBot
```

### 2. Configure Environment
```bash
cp env.txt .env
# Edit .env with your configuration
```

### 3. Environment Variables
```bash
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
YOUR_TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# OLED Display (Optional)
OLED_ENABLED=true
OLED_WIDTH=128
OLED_HEIGHT=64
OLED_ADDRESS=0x3C
OLED_SCREEN_INTERVAL=5
```

### 4. Deploy with Docker
```bash
# Make deploy script executable
chmod +x deploy.sh

# Deploy the bot
./deploy.sh
```

## OLED Display Setup

### Hardware Connection
1. Connect OLED display to Raspberry Pi I2C pins:
   - VCC → 3.3V
   - GND → Ground
   - SCL → GPIO 3 (SCL)
   - SDA → GPIO 2 (SDA)

2. Enable I2C on Raspberry Pi:
```bash
sudo raspi-config
# Navigate to: Interfacing Options → I2C → Enable
```

3. Test I2C connection:
```bash
sudo i2cdetect -y 1
```

### Display Configuration
The OLED display is fully configurable via environment variables:
- `OLED_ENABLED`: Enable/disable display functionality
- `OLED_WIDTH`: Display width in pixels (default: 128)
- `OLED_HEIGHT`: Display height in pixels (default: 64)
- `OLED_ADDRESS`: I2C address (default: 0x3C)
- `OLED_SCREEN_INTERVAL`: Screen rotation interval in seconds (default: 5)

## Usage

### Telegram Commands
- `/start` - Initialize bot and show main menu
- `/addwalk` - Record a dog walk (75 MDL)
- `/balance` - Show current balance
- `/credit` - Record credit given
- `/cashout` - Record payment made
- `/report` - Get detailed transaction report
- `/setinitial <amount>` - Set initial balance
- `/help` - Show help message

### OLED Display Screens
1. **Status Screen**: Bot status, uptime, and connection info
2. **Balance Screen**: Current balance with large text and status
3. **Statistics Screen**: Total walks, walks today, total earned
4. **Time Screen**: Current date, time, and week information

### Display Notifications
The OLED display shows temporary notifications for:
- Walk added
- Payment made
- Credit given
- Balance updates

## Monitoring

### Health Check
```bash
# Check bot status
./health_check.sh

# View logs
docker-compose logs -f
```

### Statistics Tracking
The bot automatically tracks:
- Total walks performed
- Walks completed today
- Total earnings
- Current balance
- Transaction history

## Docker Configuration

### I2C Device Access
The docker-compose.yml is configured for I2C access:
- Privileged mode for hardware access
- I2C device mapping (`/dev/i2c-1`)
- System directory mounting for hardware detection

### Volume Mounting
- `./data:/app/data` - Database persistence
- `/sys:/sys:ro` - Hardware access (read-only)

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN=your_token
export OLED_ENABLED=false  # Disable OLED for development

# Run the bot
python main.py
```

### Testing
```bash
# Run functional tests
python test_k9logbot.py
```

## Architecture

### Key Components
- `main.py`: Application entry point and OLED integration
- `bot_logic.py`: Telegram bot commands and conversation handlers
- `database.py`: SQLite database operations and statistics
- `oled_display.py`: Thread-safe OLED display manager
- `config.py`: Environment configuration management

### Database Schema
- `transactions`: All financial transactions
- `balance`: Current balance tracking

## Troubleshooting

### OLED Display Issues
1. **Display not working**: Check I2C wiring and address
2. **Permission denied**: Ensure Docker privileged mode is enabled
3. **Module not found**: Verify luma.oled installation

### Common Issues
1. **Bot not responding**: Check Telegram token and network connectivity
2. **Database errors**: Ensure data directory permissions
3. **Container won't start**: Check Docker daemon and port conflicts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs: `docker-compose logs -f`
3. Open an issue on GitHub

---

**Note**: OLED display functionality requires a Raspberry Pi with I2C enabled and an OLED display connected. The bot will function normally without the display hardware.