from HTMLParser import HTMLParser
from time import mktime
from twilio.rest import TwilioRestClient
import datetime
import httplib2
import json
import time

#--------- BEGIN CONFIG SETTINGS

# To find these visit https://www.twilio.com/user/account
ACCOUNT_SID = "ACXXXXXXXXXXXXXXXXX"
AUTH_TOKEN = "YYYYYYYYYYYYYYYYYY"
TWILIO_PHONE_NUMBER = "XXXXXX"

# Phone numbers to send SMS to
PHONE_NUMBERS = ('YOUR_PHONE_NUMBER_HERE',)

# Amount of time in seconds between checking the Diablo status page
SLEEP_AMOUNT = 60

# File name to store information about the last run
file_name = "last_run.json"

#--------- END CONFIG SETTINGS

twilio_client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)

http_timeout = 60
http = httplib2.Http(timeout=http_timeout)

diablo3_status_page = "http://us.battle.net/d3/en/status"


def get_last_run():
    data = None
    try:
        with open(file_name) as f:
            data = f.read()
            data = json.loads(data)

            # Convert from epoch seconds to datetime
            data['last_run'] = datetime.datetime.fromtimestamp(data['last_run'])
    except IOError:
        pass
    except ValueError:
        pass
    return data

def update_run_status(status):
    data = {"status": status, "last_run": mktime(datetime.datetime.utcnow().timetuple())}
    with open(file_name, "w") as f:
        f.write(json.dumps(data))


def get_diablo3_status():
    request, body = http.request(diablo3_status_page, method="GET")

    if request.status == 200:
        return body

def send_sms(phone_number, message):
    message = twilio_client.sms.messages.create(to=phone_number,
                                                from_=TWILIO_PHONE_NUMBER,
                                                body=message)


# create a subclass and override the handler methods
class Diablo3StatusPageHTMLParser(HTMLParser):
    found_column_one = False
    status = None

    def handle_starttag(self, tag, attrs):
        if self.status is None and tag == "div":
            for attr in attrs:
                if attr[0] == 'class':
                    if attr[1] == 'column column-1':
                        self.found_column_one = True
                        break
                    elif self.found_column_one and attr[1] == 'status-icon up':
                        self.status = 'UP'

                    elif self.found_column_one and attr[1] == 'status-icon down':
                        self.status = 'DOWN'



parser = Diablo3StatusPageHTMLParser()

if __name__ == "__main__":
    while True:
        # Get the status of the last run
        last_run = get_last_run()

        # Get the status page
        body = get_diablo3_status()

        if body:
            # If we got a status page parse the html
            parser.feed(body)
            parser.close()

            # If the parser successfully found a status
            if parser.status is not None:
                # Update the status
                update_run_status(parser.status)

                for number in PHONE_NUMBERS:

                    if parser.status == 'UP' and last_run['status'] == 'DOWN':
                        send_sms(number, "Diablo3 is UP!")
                    elif parser.status == 'DOWN' and last_run['status'] == 'UP':
                        send_sms(number, "Diablo3 is Down :(")

        time.sleep(SLEEP_AMOUNT)
