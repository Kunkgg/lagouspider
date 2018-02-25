#-*- coding:utf-8 -*-
#拉勾爬虫
import time
import logging
import re
from urllib.parse import urlparse
import time
from datetime import datetime
import random
import itertools
import os
import csv

import requests
from requests.exceptions import RequestException

user_agent=[
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6',
    'Mozilla/5.0 (Windows NT 6.2) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.12 Safari/535.11',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:34.0) Gecko/20100101 Firefox/34.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/44.0.2403.89 Chrome/44.0.2403.89 Safari/537.36',
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
    'Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; en) Presto/2.8.131 Version/11.11',
    'Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.11',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36'
    ]

logging.basicConfig(
                format='%(asctime)s - %(levelname)s - %(message)s',
                filename='log',
                level=logging.INFO
                            )
search_root_url = 'https://www.lagou.com/jobs/positionAjax.json'
IPProxyTool_url = 'http://127.0.0.1:8000/select?name=httpbin&https=yes'

head_file_path = 'head.txt'
search_file_path = 'search_res.csv'

def _get_headers(head_file_path):
    headers = {}
    with open(head_file_path) as f:
        for line in f:
            l = [x.strip() for x in line.split(':',1)]
            headers[l[0]] = l[1]
    return headers

def _get_data(isfrist,pagenum,keyword):
    data = {
        'first':isfrist,
        'pn':pagenum,
        'kd':keyword
        }
    return data

class IPProxyTool:
    def __init__(self,source,delay=300):
        self.source = source
        self.proxies_pool = requests.get(source).json()
        self.used_proxies = {}
        self.delay = delay
        logging.info('IP Prxoies Pool 初始化完成...包含{}个备用代理'.format(len(self.proxies_pool)))
    def sort_proxies(self):        
        self.proxies_pool = sorted(self.proxies_pool,key=lambda x:x.get('speed'))
    def new_proxy(self):
        if self.proxies_pool:
            proxy = self.proxies_pool.pop(0)
            last_accessed = self.used_proxies.get(proxy.get('ip'))
            if self.delay > 0 and last_accessed is not None:
                sleep_secs = self.delay - (datetime.now() - last_accessed).seconds
                if sleep_secs > 0:
                    time.sleep(sleep_secs)
            self.used_proxies[proxy.get('ip')] = datetime.now()
            proxy_url = 'http://' + proxy.get('ip') + ':' + str(proxy.get('port'))
            return {'http':proxy_url,'https':proxy_url}
        else :
            self.update_proxies()
            self.new_proxy()    
    def update_proxies(self):
        self.proxies_pool = requests.get(self.source).json()
        self.sort_proxies()
        self.used_proxies = {}
        logging.info('IP Prxoies Pool更新完成...包含{}个备用代理'.format(len(self.proxies_pool)))

def download_GET(
    url,session,params=None,data=None,headers=None,
    num_retry=2,proxies=None
            ):
    logging.info('GET:{}'.format(url))
    try:    
        res = session.get(url,params=params,data=data,headers=headers,proxies=proxies,timeout=2)
        res.raise_for_status()
    except RequestException as e:
        logging.info('Request异常:{}'.format(e))
        res = None
        if num_retry > 0:
            return download_GET(url,session,params,data,headers,
                            num_retry=num_retry-1,proxies=None)
    return res

def download_POST(
    url,session,params=None,data=None,headers=None,
    num_retry=2,proxies=None
            ):
    #logging.info('POST:{}'.format(url))
    #logging.info('session type:{}'.format(type(session)))
    #logging.info('params:{}'.format(params))
    #logging.info('data:{}'.format(data))
    #logging.info('headers{}'.format(headers))
    try:    
        res = session.post(url,params=params,data=data,headers=headers,proxies=proxies,timeout=3)
        res.raise_for_status()
    except RequestException as e:
        logging.info('Request异常:{}'.format(e))
        res = None
        if num_retry > 0:
            return download_POST(url,session,params,data,headers,
                            num_retry=num_retry-1,proxies=None)
    return res

def check_search_page(search_res_json):
    if (search_res_json.get('content') and 
        search_res_json['content']['positionResult']['result']):
        return True
    
def lagou_search(keyword,job_ids_done,startpagenum=1,city='全国'):
    _params = {
        'px':'default',
        'city':city,
        'needAddtionalResult':'false',
        'isSchoolJob':'0'
            }
    _headers = _get_headers(head_file_path)
    _headers['User-Agent'] = random.choice(user_agent)
    proxies_pool = IPProxyTool(IPProxyTool_url)
    proxy = None
    throttle = Throttle()
    for pagenum in itertools.count(startpagenum,1):
        num_retry = 10
        if pagenum == 1:
            _data = _get_data('true',str(pagenum),keyword)
            logging.info('已开始爬取第1页搜索结果')
            print('已开始爬取第1页搜索结果')
        else:
            _data = _get_data('false',str(pagenum),keyword)  
        while num_retry > 0:
            _session = requests.session()
            throttle.wait(search_root_url)
            search_res_json = download_POST(
                    url=search_root_url,
                    session=_session,
                    params=_params,
                    data=_data,
                    headers=_headers,
                    proxies = proxy
                                ).json()
            if check_search_page(search_res_json):
                break
            else:
                logging.info('尝试爬取{}页失败,还将尝试{}次'.format(pagenum,num_retry))
                _session.close()
                num_retry -= 1
                if num_retry < 8:
                    proxy = proxies_pool.new_proxy()
                    logging.info('变更代理地址:{}'.format(proxy))
        if not check_search_page(search_res_json):
            logging.info('爬取结束，共爬取{}条招聘信息'.format(len(job_ids_done)))
            _session.close()
            return len(job_ids_done)
        else:
            logging.info('已爬取第{}页搜索结果'.format(pagenum))                                            
            for job_info in search_res_json['content']['positionResult']['result']:
                if job_info['positionId'] not in job_ids_done:
                    job_ids_done.append(job_info['positionId'])
                    search_res_save(search_file_path,job_info)
        
def search_res_save(search_file_path,job_info):
    tiltes = [
        'city','companyFullName','companyId',
        'createTime','education','positionId',
        'positionName','salary','workYear'
            ]
    if (not os.path.exists(search_file_path) or not os.path.isfile(search_file_path)):
        with open(search_file_path,'w') as f:
            w = csv.writer(f)
            w.writerow(tiltes)
    else:
        with open(search_file_path,'a') as f:
            w = csv.writer(f)
            row = [job_info.get(field) for field in tiltes]
            w.writerow(row)

def lagou_job_detail(job_id):
    pass
"""
def lagouspider():
    lagou_search(keyword)
    lagou_job_detail(job_id)
"""

class Throttle:
    """设置访问同一域名的最小间隔
    """
    def __init__(self,delay_tag=-1):
        self.delay_tag = delay_tag
        self.domains = {}
        
    def wait(self, url,delay_down=3,delay_up=5):
        delay = random.uniform(delay_down,delay_up)
        domain = urlparse(url).netloc
        last_accessed = self.domains.get(domain)
        if self.delay_tag > 0 and last_accessed is not None:
            sleep_secs = delay - (datetime.now() - last_accessed).seconds
            if sleep_secs > 0:
                time.sleep(sleep_secs)
        self.domains[domain] = datetime.now()


if __name__ == '__main__':
    start_time = datetime.now()
    job_ids_done = []
    job_done_num = lagou_search('python',job_ids_done)
    logging.info('完成爬取用时{}'.format((datetime.now()-start_time)))
