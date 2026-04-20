# 哔哩哔哩直播盲盒监测工具

本工具只能本地运行。通过监测直播间礼物情况，提取并统计出各类盲盒成本、收益以及净收益。当前程序仅支持从程序运行开始对直播间礼物情况进行监测，监测稳定情况视运行者及直播间网络条件而定。

本程序源文件为python代码，使用bilibili_api数据库，该数据库要求版本python<3.14. 程序开发时使用python 3.13.4，测试稳定版为python 3.11.4.

程序源文件代码中固定ROOM_ID=27885573，若需监测其他直播间，请修改源码并重新生成exe文件。pyinstaller指令为：

```
pyinstaller --clean -D -w --hidden-import="httpx" --hidden-import="aiohttp" --collect-all httpx --collect-all bilibili_api collector9.py
```

本工具测试信息来源于B站用户“晚安卡米宝宝” (UID: 1224551233)，测试直播间为：

- 27885573：云崎早_haya
- 503308916：千秋斋主
- 672342685：乃琳Queen
- 12939237：有棵里里
- 7735318：Weibo-回忆
- 8618005：凉哈皮
- 3546569288714792：果宝Official
- 57863910：王者荣耀
- 50329118：哔哩哔哩英雄联盟赛事（短号6）

## Apr 20 8:29AM

由于bilibili_api需要动态监测运行库，pyinstaller -F并不可行。使用pyinstaller -D重新构建程序。

优化代码部分细节。

## Apr 19

共两个exe文件：

- collectors9.exe: 直播间盲盒统计
- collectors_sim.exe: 模拟心动盲盒抽取

直接运行collectors9.exe即可。请注意，该程序若重启所有统计数据都将归零。

关于bilibili礼物的代码：

bilibili的礼物信息分为两类：SEND_GIFT和COMBO_SEND. 部分日志具有代表性：

- log_first_try.txt: 非盲盒类礼物单击combo第一次送出，或仅送出一次
- log_second_try.txt: 非盲盒类礼物单击combo第二次到最后一次送出
- log_last_try.txt: 非盲盒类礼物单击combo后汇总发送的combo日志
- log_multiple.txt: 非盲盒类礼物批量送出
- log_box_first_try.txt: 盲盒类礼物单击combo第一次送出，或仅送出一次
- log_box_multiple.txt: 盲盒类礼物批量送出

除log_last_try为COMBO_SEND以外，其余均为SEND_GIFT. 可见，COMBO_SEND只有在单击combo结束后才会触发。

通过blind_gift这个键，实现盲盒礼物与非盲盒礼物的区分。盲盒礼物爆出礼物的信息作为gift，原盲盒信息作为blind_gift. 盲盒礼物与爆出礼物作为同一条信息发送。

自定义监听函数：

```python
@room.on('SEND_GIFT')
async def on_gift(event):
    data = event['data']
```

获取到的数据为一个字典，详见各个相关日志。下面列出不同情况下字典中部分k, v值的变化：

1. log_first_try:
   
```
"cmd": "SEND_GIFT"
"data" -> batch_combo_send -> gift_num
                           -> blind_gift: null
       -> giftId
       -> giftName
       -> is_first: true
       -> combo_total_coin
       -> sender_uinfo -> base -> name
                       -> uid
```

2. log_second_try:
   
```
"cmd": "SEND_GIFT"
"data" -> batch_combo_send: null
       -> giftId
       -> giftName
       -> is_first: false
       -> combo_total_coin
       -> sender_uinfo -> base -> name
                       -> uid
```

3. log_multiple:

```
"cmd": "SEND_GIFT"
"data" -> batch_combo_send -> gift_num
                           -> blind_gift: null
       -> giftId
       -> giftName
       -> is_first: true
       -> combo_total_coin
       -> sender_uinfo -> base -> name
                       -> uid
```

4. log_box_first_try:

```
"cmd": "SEND_GIFT"
"data" -> batch_combo_send -> gift_num
                           -> blind_gift -> gift_tip_price
                                         -> original_gift_id
                                         -> original_gift_name
                                         -> original_gift_price
       -> giftId
       -> giftName
       -> is_first: true
       -> combo_total_coin
       -> sender_uinfo -> base -> name
                       -> uid
```

