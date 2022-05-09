import requests
import json
from prettytable import *
from bs4 import BeautifulSoup

api_str = """
{
  "status": 0,
  "msg": "success",
  "data": [
    {
      "name": "江苏-无锡",
      "trend": {
        "list": [
          {
            "name": "新增无症状",
            "data": []
          },
          {
            "name": "新增本土",
            "data": []
          }
        ],
        "updateDate": []
      }
    }
  ]
}
"""

# constants
cities0 = [
    "江苏-苏州",
    "江苏-南京",
    "浙江-杭州",
]
areas = [
    "上海",
]
travel_restriction_urls = {
    "苏州": "http://m.suzhou.bendibao.com/news/gelizhengce/all.php?leavecity=nj&leavequ=&qu=", 
    "南京": "http://m.nj.bendibao.com/news/gelizhengce/all.php?leavecity=suzhou&leavequ=&qu=",
    "杭州": "http://m.hz.bendibao.com/news/gelizhengce/all.php?leavecity=suzhou&leavequ=&qu=",
    "上海": "http://m.sh.bendibao.com/news/gelizhengce/all.php?leavecity=suzhou&leavequ=&qu=",
}
chrome_request_header = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"
}

# secrets
from secrets import weCom_robot_webHook

def get_city_info(city_CHN, isArea=0):
    url_patterns = ["https://voice.baidu.com/newpneumonia/getv2?from=mola-virus&stage=publish&target=trendCity&area={}",
                    "https://voice.baidu.com/newpneumonia/getv2?from=mola-virus&stage=publish&target=trend&area={}"]
    url = url_patterns[isArea].format(city_CHN)
    response= requests.request("GET", url)
    json_str = response.text
    obj = json.loads(json_str)
    
    city = obj['data'][0]['name']
    trend = obj['data'][0]['trend']
    date_str = trend['updateDate'][-1]
    if isArea:
        newPositive = trend['list'][4]['data'][-1]
        newConfirm = trend['list'][5]['data'][-1]
    else:
        newPositive = trend['list'][0]['data'][-1]
        newConfirm = trend['list'][1]['data'][-1]
    return (city, date_str, newPositive, newConfirm)

def get_travel_res_info(url):
    info = {
        'out': [],
        'in-low': [],
        'in-mid': []       
    }
    response= requests.request("GET", url, headers = chrome_request_header)
    soup = BeautifulSoup(response.content.decode('utf-8'), 'lxml')
    
    src_out  = soup.find('div', class_='risk-border new-chu').find('div', class_='article mudi-border')    
    in_lis = src_out.find('ul').find_all('li')
    for li in in_lis:
        text = li.find('span', class_='item').get_text()
        info['out'].append(text)
    if len(info['out'])==0: # when there's no summarized info
        info['out'].append(src_out.find('p').get_text().strip("\r\n "))
    
    for risk_level in ['low', 'mid']:
        src_in = soup.find('div', class_='risk-border {}-bg'.format(risk_level))
        if src_in: 
            out_lis = src_in.find('div', class_='article mudi-border').find('ul').find_all('li')
            for li in out_lis:
                text = li.find('span', class_='item').get_text()
                info['in-{}'.format(risk_level)].append(text)
    return info

def weCom_robot_msg(covid_info, pt, travel_res_info):       
    for line in covid_info:
        pt.add_row([line[0], line[2], line[3]])
    pt.set_style(PLAIN_COLUMNS)   
    date_str = covid_info[0][1]

    headers = {
        'Content-Type': 'application/json'
    }

    content = "# {}\n{}".format(date_str, pt.get_string()) 
    payload = json.dumps({
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    })
    response = requests.request("POST", weCom_robot_webHook, headers=headers, data=payload)
    print("weCom robot response:", response.text)

    for city, info in travel_res_info.items():
        quotes = "\n> ".join(info['out'])
        lines_out = "# {}-出\n".format(city) + \
                    "> {}\n".format(quotes)

        quotes_low = "\n> ".join(info['in-low'])
        quotes_mid = "\n> ".join(info['in-mid'])
        lines_in = "\n# {}-入\n".format(city)
        if quotes_low:
            lines_in += "<font color=\"info\">低风险地区</font>" + \
                     "\n> {} \n".format(quotes_low)
        if quotes_mid:
            lines_in += "\n<font color=\"warning\">中风险地区</font>" + \
                     "\n> {}".format(quotes_mid)

        payload = json.dumps({
            "msgtype": "markdown",
            "markdown": {
                "content": lines_out+lines_in
            }
        })
        # response = requests.request("POST", weCom_robot_webHook, headers=headers, data=payload)
        # print("weCom robot response:", response.text)

def main():
    covidInfo = []
    for city in cities0:
        covidInfo.append(get_city_info(city, isArea=False))
    for area in areas:
        covidInfo.append(get_city_info(area, isArea=True))
    pt = PrettyTable()
    pt.field_names = ["城市", "新增本土","新增无症状"]
    pt.align['新增本土'] = 'r'
    pt.align['新增无症状'] = 'r'

    travel_res_info = {}
    for city in travel_restriction_urls.keys():
        info = get_travel_res_info(travel_restriction_urls[city])
        travel_res_info[city] = info

    weCom_robot_msg(covidInfo, pt, travel_res_info)
    
if __name__ == '__main__':
    main()
