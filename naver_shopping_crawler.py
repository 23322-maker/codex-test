"""Utilities for crawling product information from Naver Shopping."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright
from urllib.parse import quote


def crawl_naver_shopping(
    keyword: str,
    min_rating: float = 4.9,
    min_reviews: int = 100,
    max_pages: int = 2,
) -> List[Dict[str, Any]]:
    """
    Fetch product information from Naver Shopping using Playwright.

    Args:
        keyword: Search query to send to Naver Shopping.
        min_rating: Minimum rating that products must have to be included.
        min_reviews: Minimum number of reviews required for products.
        max_pages: Maximum number of result pages to crawl. Start low to
            avoid being blocked by Naver.

    Returns:
        A list of dictionaries containing product information, each with the
        keys ``name``, ``price``, ``rating`` and ``reviews``.
    """

    base_url = (
        "https://search.shopping.naver.com/search/all?"
        "query={query}&pagingIndex={page}&pagingSize=40"
    )

    results: List[Dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        for page_idx in range(1, max_pages + 1):
            url = base_url.format(query=quote(keyword), page=page_idx)
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(1000)  # Wait 1 second to ensure elements are loaded

            items = page.locator(
                "div.product_item__MDtDF, div.product_item__KZ02m"
            ).all()
            if not items:
                items = page.locator("div.product_item__MDtDF").all()

            for item in items:
                try:
                    name = item.locator("a.product_link__TrAac").inner_text().strip()
                except Exception:
                    # Skip cards without titles.
                    continue

                price: Optional[int] = None
                try:
                    price_text = (
                        item.locator("span.price_num__S2p_v")
                        .inner_text()
                        .replace(",", "")
                        .replace("원", "")
                        .strip()
                    )
                    if price_text.isdigit():
                        price = int(price_text)
                except Exception:
                    pass

                rating: Optional[float] = None
                try:
                    rating_text = (
                        item.locator("span.product_grade__IzyU3").inner_text().strip()
                    )
                    rating = float(rating_text.replace("별점", "").strip())
                except Exception:
                    pass

                reviews = 0
                try:
                    review_text = (
                        item.locator("span.product_review__a1z2V")
                        .inner_text()
                        .strip()
                    )
                    review_text = review_text.replace("리뷰", "").replace(",", "").strip()
                    if review_text.isdigit():
                        reviews = int(review_text)
                except Exception:
                    pass

                if rating is None or rating < min_rating or reviews < min_reviews:
                    continue

                results.append(
                    {
                        "name": name,
                        "price": price,
                        "rating": rating,
                        "reviews": reviews,
                    }
                )

        browser.close()

    return results


if __name__ == "__main__":
    KEYWORD = "삼겹살"
    data = crawl_naver_shopping(
        KEYWORD,
        min_rating=4.9,
        min_reviews=100,
        max_pages=2,
    )

    data = sorted(
        data,
        key=lambda item: (
            item["price"] is None,
            item["price"] if item["price"] is not None else 999_999_999,
        ),
    )

    print(f"=== 네이버쇼핑 '{KEYWORD}' 필터링 결과 ({len(data)}개) ===")
    for index, entry in enumerate(data, start=1):
        price_value = entry["price"]
        price_output = f"{price_value}원" if price_value is not None else "표시 안 됨"
        print(f"{index}. {entry['name']}")
        print(f"   - 가격: {price_output}")
        print(f"   - 평점: {entry['rating']}")
        print(f"   - 리뷰: {entry['reviews']}")
