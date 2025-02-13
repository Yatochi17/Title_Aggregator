from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scrape_news():
    driver = None
    try:
        logger.info("Starting scrape_news function")

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        logger.info("Chrome options configured")

        if 'DYNO' in os.environ:
            logger.info("Running on Heroku")
            chrome_options.binary_location = '/app/.chrome-for-testing/chrome-linux64/chrome'
            chrome_service = Service('/app/.chrome-for-testing/chromedriver-linux64/chromedriver')
            driver = webdriver.Chrome(
                service=chrome_service,
                options=chrome_options
            )
        else:
            logger.info("Running locally")
            from webdriver_manager.chrome import ChromeDriverManager
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )

        url = "https://www.wired.com/most-recent/"
        logger.info(f"Attempting to access URL: {url}")

        driver.get(url)
        logger.info("Page loaded successfully")

        # Add initial wait for page load
        time.sleep(5)  # Give the page some time to load dynamic content

        # Scroll down a bit to trigger lazy loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/4);")
        time.sleep(2)

        articles = []
        wait = WebDriverWait(driver, 10)

        try:
            # Try multiple different selectors
            selectors = [
                "article.summary-item",
                "div[data-testid='SummaryItemContent']",
                "div.summary-list__items div[data-testid='SummaryItemContent']",
                ".summary-item"
            ]

            article_elements = []
            for selector in selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    article_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if article_elements:
                        logger.info(f"Found {len(article_elements)} elements with selector: {selector}")
                        break
                except TimeoutException:
                    continue

            if not article_elements:
                logger.error("No articles found with any selector")
                return []

            logger.info(f"Processing {len(article_elements)} articles")

            for index, article in enumerate(article_elements):
                try:
                    # Try different approaches to find the title and link
                    try:
                        title_element = article.find_element(By.CSS_SELECTOR, "h2, h3")
                        title = title_element.text.strip()

                        # Find the closest anchor tag
                        link_element = article.find_element(By.CSS_SELECTOR, "a")
                        link = link_element.get_attribute("href")
                    except:
                        # Alternative approach
                        link_element = article.find_element(By.CSS_SELECTOR, "a[href*='/story/']")
                        link = link_element.get_attribute("href")
                        title = link_element.text.strip()

                    if title and link:
                        article_data = {
                            "title": title,
                            "link": link
                        }

                        # Try to get the date
                        try:
                            date_element = article.find_element(By.CSS_SELECTOR, "time")
                            date = date_element.get_attribute("datetime")
                            if date:
                                article_data["date"] = date
                        except:
                            pass

                        articles.append(article_data)
                        logger.info(f"Added article {index + 1}: {title[:50]}...")
                except Exception as e:
                    logger.error(f"Error processing article {index}: {str(e)}")
                    continue

            logger.info(f"Successfully scraped {len(articles)} articles")
            return articles

        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            # Print page source for debugging
            logger.error(f"Page source: {driver.page_source[:1000]}...")
            return []

    except Exception as e:
        logger.error(f"Critical error in scrape_news: {str(e)}")
        return []

    finally:
        if driver:
            logger.info("Closing driver")
            driver.quit()


if __name__ == "__main__":
    news = scrape_news()
    print(f"\nTotal articles scraped: {len(news)}")
    if len(news) > 0:
        print("\nFirst few articles:")
        for i, article in enumerate(news[:3]):
            print(f"\n{i + 1}. Title: {article['title']}")
            print(f"   Link: {article['link']}")
            if 'date' in article:
                print(f"   Date: {article['date']}")