"""
Step 1: 연합뉴스에서 기사 50개 스크래핑 → data/raw/{id}.txt 저장

raw 파일 형식 (크롤러팀이 줄 plain text 시뮬레이션):
  제목: ...
  날짜: ...
  기자: ...
  URL: ...
  ---
  본문 내용...
"""

import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from pipeline.common import RAW_DIR

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 수집할 연합뉴스 카테고리 목록 페이지
LIST_URLS = [
    "https://www.yna.co.kr/politics/all",
    "https://www.yna.co.kr/economy/all",
    "https://www.yna.co.kr/society/all",
    "https://www.yna.co.kr/entertainment/all",
    "https://www.yna.co.kr/international/all",
]


def get_article_urls(list_url: str, limit: int = 15) -> list[str]:
    """목록 페이지에서 기사 URL 수집"""
    try:
        resp = requests.get(list_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.select("a[href*='/view/AKR']"):
            href = a.get("href", "")
            if href.startswith("/"):
                href = "https://www.yna.co.kr" + href
            href = href.split("?")[0]
            if href not in links:
                links.append(href)
            if len(links) >= limit:
                break
        return links
    except Exception as e:
        print(f"  ⚠️  목록 수집 실패 {list_url}: {e}")
        return []


def fetch_article_text(url: str) -> dict | None:
    """기사 URL → plain text 데이터"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.select_one("h1.tit") or soup.select_one(".article-tit") or soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        date_el = soup.select_one(".update-time") or soup.select_one("time")
        date = date_el.get_text(strip=True) if date_el else ""

        author_el = soup.select_one(".writer") or soup.select_one(".byline")
        author = author_el.get_text(strip=True) if author_el else ""

        body_el = soup.select_one(".article") or soup.select_one(".article-txt") or soup.select_one("article")
        if body_el:
            for tag in body_el.select("figure, .sns-wrap, .copyright, script, style, .ad"):
                tag.decompose()
            content = body_el.get_text(separator="\n", strip=True)
        else:
            content = ""

        if not title or not content or len(content) < 200:
            return None

        return {"title": title, "date": date, "author": author, "url": url, "content": content}
    except Exception as e:
        print(f"  ⚠️  기사 수집 실패 {url}: {e}")
        return None


def save_raw(article_id: str, data: dict) -> Path:
    """raw text 파일로 저장"""
    path = RAW_DIR / f"{article_id}.txt"
    text = (
        f"제목: {data['title']}\n"
        f"날짜: {data['date']}\n"
        f"기자: {data['author']}\n"
        f"URL: {data['url']}\n"
        f"---\n"
        f"{data['content']}"
    )
    path.write_text(text, encoding="utf-8")
    return path


def main(target: int = 50):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    existing = len(list(RAW_DIR.glob("*.txt")))
    if existing >= target:
        print(f"이미 {existing}개 파일 존재. 스킵.")
        return

    print(f"연합뉴스 기사 수집 시작 (목표: {target}개)\n")
    collected_urls = []
    for list_url in LIST_URLS:
        urls = get_article_urls(list_url, limit=15)
        for u in urls:
            if u not in collected_urls:
                collected_urls.append(u)

    print(f"URL 수집 완료: {len(collected_urls)}개\n")

    saved = 0
    for i, url in enumerate(collected_urls):
        if saved >= target:
            break
        article_id = f"{saved+1:03d}"
        print(f"[{saved+1}/{target}] {url}")
        data = fetch_article_text(url)
        if data:
            save_raw(article_id, data)
            saved += 1
            print(f"  ✅ 저장: data/raw/{article_id}.txt ({len(data['content'])}자)")
        else:
            print(f"  ⏭  스킵 (내용 없음)")
        time.sleep(0.3)  # 서버 부하 방지

    print(f"\n완료: {saved}개 저장 → data/raw/")


if __name__ == "__main__":
    main()
