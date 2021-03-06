from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time
import progressbar
from covid19_nowcast.streaming.models.facebook import Post,Comment,Response
import re
def search(query, count, with_reactions=True):
    driver = webdriver.Firefox()
    driver.get(query) 
    posts=[]
    with open("covid19_nowcast/streaming/collection/expandall.js", "r") as file:
        code=file.read()

        scroll(driver,count)

        driver.execute_script(code)
        thing = WebDriverWait(driver, timeout=6000).until(lambda d: d.find_element(By.CSS_SELECTOR, "html > p"))
        print(thing.text)
        element = driver.find_element(By.CSS_SELECTOR, "._1pfm")
        driver.execute_script("var element = arguments[0];element.parentNode.removeChild(element);", element)
        time.sleep(1)
        posts = parse_posts(driver, count, with_reactions)

    driver.quit()
    return posts

def parse_posts(element, count, with_reactions, selector="._427x"):
    posts = element.find_elements(By.CSS_SELECTOR, selector)
    posts= posts[:min(len(posts), count)]
    parsed_posts=[]
    
    for post in posts:
        author=parse_author(post, ".fwb")
        created_at=parse_date(post,attribute="title", selector="._5ptz")
        full_text=parse_full_text(post, default="N/A", selector="div[data-testid='post_message']")
        comments_count=parse_comments_count(post)
        shares_count=parse_shares_count(post)
        comments_section = parse_comments_section(element, post, with_reactions)
        reactions=parse_post_reactions(element, post) if with_reactions else None
        parsed_posts.append(Post(author,created_at,full_text, comments_count, shares_count, reactions, comments_section))
    parsed_posts=[post.to_dict() for post in parsed_posts]
    return parsed_posts

def parse_post_reactions(driver, post, selector = "span[aria-label='Voir qui a réagi']"):
    post_reactions=post.find_elements(By.CSS_SELECTOR, selector)
    reactions = {}
    assert len(post_reactions) in [0,1]
    offset=-50
    for reaction in post_reactions:
        moods=reaction.find_elements(By.CSS_SELECTOR, "span")
        for mood in moods:
            done=False
            while not done:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);window.scrollBy(0, arguments[1]);", mood, -50+offset)
                    offset=-50-offset
                    assert(mood.is_displayed())
                    time.sleep(0.001)
                    ActionChains(driver).move_to_element(mood).perform()
                    def is_ready(driver):
                        people_js=mood.get_attribute("aria-describedby")
                        reaction_people=driver.find_element_by_id(people_js)
                        tokens=reaction_people.text.split("\n")
                        if tokens[0]=="":
                            return False
                        return tokens
                    tokens = WebDriverWait(driver, timeout=1).until(is_ready)

                    if len(tokens)>0:
                        found = re.search("[0-9]+",tokens[-1]) if re.search("^et [0-9]+ autres...$",tokens[-1]) is not None else None
                        reactions[tokens[0]]=len(tokens)-1 if found is None else len(tokens)-1+int(found.group())

                    done=True
                except:
                    print("Echec")
    return reactions

def parse_comments_count(element, selector = "a[class='_3hg- _42ft']"):
    count=0
    try: 
        count=int(re.search("^[0-9]+",element.find_element(By.CSS_SELECTOR, selector).text).group())
    except: 
        pass
    return count

def parse_shares_count(element, selector = "a[class='_3rwx _42ft']"):
    count=0
    try: 
        count=int(re.search("^[0-9]+",element.find_element(By.CSS_SELECTOR, selector).text).group())
    except: 
        pass
    return count

def parse_comments_section(driver, element, with_reactions, default=[], selector="._7a9a"):
    comments_section = element.find_elements(By.CSS_SELECTOR, selector)
    assert(len(comments_section) in [0,1])
    return parse_comment_threads(driver, comments_section[0], with_reactions) if len(comments_section)==1 else default

def parse_comment_threads(driver, element, with_reactions, selector="._7a9a > li"):
    comments = element.find_elements(By.CSS_SELECTOR, selector)

    return [parse_comment(
                    driver,
                    comment_thread,
                    [parse_response(driver, response, with_reactions) for response in parse_responses(comment_thread)],
                    with_reactions
                ) 
            for comment_thread in comments]

def parse_comment(driver, element, responses, with_reactions, selector="div[aria-label='Commenter']"):
    comment=element.find_element(By.CSS_SELECTOR,selector)

    parsed_comment=Comment(*parse_comment_infos(driver, comment, with_reactions), responses)
    return parsed_comment

def parse_comment_infos(driver,element,with_reactions):
    author = parse_author(element)
    full_text = parse_full_text(element, "N/A")
    created_at = parse_date(element)
    return author, created_at, full_text, parse_comment_reactions(driver,element) if with_reactions else None

def parse_comment_reactions(driver, post, selector = "a[aria-label='Voir qui a réagi']"):
    post_reactions=post.find_elements(By.CSS_SELECTOR, selector)
    reactions = {}
    assert len(post_reactions) in [0,1]

    for mood in post_reactions:
        tokens=None
        done=False
        while not done:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);window.scrollBy(0, -50);", mood)
                time.sleep(0.001)
                assert(mood.is_displayed())
                ActionChains(driver).move_to_element(mood).perform()
                def is_ready(driver):
                    people_js=mood.find_element_by_xpath('..').get_attribute("aria-describedby")

                    reaction_people=driver.find_element_by_id(people_js)
                    tokens=reaction_people.get_attribute("innerHTML")
                    if tokens=="<div></div>" or tokens=="<div><div>Chargement...</div></div>":
                        return False
                    return reaction_people
                reacts = WebDriverWait(driver, timeout=1).until(is_ready)
                reacts=reacts.find_elements(By.CSS_SELECTOR,"span")
                react_types=[rea for index, rea in enumerate(reacts) if index%2==0]
                react_counts=[int(rea.text) for index, rea in enumerate(reacts) if index%2==1]
                react_dict={"_3j7l _2p78 _9--":"J'aime",
                            "_3j7m _2p78 _9--":"J'adore",
                            "_3j7o _2p78 _9--":"Haha",
                            "_906t _2p78 _9--":"Solidaire",
                            "_3j7q _2p78 _9--":"Grrr",
                            "_3j7r _2p78 _9--":"Triste",
                            "_3j7n _2p78 _9--":"Wouah"}
                react_types=[react_dict.get(rea.find_element(By.CSS_SELECTOR,"i").get_attribute("class"),rea.find_element(By.CSS_SELECTOR,"i").get_attribute("class")) for rea in react_types]
                tokens={ty:react_counts[index] for index, ty in enumerate(react_types)}
                done=True
            except:
                print("Echec")

        reactions=tokens
    return reactions



def parse_author(element, selector="._6qw4"):
    return element.find_element(By.CSS_SELECTOR, selector).text

def parse_full_text(element, default=None, selector="._3l3x > span"):
    full_text=default
    try:
        full_text=element.find_element(By.CSS_SELECTOR, selector).text
    except:
        pass
    return full_text

def parse_date(element, selector = ".livetimestamp", attribute = "data-tooltip-content"):
    return element.find_element(By.CSS_SELECTOR, selector).get_attribute(attribute)

def parse_reactions(element, selector=None):
    return "N/A"

def parse_responses(element, selector="div[aria-label='Réponse au commentaire']"):
    return element.find_elements(By.CSS_SELECTOR, selector)

def parse_response(driver, element, with_reactions):
    return Response(*parse_comment_infos(driver, element, with_reactions))

def scroll(driver,count):
    SCROLL_PAUSE_TIME = 0.5
    posts=driver.find_elements(By.CSS_SELECTOR, "._4-u2 ._4-u8")

    with progressbar.ProgressBar(max_value=count, prefix="Posts: ") as bar:
        while len(posts)<count:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)
            WebDriverWait(driver, timeout=10).until(lambda d: d.find_element(By.CSS_SELECTOR, "._52jv :not(.async_saving)"))
            posts=driver.find_elements(By.CSS_SELECTOR, "._4-u2 ._4-u8")
            bar.update(min(len(posts),count))