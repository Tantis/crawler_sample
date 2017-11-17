
*抓取脚本*
```python
 
# 这是一个轻量级的抓取脚本

# 继承Crawler_ext类
class Crawler(Crawler_ext):
    
    #基础方法to_request
    def to_request(self, response):
        # 这里会是你的第一个页面，如果你只是单页，可以只要这个方法即可
        # self.xhtml = HTML的XPATH
        # self.url = 当前的网页地址
        for item in range(2, 18): #833):
            print(self.url + 'index_{0}.html'.format(item) )
            url = self.url + 'index_{0}.html'.format(item)
            self.add_request("GET",
                             url,
                             info="test",
                             to_class=Sign_test)
            # add_request = 新增一个页面抓取
            # to_class= 下一个处理类

# 继承NETWORK_MANAGER类
class Sign_test(Network_manager):

    # 基础方法parse
    def parse(self, response):
        
        # 获取该页面所有的ali
        data = [item.strip() for item in self.xhtml.xpath(
            '//ul[@class="ali"]//img/@src')]
        # 这里的DATA=所有IMG的超连接
        # 然后你可以存储或者下载这些图片了

if __name__ == "__main__":
    
    # 第一个参数，可以是一个数据库连接，也可以是一个文件
    # 第二个参数，是抓取的方法
    # 第三个参数，是第一个要抓取的页面。这个页面可以是你想要计算的某个页面，当然也可以是一个无关的页面
    p = Crawler('output.txt', 'GET', 'http://www.ivsky.com/tupian/yishu/')
    p.run()

```

