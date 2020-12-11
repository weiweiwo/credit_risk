# -*- coding: utf-8 -*-
"""
Created on Thu Dec 10 15:44:08 2020

@author: EDZ
"""
import streamlit as st
import datetime
import calendar
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
# import pymysql
# pd.set_option('display.float_format',lambda x : '%.2f' % x)
pd.set_option('display.float_format',None)

import datetime
import os
import sys
import warnings
warnings.filterwarnings("ignore")
pd.set_option("display.max_columns",100)
os.listdir('./ppdai2017')





st.sidebar.title("风控分析")
page = st.sidebar.radio(label="", options=["贷前",
"贷中", "其他"])
if page == "贷中":
    # 获取某月第一天和最后一天
    def getFirstAndLastDay(year,month):
        # 获取当前月的第一天的星期和当月总天数
        weekDay,monthCountDay = calendar.monthrange(year,month)
        # 获取当前月份第一天
        firstDay = datetime.date(year,month,day=1)
        # 获取当前月份最后一天
        lastDay = datetime.date(year,month,day=monthCountDay)
        # 返回第一天和最后一天
        return firstDay,lastDay
    
    def convert(x):
        
        if x<=0:
            return 'C'
        elif x<=30:
            return 'm1'
        elif x<=60:
            return 'm2'
        elif x<=90:
            return 'm3'
        elif x<=120:
            return 'm4'
        elif x<=150:
            return 'm5'
        else:
            return 'm5+'
      
    def vintage(df_repay,df_dtl,DPD=0,rate_sum="rate",condition="capital"):
        result_all=pd.DataFrame()
        result_figure=pd.DataFrame()
            
        # 循环每个月的放款日期
        for lending_month in df_dtl.groupby(df_dtl.TRANSFER_TS.map(lambda x:str(x)[:7]))["LOAN_ID"]:
            #print(lending_month[0]) # 打印放款日期
            loan_19_11=df_repay[df_repay.LOAN_ID.isin(lending_month[1])] # 提取当月放款的所有还款计划表记录
            loan_19_11["当月月底"]=loan_19_11["CLOSE_DATE"].map(lambda x:getFirstAndLastDay(x.year,x.month)[1]) # 获取每个到期日期的月底日期
            
            # 生成账龄日期 与 建立某一个放款月的所有账龄
            aging=np.sort(loan_19_11["当月月底"].unique()) # 求得所有月底日期的唯一值，并且从小到大日期排序 (账龄)
            # 排除最月底的日期是当前时间，或者说是以当前月份的上一个月来统计账龄
            aging=aging[aging<=(datetime.datetime.now().date()- datetime.timedelta(days=datetime.datetime.now().day))]
            periods=1
            result =pd.DataFrame(columns=("账龄年月",lending_month[0]))
            result_fig=pd.DataFrame(columns=("账龄期数",lending_month[0]))
            ii=0
                
            # 循环每个月放款后资产的账龄变化
            for i in aging:
                dff=loan_19_11.copy() #复制还款计划表
                dff["真实还款时间"]=dff["PAY_DT"] #复制一份真实还款时间
                
                #  修改基础数据
                #  实际还款日期为空或者实际还款日期大于记录时间，都替换为记录时间
                dff.loc[(pd.to_datetime(dff["PAY_DT"]).isnull()) | (pd.to_datetime(dff["PAY_DT"])>pd.to_datetime(i)),"PAY_DT"]=i
                #  根据修改后的实际还款日期与到期日期之差求得逾期天数，与逾期状态
                dff[str(i)[:7]]=(pd.to_datetime(dff["PAY_DT"].astype(str))-pd.to_datetime(dff["CLOSE_DATE"].astype(str))).map(lambda x:convert(x.days))
                dff[str(i)[:7]+"天数"]=(pd.to_datetime(dff["PAY_DT"].astype(str))-pd.to_datetime(dff["CLOSE_DATE"].astype(str))).map(lambda x:x.days)
                dff.loc[dff['真实还款时间']>pd.to_datetime(i),'PRIN_PD_AMT']=0
                dff.loc[dff['真实还款时间']>pd.to_datetime(i),'intrPdAmt']=0
                dff["剩余本金"]=dff["PRIN_PY_AMT"]-dff["PRIN_PD_AMT"]
                
                    
                if condition=='capital':
                    
                    # 逾期余额（包含未入账）
                    # 筛选出 真实还款时间大于记录时间 或者为空的实际 同时逾期天数>0的原数据   在此数据减去真实还款日期不为空同时小于等于记录日期
                    balance=dff[dff.LOAN_ID.isin(dff.loc[dff.iloc[:,-2]>DPD]\
                    [lambda x:((pd.to_datetime(x["真实还款时间"])>pd.to_datetime(i)) | (x["真实还款时间"].isnull())) ]\
                    ["LOAN_ID"])]["剩余本金"].sum()
                        
                    # 判断存放逾期率或者逾期余额（包含未入账本金）
                    if rate_sum=="rate":
                        # 计算逾期率
                        balance_rate=balance/dff["PRIN_PY_AMT"].sum()
                        # 以年月存放账龄
                        result=result.append(pd.DataFrame({"账龄年月":[str(i)[:7]],lending_month[0]:[balance_rate]}),ignore_index=True)
                        # 以期数存放账龄
                        result_fig=result_fig.append(pd.DataFrame({"账龄期数":periods,lending_month[0]:[balance_rate]}),ignore_index=True)
                        #print(balance_rate)
                        periods+=1
                    elif rate_sum=="sum":
                        # 计算金额
                        # 以年月存放账龄
                        result=result.append(pd.DataFrame({"账龄年月":[str(i)[:7]],lending_month[0]:[balance]}),ignore_index=True)
                        # 以期数存放账龄
                        result_fig=result_fig.append(pd.DataFrame({"账龄期数":periods,lending_month[0]:[balance]}),ignore_index=True)
                        #print(balance)
                        periods+=1
                        
                elif condition=='loanid':
                    # 逾期贷款笔数
                    count_loanid=dff.loc[dff.iloc[:,-2]>DPD]\
                    [lambda x:((pd.to_datetime(x["真实还款时间"])>pd.to_datetime(i)) | (x["真实还款时间"].isnull()))]\
                    ["LOAN_ID"].nunique()
                    
                    # 判断存放笔数逾期率或者逾期笔数
                    if rate_sum=="rate":
                        # 计算逾期率
                        loanid_rate=count_loanid/dff["LOAN_ID"].nunique()
                        # 以年月存放账龄
                        result=result.append(pd.DataFrame({"账龄年月":[str(i)[:7]],lending_month[0]:[loanid_rate]}),ignore_index=True)
                        # 以期数存放账龄
                        result_fig=result_fig.append(pd.DataFrame({"账龄期数":periods,lending_month[0]:[loanid_rate]}),ignore_index=True)
                        #print(loanid_rate)
                        periods+=1
                    elif rate_sum=="sum":
                        # 计算笔数
                        # 以年月存放账龄
                        result=result.append(pd.DataFrame({"账龄年月":[str(i)[:7]],lending_month[0]:[count_loanid]}),ignore_index=True)
                        # 以期数存放账龄
                        result_fig=result_fig.append(pd.DataFrame({"账龄期数":periods,lending_month[0]:[count_loanid]}),ignore_index=True)
                        #print(count_loanid)
                        periods+=1
                        
                elif condition=='userid':
                    # 逾期贷款用户数
                    count_userid=dff.loc[dff.iloc[:,-2]>DPD]\
                    [lambda x:((pd.to_datetime(x["真实还款时间"])>pd.to_datetime(i)) | (x["真实还款时间"].isnull()))]\
                    ["USER_ID"].nunique()
                    
                    # 判断用户数逾期率或者逾期用户数
                    if rate_sum=="rate":
                        # 计算逾期率
                        userid_rate=count_userid/dff["USER_ID"].nunique()
                        # 以年月存放账龄
                        result=result.append(pd.DataFrame({"账龄年月":[str(i)[:7]],lending_month[0]:[userid_rate]}),ignore_index=True)
                        # 以期数存放账龄
                        result_fig=result_fig.append(pd.DataFrame({"账龄期数":periods,lending_month[0]:[userid_rate]}),ignore_index=True)
                        #print(userid_rate)
                        periods+=1
                    elif rate_sum=="sum":
                        # 计算用户数
                        # 以年月存放账龄
                        result=result.append(pd.DataFrame({"账龄年月":[str(i)[:7]],lending_month[0]:[count_userid]}),ignore_index=True)
                        # 以期数存放账龄
                        result_fig=result_fig.append(pd.DataFrame({"账龄期数":periods,lending_month[0]:[count_userid]}),ignore_index=True)
                        #print(count_userid)
                        periods+=1                                      
            result_all=pd.concat([result_all,result.set_index("账龄年月").T])
            result_figure=pd.concat([result_figure,result_fig.set_index("账龄期数").T])
            #print(dff["PRIN_PY_AMT"].sum())
        return result_all,result_figure        
      
    df_dtl=pd.read_csv('./ppdai2017/df_dtl.csv')
    loan_LP_1=pd.read_csv('./ppdai2017/loan_LP_1.csv')

    loan_LP_1["CLOSE_DATE"]=pd.to_datetime(loan_LP_1["CLOSE_DATE"])
    loan_LP_1["PAY_DT"]=pd.to_datetime(loan_LP_1["PAY_DT"].replace('\\N',np.NAN))
    loan_LP_1["TRANSFER_TS"]=pd.to_datetime(loan_LP_1["TRANSFER_TS"])
    
    
    alldate,number=vintage(df_repay=loan_LP_1[loan_LP_1["TRANSFER_TS"]<"2015-5-1"],
                           df_dtl=df_dtl[df_dtl["TRANSFER_TS"]<"2015-5-1"],DPD=0,rate_sum="rate",condition="loanid")
    
    st.dataframe(alldate)
    st.dataframe(number.style.highlight_max(axis=0))
    
    import plotly.express as px
    
    fig=px.line(number.T)
    st.plotly_chart(fig)
    
elif page == "贷前":
    st.write("在此展示贷前分析")
    
elif page == "其他":
    
    st.write("在此展示其他")