# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**K9LogBot** is a Telegram bot for tracking dog walks and managing payments. It runs on Raspberry Pi with optional OLED display support, SQLite database persistence, and automated scheduling for weekly reports and monthly database cleanup.

- **Primary Language**: Python 3.11+
- **Deployment**: Docker/Docker Compose
- **Database**: SQLite with WAL mode and performance optimizations
- **Core Dependencies**: `python-telegram-bot`, `APScheduler`, `luma.oled` (optional display), `python-dotenv`

## Architecture

### High-Level Structure

1. **main.py** - Application entry point
   - Initializes database, Telegram bot, scheduler, and OLED display
   - Manages `BotStatsManager` for caching database stats (reduces query frequency)
   - Sets up `APScheduler` for weekly reports (Sundays 20:00) and monthly cleanup
   - Handles graceful shutdown with cleanup

2. **bot_logic.py** - Telegram command handlers
   - Command handlers: `/start`, `/addwalk`, `/balance`, `/help`, `/setinitial`, `/report`
   - Conversation handlers for credit/cashout flows using `ConversationHandler`
   - Inline buttons for transaction deletion (admin-only)
   - Interactive keyboard with role-based buttons

3. **database.py** - SQLite operations
   - Performance-optimized connection with PRAGMA settings (WAL mode, mmap, temp_store=MEMORY)
   - Two core tables: `transactions` (id, timestamp, amount, type, description) and `balance`
   - Indexed columns on `transaction_type`, `timestamp` for fast queries
   - Functions for: walks, credits, payments, reports, cleanup
   - Cache-busting in `main.py` when activity occurs

4. **config.py** - Configuration and admin management
   - Environment variable loading via `python-dotenv`
   - `is_admin(chat_id)` utility for role-based access control
   - Configurable: cache duration, cleanup schedule, auto-cleanup toggle

5. **oled_display.py** - Raspberry Pi OLED display manager
   - Optional hardware integration (gracefully fails if not connected)
   - Displays bot stats and notifications

6. **report_cleanup.py** - Transaction history cleanup
   - Cleanup by date range, count, or presets (last week/month/10 entries)
   - Preserves balance while deleting records

7. **manual_cleanup.py** - Standalone cleanup utility
   - On-demand cleanup script

### Key Design Patterns

- **Conversation Handlers**: Credit/cashout flows use `ConversationHandler` with state management
- **Caching Layer**: `BotStatsManager` caches database stats; cache invalidates on user activity
- **Admin Role System**: `config.ADMIN_CHAT_IDS` list controls access to sensitive operations
- **Async Patterns**: Uses `async/await` for Telegram bot handlers and scheduled tasks
- **Database Optimization**: WAL mode for concurrency, memory-mapped access, indexed queries

## Common Development Tasks

### Running the Bot Locally (with Docker)

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Stop
docker-compose down
```

### Running the Bot Without Docker

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Set TELEGRAM_BOT_TOKEN and YOUR_TELEGRAM_CHAT_ID

# Run
python main.py
```

### Deployment

```bash
# Deploy script (creates data dir, builds image, starts container)
chmod +x deploy.sh
./deploy.sh
```

### Testing & Health Checks

```bash
# Deployment test script
./test_deployment.sh

# Health check script
./health_check.sh
```

### Viewing Container Logs

```bash
# Real-time logs
docker-compose logs -f k9logbot

# Last 50 lines
docker-compose logs --tail=50 k9logbot
```

## Configuration

### Environment Variables (in .env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | *Required* | Bot token from BotFather |
| `YOUR_TELEGRAM_CHAT_ID` | *Required* | Chat ID for scheduled reports |
| `STATS_CACHE_DURATION` | `30` | Seconds to cache database stats |
| `DISPLAY_UPDATE_INTERVAL` | `10` | OLED display refresh interval (seconds) |
| `AUTO_CLEANUP_DAY` | `10` | Day of month for auto cleanup (1-28) |
| `AUTO_CLEANUP_MONTHS_TO_KEEP` | `1` | Months of records to retain |
| `AUTO_CLEANUP_ENABLED` | `true` | Enable/disable auto cleanup |

### Admin Setup

Edit `config.py`:
```python
ADMIN_CHAT_IDS = [864342269]  # Add admin chat IDs here
```

Admin-only features:
- Individual transaction deletion from detailed reports
- Cleanup operations with date range/count options
- Manual cleanup via `manual_cleanup.py`

## Database Schema

### tables

**transactions**
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `timestamp` (TEXT, ISO format)
- `amount` (REAL)
- `transaction_type` (TEXT: 'walk', 'credit', 'payment')
- `description` (TEXT)

**balance**
- `id` (INTEGER PRIMARY KEY)
- `current_balance` (REAL)

### indexes

- `idx_transaction_type`: Fast filtering by type
- `idx_timestamp`: Fast date-based queries
- `idx_type_timestamp`: Combined index for frequent queries

## Important Implementation Details

### Walk Recording
- Each walk adds 75 MDL to balance
- Creates transaction record with type 'walk'
- Cache is invalidated on user activity

### Balance Management
- Single row in `balance` table (id=1)
- Updated atomically with transaction insertion
- Cached in `BotStatsManager` to reduce query frequency

### Scheduled Tasks
- **Weekly Report**: Sundays at 20:00 via APScheduler
- **Monthly Cleanup**: Configurable day at 03:00, removes records older than N months while preserving balance

### OLED Display (Optional)
- Fails gracefully if hardware not available
- Shows bot stats and notifications
- Respects `DISPLAY_UPDATE_INTERVAL` configuration

## Performance Optimizations

1. **Database**:
   - WAL mode for concurrent access
   - PRAGMA settings: `synchronous=NORMAL`, `temp_store=MEMORY`, `mmap_size=268435456`
   - Indexes on frequently queried columns
   - Connection reuse with context manager

2. **Caching**:
   - `BotStatsManager._stats_cache` reduces database hits
   - Cache duration configurable via `STATS_CACHE_DURATION`
   - Cache invalidates when activity occurs

3. **Queries**:
   - Use indexed columns in WHERE clauses
   - Aggregate calculations in database (SUM, COUNT)
   - Batch operations where possible

## Testing Checklist

When modifying features:
- [ ] Test with Docker: `docker-compose up -d --build`
- [ ] Verify logs: `docker-compose logs -f`
- [ ] Test bot commands: `/start`, `/addwalk`, `/balance`, `/report`
- [ ] Test user flows: credit, cashout, detailed reports
- [ ] Admin tests: transaction deletion, cleanup operations
- [ ] Database consistency: balance matches sum of transactions
- [ ] OLED display updates (if hardware available)
- [ ] Scheduled tasks work as expected

## Common Pitfalls

1. **Cache Invalidation**: Ensure `record_activity()` is called when user makes changes, or cached stats will be stale
2. **Database Transactions**: Always use context manager (`with get_db_connection() as conn:`) to ensure commits
3. **Admin IDs**: Remember to add new admin IDs to `config.ADMIN_CHAT_IDS`, not just database
4. **Timezone Handling**: Timestamps are ISO format; scheduler is timezone-aware
5. **OLED Display**: Graceful degradation if hardware unavailable; exceptions are caught and logged
6. **Conversation States**: ConversationHandler states must be unique integers; review all state definitions before adding new ones

## References

- **Telegram Bot API**: [python-telegram-bot documentation](https://python-telegram-bot.readthedocs.io/)
- **APScheduler**: [Scheduling docs](https://apscheduler.readthedocs.io/)
- **SQLite Performance**: Built-in PRAGMA optimizations in `database.py`
- **Docker**: See `dockerfile` and `docker-compose.yml` for container setup
- **OLED Library**: [luma.oled](https://github.com/rm-hull/luma.oled) for display integration
