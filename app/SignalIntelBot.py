import feedparser
import os
import requests
import time
import logging

from configparser import ConfigParser, NoOptionError
from signal import signal

# Configure logger
logging.basicConfig(format='%(asctime)s %(message)s',  level=logging.INFO)

# expects the configuration file in the same directory as this script by default, replace if desired otherwise
configuration_file_path = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'Config.txt')

rss_feed_list = [
    ['https://grahamcluley.com/feed/', 'Graham Cluley'],
    ['https://threatpost.com/feed/', 'Threatpost'],
    ['https://krebsonsecurity.com/feed/', 'Krebs on Security'],
    ['https://www.darkreading.com/rss.xml', 'Dark Reading'],
    ['http://feeds.feedburner.com/eset/blog', 'We Live Security'],
    ['https://davinciforensics.co.za/cybersecurity/feed/', 'DaVinci Forensics'],
    ['https://blogs.cisco.com/security/feed', 'Cisco'],
    ['https://www.infosecurity-magazine.com/rss/news/', 'Information Security Magazine'],
    ['http://feeds.feedburner.com/GoogleOnlineSecurityBlog', 'Google'],
    ['http://feeds.trendmicro.com/TrendMicroResearch', 'Trend Micro'],
    ['https://www.bleepingcomputer.com/feed/', 'Bleeping Computer'],
    ['https://www.proofpoint.com/us/rss.xml', 'Proof Point'],
    ['http://feeds.feedburner.com/TheHackersNews?format=xml', 'Hacker News'],
    ['https://www.schneier.com/feed/atom/', 'Schneier on Security'],
    ['https://www.binarydefense.com/feed/', 'Binary Defense'],
    ['https://securelist.com/feed/', 'Securelist'],
    ['https://research.checkpoint.com/feed/', 'Checkpoint Research'],
    ['https://www.virusbulletin.com/rss', 'VirusBulletin'],
    ['https://modexp.wordpress.com/feed/', 'Modexp'],
    ['https://www.tiraniddo.dev/feeds/posts/default', 'James Forshaw'],
    ['https://blog.xpnsec.com/rss.xml', 'Adam Chester'],
    ['https://msrc-blog.microsoft.com/feed/', 'Microsoft Security'],
    ['https://www.recordedfuture.com/feed', 'Recorded Future'],
    ['https://www.sentinelone.com/feed/', 'SentinelOne'],
    ['https://redcanary.com/feed/', 'RedCanary'],
    ['https://cybersecurity.att.com/site/blog-all-rss', 'ATT']
]

gov_rss_feed_list = [
    ['https://www.cisa.gov/uscert/ncas/alerts.xml', 'US-CERT CISA'],
    ['https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml', 'NCSC'],
    ['https://www.cisecurity.org/feed/advisories', 'Center of Internet Security']
]

config_file = ConfigParser()
config_file.read(configuration_file_path)


def get_ransomware_updates():
    r = requests.get('https://raw.githubusercontent.com/joshhighet/ransomwatch/main/posts.json')

    for entries in r.json():
        date_activity = entries['discovered']
        try:
            config_entry = config_file.get('main', entries['group_name'])
        # TODO this treats entities on github but not in the config as errors, might just want to add them to the config?!
        except NoOptionError:
            continue

        if config_entry.endswith('?'):
            config_file.set('main', entries['group_name'], date_activity)

        if(config_entry >= date_activity): # TODO this works but is probably not the best way to handle datetimes
            continue
        else:
            config_file.set('main', entries['group_name'], entries['discovered'])
        
        message = f'{entries["group_name"]}\n{entries["discovered"]}\n{entries["post_title"]}'
        # ransomware_feed.send(message)
        logging.info(f"Ransomware: {message}")
        publish_to_signal(message)
        
        time.sleep(3)

        config_file.set('main', entries['group_name'], entries['discovered'])

    with open(configuration_file_path, 'w') as f:
        config_file.write(f)


def get_rss_from_url(rss_item, hook_channel_descriptor):
    news_feed = feedparser.parse(rss_item[0])
    date_activity = None

    for rss_object in news_feed.entries:
        try:
            date_activity = time.strftime('%Y-%m-%dT%H:%M:%S', rss_object.published_parsed)
        except: 
            date_activity = time.strftime('%Y-%m-%dT%H:%M:%S', rss_object.updated_parsed)

        config_entry = config_file.get('main', rss_item[1])

        if config_entry.endswith('?'):
            config_file.set('main', rss_item[1], date_activity)
        else:
            if(config_entry >= date_activity):
                continue
            else:
                config_file.set('main', rss_item[1], date_activity)

        message = f'{rss_item[1]}\nDate: {date_activity}\nTitle: {rss_object.title}\nRead more: {rss_object.link}\n'

        if hook_channel_descriptor == 1:
            # private_sector_feed.send(message)
            logging.info(f"Private Sector: {message}")
            publish_to_signal(message)
        elif hook_channel_descriptor == 2:
            # government_feed.send(message)
            logging.info(f"Government: {message}")
            publish_to_signal(message)
        else:
            pass

        time.sleep(3)

    with open(configuration_file_path, 'w') as f:
        config_file.write(f)


signal_configuration_file_path = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'signal.conf')
signal_conf = ConfigParser()
signal_conf.read(signal_configuration_file_path)

def publish_to_signal(message):
    headers = {'Content-type': 'application/json'}
    message = message.replace('\n', '\\n').replace('\t', '\\t')

    try:
        resp = requests.post(
            url=f"{signal_conf['signal']['signal_url']}/v2/send", 
            data=f'{{ "message":"{message}", "number":"{signal_conf["signal"]["sending_number"]}", "recipients":["{signal_conf["signal"]["receiving_number"]}"]}}',
            headers=headers)
        logging.info(f'[+] Send: {{"message":"{message}", "number":"{signal_conf["signal"]["sending_number"]}", "recipients":["{signal_conf["signal"]["receiving_number"]}"]}}')
    except:
        logging.info(f'[!] Unable to send: {{"message":"{message}", "number":"{signal_conf["signal"]["sending_number"]}", "recipients":["{signal_conf["signal"]["receiving_number"]}"]}}')
        

if __name__ == '__main__':
    logging.info('[+] Bot started]')
    while(True):
        for rss_item in rss_feed_list:
            get_rss_from_url(rss_item, 1)

        for rss_item in gov_rss_feed_list:
            get_rss_from_url(rss_item, 2)

        get_ransomware_updates()

        logging.info('[+] Bot finished loop')
        time.sleep(1800)