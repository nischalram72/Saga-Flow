import asyncio
import uvicorn
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)
