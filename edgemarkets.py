import os
import sys
import json
import logging
from datetime import datetime as dt

import yagmail
from bs4 import BeautifulSoup, NavigableString

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC


def get_logger(log_level=logging.INFO):
    filename = os.path.split(__file__)[-1]
    log = logging.getLogger(filename)
    log_level = logging.INFO
    log.setLevel(log_level)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter('%(levelname)s: %(asctime)s - %(name)s:%(lineno)d - %(message)s')
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)
    return log

log = get_logger(__file__)


class EdgeMarkets(object):

    base_url = "https://www.theedgemarkets.com"
    endpoint = "/categories/malaysia"

    def __init__(self, settings):
        self.strtime = "%b %d, %Y %I:%M %p"

        self.settings = settings

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        log_path = '/dev/null' if sys.platform == "linux" else "NUL"
        self.chrome = webdriver.Chrome(self.settings["driver_path"]["value"], chrome_options=options, service_log_path=log_path)

        self.news = []

    def get_alerts(self):
        url = self.base_url + self.endpoint
        self.chrome.get(url)
        wait = self.settings["page_load_timeout"]["value"]
        WebDriverWait(self.chrome, wait).until(EC.presence_of_element_located((By.CLASS_NAME, "views-view-grid")))
        log.info(f"Loaded the web page - {url}")

        soup = BeautifulSoup(self.chrome.page_source, "html.parser")
        newss = soup.find("div", class_="views-view-grid").select("div.grid.col-lg-4.col-md-4.col-sm-4.col-xs-12")
        for news in newss:
            create_time = news.find("div", class_="views-field-created").text.strip()
            soup_title = news.find("div", class_="views-field-title").find("a")
            title, link = soup_title.text, soup_title.attrs["href"]

            ct = dt.strptime(f"{dt.now().year}, {create_time}", "%Y, %d %b | %I:%M%p").strftime(self.strtime)
            self.news.append({
                "url": self.base_url + link,
                "title": title,
                "create_time": ct
            })
        
        self.chrome.close()

    def filter_news(self):
        if not os.path.exists(os.path.join(os.getcwd(), "last_news.json")):
            with open("last_news.json", "w+") as f:
                json.dump(self.news[0], f, indent=2)

            return self.news

        with open("last_news.json") as f:
            last_news_time = dt.strptime(json.load(f)["create_time"], self.strtime)
            newss = list(filter(lambda x: dt.strptime(x["create_time"], self.strtime) > last_news_time, self.news))

            if newss:
                with open("last_news.json", "w+") as f:
                    json.dump(newss[0], f, indent=2)

            return newss

    def notify(self):
        self.get_alerts()
        newss = self.filter_news()

        log.info(f"Fetched recent news - ({len(newss)})")

        if newss:
            try:
                contents = [
                    "Hi", "\n"
                    "PFB for the news updates!", "\n\n",
                ]
                for news in newss:
                    contents.extend([
                        f"News: {news['title']}",
                        f"Time: {news['create_time']}",
                        f"Link: {news['url']}",
                        "\n"
                    ])
                contents.append("Thanks!")

                user, password, to = self.settings["smtp"]["mail"], self.settings["smtp"]["password"], self.settings["smtp"]["to"]
                yag = yagmail.SMTP(user=user, password=password)
                yag.send(
                    to=to, 
                    subject='Notification | The Edge Markets.', 
                    contents=contents
                )
                log.info(f"Email notification sent to {to}")
            except:
                log.error("Error on sending the email.. Please check the credentials provided in settings.json")
        else:
            log.info("No recent news. No email is triggered.")


def get_settings():
    with open("settings.json", "r") as f:
        return json.load(f)


def main():
    start = dt.now()
    log.info("Script starts at: {}".format(start.strftime("%d-%m-%Y %H:%M:%S %p")))

    settings = get_settings()
    EdgeMarkets(settings).notify()

    end = dt.now()
    log.info("Script ends at: {}".format(end.strftime("%d-%m-%Y %H:%M:%S %p")))
    elapsed = round(((end - start).seconds / 60), 4)
    log.info("Time Elapsed: {} minutes".format(elapsed))


if __name__ == "__main__":
    main()
