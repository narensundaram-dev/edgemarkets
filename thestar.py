import os
import sys
import json
import logging
from datetime import datetime as dt

import psutil
import yagmail
from bs4 import BeautifulSoup, NavigableString

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC


import utils


log = utils.get_logger(os.path.split(__file__)[-1])


JSONF_LAST_UPDATE = "last_news_thestar.json"


class TheStar(object):

    base_url = "https://www.thestar.com.my"
    endpoint = "/news/latest?tag=Business"

    def __init__(self, settings):
        self.strtime = "%b %d, %Y %I:%M %p"

        self.settings = settings

        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        log_path = '/dev/null' if sys.platform == "linux" else "NUL"
        self.chrome = webdriver.Chrome(self.settings["driver_path"]["value"], chrome_options=options, service_log_path=log_path)

        self.news = []

    def get_news(self):
        url = self.base_url + self.endpoint
        self.chrome.get(url)
        wait = self.settings["page_load_timeout"]["value"]
        WebDriverWait(self.chrome, wait).until(EC.presence_of_element_located((By.ID, "2a")))

        soup = BeautifulSoup(self.chrome.page_source, "html.parser")
        tiles = soup.find_all("li", class_="row")
        for tile in tiles:
            soup_desc = tile.find(lambda tag: tag.name == 'a' and 'data-content-id' in tag.attrs)

            self.news.append({
                "id": soup_desc.attrs["data-content-id"],
                "url": soup_desc.attrs["href"],
                "create_time": tile.find("time", class_="timestamp").text,
                "title": tile.find("a", class_="kicker").text,
                "description": soup_desc.text.strip()
            })
        self.shutdown()

    def shutdown(self):
        process = psutil.Process(self.chrome.service.process.pid)
        for child_process in process.children(recursive=True):
            log.debug(f"Killing child process: ({child_process.pid}) - {child_process.name()} [{child_process.status()}]")
            
            try:
                child_process.kill()
            except psutil.NoSuchProcess as _:
                log.debug("Already a dead process.")
        
        log.debug(f"Killing main process: ({process.pid}) - {process.name()} [{process.status()}]")
        process.kill()
        self.chrome.quit()

    def filter_news(self):
        if not os.path.exists(os.path.join(os.getcwd(), JSONF_LAST_UPDATE)):
            with open(JSONF_LAST_UPDATE, "w+") as f:
                json.dump(self.news[0], f, indent=2)

            return self.news

        newss = []
        with open(JSONF_LAST_UPDATE) as f:
            last_news_id = json.load(f)["id"]
            for news in self.news:
                if news["id"] == last_news_id:
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
                        f"News: {news['description']}",
                        f"Link: {news['url']}",
                        "\n"
                    ])
                contents.append("Thanks!")

                user, password, to = self.settings["smtp"]["mail"], self.settings["smtp"]["password"], self.settings["smtp"]["to"].split(",")
                yag = yagmail.SMTP(user=user, password=password)
                yag.send(
                    to=to, 
                    subject='Notification | The Star.', 
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
    print("")
    log.info("Script starts at: {}".format(start.strftime("%d-%m-%Y %H:%M:%S %p")))

    settings = get_settings()
    TheStar(settings).notify()

    end = dt.now()
    log.info("Script ends at: {}".format(end.strftime("%d-%m-%Y %H:%M:%S %p")))
    elapsed = round(((end - start).seconds / 60), 4)
    log.info("Time Elapsed: {} minutes".format(elapsed))


if __name__ == "__main__":
    main()
