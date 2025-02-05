import asyncio
from twscrape import API

async def search_tweets(query: str):
    api = API()
    try:
        print(f"Searching for tweets related to: {query}")
        async for tweet in api.search(query, limit=5):
            print(f"[{tweet.date}] @{tweet.user.username}: {tweet.text}")
    except Exception as e:
        print(f"Error during search: {e}")

if __name__ == "__main__":
    query = "basketball highlights"
    asyncio.run(search_tweets(query))
