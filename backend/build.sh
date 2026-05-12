#!/usr/bin/env bash
# Build script for the FastAPI backend (DO App Platform / local)
set -o errexit

# Install uv
pip install uv

# Install dependencies using requirements.txt (system-wide for Render)
uv pip install -r requirements.txt --system

# Run database migrations (creates tables on first deploy)
python -c "
import asyncio, ssl, os

async def init_db():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        print('No DATABASE_URL set, skipping DB init')
        return

    # Convert URL for asyncpg
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    elif url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+asyncpg://', 1)

    # SSL for managed DB
    connect_args = {}
    if 'localhost' not in url and '127.0.0.1' not in url:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args['ssl'] = ssl_ctx

    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(url, connect_args=connect_args)

    # Import all models so metadata knows about them
    from app.core.database import Base
    from app.models.job import Job
    from app.models.mechanic import Mechanic
    from app.models.dispatch_attempt import DispatchAttempt
    from app.models.tracking_session import TrackingSession
    from app.models.audit_event import AuditEvent
    # Major vendor (chain) locations — Love's, TA, Petro, Pilot/FJ, Speedco,
    # Rush, FleetPride, Boss Truck Shops, Southern Tire Mart, etc.
    from app.models.major_vendor_location import MajorVendorLocation

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print('Database tables created/verified successfully')

asyncio.run(init_db())
"

# Seed the major chain vendor table from the bundled Apify scrape.
# Idempotent — safe on every deploy. Falls back silently if no DATABASE_URL.
echo "Seeding major chain vendor locations from data/chains_raw.json…"
python -m scripts.import_chain_locations --file data/chains_raw.json || \
    echo "⚠️  chain seed skipped (non-fatal)"

echo "Build complete"
