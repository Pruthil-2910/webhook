import requests
from bs4 import BeautifulSoup
import time
import hashlib
import os

# --- CONFIGURATION ---
URL = "https://mgscience.ac.in/latest-news/"
STATE_FILE = "last_news_hash.txt"

_webhook_env = os.environ.get("DISCORD_WEBHOOK_URL")
DISCORD_WEBHOOK_URL = _webhook_env if _webhook_env else "https://discord.com/api/webhooks/1477580831126978661/oB1WxBkCVQt5RnSMQGaIhZvAmfbxr-YLwwFwMgY-rlT31Ro7BPsj-NueWWF3T7d9HpRQ"

def get_latest_news(url):
    """Robust scraping logic to extract news items (title, link, date)."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    news_container = soup.find('div', class_='elementor-loop-container elementor-grid')

    if not news_container:
        # Fallback if the main container is not found, try to find direct news elements
        news_elements = soup.find_all(['h3', 'h2'], class_='entry-title')
        if news_elements:
            return [{'title': el.get_text(strip=True), 'link': el.find('a')['href'] if el.find('a') else 'No Link', 'date': 'N/A (Scraped from direct elements)'} for el in news_elements]

        print("Could not find the main news container or direct news elements. Check the class names.")
        return []

    latest_news_items = []

    # Find all individual news items within the container
    news_articles = news_container.find_all('div', class_=lambda c: c and 'e-loop-item' in c.split() and 'elementor-6279' in c.split())

    for article in news_articles:
        title_element = article.find('div', class_='elementor-widget-theme-post-title')
        if title_element:
            link_tag = title_element.find('a', href=True)
            title = link_tag.get_text(strip=True) if link_tag else 'No Title Found'
            link = link_tag['href'] if link_tag else 'No Link Found'
        else:
            title = 'No Title Found'
            link = 'No Link Found'

        date_element = article.find('span', class_='elementor-post-info__item--type-date')
        if date_element:
            date_time_tag = date_element.find('time')
            date = date_time_tag.get_text(strip=True) if date_time_tag else 'No Date Found'
        else:
            date = 'No Date Found'

        latest_news_items.append({
            'title': title,
            'link': link,
            'date': date
        })

    return latest_news_items

def get_latest_news_hash():
    """Fetches the news page using robust scraping and returns a hash of the current news titles, plus the latest title."""
    news_items = get_latest_news(URL)

    if not news_items:
        return None, None

    # Combine all news item titles and links into one string to detect any change
    news_text_for_hash = "".join([f"{item['title']}{item['link']}" for item in news_items])

    if not news_text_for_hash:
        return None, None

    # Return the hash and the latest title from the list
    return hashlib.md5(news_text_for_hash.encode('utf-8')).hexdigest(), news_items[0]['title']

def notify(message):
    """Prints to console and sends to Discord if configured."""
    print(f"🔔 ALERT: {message}")
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🚀 **New MG Science Notification:** {message}\nCheck here: {URL}"})

def check_news():
    print(f"Checking for updates on {URL}...")

    current_hash, latest_title = get_latest_news_hash()

    if current_hash:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                old_hash = f.read().strip()

            if current_hash != old_hash:
                notify(f"New news detected: {latest_title}")
                with open(STATE_FILE, "w") as f:
                    f.write(current_hash)
            else:
                print(f"No new updates. Last checked: {time.ctime()}")
        else:
            # First run: create the file and notify of initial state
            print(f"Initial state captured: {latest_title}")
            with open(STATE_FILE, "w") as f:
                f.write(current_hash)
    else:
        print("Could not fetch current news hash.")

if __name__ == "__main__":
    check_news()
