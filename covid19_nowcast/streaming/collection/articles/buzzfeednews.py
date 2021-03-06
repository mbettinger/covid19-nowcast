from covid19_nowcast.streaming.collection.articles.crawler import Crawler
from bs4 import BeautifulSoup
import requests
import sys
import json
import progressbar

from datetime import datetime
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

class BFN_Crawler(Crawler):
    def __init__(self,categories_to_crawl=None, HI_category_nomenclature=False, parsed_urls=[]):
        if categories_to_crawl==None:
            categories_to_crawl=list(BFN_Crawler.site_categories_to_ours.keys())
        super().__init__(BFN_Crawler.root_url,categories_to_crawl,BFN_Crawler.site_categories_to_ours,HI_category_nomenclature)

    def articles_from_site(self, link, separate=False):
        if separate:
            return [self.articles_from_category(self.root_url+link, category) for category, link in progressbar.progressbar(BFN_Crawler.category_urls.items(), prefix=link)]
        else:
            for category, link in progressbar.progressbar([(cat, lnk) for cat,lnk in BFN_Crawler.category_urls.items() if cat in self.categories_to_crawl], prefix=link):
                yield from self.articles_from_category(self.root_url+link, category)

    def articles_from_category(self, link, category):
        response = requests.get(link)
        soup = BeautifulSoup(response.text, 'lxml')
        links = [a.get("href") for a in soup.find_all("a") if link != a.get("href") and self.root_url+"article/" in a.get("href")]
        links = list(set(links))
        for page_url in progressbar.progressbar(links, prefix=category):
            yield from self.parse_article(page_url, category)

    def parse_article(self, link, category):
        try:
            response = requests.get(link)
            soup = BeautifulSoup(response.text, 'lxml')
            details=soup.find("div",{"data-module":"article-wrapper"})
            text=[p.text for p in details.find_all("p")]
            author=soup.find("span",{"class":"news-byline-full__name xs-block link-initial--text-black"})
            if author is not None:
                author=author.text
            else:
                author="N/A"
            date=soup.find("p",{"class":"news-article-header__timestamps-posted"}).text
            yield {"author":author,"created_at":date,"full_text":"\n".join(text), "category":category}
        except:
            print(link)
            yield None

BFN_Crawler.root_url="https://www.buzzfeednews.com/"
BFN_Crawler.category_urls={
    "Arts & Entertainment":"section/arts-entertainment/",
    "Books":"section/books/",
    "Business":"section/business/",
    "LGBTQ":"section/lgbtq/",
    "Opinion":"collection/opinion/",
    "Politics":"section/politics/",
    "Reader":"section/reader/",
    "Science":"section/science/",
    "Tech":"section/tech/",
    "World":"section/world/",
}
BFN_Crawler.site_categories_to_ours={
    "Arts & Entertainment":"arts-entertainment/",
    "Books":"books/",
    "Business":"business/",
    "LGBTQ":"lgbtq/",
    "Opinion":"opinion/",
    "Politics":"politics/",
    "Reader":"reader/",
    "Science":"science/",
    "Tech":"tech/",
    "World":"world/",
}