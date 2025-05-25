import re
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime 
import json
from timer import Stagetimer

DESKTOP_HEADERS = {
'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
'AppleWebKit/537.36 (KHTML, like Gecko) '
'Chrome/115.0.0.0 Safari/537.36'),
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
'Accept-Language': 'en-US,en;q=0.5',
'Connection': 'keep-alive'
}
    

def parse_from_soup_boxoffice_mojo(web_url):
    '''
    Parse movie titles and movie urls from the HTML in the boxoffice mojo website
    '''
    try:
        response = requests.get(web_url, headers=DESKTOP_HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        movie_links = soup.find_all("a",class_="a-link-normal",href=re.compile(r'^/release/')) # get all movie links
        print(f"find {len(movie_links)} title links")
        movie_urls_dict = {}
        for link in movie_links:
            title = link.get_text(strip=True)
            href = link.get("href","")
            movie_url = "https://www.boxofficemojo.com" + href
            movie_urls_dict[title] = movie_url
        return movie_urls_dict
    except Exception as e:
        print(f"Failed to get details: {e}")

def fetch_movie_boxoffice_timeseries(movie_url):
    """
    fetch the movie boxoffice timeseries
    """
    try:
        response = requests.get(movie_url, headers=DESKTOP_HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        trs = soup.find_all("tr")[1:]
        
        first_day = trs[0].find("td", class_="a-text-left mojo-header-column mojo-truncate mojo-field-type-date_interval mojo-sort-column").get_text(strip=True)
        last_day = trs[-1].find("td", class_="a-text-left mojo-header-column mojo-truncate mojo-field-type-date_interval mojo-sort-column").get_text(strip=True)
        revenue_all, theaters_all, accumulated_revenue_all = [],[],[]
        for tr in trs:
            daily_revenue = tr.find("td", class_="a-text-right mojo-field-type-money mojo-estimatable").get_text(strip=True)
            theaters = tr.find("td", class_="a-text-right mojo-field-type-positive_integer mojo-estimatable").get_text(strip=True)
            accumulated_revenue = tr.find("td", class_="a-text-right mojo-field-type-money mojo-estimatable").get_text(strip=True)
            revenue_all.append(re.sub(r"[^\d]","",daily_revenue))
            theaters_all.append(re.sub(r"[^\d]","",theaters))
            accumulated_revenue_all.append(re.sub(r"[^\d]","",accumulated_revenue))
        return {'first_day':first_day, 'last_day':last_day, 'revenue': revenue_all, 'theaters':theaters_all, 'accumulated_revenue':accumulated_revenue_all}
    except Exception as e:
        print(f"Failed to get box office timeseries: {e}")
    
            
if __name__ == "__main__":
    timer = Stagetimer()
    # Parsing out the movie list from Boxoffice Mojo
    url_boxoffice_mojo = "https://www.boxofficemojo.com/quarter/q2/2025/?ref_=bo_ql_table_1"
    movie_urls_dict = parse_from_soup_boxoffice_mojo(url_boxoffice_mojo)

    results = {}
    for movie in movie_urls_dict:
        print(f"process film: {movie}")
        boxoffice_data = fetch_movie_boxoffice_timeseries(movie_urls_dict[movie])
        results[movie] = boxoffice_data
        timer.mark(f"Fetch details for {movie}")
    timer.report()
    
    with open("./IMDB_Movie_Review_Multifunction_Engine/crawler/mojo_2025_boxoffice.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("✅ Data capture complete")