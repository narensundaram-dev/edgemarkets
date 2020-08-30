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


import utils


log = utils.get_logger(os.path.split(__file__)[-1])


JSONF_LAST_UPDATE = "last_news_nst.json"


class NST(object):
    base_url = "https://www.nst.com.my"
    endpoint = "/business"

    def __init__(self, settings):
        self.strtime = "%b %d, %Y @ %I:%M%p"

        self.settings = settings

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        log_path = '/dev/null' if sys.platform == "linux" else "NUL"
        self.chrome = webdriver.Chrome(self.settings["driver_path"]["value"], chrome_options=options, service_log_path=log_path)

        self.news = []

    def get_news(self):
        url = self.base_url + self.endpoint
        self.chrome.get(url)
        wait = self.settings["page_load_timeout"]["value"]
        WebDriverWait(self.chrome, wait).until(EC.presence_of_element_located((By.CLASS_NAME, "container-fluid")))
        soup = BeautifulSoup(self.chrome.page_source, "html.parser")

        cards = soup.find_all("div", class_="article-teaser")
        for card in cards:
            if "native-loaded" not in card.attrs["class"]:
                create_time = card.find("span", class_="created-ago").text.strip()
                url = card.find("a").attrs["href"]
                title = card.find("h3", class_="field-title").text.strip()
                self.news.append({
                    "create_time": create_time,
                    "title": title,
                    "url": self.base_url + url,
                })
        self.chrome.quit()
        

    def filter_news(self):
        if not os.path.exists(os.path.join(os.getcwd(), JSONF_LAST_UPDATE)):
            with open(JSONF_LAST_UPDATE, "w+") as f:
                json.dump(self.news[0], f, indent=2)

            return self.news

        newss = []
        with open(JSONF_LAST_UPDATE) as f:
            last_news_url = json.load(f)["url"]
            for news in self.news:
                if news["url"] == last_news_url:
                    break
                newss.append(news)

            if newss:
                with open(JSONF_LAST_UPDATE, "w+") as f:
                    json.dump(newss[0], f, indent=2)

            return newss

    def notify(self):
        self.get_news()
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
                        f"Time: {news['create_time']}",
                        f"Category: {news['title']}",
                        f"Link: {news['url']}",
                        "\n"
                    ])
                contents.append("Thanks!")

                user, password, to = self.settings["smtp"]["mail"], self.settings["smtp"]["password"], self.settings["smtp"]["to"].split(",")
                yag = yagmail.SMTP(user=user, password=password)
                yag.send(
                    to=to, 
                    subject='Notification | NST.', 
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
    NST(settings).notify()

    end = dt.now()
    log.info("Script ends at: {}".format(end.strftime("%d-%m-%Y %H:%M:%S %p")))
    elapsed = round(((end - start).seconds / 60), 4)
    log.info("Time Elapsed: {} minutes".format(elapsed))


if __name__ == "__main__":
    main()
