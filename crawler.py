#!/usr/bin/python
# -*- coding:utf-8 -*-

# Copyright (c) 2015 yu.liu <showmove@qq.com>
# All rights reserved
"""
---------
轻量级采集程序
---------
.. note::
    1. 使用多线程采集
    2. 分量采集
.. note::
    1. 解决过于占用内存问题
    2. 解决采集速度问题
.. note::
    1.无法控制线程数量
    2.多线程下载时！会先下载所有的页面然后再现在里面的页面！
此处需要考虑！如果一个上万的页面应该如何控制他的下载数

.. note::
    Example 简单是例子

    .. literalinclude:: ../extend/Flacrawl/Crawler.py
       :pyobject: example

"""

import logging
import logging.config
import re
import time
from socket import timeout

import requests
from eventlet import GreenPool, Queue
from lxml import html
from requests.exceptions import ConnectionError, Timeout


class ServerErrorWithoutRetry(Exception):

    """这个服务器异常不进行重试"""


class TryAgain(Exception):

    """这个异常会导致重试。"""


class NoContent(TryAgain):

    """网络返回没内容。"""


class BreakenContent(TryAgain):

    """返回的内容是不全的（没有</html>）。"""


class ServerError(TryAgain):

    """服务器错误。"""


class Network_manager(object):
    """网络控制

    """

    def __init__(self, _crawler):
        """
        ::网络控制类
        :param _crawler: 传递的crawler类
        :type limit: class
        """
        self.crawler = _crawler
        self.cur_url = self.crawler.cur_url
        self.xhtml = self.crawler.xhtml
        self.html = self.crawler.html
        self.info = self.crawler.info
        self.logger = self.crawler.logger
        self.add_request = self.crawler.add_request
        self.execute_process = self.crawler.execute_process

    def run(self):
        """运行方法

        """
        self.crawler.run()

    def parse(self, response):
        """备用方法

        """
        raise NotImplementedError


class Crawler_ext(object):
    """新增爬虫系统

    """
    timeout = 30
    #: 预定义网页编码。
    encoding = None

    #: 设置User Agent，有时候模拟Google Bot会有事倍功半的效果。
    user_agent = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'

    # 页面语言，有些网站会以这个为标记实现国际化
    accept_language = 'zh_CN'
    encoding = 'gb2312'
    # 可接受的数据类型
    accept_mine = 'text/html,application/xhtml+xml,' \
        'application/xml;q=0.9,*/*;q=0.8'
    max_times = 20
    #: 如果服务器遇到这些error code，当做正常页面处理
    ignore_server_error_code = ()
    proxies = None
    #: 如果服务器遇到这些error code，不进行重试，直接忽略掉
    do_not_retry_with_server_error_code = ()
    retry_with_broken_content = False
    retry_with_no_content = False

    #: 是否开启远端服务器下载
    Server_Get = False

    logger = logging.getLogger('Crawler')

    def __init__(self, dbname, method, url, info=None, to_class=None, to_inter_net=False, **keyword):
        """

        :param dbname: 传递的数据库
        :param method: 下载网页的方法[GET|POST]
        :param url: 下载的URL地址
        :param table: 存储的数据表
        :param info: 额外传递的参数
        :param to_class: 去往的下一个类，不设定将去往to_request
        :param to_inter_net: 开启网络服务器下载
        :param keyword: Request 常用的传递参数例如(proxy, auth, paydata)
        :type dbname: [String]
        :type method: [GET|POST|PUT|DELETE]
        :type url: [标准网页URL格式]
        :type table: ORM Table

        Example
        .. literalinclude:: ../extend/Flacrawl/Crawler.py
            :pyobject: example

        """
        #self.Server_Get = to_inter_net
        #: 如果是起始类
        self.url = url
        self.method = method
        self.session = requests.session()
        self.queue = Queue()
        self.pool = GreenPool()
        self.dbname = dbname

        self.keyword = keyword
        self.default_header = {
            'Accept': self.accept_mine,
            'Accept-Language': self.accept_language,
            'User-Agent': self.user_agent,
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate'
        }
        self.xhtml = None
        self.html = None
        self.cur_url = url
        self.info = info
        self.to_class = to_class

    def request_url_list(self, url_list):
        """请求一个iter或者一个数组的列队

        """
        pass

    def Network_Reuqest(self):
        """请求一个网络列队

        """
        pass

    def request(self):
        """请求数据

        """
        retry_time = 0
        kwargs = self.keyword
        if self.keyword.get('header'):
            headers = self.keyword['header']
        headers = self.default_header

        kwargs['headers'] = headers
        # 如果没有设置timeout就使用全局设置
        kwargs['timeout'] = kwargs.pop('timeout',
                                       self.timeout)

       # kwargs['cookies'] = kwargs.pop('cookies', {})

        # 设置代理
        kwargs['proxies'] = kwargs.pop('proxies', self.proxies)

        while retry_time <= self.max_times:
            self.logger.info('[%s]>> url = %s' %
                             (self.method.upper(), self.url))
            try:
                if self.method.upper == 'GET':
                    response = requests.get(self.url,
                                            **kwargs)
                elif self.method.upper == 'POST':
                    response = requests.post(self.url,
                                             **kwargs)
                else:
                    response = self.session.request(self.method.upper(),
                                                    self.url,
                                                    **kwargs)
                if response.ok and response.status_code == 200:
                    break

                retry_time += 1
                if self.retry_with_no_content and not response.content:
                    self.logger.warning('Page have no content.')
                    raise NoContent
                if self.retry_with_broken_content and '</html>' not in response.content:
                    self.logger.warning('Page content has been breaken.')
                    raise BreakenContent
                if response.status_code in self.do_not_retry_with_server_error_code:
                    self.logger.warning(
                        'Something wrong with server,but we DO NOT retry with it.')
                    raise ServerErrorWithoutRetry(
                        'Error Code:%s' % response.status_code)
                # 遇到非200错误
                if response.status_code != 200 and response.status_code not in self.ignore_server_error_code:
                    self.on_server_error(response)
                self.logger.info(
                    "Connection %s [Get] retry = %s" % (self.url, retry_time))
            except (ConnectionError, Timeout), err:

                self.logger.info(
                    "Connection %s [Get] retry = %s" % (self.url, retry_time))
                self.logger.warning(err)
            except timeout, err:
                self.logger.info('Connect %s [GET] retry = %s' %
                                 (self.url, retry_time))
                self.logger.warning(err)

        else:
            if 'err' not in locals().keys():
                raise Timeout, 'Retry Timeout'
            raise err

        response.encoding = self.encoding
        # try:
        self.xhtml = html.document_fromstring(response.text)

        self.html = response.text
        self.cur_url = response.url
        return (response)

    def on_server_error(self, response):
        """服务器出错

        """
        self.logger.warning('Warning code %d' % response.status_code)

    def execute_process(self):
        """执行进程
        * 如果将阻塞放置在while外则会先下载分页再下载详情页
        * 如果将阻塞放置在while内则会同步下载

        """
        while not self.queue.empty():
            p = Network_manager(self.queue.get())
            self.pool.spawn_n(p.run)

            self.pool.waitall()
        #: self.pool.waitall()

    def add_request(self, method, url, info="", to_class=None,  **keyword):
        """
        :param dbname: 传递的数据库
        :param method: 下载网页的方法
        :param url: 下载的URL地址
        :param table: 存储的数据表
        :param info: 额外传递的参数
        :param to_class: 去往的下一个类，不设定将去往to_request
        :param keyword: Request 常用的传递参数例如(proxy, auth, paydata)
        :type dbname: String
        :type method: GET|POST|PUT|DELETE
        :type url: 标准网页URL格式
        :type table: ORM Table


        Example

        1. ADD REQUEST

        .. literalinclude:: ../extend/Flacrawl/Crawler.py
            :pyobject: Crawler_ext.to_request

        2. TO CLASS FUNCTION

        .. literalinclude:: ../extend/Flacrawl/Crawler.py
            :pyobject: Sign_test.param
        """

        self.queue.put(self.__class__(
            self.dbname, method, url, info=info, to_class=to_class, **keyword))

    def run(self, funtion_Name=None):
        """
        .. note::
            1. 第一次请求时指定到一个方法吧
            2. 载入类时存在to_class则指向类
            3. 不存在to_class存在function_name则指定funtion_name
            4. 以上都不满足则指向to_request
        """
        #: Run one url , to Funtion
        if self.Server_Get:
            req = self.Network_Reuqest()
            if self.to_class:
                self.to_class(self).Result(req)
            else:
                self.to_request(req)
        else:
            req = self.request()

            if self.to_class:
                self.to_class(self).parse(req)
            else:
                if funtion_Name:
                    func = funtion_Name
                else:
                    func = self.to_request
                func(req)
        self.execute_process()

    def to_request(self, response):
        """可重载函数

        """

        for item in range(2, 18): #833):
            print(self.url + 'index_{0}.html'.format(item) )
            url = self.url + 'index_{0}.html'.format(item)
            self.add_request("GET",
                             url,
                             info="test",
                             to_class=Sign_test)


class Sign_test(Network_manager):

    def parse(self, response):

        # URL
        print self.cur_url
        # html
        # self.html
        # xhtml
        # self.xhtml
     
        data = [item.strip() for item in self.xhtml.xpath(
            '//ul[@class="ali"]//img/@src')]
        for item in data:
            getImage("3", item)


def getImage(name, url):
    
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open("image/%s-%s.jpg" % (name,time.time()), "wb") as f:
            for chunk in r:
                f.write(chunk)
    r.close()


if __name__ == '__main__':

    # p = Crawler_ext('output.txt', 'GET', 'http://www.woyaogexing.com/touxiang/nv/')
    p = Crawler_ext('output.txt', 'GET', 'http://www.ivsky.com/tupian/yishu/')
    p.run()
    #getImage("http://img2.woyaogexing.com/2017/11/10/5c40a6776ae049bb!400x400_big.jpg")
