import asyncio
from sqlalchemy import text

from app.core.database import async_session_factory
from app.utils.location import parse_city_state_from_address


DDL_STATEMENTS = [
    "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS city VARCHAR(120)",
    "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS state VARCHAR(10)",
    "CREATE INDEX IF NOT EXISTS ix_mechanics_city ON mechanics(city)",
    "CREATE INDEX IF NOT EXISTS ix_mechanics_state ON mechanics(state)",
    "CREATE INDEX IF NOT EXISTS ix_mechanics_state_city ON mechanics(state, city)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS driver_city VARCHAR(120)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS driver_state VARCHAR(10)",
]


async def main() -> None:
    async with async_session_factory() as session:
        for statement in DDL_STATEMENTS:
            await session.execute(text(statement))

        result = await session.execute(
            text("SELECT id, address, city, state FROM mechanics")
        )
        mechanics = result.mappings().all()

        updated = 0
        for mechanic in mechanics:
            city, state = parse_city_state_from_address(mechanic["address"])
            if mechanic["city"] != city or mechanic["state"] != state:
                await session.execute(
                    text(
                        "UPDATE mechanics SET city = :city, state = :state WHERE id = :id"
                    ),
                    {"id": mechanic["id"], "city": city, "state": state},
                )
                updated += 1

        await session.commit()
        print(f"Migration complete. Backfilled {updated} mechanic records.")


if __name__ == "__main__":
    asyncio.run(main())
