import asyncio, sys
sys.path.insert(0, "/app")
from app.services.web_search import search_web, generate_web_answer


async def t():
    print("=== Gemini search ===")
    text, meta = await generate_web_answer("iPhone 15 price in Bangladesh")
    print(f"Answer: {text[:500]}")
    chunks = meta.get("groundingChunks", [])
    print(f"Sources: {len(chunks)}")
    for s in chunks[:3]:
        w = s.get("web", {})
        print(f"  - {w.get('name','')} | {w.get('uri','')[:60]}")

    print()
    r = await search_web("iPhone 15 price in Bangladesh", 2)
    print(f"Chunks: {len(r)}")
    for x in r:
        print(f"  {x['filename'][:60]} | {len(x['content'])}c")


asyncio.run(t())
