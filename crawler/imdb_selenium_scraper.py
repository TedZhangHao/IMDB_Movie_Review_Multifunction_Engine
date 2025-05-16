import re
import requests
from bs4 import BeautifulSoup
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

DESKTOP_HEADERS = {
'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
'AppleWebKit/537.36 (KHTML, like Gecko) '
'Chrome/115.0.0.0 Safari/537.36'),
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
'Accept-Language': 'en-US,en;q=0.5',
'Connection': 'keep-alive'
}

def selenium_get_full_page(url, button_selector="span.ipc-see-more__text", wait_time=2, max_clicks=1, wait_selector='a[href^="/title/"]'):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument(f"user-agent={DESKTOP_HEADERS['User-Agent']}")

    service = Service("C:/Users/suke1/Desktop/IR/601.466.hw4/HW4/chromedriver-win64/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
        )
    except Exception as e:
        print(f"page load failed: {e}")
        driver.quit()
        return ""

    for i in range(max_clicks):
        try:
            print(f"wait for {i + 1} button...")
            button = WebDriverWait(driver, wait_time).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
            )
            print(f"click {i + 1} button")
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", button)
            time.sleep(wait_time + 1)
        except Exception as e:
            print(f"⚠️ 点击失败：{e}")
            break

    html = driver.page_source
    driver.quit()
    return html

def parse_movies_from_soup(html):
    soup = BeautifulSoup(html, "html.parser")
    all_movies = []
    movie_links = soup.find_all("a",class_="ipc-title-link-wrapper",href=re.compile(r'^/title/'))
    print(f"find {len(movie_links)} title links")
    for link in movie_links:
        try:
            title_tag = link.find("h3", class_="ipc-title__text")
            title = title_tag.get_text(strip=True)
            href = link.get("href", "").split("?")[0]
            movie_id = href.split("/")[2]
            movie_url = "https://www.imdb.com" + href
            all_movies.append({
                "title": title,
                "movie_id": movie_id,
                "movie_url": movie_url
                })
        except Exception as e:
            print(f"skip films，Reason: {e}")
    return all_movies

def fetch_reviews_selenium(movie_id,max_clicks=1, max_reviews=100):
    url = f"https://www.imdb.com/title/{movie_id}/reviews?sort=num_votes,desc"
    html = selenium_get_full_page(url, button_selector="span.ipc-see-more__text", max_clicks=max_clicks, wait_selector='review-container')
    soup = BeautifulSoup(html, "html.parser")
    reviews = []
    review_links = soup.find_all(href=re.compile(r'^/review/'))
    # de-duplication
    seen = set()
    unique_links = []
    for link in review_links:
        href = link.get("href")
        if href and href not in seen:
            seen.add(href)
            unique_links.append(link)

    if len(unique_links) < 20:
        print(f"skip {movie_id}，because reviews {len(unique_links)} < 20")
        return [], len(unique_links)

    for link in unique_links[:max_reviews]:
        full_review_url = "https://www.imdb.com" + link["href"]
        time.sleep(2)
        try:
            r = requests.get(full_review_url, headers=DESKTOP_HEADERS, timeout=10)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Full Review Page Crawl Failed: {e}")
            continue

        full_soup = BeautifulSoup(r.text, "html.parser")

        name_div = full_soup.find(class_="parent")
        review_div = full_soup.find(class_="review-container")
        if not review_div:
            print("Not find review-container，skip...")
            continue

        user_tag= name_div.find("a", href=re.compile(r"^/user/"))
        user_name = user_tag.get_text(strip=True)

        title_tag = review_div.find(class_="title")
        review_title = title_tag.get_text(strip=True) if title_tag else ""

        content_tag = review_div.find(class_="text.show-more__control")
        if not content_tag:
            content_tag = review_div.find(class_="text")
        review_content = content_tag.get_text(strip=True) if content_tag else ""

        rating_value = ""
        rating_tag = review_div.find("span", class_="rating-other-user-rating")
        if rating_tag:
            sub_spans = rating_tag.find_all("span")
            if len(sub_spans) >= 1:
                rating_value = sub_spans[0].get_text(strip=True)

        reviews.append({
            "user": user_name,
            "title": review_title,
            "content": review_content,
            "review_url": full_review_url,
            "rating": rating_value
        })

    return reviews, len(unique_links)

def fetch_movie_details(movie_url):
    try:
        response = requests.get(movie_url, headers=DESKTOP_HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')


        runtime_tag = soup.find('meta', property="og:description")
        runtime = runtime_tag.get("content", "N/A") if runtime_tag else "N/A"

        directors = [tag.get_text(strip=True) for tag in soup.find_all('a', href=re.compile(r'tt_ov_dr'))[:1]]
        stars = [tag.get_text(strip=True) for tag in soup.find_all('a', href=re.compile(r'tt_ov_st'))[1:4]]

        return {"runtime": runtime, "directors": directors, "stars": stars}
    except Exception as e:
        print(f"Failed to get details: {e}")
        return {"runtime": "N/A", "directors": [], "stars": []}


def deduplicate_reviews(reviews):
    seen_urls = set()
    deduped = []
    for r in reviews:
        if r["review_url"] not in seen_urls:
            deduped.append(r)
            seen_urls.add(r["review_url"])
    return deduped

if __name__ == '__main__':
    # Step 1: Get full HTML (click multiple times to load more)
    url = "https://www.imdb.com/search/title/?release_date=2025-01-01,2025-05-12&genres=action&title_type=feature"
    html = selenium_get_full_page(url, max_clicks=9)


    # Step 2: Parsing out the movie list
    movies = parse_movies_from_soup(html)

    results = []
    for movie in movies:
        print(f"process film: {movie['title']} (ID: {movie['movie_id']})")
        details = fetch_movie_details(movie['movie_url'])
        reviews_data, review_count = fetch_reviews_selenium(movie['movie_id'], max_reviews=20)
        if review_count < 15:
            print(f"skip film {movie['title']}，lack of reviews:{review_count}")
            continue
        reviews_data = deduplicate_reviews(reviews_data)
        movie.update(details)
        movie['reviews'] = reviews_data
        results.append(movie)
        time.sleep(3)

    with open("imdb_action_movies_full.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("✅ Data capture complete")

