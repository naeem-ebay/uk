import os
import base64
import httpx
from fastmcp import FastMCP

mcp = FastMCP("eBay UK Product Hunter")

EBAY_APP_ID = os.environ["EBAY_APP_ID"]
EBAY_CERT_ID = os.environ["EBAY_CERT_ID"]

EBAY_API = "https://api.ebay.com"
MARKETPLACE_ID = "EBAY_GB"


async def get_ebay_token():
    credentials = f"{EBAY_APP_ID}:{EBAY_CERT_ID}"
    encoded = base64.b64encode(credentials.encode()).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{EBAY_API}/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )

        response.raise_for_status()
        return response.json()["access_token"]


@mcp.tool()
async def ebay_search(
    keyword: str,
    min_price: float = 20,
    max_price: float = 60,
    limit: int = 10,
):
    """Search current eBay UK listings for product-hunting research."""

    token = await get_ebay_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{EBAY_API}/buy/browse/v1/item_summary/search",
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
            },
            params={
                "q": keyword,
                "filter": (
                    f"price:[{min_price}..{max_price}],"
                    "priceCurrency:GBP,"
                    "buyingOptions:{FIXED_PRICE}"
                ),
                "limit": min(limit, 50),
            },
        )

        response.raise_for_status()
        data = response.json()

    results = []

    for item in data.get("itemSummaries", []):
        results.append({
            "title": item.get("title"),
            "price": item.get("price", {}).get("value"),
            "currency": item.get("price", {}).get("currency"),
            "item_id": item.get("itemId"),
            "condition": item.get("condition"),
            "seller": item.get("seller", {}).get("username"),
            "seller_feedback": item.get("seller", {}).get("feedbackPercentage"),
            "url": item.get("itemWebUrl"),
        })

    return {
        "marketplace": "eBay UK",
        "keyword": keyword,
        "results": results,
        "total_found": data.get("total"),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
