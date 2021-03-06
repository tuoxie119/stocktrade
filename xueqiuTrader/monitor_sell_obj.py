#coding=utf-8
import pymongo
import json
import tushare as ts
import time
import easytrader as et
import math

"""
监控所有已经购买的股票，到达止损或者止盈，卖出
卖出策略修改（止损5个点，破MA5卖出）
每天统计个股收益，并根据收益计算止损
"""
class sellMonitor:
    conn = pymongo.MongoClient('192.168.222.188', port=27017)
    # user_sell = et.use('xq')
    # user_sell.prepare('xq.json')
    user = et.use('xq')
    user.prepare('xq.json')
    today = time.strftime("%Y-%m-%d", time.localtime())
    def deal(self):
        conn = self.conn
        for item in conn.mystock.yjbtrade.find({'tradestatus':0}):

            try:
                df = ts.get_realtime_quotes(item['code'])
                # 取得开始时间开始的最大值
                starttime = item['buytime'].split(' ')[0]


                # 最大值需要替换前面程序
                maxprice = round(float(item['maxprice']), 2)
                nowprice = round(float(df['price'][0]), 2)
                if nowprice == 0.0:
                    continue
                preclose = round(float(df['pre_close'][0]), 2)
                lossprice = round(float(df['low'][0]), 2)
                #如果当天，更新最大价格
                if starttime == self.today:
                    # 更新最大收益价格值
                    if (nowprice > maxprice):
                        conn.mystock.yjbtrade.update({'code': item['code'],'buytime':item['buytime']}, {'$set': {'maxprice': nowprice}})
                    # 更新最低价格
                    if (nowprice < lossprice):
                        conn.mystock.yjbtrade.update({'code': item['code'],'buytime':item['buytime']}, {'$set': {'lossprice': lossprice}})
                    continue

                # 更新最大收益价格值
                if (nowprice > maxprice):
                    conn.mystock.yjbtrade.update({'code': item['code'],'buytime':item['buytime']}, {'$set': {'maxprice': nowprice}})

                # 当前收益
                profit = round((float(nowprice) - float(item['buyprice'])) / float(item['buyprice']) * 100, 2)
                # 最大收益
                maxprofit = round((float(maxprice) - float(item['buyprice'])) / float(item['buyprice']) * 100, 2)

                # 当天收益
                todayprofit = round((float(nowprice) - float(preclose)) / float(preclose) * 100, 2)

                # 坑爹的卖出价格计算
                sellprice = round(float(nowprice) * 0.98, 2)

                #可以卖出标识
                if item['tradestatus']==0:

                    #止损卖出
                    sellcount = item['stockcount']
                    # if nowprice < item['lossprice']:
                    #     print "nowprice",nowprice,"   item['lossprice']",item['lossprice']
                    #     self.sellStock(item['code'].encode("utf-8"), sellprice, sellcount, 'zhisun', item['buytime'])


                    #止盈卖出=
                    if  self.ifSell(profit, maxprofit, todayprofit, 0):
                        self.sellStock(item['code'].encode("utf-8"), sellprice, sellcount, 'zhiying', item['buytime'])

            except Exception as e:
                print e
                continue

    #卖出方法
    def sellStock(self,code,sellprice,sellcount,sellType,buytime):
        sellret = self.user.adjust_weight(code, 0)
        # if sellret['error_no'].encode('utf-8') == '0':
        self.conn.mystock.yjbtrade.update({'code': code, 'tradestatus': 0,'buytime':buytime}, {
            '$set': {'tradestatus': 1, 'sellprice': sellprice, 'selldate': self.today,
                     'selltype': sellType, 'sellret': sellret}})
        print sellret
        print sellret['error_info'].encode("utf-8")
        print '止盈卖出'
        print '账户卖出成功 ', sellcount
        print '========================================'



    #卖出策略
    def ifSell(self,profit,maxprofit,todayprofit,daycount):

            # 止损点为5个点
        if profit < -3 and todayprofit < 0:
            print 'profit < -5 and todayprofit < 0'
            return 1

        # 最大收益大于10个点，止盈点为最大收益回落5个点
        if maxprofit > 10 and maxprofit - 3 >= profit:
            print 'maxprofit > 10 and maxprofit - 3 >= profit'
            return 1


        # 收益低于10，回落3个点止盈
        if maxprofit <= 10:
            if maxprofit - 3 >= profit:
                print 'maxprofit - 3 >= profit'
                return 1
            # 最大收益为负数
            # if profit <= 0:
            #     print 'profit <= 0'
            #     return 1

        # 暂时停止使用策略
        # #低于最大收益的30%卖出
        # if profit > 0 and profit <= maxprofit*0.6:
        #     return 1
        # #超过3天收益低于3个点，出局
        # if daycount >= 3:
        #     if maxprofit < 3:
        #         return 1
        return 0


    #更新止损价
    def updateLossprice(self):
        for item in self.conn.mystock.yjbtrade.find({'tradestatus': 0}):
            starttime = item['buytime'].split(' ')[0]
            if starttime == self.today:
                df = ts.get_realtime_quotes(item['code'])
                if float(item['buyprice']) < float(df['price'][0]):
                    self.conn.mystock.yjbtrade.update({'code': item['code'], 'buytime': item['buytime']},
                                                      {'$set': {'lossprice': item['buyprice']}})
                    continue
                lossprice = round(float(df['low'][0]), 2)
                self.conn.mystock.yjbtrade.update({'code': item['code'], 'buytime': item['buytime']},
                                                  {'$set': {'lossprice': lossprice}})

    def updateholddays(self):
        for item in self.conn.mystock.yjbtrade.find({'tradestatus': 0}):
            self.conn.mystock.yjbtrade.update({'code': item['code'], 'buytime': item['buytime']},
                                          {'$set': {'holddays': item['holddays'] + 1}})

    def monitor(self):
        while 1:

            if (time.strftime("%H:%M:%S", time.localtime()) < '08:30:00'):
                time.sleep(3600)
            if (time.strftime("%H:%M:%S", time.localtime()) < '09:30:00'):
                continue

            if (time.strftime("%H:%M:%S", time.localtime()) == '11:30:00'):
                time.sleep(5400)

            #更新当天最小值作为止损价
            # 下午3点退出
            if (time.strftime("%H:%M:%S", time.localtime()) > '15:00:00'):
                self.updateLossprice()
                self.updateholddays()
                break
            self.deal()

sellMonitor().monitor()






