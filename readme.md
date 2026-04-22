# 哔哩哔哩直播间弹幕互动盲盒查询工具

本工具（boxlive.py）通过本地运行python程序，当直播间弹幕出现"呼叫盲盒姬"这一触发词时，自动以弹幕形式输出该用户的投喂盲盒数量、成本及净收益。所有用户的盲盒信息会被保存至user_stats.json文件。

boxlive_v2.py额外添加了直播间所有礼物的电池数统计功能。各个用户送出的电池数量及礼物详细信息会按照电池数量降序排列，整理成gift_ledger.json文件。

gift_ledger.json可被后续程序处理以便发布在网页。后续处理步骤请前往我的mroxoroxen.github.io仓库：[mroxoroxen.github.io](https://github.com/MrOxOrOxen/mroxoroxen.github.io).

**请不要过于频繁地调用触发词，过于频繁的访问会直接导致程序绑定的bilibili账号被风控！**

## Apr 22

更新：boxlive_v2.py

该程序在boxlive.py的基础上，添加了直播间所有礼物的电池数统计。与boxlive.py仅监听bilibili_api的DANMU_MSG和SEND_GIFT不同，该版本还需监听SUPER_CHAT_MESSAGE和GUARD_BUY，即SC和大航海，从而统计电池送出数量。单击combo的COMBO_SEND无需监听。

更新：boxlive_analyse.py

该程序将user_stats.json文件转换为excel，便于直观观察盲盒盈亏情况。analysis文件夹为该程序历史运行数据。

## Apr 21

共包含两个文件：

- boxlive.py: 主程序
- boxlive_v1.py: 测试程序

在以上两个程序中，需要SESSDATA与BILI_JCT两个参数。该参数可以在已登录bilibili账号的浏览器中获取。**请注意，公开该参数会导致bilibili账号无需密码即可直接登录，请不要向任何人透露以上参数！**

boxlive.py中，SESSDATA与BILI_JCT通过其他存储位置的data.py文件获取，设定的触发词为"呼叫盲盒姬"。