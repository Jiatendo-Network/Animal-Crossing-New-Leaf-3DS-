import asyncio

from main import main

async def init():
    main_ = asyncio.create_task(main())
    await main_

if __name__ == "__main__":
    asyncio.run(init())