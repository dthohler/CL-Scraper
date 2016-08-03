##on the command line, make sure that the requirements are installed with "pip install -r requirements.txt"

##run from command line with "python main_loop.py" make you are in the correct directory

## taken from here --  https://github.com/vikparuchuri/apartment-finder

from craigslist import CraigslistForSale
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import sessionmaker
from dateutil.parser import parse
from util import post_listing_to_slack
from slackclient import SlackClient
import time
import settings

engine = create_engine('sqlite:///listings.db', echo=False)

Base = declarative_base()

class Listing(Base):
    """
    A table to store data on craigslist listings.
    """

    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True)
    link = Column(String, unique=True)
    created = Column(DateTime)
##    geotag = Column(String)
##    lat = Column(Float)
##    lon = Column(Float)
    name = Column(String)
    price = Column(Float)
##    location = Column(String)
    cl_id = Column(Integer, unique=True)
##    area = Column(String)
##    bart_stop = Column(String)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

##need to be able to get the scraper to search the query box, rather than the
##make and model box. then set a loop to search multiple queries
##
##make/model---   https://sfbay.craigslist.org/search/mcy?auto_make_model=triumph
##query box---    https://sfbay.craigslist.org/search/mcy?query=triumph

##{'query': {'url_key': 'query', 'value': 'honda cb'}}

##try to sort by price?


def scrape_area(area):
    """
    Scrapes craigslist for a certain geographic area, and finds the latest listings.
    :param area:
    :return: A list of results.
    """
    cl_fs = CraigslistForSale(site=settings.CRAIGSLIST_SITE, area=area, category=settings.CRAIGSLIST_FORSALE_SECTION,
                          filters = {'make': 'triumph'})

    results = []
    gen = cl_fs.get_results(sort_by='newest', limit=150)
    while True:
        try:
            result = next(gen)
        except StopIteration:
            break
        except Exception:
            continue
        listing = session.query(Listing).filter_by(cl_id=result["id"]).first()

        # Don't store the listing if it already exists.
        if listing is None:
            
            # Try parsing the price.
            price = 0
            try:
                price = float(result["price"].replace("$", ""))
            except Exception:
                pass

            # Create the listing object.
            listing = Listing(
                link=result["url"],
                created=parse(result["datetime"]),
##                lat=lat,
##                lon=lon,
                name=result["name"],
                price=price,
##                location=result["where"],
                cl_id=result["id"],
##                area=result["area"],
##                bart_stop=result["bart"]
            )

            # Save the listing so we don't grab it again.
            session.add(listing)
            session.commit()

            if len(result["name"]) > 0:
                results.append(result)

    return results

def do_scrape():
    """
    Runs the craigslist scraper, and posts data to slack.
    """

    # Create a slack client.
    sc = SlackClient(settings.SLACK_TOKEN)

    # Get all the results from craigslist.
    all_results = []
    for area in settings.AREAS:
        all_results += scrape_area(area)

    print("{}: Got {} results".format(time.ctime(), len(all_results)))

    # Post each result to slack.
    for result in all_results:
        post_listing_to_slack(sc, result)
