# 哔哩哔哩直播间弹幕互动盲盒查询工具

本工具通过本地运行python程序，当直播间弹幕出现特定词语时，自动输出该用户的投喂盲盒数量、成本及净收益。

<font color="red">请不要过于频繁地调用触发词，过于频繁的访问会直接导致程序绑定的bilibili账号被风控！</font>

共包含两个文件：

- boxlive.py: 主程序
- boxlive_v1.py: 测试程序

在以上两个程序中，需要SESSDATA与BILI_JCT两个参数。该参数可以在已登录bilibili账号的浏览器中获取。**请注意，公开该参数会导致bilibili账号无需密码即可直接登录，请不要向任何人透露以上参数！**

boxlive.py中，SESSDATA与BILI_JCT通过其他存储位置的data.py文件获取，设定的触发词为"呼叫弹幕姬"。