# -*- coding: utf-8 -*-
"""
Created on Wed Jan 11 20:10:49 2017

@author: wangjing
"""
from pandas import Series
from pandas import DataFrame
import requests
import json
import re
import time as ti
import MySQLdb 
import http.cookiejar as cookielib
from pandas import to_datetime 

#实现原始微博数据的抓取
#模拟微博登录请求的headers配置，在chrome浏览器上 移动端登录微博 
#https://passport.weibo.cn/signin/login?entry=mweibo&res=wel&wm=3349&r=http%3A%2F%2Fpad.weibo.cn%2F 
#下面的header来自Network-->Name-->login--->Request Headers
headers={"Accept":"*/*",
         "Accept-Encoding":"gzip, deflate, br",
         "Accept-Language":"zh-CN,zh;q=0.8",
         "Connection":"keep-alive",
         "Content-Length":"242",
         "Content-Type":"application/x-www-form-urlencoded",
         "Cookie":"_T_WM=37b259d3086958b0b209640735bb0af0",
         "Host":"passport.weibo.cn",
         "Origin":"https://passport.weibo.cn",
         "Referer":"https://passport.weibo.cn/signin/login?entry=mweibo&res=wel&wm=3349&r=http%3A%2F%2Fm.weibo.cn%2F",
         "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36"

         }
         
         

fromData={
          "username":"用户名",
          "password":"密码",
          "savestate":"1",
          "ec":"0",
          "entry":"mweibo"
        
          }
'''          
proxies = {
  'http': 'http://49.68.6.166:8118',
  'https': 'https://49.68.6.166:8118',
}
'''
pageURL="https://passport.weibo.cn/sso/login"
session = requests.session()
session.cookies = cookielib.LWPCookieJar(filename='cookies')

login_page = session.post(pageURL, data=fromData, headers=headers)
conn = MySQLdb.connect(
            host='127.0.0.1',
            user='root',
            passwd='admin',
            port=3306,
            db='weibo',
            charset='utf8'
        )


#使发表时间按照统一的字符串格式输出
def format_time(time_string):
    ti_string=ti.strftime("%H:%M",ti.localtime())
    (hour,minute)=ti_string.split(':')
    hour=int(hour)
    minute=int(minute)
    if '分钟前' in time_string:
        result = re.findall(r"[0-9]",time_string)
        l=len(result)
        if l==1:
            diff=int(result[0])
            if minute>=diff:
                new_minute=minute-diff
                return(ti.strftime("%m-%d ",ti.localtime())+str(hour)+':'+str(new_minute))                                                                     
            else:
                new_hour=hour-1
                new_minute=60+minute-diff
                return(ti.strftime("%m-%d ",ti.localtime())+str(new_hour)+':'+str(new_minute))
        else:
            diff=str(result[0])+str(result[1])
            diff=int(diff)
            if minute>=diff:
                new_minute=minute-diff
                return(ti.strftime("%m-%d ",ti.localtime())+str(hour)+':'+str(new_minute))                                                                     
            else:
                new_hour=hour-1
                new_minute=60+minute-diff
                return(ti.strftime("%m-%d ",ti.localtime())+str(new_hour)+':'+str(new_minute))
    elif  '今天' in time_string:
        return(time_string.replace('今天',ti.strftime("%m-%d",ti.localtime(ti.time()))))
    else:
        return(time_string) 
        
#微博发表的时间段
def get_hour(time_string):
    f_date=to_datetime('2017-'+time_string,format='%Y-%m-%d %H:%M')
    hour_num=f_date.hour
    return(hour_num)

#获得某个数据库的某个数据表当前的记录数，返回值为int类型
def get_records_num(conn,table_name):
    cursor=conn.cursor()
    sql=("""SELECT count(*) FROM  %s"""%(table_name))
    cursor.execute(sql)
    records_num=cursor.fetchone()[0]
    return(records_num)     

#拼接demo_page的url
def joinURL(now_cursor,pageNum):
    demo_pageURL="http://m.weibo.cn/feed/friends?version=v4&next_cursor="+str(now_cursor)+"&page="+str(pageNum)
    return(demo_pageURL)
    
#获取某页的card的内容，并格式化为dataframe
def get_card_group(pageNum,jsonObject,conn,table_name):
    record_count=get_records_num(conn,table_name)
    data=DataFrame(columns=['record_count','hourNum','pageNum','userID','nickName','user_description','user_fansNum','time','content','reposts_count'])
    counts=len(jsonObject[0]['card_group'])
    for each_count in range(0,counts):
        record_count=record_count+1
        id=str(jsonObject[0]['card_group'][each_count]['mblog']['id'])
        time=format_time(jsonObject[0]['card_group'][each_count]['mblog']['created_at'])
        hour_num=get_hour(time)
        screen_name=jsonObject[0]['card_group'][each_count]['mblog']['user']        ['screen_name']
        description=jsonObject[0]['card_group'][each_count]['mblog']['user']['description']
        fansNum=jsonObject[0]['card_group'][each_count]['mblog']['user']['follow_count']
        reposts_count=str(jsonObject[0]['card_group'][each_count]['mblog']['reposts_count'])
        if 'retweeted_status' in str(jsonObject[0]['card_group'][each_count]['mblog']):
            content=str(jsonObject[0]['card_group'][each_count]['mblog']['text'])+'---转发自---'+str(jsonObject[0]['card_group'][each_count]['mblog']['retweeted_status']['text'])
        else:
            content=str(jsonObject[0]['card_group'][each_count]['mblog']['text'])
    
        data=data.append(
                             Series(
                [record_count,hour_num,pageNum,id,screen_name,description,fansNum,time,content,reposts_count], 
                index=['record_count','hourNum','pageNum','userID','nickName','user_description','user_fansNum','time','content','reposts_count']
            ), ignore_index=True
                                    )
    return(data)

#-----------------------------------------------------------------------------

total_page=100
now_cursor=4073649739283309
for pageNum in range(1,total_page+1):
    demo_page = session.get(joinURL(now_cursor,pageNum))  
    jsonString =demo_page.text 
    jsonObject = json.loads(jsonString)
    df=get_card_group(pageNum,jsonObject,conn,'day0210') 
    df.to_sql(name='day0210', con=conn, flavor='mysql', if_exists='append', index=False)
    ti.sleep(2)
    print('*********************第'+str(pageNum)+'页的微博已存入数据库***********************')
    if jsonObject[0]['next_cursor']==0:
        print('end with pageNum='+str(pageNum-1))
        break








    