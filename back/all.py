import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

BASE_URL = "https://epp.genproc.gov.ru"

# генерируем все URL-ы от 01 до 77
URLS = {
    f"{i:02}": f"https://epp.genproc.gov.ru/web/proc_{i:02}/mass-media/news/reg-news"
    for i in range(1, 78)
}


def parse_date(raw_date: str, raw_time: str | None = None) -> datetime:
    """Возвращает datetime-объект (для сортировки и RSS)."""
    raw_date = raw_date.strip()

    if raw_date.lower() == "сегодня":
        dt = datetime.today()
    elif raw_date.lower() == "вчера":
        dt = datetime.today() - timedelta(days=1)
    else:
        try:
            dt = datetime.strptime(raw_date, "%d.%m.%Y")
        except ValueError:
            dt = datetime.today()

    if raw_time:
        try:
            t = datetime.strptime(raw_time, "%H:%M").time()
            dt = datetime.combine(dt.date(), t)
        except ValueError:
            pass

    return dt


def format_rss_date(dt: datetime) -> str:
    """Конвертирует datetime в строку RSS (RFC-2822)."""
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0300")


def fetch_articles(region, url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    articles = []
    news_blocks = soup.select("div.feeds-list__list_body.feeds-list__list_body--carousel > div")
    if not news_blocks:
        print(f"Новости не найдены на {url}")
        return articles

    for block in news_blocks:
        link_tag = block.find("a")
        if not link_tag:
            continue

        title = link_tag.get_text(strip=True)
        link = link_tag["href"]
        if link.startswith("/"):
            link = BASE_URL + link

        date_tag = block.select_one("h4")
        time_tag = block.select_one("span > span:nth-child(1)")

        raw_date = date_tag.get_text(strip=True) if date_tag else ""
        raw_time = time_tag.get_text(strip=True) if time_tag else None

        dt = parse_date(raw_date, raw_time)

        articles.append({
            "title": title,
            "link": link,
            "pubDate": format_rss_date(dt),
            "dt": dt,  # для сортировки
            "region": region
        })

    return articles


def generate_rss(articles, filename="all.xml"):
    rss_items = ""
    for art in articles:
        rss_items += f"""
        <item>
            <title>[{art['region']}] {art['title']}</title>
            <link>{art['link']}</link>
            <pubDate>{art['pubDate']}</pubDate>
        </item>
        """

    rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <title>Новости прокуратуры РФ (агрегатор)</title>
        <link>{BASE_URL}</link>
        <description>Новости прокуратуры по всем регионам</description>
        {rss_items}
      </channel>
    </rss>
    """

    with open(filename, "w", encoding="utf-8") as f:
        f.write(rss_feed)


if __name__ == "__main__":
    all_articles = []

    for region, url in URLS.items():
        try:
            articles = fetch_articles(region, url)
            all_articles.extend(articles)
            print(f"[Регион {region}] собрано {len(articles)} новостей")
        except Exception as e:
            print(f"[Регион {region}] ошибка: {e}")

    # сортируем по дате (от новых к старым)
    all_articles.sort(key=lambda x: x["dt"], reverse=True)

    # создаём общий RSS
    generate_rss(all_articles, "all.xml")
    print(f"✅ Итоговый агрегатор сохранён в all.xml (всего {len(all_articles)} новостей)")
