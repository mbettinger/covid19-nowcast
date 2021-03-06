from workflow_manager.pipeline import Pipeline
from workflow_manager.step import Step
from workflow_manager.parameter_grid import parameter_grid as PG
import util
import streaming

pipeline=Pipeline(
    [
        Step(
            lambda cats: streaming.collection.articles.newyorktimes.NYT_Crawler(cats,False),
            params={"cats":None},
            outputs=["crawler"]
        ),
        Step(
            lambda crwlr, amount:list(crwlr.crawl(amount)),
            args=["crawler"],
            params={"amount":10},
            outputs=["articles"],
            keep_inputs=False
        ),
    ],
    name="crawling articles")