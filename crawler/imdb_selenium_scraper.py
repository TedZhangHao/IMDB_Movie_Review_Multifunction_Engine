import re
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime 
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from timer import Stagetimer
from collections import defaultdict
from requests_html import HTMLSession

DESKTOP_HEADERS = {
'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
'AppleWebKit/537.36 (KHTML, like Gecko) '
'Chrome/115.0.0.0 Safari/537.36'),
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
'Accept-Language': 'en-US,en;q=0.5',
'Connection': 'keep-alive'
}

def selenium_get_full_page(url, if_all=True, wait_selector='a[href^="/title/"]', button_selector="span.ipc-see-more__text", max_clicks=1, multibutton = False, two_stage=False, wait_time=2):
    '''
    Using Webdriver to load the full page by clicking the "See More" button
    '''
    # Chrome start options
    options = Options()
    # options.add_argument("--headless=new") # no interface
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-features=VizDisplayCompositor") # avoid rendering errors
    options.add_argument(f"user-agent={DESKTOP_HEADERS['User-Agent']}") # camouflage as normal desktop browser

    service = Service("D:/graduate_first/NLP_movie/chromedriver-win64/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)

    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
        )
    except Exception as e:
        print(f"page load failed: {e}")
        driver.quit()
        return ""
    
    if if_all:
        try:
            button = WebDriverWait(driver, wait_time).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", button) # scroll to the button (second one for 'all')
            time.sleep(1)
            driver.execute_script("arguments[0].click();", button) 
            if "see-more" in button_selector:
                print("click All")
                time.sleep(wait_time + 30) # to load all
            if multibutton:    
                if not two_stage:
                    print("click Spoiler and Load more")
                    load_more_buttons = driver.find_elements(By.CSS_SELECTOR,"button.ipc-overflowText-overlay")
                    spoiler_buttons = driver.find_elements(By.CSS_SELECTOR,"button.review-spoiler-button")
                    print("click Load more")
                    for btn in load_more_buttons:
                        driver.execute_script("arguments[0].click();", btn) 
                        # time.sleep(0.1)
                    print("click Spoiler")
                    for btn in spoiler_buttons:
                        driver.execute_script("arguments[0].click();", btn) 
                        # time.sleep(0.1)
                    time.sleep(wait_time + 30) # to load all
                else:
                    print("click Spoiler")
                    time.sleep(wait_time + 1) # to load all
        except Exception as e:
            print(f"⚠️ 点击失败：{e}")
            
    else:
        for i in range(max_clicks):
            try:
                print(f"wait for {i + 1} button...")
                button = WebDriverWait(driver, wait_time).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
                )
                print(f"click {i + 1} button")
                driver.execute_script("arguments[0].scrollIntoView(true);", button) # scroll to the button
                time.sleep(1)
                driver.execute_script("arguments[0].click();", button) # using Javascript to click
                time.sleep(wait_time + 1)
            except Exception as e:
                print(f"⚠️ 点击失败：{e}")
                break

    html = driver.page_source # get the full page 
    driver.quit()
    return html

def parse_movies_from_soup(html):
    '''
    Parse movie titles, IDs, and movie urls from the HTML
    '''
    soup = BeautifulSoup(html, "html.parser")
    all_movies = []
    movie_links = soup.find_all("a",class_="ipc-title-link-wrapper",href=re.compile(r'^/title/')) # get all movie links
    print(f"find {len(movie_links)} title links")
    for link in movie_links:
        try:
            title_tag = link.find("h3", class_="ipc-title__text")
            title = re.sub( r"^/d+\.\s*","",title_tag.get_text(strip=True))
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

def fetch_movie_details(movie_url):
    """
    Scrape neccessary movie details from the HTML:
    runtime, directors, and stars, buget, opening weekend gross, opening weekend date, opening weekend gross North America, release date
    """
    try:
        response = requests.get(movie_url, headers=DESKTOP_HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        meta_score = soup.find("span",class_="metacritic-score-box").get_text(strip=True)
        meta_rate = soup.find("div",{"data-testid": "hero-rating-bar__aggregate-rating__score"}).find("span",class_="imUuxf").get_text(strip=True)
        runtime_tag = soup.find('meta', property="og:description")
        runtime = runtime_tag.get("content", "N/A") if runtime_tag else "N/A"
        detailed_section = soup.find('section', {"data-testid":"Details"})
        details_div = detailed_section.find("div", {"data-testid": "title-details-section"}).find("div", class_="ipc-metadata-list-item__content-container")
        release_date = details_div.find("a",class_="ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link").get_text(strip=True)
        box_office_section = soup.find('section', {"data-testid":"BoxOffice"})
        boxoffice_div = box_office_section.find("div", {"data-testid": "title-boxoffice-section"})
        budget = boxoffice_div.find("li",{"data-testid": "title-boxoffice-budget"}).find("span", class_ ="ipc-metadata-list-item__list-content-item ipc-btn--not-interactable").get_text(strip=True)
        Gross_NorthAmerica = boxoffice_div.find("li",{"data-testid": "title-boxoffice-grossdomestic"}).find("span", class_ ="ipc-metadata-list-item__list-content-item ipc-btn--not-interactable").get_text(strip=True)
        Opening_weekend_NorthAmerica = boxoffice_div.find("li",{"data-testid": "title-boxoffice-openingweekenddomestic"})
        Opening_weekend_span = Opening_weekend_NorthAmerica.select("span.ipc-metadata-list-item__list-content-item.ipc-btn--not-interactable")
        budget = re.sub(r"[^\d]","", budget) if budget else "N/A"
        Gross_NorthAmerica = re.sub(r"[^\d]","", Gross_NorthAmerica) if Gross_NorthAmerica else "N/A"
        Opening_weekend_gross_NorthAmerica = re.sub(r"[^\d]","", Opening_weekend_span[0].get_text(strip=True)) if Opening_weekend_span[0].get_text(strip=True) else "N/A"
        Opening_weekend_date_NorthAmerica = Opening_weekend_span[1].get_text(strip=True) if Opening_weekend_span[1].get_text(strip=True) else "N/A"
        # poster_tag = soup.find('meta', property="og:image")
        poster_url =  "https://www.imdb.com" + soup.find_all("a", href=re.compile(r'tt_ov_i'))[0].get("href", "").split("?")[0]
        description = soup.find('p',{"data-testid":"plot"}).find("span",{"data-testid":"plot-xs_to_m"}).get_text(strip=True)
        # storyline = soup.find("section",{"data-testid":"Storyline"}).find("div",class_="ipc-html-content-inner-div").get_text(strip=True)
        directors = [tag.get_text(strip=True) for tag in soup.find_all('a', href=re.compile(r'tt_ov_dr'))[:1]]
        stars = [tag.get_text(strip=True) for tag in soup.find_all('a', href=re.compile(r'tt_ov_st'))[1:4]]

        return {"meta_score":meta_score,
                "meta_rate":meta_rate,
                "runtime": runtime,
                "directors": directors, 
                "stars": stars , 
                "estimated budget": budget, 
                "Gross North America": Gross_NorthAmerica,
                "Opening weekend North America": Opening_weekend_gross_NorthAmerica,
                "Opening weekend date North America": Opening_weekend_date_NorthAmerica,
                "release date": release_date,
                "description": description,
                "poster_url":poster_url,
                # "storyline": storyline
                }
    except Exception as e:
        print(f"Failed to get details: {e}")
        return {"meta_score":"N/A","meta_rate":'N/A',"runtime": "N/A", "directors": [], "stars": [], "estimated budget": "N/A",
                "Gross North America": "N/A", "Opening weekend North America": "N/A",
                "Opening weekend date North America": "N/A", "release date": "N/A","description": "N/A",# "poster":"N/A","storyline": "N/A"
                "poster_url":poster_url}

def fetch_reviews_selenium(movie_id, max_clicks=1, max_reviews=-1):
    """
    Scrape movie reviews from each Movie, using Webdriver to load all reviews
    """
    url = f"https://www.imdb.com/title/{movie_id}/reviews?sort=num_votes,desc"
    one_rendering = True
    
    if one_rendering:
        html = selenium_get_full_page(url, if_all=True, wait_selector="[data-testid='tturv-pagination']", button_selector="span.chained-see-more-button > button.ipc-see-more__button", max_clicks=max_clicks, multibutton=True, two_stage=False)
        soup = BeautifulSoup(html, "html.parser")
        reviews_date = defaultdict(list)
        all_review_frame = soup.find_all('div', {"data-testid":"review-card-parent"})
        temp_record = {'username':soup.find_all('a',{"data-testid":'author-link'}), # username
                       'review_title':soup.find_all(href=re.compile(r'/review/'), class_='ipc-title-link-wrapper'), # review_title
                       'review_content':soup.find_all('div',class_='ipc-html-content-inner-div'), # review_content
                       'date':soup.find_all('li', class_='ipc-inline-list__item review-date'), # date
                       'helpful number':soup.find_all('span', class_='ipc-voting__label__count--up'), # helpful number
                       'nohelpful number':soup.find_all('span', class_='ipc-voting__label__count--down')}
        for counts in range(len(all_review_frame)):
            rating_tag = all_review_frame[counts].find("span", class_="ipc-rating-star--rating")
            if not rating_tag:
                continue
            rating_value = rating_tag.get_text(strip=True) if rating_tag else ""
            user_name = temp_record['username'][counts].get_text(strip=True)
            review_title = temp_record['review_title'][counts].get_text(strip=True)
            review_content = temp_record['review_content'][counts].get_text(strip=True)
            full_review_url = "https://www.imdb.com" + temp_record['review_title'][counts]["href"]

            date = temp_record['date'][counts].get_text(strip=True)
            date = str(datetime.strptime(date, '%b %d, %Y')).split(' ')[0]
            reviews_date[date].append({
                "user": user_name,
                "title": review_title,
                "review_url": full_review_url,
                "rating": rating_value,
                "helpful": temp_record['helpful number'][counts].get_text(strip=True),
                "nohelpful": temp_record['nohelpful number'][counts].get_text(strip=True),
                "content": review_content
            })
        review_date_sort = dict(sorted(reviews_date.items()))
        print(counts)
        return review_date_sort, len(all_review_frame)
    else:  
        html = selenium_get_full_page(url, if_all=True, wait_selector="[data-testid='tturv-pagination']", button_selector="span.chained-see-more-button > button.ipc-see-more__button", max_clicks=max_clicks, multibutton=False)
        soup = BeautifulSoup(html, "html.parser")
        temp_record = [soup.find_all('span', class_='ipc-voting__label__count--up'),soup.find_all('span', class_='ipc-voting__label__count--down')]
        reviews = []
        review_links = soup.find_all(href=re.compile(r'/review/'), class_='ipc-title-link-wrapper')
        review_len = len(review_links)
        # de-duplication
        seen = set()
        unique_links = []
        for link in review_links:
            href = link.get("href")
            if href and href not in seen:
                seen.add(href)
                unique_links.append(link)
        # restriction 
        if len(unique_links) < 20:  # undetermined
            print(f"skip {movie_id}，because reviews {len(unique_links)} < 20")
            return [], len(unique_links)
        counts = -1
        for link in unique_links[:max_reviews]:
            counts+=1
            full_review_url = "https://www.imdb.com" + link["href"]
            time.sleep(2)
            try:
                r = requests.get(full_review_url, headers=DESKTOP_HEADERS, timeout=10)
                r.raise_for_status()
                time.sleep(2)
            except requests.exceptions.RequestException as e:
                print(f"Full Review Page Crawl Failed: {e}")
                continue

            full_soup = BeautifulSoup(r.text, "html.parser")
            # if full_soup.find(class)
            
            user_tag = full_soup.find("a", href=re.compile(r"/user/"))
            review_section = full_soup.find("section", class_='ipc-page-section--sp-pageMargin')
            if review_section.find("button",class_="review-spoiler-button"):
                review_html = selenium_get_full_page(full_review_url, if_all=True, wait_selector="[data-testid='review-card-parent']", button_selector="button.review-spoiler-button", max_clicks=1, multibutton=True, two_stage=True)
                full_soup = BeautifulSoup(review_html, "html.parser")
                review_section = full_soup.find("section", class_='ipc-page-section--sp-pageMargin')
                print(f'{counts+1}/{review_len}')
            if not review_section:
                print("Not find review-container，skip...")
                continue
            
            user_name = user_tag.get_text(strip=True)

            title_tag = review_section.find(class_="ipc-title__text")
            review_title = title_tag.get_text(strip=True) if title_tag else ""

            content_tag = review_section.find(class_="ipc-html-content-inner-div")
            review_content = content_tag.get_text(strip=True) if content_tag else ""

            rating_tag = review_section.find("span", class_="ipc-rating-star--rating")
            if not rating_tag:
                continue
            rating_value = rating_tag.get_text(strip=True) if rating_tag else ""
            date = review_section.find("li", class_="review-date").get_text(strip=True)

            reviews.append({
                "user": user_name,
                "title": review_title,
                "content": review_content,
                "review_url": full_review_url,
                "rating": rating_value,
                "date": date,
                "helpful": temp_record[0][counts].get_text(strip=True),
                "nohelpful": temp_record[1][counts].get_text(strip=True)
            })
        return reviews, len(unique_links)

def deduplicate_reviews(reviews):
    seen_urls = set()
    deduped = []
    for r in reviews:
        if r["review_url"] not in seen_urls:
            deduped.append(r)
            seen_urls.add(r["review_url"])
    return deduped

if __name__ == '__main__':
    timer = Stagetimer()
    # Step 1: Get full HTML (click multiple times to load more)
    url_IMDb = "https://www.imdb.com/search/title/?release_date=2025-01-01,2025-05-12&genres=action&title_type=feature"
    html = selenium_get_full_page(url_IMDb, if_all=False, wait_selector='a[href^="/title/"]',max_clicks=1, multibutton=False)
    timer.mark("Get full movie HTML")
    # Step 2: Parsing out the movie list from IMDb
    movies = parse_movies_from_soup(html)
    timer.mark("Parse movie list")
    
    results = []
    num = 0
    for movie in movies:
        print(f"process film: {movie['title']} (ID: {movie['movie_id']})")
        details = fetch_movie_details(movie['movie_url'])
        reviews_data, review_count = fetch_reviews_selenium(movie['movie_id'])
        if review_count < 15:
            print(f"skip film {movie['title']}，lack of reviews:{review_count}")
            continue
        # reviews_data = deduplicate_reviews(reviews_data)
        movie.update(details)
        movie['reviews'] = reviews_data
        results.append(movie)
        time.sleep(3)
        timer.mark(f"Fetch details for {movie['title']}")
        num+=1
        if num == 3:
            break
    timer.report()
    
    with open("./IMDB_Movie_Review_Multifunction_Engine/crawler/imdb_action_movies_full_all_review.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("✅ Data capture complete")

