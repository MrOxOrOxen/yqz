# 哔哩哔哩直播间弹幕互动盲盒查询工具

本工具（boxlive.py）通过本地运行python程序，当直播间弹幕出现"呼叫盲盒姬"这一触发词时，自动以弹幕形式输出该用户的投喂盲盒数量、成本及净收益。所有用户的盲盒信息会被保存至user.json文件。

此外，额外添加了直播间所有礼物的电池数统计功能。各个用户送出的电池数量及礼物详细信息会按照电池数量降序排列，整理成gift.json文件。

gift.json可被后续程序处理以便发布在网页。后续处理步骤请前往我的mroxoroxen.github.io仓库：[mroxoroxen.github.io](https://github.com/MrOxOrOxen/mroxoroxen.github.io).

直播结束后，生成包含礼物时间戳及礼物电池数的all.json文件。通过transfer.py处理数据，可生成盲盒统计excel文件、各个用户送出电池excel情况，以及各时间送出电池数量的柱状统计图。

**请不要过于频繁地调用触发词，过于频繁的访问会直接导致程序绑定的bilibili账号被风控！**

## Apr 24

**更新：boxlive_test.py**

实测时遇到以下问题，均已解决：

1. 大航海电池数不正确

经测试，boxlive_v3.py无法准确显示大航海电池数，原因为：

bilibili的GUARD_BUY接口的price键值为固定的1980, 19980, 199980，即不管用户送出大航海时有多少折扣，程序获取到的金额均为原价。

为解决这一问题，引入USER_TOAST_MSG监听。该接口的price键值为用户实际支付金瓜子数量。

GUARD_BUY与USER_TOAST的区别请查看log.txt.

以下有关上文的网址内容供参考：

- [直播弹幕](https://github.com/czp3009/bilibili-api/blob/master/record/%E7%9B%B4%E6%92%AD%E5%BC%B9%E5%B9%95)
- [OnGuard命令可能不再可用于检测大航海](https://github.com/Akegarasu/blivedm-go/issues/7)
- [bilibili直播插件使用方法](https://zhuanlan.zhihu.com/p/665035523)

2. unpack requires a buffer of 16 bytes
   
B站的直播协议头为16字节。当直播间瞬间涌入大量礼物时，B站会将数据切片发送，导致Python的异步读取器有概率读取到8或12字节的数据，从而引发报错。

解决方法：使用pm2启动，使得404 Error时程序能自动重启。

3. Invalid HTTP request received

代码中设定了host=0.0.0.0，会导致Bot持续扫描端口。如果Bot发送的数据不符合HTTP协议标准，就会报无效请求错误。

解决方法：设定python程序只监听127.0.0.1，并使用Nginx监听80端口，将html请求转发给python程序。

4. 内存数据在json文件删除后自动恢复

由于内存数据被放进了全局变量MEMORY，当json文件被删除但python进程仍继续时，MEMORY依然会包含历史数据。

解决方法：优化了boxlive程序中load_json_files函数的逻辑，当json文件被手动删除（即不存在）时，清除相对应的内存值，以防继续保存历史数据。

## Apr 23

**更新：boxlive_v3.py**

原boxlive相关文件已被移至outdated文件夹。

计划生成的json文件：

- box.json: 盲盒统计，字典key为uid, uname, count, cost, profit;
- gift.json: 个人送出电池统计，字典key为uid, uname, gift_list, profit;
- all.json: 直播间所有电池流水统计，字典key为time, battery;
- log.json: 仅保留最后10条信息的日志文件。

由于服务器IO接口崩溃，代码中调整了所有的写入与读取逻辑，具体为：

1. 仅允许在代码启动时读取一次以上json文件。
2. 盲盒数据 (box.json) 允许实时写入；
3. 日志数据 (log.json) 每5s写入一次；
4. gift.json与all.json每60s写入一次。

API获取数据目前设定为1min读取一次（见github.io仓库），且API只允许读取内存文件，不允许读取json文件。

**更新：transfer.py**

直播结束后，通过transfer.py处理数据，可生成盲盒统计excel文件、各个用户送出电池excel情况，以及各时间送出电池数量的柱状统计图。

## Apr 22

**更新：boxlive_v2.py**

该程序在boxlive.py的基础上，添加了直播间所有礼物的电池数统计。

与boxlive.py仅监听bilibili_api的DANMU_MSG和SEND_GIFT不同，该版本还需监听SUPER_CHAT_MESSAGE和GUARD_BUY，即SC和大航海，从而统计电池送出数量。单击combo的COMBO_SEND无需监听。

**更新：boxlive_analyse.py**

该程序将user_stats.json文件转换为excel，便于直观观察盲盒盈亏情况。analysis文件夹为该程序历史运行数据。

## Apr 21

共包含两个文件：

- boxlive.py: 主程序
- boxlive_v1.py: 测试程序

在以上两个程序中，需要SESSDATA与BILI_JCT两个参数。该参数可以在已登录bilibili账号的浏览器中获取。**请注意，公开该参数会导致bilibili账号无需密码即可直接登录，请不要向任何人透露以上参数！**

boxlive.py中，SESSDATA与BILI_JCT通过其他存储位置的data.py文件获取，设定的触发词为"呼叫盲盒姬"。