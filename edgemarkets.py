import os
import sys
import json
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


JSONF_LAST_UPDATE = "last_news_edgemarkets.json"


class EdgeMarkets(object):

    base_url = "https://www.theedgemarkets.com"
    endpoint = "/categories/malaysia"

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
        
        self.shutdown()

    def shutdown(self):
        process = psutil.Process(self.chrome.service.process.pid)
        for child_process in process.children(recursive=True):
            log.debug(f"Killing child process: ({child_process.pid}) - {child_process.name()} [{child_process.status()}]")
            child_process.kill()
        
        log.debug(f"Killing main process: ({process.pid}) - {process.name()} [{process.status()}]")
        process.kill()
        self.chrome.quit()

    def filter_news(self):
        if not os.path.exists(os.path.join(os.getcwd(), JSONF_LAST_UPDATE)):
            with open(JSONF_LAST_UPDATE, "w+") as f:
                json.dump(self.news[0], f, indent=2)

            return self.news

        with open(JSONF_LAST_UPDATE) as f:
            last_news_time = dt.strptime(json.load(f)["create_time"], self.strtime)
            newss = list(filter(lambda x: dt.strptime(x["create_time"], self.strtime) > last_news_time, self.news))

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
                        f"News: {news['title']}",
                        f"Link: {news['url']}",
                        "\n"
                    ])
                contents.append("Thanks!")

                user, password, to = self.settings["smtp"]["mail"], self.settings["smtp"]["password"], self.settings["smtp"]["to"].split(",")
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


def main():
    start = dt.now()
    log.info("\nScript starts at: {}".format(start.strftime("%d-%m-%Y %H:%M:%S %p")))

    settings = utils.get_settings()
    EdgeMarkets(settings).notify()

    end = dt.now()
    log.info("Script ends at: {}".format(end.strftime("%d-%m-%Y %H:%M:%S %p")))
    elapsed = round(((end - start).seconds / 60), 4)
    log.info("Time Elapsed: {} minutes".format(elapsed))


if __name__ == "__main__":
    main()
