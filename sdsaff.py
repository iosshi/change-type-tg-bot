#!/usr/bin/env python3
# coding: utf-8

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from bs4 import BeautifulSoup

BASE_URL = "https://kolesa.kz/cars/region-karagandinskaya-oblast/"
MIN_PRICE = 6000000
PAGES = 3

def init_driver():
    # Задаём стратегию загрузки — EAGER
    caps = DesiredCapabilities().CHROME.copy()
    caps["pageLoadStrategy"] = "eager"

    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    # Отключим загрузку изображений, чтоб точно не зависать на них:
    opts.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2
    })

    driver = webdriver.Chrome(desired_capabilities=caps, options=opts)
    # Бросать TimeoutException, если страница не загрузилась за 30 секунд
    driver.set_page_load_timeout(30)
    return driver

def fetch_listings(driver, min_price=MIN_PRICE, pages=PAGES):
    results = []
    for page in range(1, pages + 1):
        url = f"{BASE_URL}?price[from]={min_price}&page={page}"
        try:
            driver.get(url)
        except Exception as e:
            print(f"[WARN] страница {page} не успела загрузиться: {e}")
            # можно либо перейти к парсингу частичного page_source,
            # либо сразу перейти к следующей странице
        # Ждём, пока появятся объявления, но не дольше 15 сек
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-item-id]"))
            )
        except:
            print(f"[WARN] на странице {page} не нашёл article[data-item-id], структура могла измениться")
            continue

        soup = BeautifulSoup(driver.page_source, "html.parser")
        for art in soup.select("article[data-item-id]"):
            title_tag = art.select_one("h2.a-card__title")
            price_tag = art.select_one("div.a-card__price")
            link_tag  = art.select_one("a.a-card__link")

            title = title_tag.get_text(strip=True) if title_tag else ""
            price_str = price_tag.get_text(strip=True).split("₸")[0].replace(" ", "") if price_tag else "0"
            price = int(price_str) if price_str.isdigit() else 0
            href = link_tag["href"] if link_tag and link_tag.has_attr("href") else ""
            link = href if href.startswith("http") else "https://kolesa.kz" + href

            results.append({
                "id":    art["data-item-id"],
                "title": title,
                "price": price,
                "link":  link
            })
    return results

if __name__ == "__main__":
    driver = init_driver()
    try:
        cars = fetch_listings(driver)
        if not cars:
            print("Ни одного объявления не найдено.")
        for c in cars:
            print(f"{c['title']} — {c['price']:,} ₸ — {c['link']}")
    finally:
        driver.quit()
