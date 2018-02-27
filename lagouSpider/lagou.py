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

import spider

logging.basicConfig(
                format='%(asctime)s - %(levelname)s - %(message)s',
                filename='log',
                level=logging.INFO
                            )
search_root_url = 'https://www.lagou.com/jobs/positionAjax.json'
IPProxyTool_url = 'http://127.0.0.1:8000/select?name=httpbin&https=yes'

search_file_path = 'search_result.csv'

def check_search_page(search_res_json):
    if (search_res_json.get('content') and 
        search_res_json['content']['positionResult']['result']):
        return True
    
def lagou_search_response_onepage(keyword,proxies=None,first_tag='false',city='全国',pagenum='1',cache=None):
    params = {
            'px':'default',
            'city':city,
            'needAddtionalResult':'false',
            'isSchoolJob':'0'}
    data = {
        'first':first_tag,
        'pn':pagenum,
        'kd':keyword}
    d = spider.Downloader(search_root_url,headers=spider.HEADERS)
    d.params = params
    d.data = data
    d.cache = cache
    d.proxies = proxies
    d.use_session()
    d.method = 'POST'
    return d(),d.label

def lagou_search_parser(response):
    try :
        con = response.json().get('content')
        return con.get('positionResult').get('result')
    except Exception:
        logging.info('response未包含有效信息!!!')

def search_result_save(search_file_path,job_info,saved_check):
    if job_info.get('positionId') not in saved_check:
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
        saved_check.append('positionId')

def lagou_search(keyword,city='全国'):
    saved_check = []
    failed_page = []
    proxies_pool = spider.ProxyTool(IPProxyTool_url)
    cache = spider.DiskCache()
    end_test = 0
    for pagenum in itertools.count(1,1):
        if pagenum == 1:
            first_tag = 'true' 
        else :
            first_tag = 'false'
        num_retry = 10
        while num_retry > 0:
            proxies = proxies_pool.new_proxy()
            logging.info('更换代理地址为:{}'.format(proxies))
            response,label = lagou_search_response_onepage(
                                keyword,proxies=proxies,
                                first_tag=first_tag,city=city,pagenum=pagenum,cache=cache)
            num_retry -= 1
            if response and lagou_search_parser(response):
                for job_info in lagou_search_parser(response):
                    search_result_save(search_file_path,job_info,saved_check)
                logging.info('*已成功存储第{}页搜索结果'.format(pagenum))
                end_test = 0
                break
        else:            
            logging.info('*爬取第{}页失败'.format(pagenum))
            failed_page.append(pagenum)
            end_test += 1
            cache.del_cache(label)
        if end_test >= 5:
            logging.info('***爬取结束***')
            logging.info('*已爬取{}页，其中{}页爬取成功，{}页爬取失败，共{}条招聘信息'.format(
                                        (pagenum-5),
                                        (pagenum-5)-len(failed_page[:-5]),
                                        len(failed_page[:-5]),
                                        len(saved_check)
                                        ))
            if failed_page[:-5]:
                logging.info('其中爬取失败pagenum：{}'.format(failed_page[:-5]))
            break
         
def lagou_job_detail(job_id):
    pass
    """
    def lagouspider():
        lagou_search(keyword)
        lagou_job_detail(job_id)
    """

if __name__ == '__main__':
    start = datetime.now()
    lagou_search('python')
    print('运行时间:{}'.format(datetime.now()-start))

