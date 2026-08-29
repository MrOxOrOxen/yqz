本markdown文件为非正式技术说明文档，仅对代码文件进行较为详细的原理及功能说明，不详细介绍代码内容。

（卡米根据印象写的，有些记不太清了看了看代码，如文档有误敬请谅解）

*Developed and written by 晚安卡米宝宝

*Last updated on 29 Aug, 2026*

# 0 需要先知道的一些内容

## 0.1 程序结构

```
| - web
|   - gift
|       - index.html
|   - superchat
|       - index.html
| - files
|   - all.json
|   - audience.json
|   - box.json
|   - danmu.jsonl
|   - gift.json
|   - log.json
|   - meta.json
|   - reset.json
|   - superchat.jsonl
| - history_files
|   - all
|   - audience
|   - box
|   - danmu
|   - gift
|   - livetime
|   - meta
|   - superchat
| - stable_json
|   - birthday_cache.json
|   - livetime.json
|   - runtime_state.json
| - bili_gift_map.json
| - bili_gift_map.py
| - birthday_cache_manage.py
| - box_bot.py
| - constants.py
| - data.py
| - eggs.py
| - error_log.txt
| - get_data.py
| - gift_bot.py
| - hotglobal.py
| - hotreload_config.py
| - ids.py
| - json_handle.py
| - livetime.py
| - logger.py
| - lunar.py
| - mail.py
| - main_v2.py
| - memory_store.py
| - qq_bot.py
| - reset.sh
| - runtime_state.json
| - send_reply.py
| - transfer.py
| - transfer.sh
```

## 0.2 json

json格式文件类似于python的字典格式，包含所谓的key与value，也就是键和值。Json格式文件可以在不同种类编程语言之间传输，也可以作为数据直接存储。

本程序的数据均以json或者jsonl (json lines)格式存储。如果数据量过大，需要考虑用sqlite等数据库格式来存储。

# 1 基本原理

## 1.1 nginx代理websocket

### 1.1.1 nginx

nginx用来反向代理web框架，就是把客户端和后端的服务器串接起来，这样服务器的代码写好之后，客户端就可以看到网页。

nginx运行前需要配置nginx的conf文件。为了使绑定域名的网页能够通过https协议，需要使用certbot自动更新域名证书。Certbot会自动修改conf文件，使其支持https协议。

### 1.1.2 端口搭建

服务器有一个特定的ip，比如xx.xx.xx.xx，可以把端口理解为服务器这个楼里面不同的门牌号，比如xx.xx.xx.xx:xxxx. 或者如果有域名的话就是http://xxx.com:xxxx.

最底层的端口搭建方式是使用socket，python中有对应的socket的库可以直接使用。

直播间机器人的python程序使用的是FastAPI框架配合uvicorn来管理端口， uvicorn用来封装socket，在后台监听端口。

可以认为整个的流程是这样的：用户访问http://xxx.com:xxxx ，nginx把这个端口需求转发给python程序，然后python里面的uvicorn把这个端口的消息提供出去。

但实际上为了安全，nginx会做一步转发，就是用户访问a端口，nginx收到a端口，转发成b端口，然后python看的是b端口。

### 1.1.3 网页搭建

1. 备案

根据工信部的要求，所有的网站或者app如果根服务器的ip在中国大陆，都需要进行备案（工信部icp备案以及公安备案），自建服务器做这些功能如果ip在中国大陆也需要备案。

这就是yqzhaya.com这个网站需要备案的原因，这台服务器的ip在大陆。

备案是一件不是很复杂但是很耗时间的事情，过程我就不写了。总之，你需要先买一个域名，然后通过nginx把域名和你这台服务器捆绑上，然后先去icp备案，再去公安备案。备案好以后，需要在网站底端添加备案号，就像yqzhaya.com里面的那样。

（上面的网站指的是域名网站，如果你只是通过服务器的ip直接访问而不搭建域名，其实不备案也行）

2. 从端口获取数据

如果想要发送一些服务器上的数据到网站的话，通过python里面的FastAPI，可以自定义特定端口下接口的名称，可以认为最终的形式就是xx.xx.xx.xx:xxxx/xxxx或者http://xxx.com:xxxx/xxxx.

FastAPI会将想要发送的数据转换成json文件的形式，并且通过上面的url发送出去。这也就意味着，如果直接访问xx.xx.xx.xx:xxxx/xxxx或者http://xxx.com:xxxx/xxxx 看到的就是FastAPI转换完的json文件。

网页文件中，有一种文件是javascript文件，这种格式的文件里面有一个fetch函数，可以直接调用端口对应的url地址。这样用户访问要传输的数据时，javascript文件就会通过fetch函数向url索要内容，python程序会把数据发出去。

（FastAPI需要配置跨域转发，不然fetch函数会报错）

## 1.2 bilibili_api

Bilibili_api是一个**非官方**的哔哩哔哩api python库，和哔哩哔哩交互的几乎所有操作都需要用到这个库。

Bilibili是异步驱动的，可以把异步理解为即使程序的某一个部分报错，和报错程序不在同一个block的程序也会正常运行，所以即使代码有些小bug，也只是这部分的功能崩溃，而不会影响大局。

机器人程序里，除了一些比较底层的函数是直接def部署的，其余的大多数实现特定功能的函数都是async def，也就是异步函数。

### 1.2.1 登录态cookie

Bilibili_api中有些接口的调用需要账号登录，但服务器是一个没有图形交互、只有终端的东西，想要登录b站账号只能使用cookie的方式。

一个b站账号在任何平台（比如Windows浏览器、手机app甚至是脚本里）登录时，都会生成一个cookie. 这个cookie会保存在你登录的平台上，这样你下一次访问的时候就还能保持登录状态。Bilibili_api就是利用这个cookie来实现伪登录的。

具体的cookie内容包括但不限于：SESSDATA（登录凭证）, bili_jct（防御校验值）, buvid3与buvid4（设备指纹）, DedeUserID（用户的数字ID）等等。

通过把这些cookie结合成特定的字符串，就可以假装自己在服务器上登录了b站账号。但同样的，如果这些参数泄露，别人就可以不使用你的手机号和密码而直接在任何平台登录你的账号。

Cookie是有有效期的，有效期过了之后需要重新登录来更新cookie（因此服务器的cookie信息也需要定期更新）。另外一种强制刷新b站cookie的方式是在任何一个已登录的平台上退出登录b站账号。

注：过于频繁的访问与写入会导致cookie所属账号报错412，即风控。风控后一段时间内不再进行访问与写入操作即可解除风控。

### 1.2.2 通过api获取信息

1. 直接利用api网址获取信息

哔哩哔哩的一些公开api网页可以直接获取信息。例如，https://api.bilibili.com/x/polymer/web-dynamic/v1/name-to-uid 可以在给定用户名的情况下，直接返回用户的uid. 其他的api网页也可以返回其他的json数据。

通过cookie的特定字段组合，程序可以模拟真人来访问这个url（或者从其他url跳转到这个url来绕过风控），从而获取到想要的信息。

yqzhaya.com主页上面的粉丝数也是采用这种方式来获取。

2. live.LiveRoom

通过bilibili_api库中live.LiveRoom这个类下面的函数，可以获取一些信息。例如get_room_info可以获取到直播间房间基础信息，get_user_info可以获取到用户基本信息。

机器人程序中，开播时的直播标题就是通过get_room_info获取，程序中涉及到一些查询用户大航海身份、粉丝牌等级及粉丝牌名字、用户uid及名称等，就是通过get_user_info获取。

3. live.LiveDanmaku

这个模块用于长连接监听，可以实时监听直播间弹幕、礼物等事件。每个事件使用@room.on()指令，也就是监听指令来调用，后面接需要接的接口名称。具体的所有接口及其功能可以通过bilibili_api的指令获取，也可以看danmaku.txt.

以下为本程序使用的监听端口：

- DANMU_MSG：弹幕监听
- SEND_GIFT：礼物监听（包括盲盒）
- SUPER_CHAT_MESSAGE：SuperChat监听
- USER_TOAST_MSG：官方说这是高光时刻监听，实际上我用这个来判断大航海了
- GUARD_BUY：大航海监听，但是这个接口只会显示大航海的原价（比如舰长就全是198），所以后来弃用了
- INTERACT_WORD_V2：观众进入直播间监听
- ENTRY_EFFECT：观众进入直播间（带特效，比如大航海）监听
- COMMON_NOTICE_DANMAKU：特殊弹幕类型监听，例如上舰时在弹幕区出现的“今天是xxx陪伴TA的多少多少天这种）
- LIVE：开播事件监听
- PREPARING：下播事件监听

（吐槽一句，bilibili_api自己也没说明白很多的接口能做什么）

每个监听事件一旦发生，就会返回一个字典，字典里包括了事件以及用户的详细信息。通过提取字典里特定的key对应的value值，就可以获取到想要的信息。

send_gift接口提供的字典（event）部分结构：

```
event -> data -> data -> uid
                      -> gift_name
                      -> num
                      -> sender_uinfo -> base -> name
                      -> blind_gift -> original_box_name
                                    -> original_gift_price
                                    -> gift_tip_price
```

若blind_gift非None，则礼物为盲盒。blind_gift内侧的信息为盲盒信息，外侧信息为开出的礼物信息。

super_chat_msg接口提供的字典部分结构：

```
event -> data -> data -> uid
                      -> price
                      -> uname
                      -> content
```

user_toast接口提供的字典部分结构：

```
event -> data -> data -> guard_level
                      -> uid
                      -> username
                      -> price
                      -> start_time
```

interact_word_v2接口提供的字典部分结构：

```
event -> data -> data -> pb_decoded -> uname
                                    -> user_info -> medal -> name
                                                          -> level
                                                 -> uid
```

entry_effect接口提供的字典部分结构：

```
event -> data -> data -> uinfo -> base -> name
                               -> uid
                               -> medal -> name
                                        -> level
                               -> guard -> guard_level
```

common_notice_danmaku接口提供的字典部分结构：

```
event -> data -> data -> content_segments(list) -> content_segments[0] -> text
                                                -> ...
```

danmu_msg接口提供的字典部分结构：

```
event -> data -> info(list) -> info[0]
                            -> info[1] # 弹幕内容
                            -> info[2][0] # uid
                            -> info[2][1] # 用户名
```

### 1.2.3 通过api发送消息

发送弹幕需要用live.LiveDanmaku下面的send_danmaku方法。在send_danmaku()里面添加弹幕内容，即可以cookie归属账号的身份发送弹幕。

若需要@某个用户发送弹幕，只需要向函数中传入被@的用户的uid即可，但是只有进入过直播间的用户（或者脚本）才能被@，如果不满足被@的条件，弹幕仍会被正常发送，但不会出现前面的@内容。

注：直播间机器人所使用的大多数bilibili_api下的函数需要cookie账号登录。这既是bilibili_api这个库的限制，也是b站官方的限制。最形象的例子是，如果没有登录就打开一个直播间，是看不到发送弹幕用户的全名的，因此bilibili_api在没有登录的状态下也就抓取不到用户名。

另外，还有些其他的写入操作。例如，当账号有房管权限或本身就是主播时，可以通过bilibili_api库对特定用户禁言、解除禁言；主播本人可以通过程序直接修改直播间标题等等功能。

机器人程序的写入操作只有发送弹幕这一种。为防止弹幕频率过高导致账号风控，将所有等待发送的弹幕放入一个list，并设置2.5-3.5s的随机间隔时间，逐个回复list中的弹幕。

## 1.3 FastAPI

FastAPI的端口推送数据请参考1.1.3第2部分。

### 1.3.1 跳板机制

FastAPI端口一旦触发，就一定会执行接口下面对应的函数。

借此，可以通过手动触发特定的端口，来执行特定的函数修改全局变量，也就实现了热修改与热删除，同时也可以实现弹幕的热发送。

### 1.3.2 生命进程

通过asynccontextmanager可以给FastAPI注册生命进程lifespan，在其scheduler中添加带参的cron任务，可实现在特定时间周期性执行指定任务。stable_json文件夹中的所有json文件通过这个进程更新。

该方法与下文提到的pm2类似都可以执行周期任务。在机器人程序中，两个周期性任务所设置的循环时间不同，且两个循环任务无法兼容。

## 1.4 NapCat

NapCat是**第三方**的一个开源QQ机器人框架（鹅厂自己的框架不开源），或者可以理解为，在服务器端登录一个QQ，然后接收消息发送消息，以及一些群管理操作之类的。

（由于腾讯的风控比较严，所以NapCat以及其他开源的或者闭源的，总之是非官方的框架都不是很稳定，不能保证推送姬程序稳定运行，但也没办法）

推送姬的NapCat是通过docker部署的，NapCat官方对于docker部署的支持比较好。

推送姬只部署了接收与发送信息的功能，没有部署其他NapCat支持的功能。

## 1.5 邮件发送

利用python发送邮件，就是利用smtp协议和邮件服务器进行通信，然后把邮件数据发送到目标邮件服务器。Python的email库可以构建邮件发送人名称、标题以及内容，smtplib模块可以和smtp服务器建立连接并且发送邮件。

使用smtplib模块发送邮件时，需要的参数为发件人的账号以及授权码。

机器人程序中，开播时会记录开播时间，下播时会将直播的一些信息直接发送给admin@yqzhaya.com.

## 1.6 lsyncd

这是一个在linux系统下监测linux本地文件变动之后，将变动实时同步到本地或其他服务器的进程。

使用lsyncd是因为yqzhaya.com网页最初是在斯卡蕾特老师的服务器构建的，需要同步到我的服务器。我在域名的管理界面中做了以下的配置：

- 访问yqzhaya.com时，如果是境外访问，走斯卡蕾特老师的服务器（这个服务器在境外，所以访问会快一些）；
- 访问yqzhaya.com时，如果是境内访问，走我的服务器。在网站调试时，为了保证同步正常，会临时调整为任意地区访问都走我的服务器。
- 访问yqzhaya.com的任意子域名，即xxx.yqzhaya.com时，一律走我的服务器。因为这些子域名网页需要调用我服务器上的数据，而斯卡蕾特老师的服务器到我的服务器已经有了特定文件路径的单向同步，lsyncd不支持再找一个新的文件路径反向同步回去。

## 1.7 crontab

这是一个可以指定特定周期或者特定时间后，周期性执行任务的程序。机器人程序通过设定crontab任务来实现直播数据的整理与重置。

## 1.8 pm2

当服务器与本地断开连接时，在终端中运行的python程序会被强制停止。为保证机器人程序24小时运行，需要使用pm2程序，其支持在本地与服务器断开连接时仍运行托管给pm2的程序。

pm2程序运行时，若修改托管给pm2的程序（机器人程序里就是python代码），pm2程序不受影响。但这同时也意味着如果原来的程序报错，就需要修改代码然后重启pm2程序。

pm2程序重启需要2-3秒的时间，因此若在直播时重启pm2程序，会导致短时间内的数据丢失。

推送姬的docker程序与机器人的pm2程序独立。

通过在crontab里设置pm2指令，即可自动实现每天特定时间的程序自动重启与缓存数据归零。

# 2 直播间机器人

## 2.1 代码文件功能概述

以下为与直播间机器人相关的，除main程序以外的python文件与脚本程序名称及其功能：

- bili_gift_map.py: 开播时在后台自动运行一次，用于生成开播时刻b站所有礼物的json文件。用于用户送出非send_gift形式的礼物（比如干杯之旅等大航海专属礼物）的时候查询礼物价值。
- birthday_cache_manage.py: 存储、写入、修改birthday.json（即当日已推送生日祝福的uid集合）的程序。
- box_bot.py: 盲盒姬函数集，包含特定种类或者所有种类的、特定时间或者所有时间的、特定用户或者所有用户的盲盒数据查询函数，以及一些为实现上述功能的辅助计算函数。
- constants.py: 存储其他代码中需要的一部分常量。
- data.py: 存储cookie值，包含SESSDATA, bili_jct, buvid3, buvid4, b_nut以及dedeuserid.
- eggs.py: 存储几乎所有彩蛋函数，包括盲盒、礼物、弹幕、大航海、SuperChat等事件发生即触发的彩蛋，以及一些和全局变量相关的彩蛋。
- get_data.py: 模拟登录b站从而获取或更新cookie值。
- gift_bot.py: 礼物姬函数集，包含特定用户或所有用户送出的礼物电池数的查询函数，以及总收入达到特定电池数后触发的“你看又⭕️”彩蛋，以及用户送出单价超过一定电池数的礼物后的礼物姬感谢程序。这里的“礼物”指包括普通礼物、盲盒、大航海、SuperChat等所有消费电池的行为。
- hotglobal.py: 存储、写入、修改runtime_state.json（即总推送次数与开播下播推送次数）的程序。
- hotreload_config.py: 允许热更新的函数与常量名集合。
- ids.py: 存储用户uid的程序，这些id大多数用在欢迎姬以及彩蛋中，但也有少部分（比如云崎早自己的uid）用于特殊判断程序中。
- json_handle.py: 用于程序启动时创建或加载json文件，以及保存或追加保存json文件。
- livetime.py: 存储、写入、修改livetime.json（即当月开播时长与开播天数）的程序。
- logger.py: 将程序输出添加一个时间戳并存储在日志文件中，从而便于在程序出错时判断错误原因。
- lunar.py: 判断当日是否为用户生日日期（公历或农历，以及农历闰月生日的处理）。
- mail.py: 发送邮件的程序。
- memory_store.py: 存储初始化常量，即程序启动时需要调用一次，后续不再调用的常量。
- send_reply.py: 发送弹幕的程序。
- transfer.py: 将部分直播数据转换为excel以及png格式，便于直观观察的程序。
- transfer.sh: 将直播数据的原始json文件加上直播日期字符，和转换后的excel与png一起归档。
- reset.sh: 删除直播过程中临时存储的json文件，从而重置机器人的所有数据。

main_v2.py为主程序，负责集成上述功能。

## 2.2 内存加载与数据存储

### 2.2.1 数据文件的创建

程序开始时，会通过json_handle.py，在files路径下创建一些全新的json数据文件，包括：

- all.json: 一个list，负责存储所有礼物信息，每一个单一的礼物作为一个字典存储在list中。字典中包含uid、用户名、时间戳、礼物名称以及礼物电池数信息。
- audience.json: 一个dict，负责存储所有进房观众的uid以及进房总观众数。
- gift.json: 一个dict，负责按用户整理所有的礼物信息。每个用户的子字典包括其uid、用户名、礼物字典（礼物名称以及电池数）以及总电池数。
- log.json: 日志保存路径。为防止服务器读取过高炸掉，设置只保存最近的100条日志，但所有日志仍可通过pm2的日志记录读取。
- meta.json: 存储直播标题、所有数值可变量（比如开播时间、总电池数、总弹幕数、“你看又⭕️”升档阈值及目前档位等），以及所有布尔值可变量。
- reset.json: 当reset.sh脚本运行时生成的数据充值日志文件，包含重置状态与重置时间。

此外，当直播间监听端口第一次发生部分事件时，会创建一些新json与jsonl文件，具体为：

- box.json: 一个dict，负责按用户整理所有的盲盒信息。每个用户的子字典包括其uid、用户名、盲盒总数、盲盒成本电池数、盲盒开出价值电池数，以及每种盲盒的数量、每种盲盒的成本与开出价值，以及是否触发个人亏损彩蛋的布尔值常量。
- danmu.jsonl: 存储本场直播中所有弹幕的uid、用户名、时间戳以及弹幕内容。
- superchat.jsonl: 存储本场直播中所有SuperChat的uid、用户名、时间戳以及SuperChat内容。
  
通过asynccontextmanager定期创建与更新的json文件：

- birthday_cache.json: 一个list，存储本个自然日已推送过生日祝福的所有uid.
- livetime.json: 一个dict，存储本月的开播时长与开播天数，以及二者的详细信息。
- runtime_state.json：一个dict，存储本个自然日的总推送次数（push_times）以及开播下播推送次数（push_live_times）。

以下为所有json及jsonl数据文件的大致结构：

- all.json，gift_price单位为电池，time为整数形式时间戳:

```python
[
    {
        "uid": xxx,
        "uname": "xxx",
        "time": xxx,
        "gift_name": "xxx",
        "gift_price": xxx
    }
]
```

- audience.json，interact_cache记录曾进入过直播间的用户uid:

```python
{
    "total_audience": xxx,
    "interact_cache": [
        xxx,
        xxx
    ]
}
```

- gift.json，其中gift_list记录礼物数量，profit单位为电池:

```python
{
    "uid": {
        "uid": xxx,
        "uname": "xxx",
        "gift_list": {
            "xxx": xxx,
            "xxx": xxx
        },
        "profit": xxx
    }
}
```

- box.json:

```python
{
    "uid": {
        "uid": xxx,
        "uname": "xxx",
        "count": xxx,
        "cost": xxx,
        "profit": xxx,
        "info": {
            "xxx": xxx,
            "xxx": xxx,
        },
        "cost_detail": {
            "xxx": xxx,
            "xxx": xxx,
        },
        "profit_detail": {
            "xxx": xxx,
            "xxx": xxx,
        },
        "is_personal_loss_egg_sent": false
    }
}
```

其中，cost为总消耗电池数，profit为总开出电池数，info为各类盲盒抽取数，cost_detail为各类盲盒各自的消耗电池数，profit_detail为各类盲盒各自开出的电池数, is_personal_loss_egg_sent为个人盲盒亏损彩蛋是否触发的控制变量。

- meta.json:

```python
{
    "title": "xxx",
    "live_time": xxx,
    "total_battery": xxx,
    "total_danmu_count_from_start": xxx,
    "next_threshold": xxx,
    "current_gear": xxx,
    "is_birthday_msg_sent": false
}
```

其中，title为直播标题，live_time为开播时间戳，total_battery为直播总电池数，total_danmu_cnt_from_start为直播总弹幕数。

next_threshold与current_gear为“你看又⭕️”这个彩蛋的下一阶段触发阈值与目前档位。类似于这两个key的、用于彩蛋的其他数字类型变量也存在meta.json中。

is_birthday_msg_sent为云崎早的生日彩蛋的控制变量。类似于is_birthday_msg_sent的、用于彩蛋的其他布尔类型变量也存在meta.json中。

- danmu.jsonl:

```python
{"uid": xxx, "uname": "xxx", "time": xxx, "danmu": xxx}
```

- superchat.jsonl:

```python
{"uid": xxx. "uname": "xxx", "time": xxx, "battery": xxx, "content": xxx}
```

当同一用户送出新的礼物，但修改了用户名时，gift_json以及box.json的用户名会被同步修改，同时其余json或jsonl文件新增的礼物数据中，用户名会按照新的名字来记录。

- birthday_cache.json:

```python
[xxx, xxx, xxx]
```

这就是一个简单的list结构。

- livetime.json，其中livetime单位为秒:

```python
{
    "month": "yymm",
    "livetime": xxx,
    "liveday": xxx,
    "exacttime": [
        "yyyymmdd hh:mm:ss - yyyymmdd hh:mm:ss",
        "yyyymmdd hh:mm:ss - yyyymmdd hh:mm:ss"
    ],
    "exactday": [
        "yyyymmdd", "yyyymmdd"
    ]
}
```

- runtime_state.json:

```python
{
    "date": "yyyy-mm-dd",
    "push_times": xxx,
    "push_live_times": xxx
}
```

### 2.2.2 内存加载与释放

内存加载遵循以下设定：

- 程序开始或重启时，读取上面所有的json文件到内存变量MEMORY；
- 若盲盒事件或SuperChat事件发生，直接写入json或jsonl文件，同时保存到内存变量。这样做的目的是保证盲盒数据可以立即被查询，以及云宝如果漏了SuperChat可以立即查询，不会出现数据遗漏；
- 若其余事件（比如普通礼物、弹幕、大航海等）发生，先写入内存中，每30s写入一次json或jsonl文件。这样做的目的是避免频繁写入，防止服务器因高频写入而崩溃；
- 若程序因pm2、sh脚本或者手动停止等原因停止，停止前会先将内存变量的所有值保存至json文件，避免数据丢失。

### 2.2.3 直播数据存储

直播数据存储的所有流程通过crontab自动周期性执行。

每天7:25，transfer.py会先将部分直播数据转换为excel和png，然后transfer.sh会把添加了日期名称的json原始数据文件以及excel和png文件统一转存至history_files文件夹中，从而实现数据存储。

如果下播时间晚于7:25，则需手动再次执行transfer.sh脚本程序，覆盖crontab自动存储的数据文件。

如果下播时间晚于8:59（且开播时间在8:59前），则需将两份不同的文件合并。具体原因可以看下一小部分。

### 2.2.4 数据文件的删除

每天8:59，为解决上文提到的8:59还未下播导致本来应该是一个json文件但被重置操作导致切分为了两份的情况，可以先执行transfer.sh，再执行reset.sh. reset.sh会重置服务器数据。具体为：删除files路径下的所有json和jsonl文件，并重启整个机器人程序。这样，json_handle.py会先在files创建初始json文件，之后内存读取这些初始json文件，所有的数据就处于了归零的状态。

为什么不设置成云崎早下播就整理并重置数据，而是一定要设置一个固定时间呢？因为云崎早可能会二次开播，会导致二次下播时第一次下播的数据被直接覆盖。

对于stable_json文件夹中的json文件，由于这些文件不在files文件夹内，因此不会随pm2重启而自动清除。

（为什么设置了8:59这样一个毫无规律的时间呢？是为了防止云崎早设置9点整的定时动态。程序重启需要2-3秒钟的时间，在这2-3秒内程序不会运行。如果设置成8点整，万一云崎早设置了9点定时发动态，由于9点这一瞬间程序没有运行，推送姬就不会监测到有新动态发送，也不会向群里推送消息了）

## 2.3 开播与下播

机器人程序有一个全局变量LIVE_STATUS，可以通过bilibili_api的get_room_info直接获取直播状态变量值。直播状态变量值：

- 0：未开播
- 1：开播
- 2：轮播（就是主播没开播，放几张图片或者几段视频来回播）

机器人程序中，当LIVE_STATUS不为1时，所有事件即使触发也不会被记录。也就是说，未开播状态下，机器人不会记录任何弹幕、礼物等信息。

但是，盲盒姬和礼物姬查询没有做这一层限制，意味着盲盒姬和礼物姬可以随时被呼叫。但正如前文提到的，数据会在每天8:59重置，因此只有在8:59前才能查询到数据。

bilibili_api监听端口LIVE是用来监听开播这一瞬间的。当云崎早开播时，LIVE会发送一个字典过来。机器人程序没有对这个字典进行处理，但是一旦接收到这个字典就意味着开播，此时设置LIVE_STATUS为1，通过调用live.LiveRoom即可获取直播间标题及封面，通过time库可以获取开播时间，然后把这些信息传入meta.json、内存以及推送姬程序。

在很偶尔的情况下，LIVE端口会漏掉开播的信息。为防止漏掉开播导致所有机器人程序都不会运行（前面说的LIVE_STATUS不为1时机器人不会工作），程序中做了每30s查询直播间状态的设置。如果查询结果为1但LIVE_STATUS为0，则强制将LIVE_STATUS设为1，同时将直播信息保存进meta.json与内存，但不发给推送姬（因为开播时间不一定准确）。

为防止云宝那边网络卡顿导致多次收到LIVE接口，程序中设定如果监听到LIVE接口信息时LIVE_STATUS为1，则自动忽略此次LIVE监听。但若是仅修改了直播标题，程序会先将新的标题存储进内存然后再忽略此次监听。

同理，如果监听到PREPARING接口信息时LIVE_STATUS不为1，则自动忽略此次PREPARING监听。

为什么不只依靠每30s查询一次开播状态，而一定要配合LIVE接口查询呢？因为开播信息要的就是实时性，推送姬在开播的那一瞬间就必须向群里推送消息，而不是等30秒钟再发。LIVE端口的优势就是开播的一瞬间就会接收到字典。

下播接口PREPARING同理，只不过推送姬的内容有所改变，同时调用mail.py给admin@yqzhaya.com发送一封含有开播下播时间、直播标题等信息的邮件作为备份。

## 2.4 盲盒姬

### 2.4.1 正则提取

通过设置正则表达式，可以在一段特定字符串中直接提取出指定的内容。在python中，可以通过re库实现。

正则提取会在下面的盲盒姬和礼物姬中用到。

### 2.4.2 盲盒信息提取

bilibili_api并没有提供盲盒的接口，而是要通过监听send_gift事件字典中data->data->blind_gift这个value是否为空来判断。若为空则为普通礼物，否则为盲盒。这意味着，盲盒礼物不需要通过礼物名称是否含有“盲盒”这两个字来判断。

### 2.4.3 盲盒姬信息正则提取

由于盲盒姬可以查询特定种类或者所有种类的盲盒，或者查询特定某个月的盲盒，或者把他们结合起来来查询，需要通过正则提取以及一些其他的字符串判断方式提取出用户的实际查询目的。具体为：

- 查询特定种类还是所有种类：使用正则表达式的?即可，?的作用是类型可输入可不输入，如果不输入，程序会走到查询所有盲盒的分支。
- 查询当天还是某个月的盲盒：使用?与|表达式可以在可输入可不输入的基础上，匹配用户输入的月份。如果不输入，程序会走到查询当天盲盒的分支。
- 是否指定查询特定用户：需要通过?正则判断字符串中是否含有@字符，以及通过$表达式判断这段文本是否位于字符串的结尾处。

当以上正则表达式能够匹配盲盒姬的预设指令时，如果查询的是当天的盲盒信息，程序会从files文件夹下的box.json文件来获取数据。如果查询的是月度盲盒信息，程序不仅会查询当天的box.json，还会去history_files文件夹，也就是已归档的数据中查询日期符合条件的盲盒数据。

考虑到用户输入例如“呼叫心动盲盒姬”与“呼叫心动盲盒盲盒姬”均为查询心动盲盒数据的意图，对正则提取与数据查询过程作以下处理：

1. 剔除输入盲盒名称结尾的所有“盲盒”字样；
2. 将剔除后的盲盒名称代入json数据中查询，这主要是为了查询那些不是以“盲盒”二字结尾的盲盒（例如七夕鹊匣）；
3. 如果没有查到任何盲盒信息，将盲盒名称后面添加上“盲盒”二字，再重新查询。若查询到盲盒信息，返回带有“盲盒”二字的盲盒名称，否则返回没有添加“盲盒”二字的盲盒名称。

也就是说：

```
呼叫心动盲盒姬          -> 心动         -> 心动（剔除后）       -> 查询名为“心动”的盲盒       -> 没有查到“心动”这个盲盒，查询“心动盲盒”这个盲盒   -> 返回“心动盲盒”这个盲盒名称以及盲盒数据
呼叫心动盲盒盲盒姬      -> 心动盲盒     -> 心动（剔除后）       -> 查询名为“心动”的盲盒        -> 没有查到“心动”这个盲盒，查询“心动盲盒”这个盲盒   -> 返回“心动盲盒”这个盲盒名称以及盲盒数据
呼叫心动盲盒盲盒盲盒姬  -> 心动盲盒盲盒  -> 心动（剔除后）      -> 查询名为“心动”的盲盒         -> 没有查到“心动”这个盲盒，查询“心动盲盒”这个盲盒   -> 返回“心动盲盒”这个盲盒名称以及盲盒数据
呼叫七夕鹊匣盲盒姬      -> 七夕鹊匣     -> 七夕鹊匣（剔除后）   -> 查询名为“七夕鹊匣”的盲盒     -> 返回“七夕鹊匣”这个盲盒名称以及盲盒数据
呼叫aaa盲盒盲盒姬       -> aaa盲盒      -> aaa（剔除后）        -> 查询名为“aaa”的盲盒        -> 没有查到“aaa”这个盲盒，查询“aaa盲盒”这个盲盒   -> 返回“aaa”这个盲盒名称以及空数据
```

## 2.5 礼物姬

### 2.5.1 批量与连击送出礼物的区别

- 批量：指用户一次在一瞬间送出很多礼物。通过send_gift事件可以直接获取礼物总数量。
- 连击：指用户在时限之内一个一个点然后送出礼物。这种情况下send_gift事件会多次接收到信息。实际上，在连击结束以后，还有一个combo_send端口会有汇总信息，但带上combo_send会导致程序过于复杂，因此没有使用。

### 2.5.2 礼物姬数据查询

礼物姬数据查询逻辑与盲盒姬基本一致，只不过数据来源从box.json变成了gift.json.

此外，礼物姬没有做月度查询功能，也没有做总电池数查询，因为云宝不想公开流水，也因为正则匹配的整个流程过于复杂，我也不太想做。

### 2.5.3 “你看又⭕️”彩蛋

虽然云宝不想公开流水，但是我还是做了“你看又⭕️”这个彩蛋。这个彩蛋有档位，也就是后面的"x2, x3"这些东西。

为了保证云宝的流水不会被准确算出来，我对档位阈值加了随机值调整。在生日回、周年庆等可以预测流水较高的日期，需要手动调高阈值，从而避免这个彩蛋刷屏。

### 2.5.4 感谢礼物

当用户送出单价大于1000电池的礼物时（这里的“礼物”指任意花费电池的行为），礼物姬会通过预设的文本内容进行感谢。

注：大航海盲盒是一种较为特殊的礼物，因为被算作大航海而不是盲盒。程序中花了大量篇幅对大航海盲盒进行特殊判断，使其被大航海接口接收以后，不执行大航海接口的程序，而是假装自己是一个盲盒，走盲盒的程序。

### 2.5.5 不同类型的礼物数据处理

1. SuperChat

根据super_chat_msg接口返回的信息，提取出uid、用户名、SuperChat价值以及内容。

将类似于all.json格式的json信息追加存储进MEMORY["all"]，等待自动保存至all.json. 

将类似于gift.json格式的json信息追加存储进MEMORY["gift"]，等待自动保存至gift.json, gift_name记为"SuperChat". 若原用户已存在，则进行礼物是否重复的判断以及profit叠加。

将类似于superchat.jsonl格式的jsonl信息追加存储至superchat.jsonl:

此外，修改MEMORY["meta"]中total_battery的值，并进行彩蛋判断。

注：受网络波动影响，部分SuperChat会被接口二次发送。为避免这一情况，程序中设定所有参数与superchat.jsonl中某个SuperChat完全一致的SuperChat会被自动忽略。

2. 大航海（除大航海盲盒）

大航海数量处理：

由于大航海接口user_toast_msg只会返回大航海类型以及大航海总电池数，无法判断同时送出了几个大航海，因此需要对大航海数量进行处理。具体算法如下：

- 默认舰长、提督、总督单价为1680、15980、159980电池。
- 先用总电池数除以默认电池数，会得到一个余数。将余数与GUARD_FIRST_PRICE这个字典匹配。

```python
GUARD_FIRST_PRICE = {
    "舰长": {0: 1680, 1380: 1380, 300: 1980},
    "大航海": {0: 1680, 1380: 1380, 300: 1980},
    "提督": {0: 15980, 4000: 19980},
    "总督": {0: 159980, 40000: 199980},
}
```

- 若余数落在字典的key当中，则可认为第一个月的大航海金额不同，其余月份的大航海正常计算。例如，用户上了n个月的舰长，总计5340电池。由于5340对1680求余为300，与舰长中300的key匹配，则可认为用户第一个月舰长为1980电池，剩余两个月为1680电池，即n=3.
- 若余数不落在字典的key当中，则直接根据默认单价计算理论大航海数量，采用四舍五入计入数量。单价按照总价值处于计算出来的数量计入。

这种算法能够实现的条件是大航海盲盒以及非标准价值的大航海（例如舰长红包）一次只能送出1个。若可以连续送出多个，这种算法不成立。

大航海数据保存：

与上文同理，将礼物信息加载进MEMORY["all"], MEMORY["gift"]，等待自动保存至all.json以及gift.json. 此外，修改MEMORY["meta"]中total_battery的值，并进行彩蛋判断。

若为大航海盲盒，则将类似于box.json格式的json信息追加存储进box.json.

3. 普通礼物（除盲盒）

与上文同理，将礼物信息加载进MEMORY["all"], MEMORY["gift"]，等待自动保存至all.json以及gift.json. 此外，修改MEMORY["meta"]中total_battery的值，并进行彩蛋判断。

4. 盲盒

与上文同理，将礼物信息加载进MEMORY["all"], MEMORY["gift"]，等待自动保存至all.json以及gift.json. 此外，修改MEMORY["meta"]中total_battery的值，并进行彩蛋判断。

此外，将类似于box.json格式的json信息追加存储进box.json.

5. 其他

有些类型的礼物会通过特殊弹幕形式显示，例如大航海专属礼物“干杯之旅”。对于这类走common_notice_danmaku而不是send_gift接口的礼物，需要通过bili_gift_map.json查询礼物价值并记录在gift.json及内存中。

获取到礼物信息与礼物价值后，与上文同理，将礼物信息加载进MEMORY["all"], MEMORY["gift"]，等待自动保存至all.json以及gift.json. 此外，修改MEMORY["meta"]中total_battery的值，并进行彩蛋判断。

如果无法通过bili_gift_map.json查询到，则将错误时间与错误信息录入至error_log.txt中，后续手动添加（或热更新）至礼物数据中。

## 2.6 欢迎姬

### 2.6.1 用户进入直播间时

当观众进入直播间时，不管是不是第一次进入直播间，interact_word_v2与entry_effect事件都会触发（其实是有概率触发，websocket底层未必会发送信息）。观众第一次进入直播间时，会在audience.json文件中添加观众uid，后续再次进房时会在audience.json里对uid进行校验，如果已经进入过直播间，则不会执行欢迎程序（云崎早本人除外）。

为防止欢迎姬刷屏，设置了佩戴“早崎鸭”粉丝团灯牌且灯牌等级大于等于31级、或者通过entry_effect的guard_level检测到为总督或提督（即1或2）才能走到后续的判断逻辑。

如果用户是先被interact_word_v2接口识别到，则设置guard_level为0，即无大航海信息。

欢迎姬支持欢迎词定制，拥有定制欢迎词的用户不受31级粉丝牌的限制。欢迎词的归属人以及欢迎词内容被存在constants.py的WELCOME_MAP字典中。

也有一些用户满足了粉丝团灯牌的条件但是不想要欢迎姬的欢迎。针对这种情况，设置了REFUSE_WELCOME_LIST，处于这个list里面的uid在欢迎姬程序中会直接跳出，不会进行任何欢迎。

由于interact_word_v2与entry_effect事件都有概率触发，因此设计了一个带有异步锁的函数，内含欢迎姬、生日祝福等逻辑的处理。但即使是这样，也无法保证用户进入直播间时有100%的概率被识别到，但这是bilibili_api中websocket的缺陷，无法靠这两个接口来解决。

### 2.6.2 用户生日字典设计

程序中，手动录入的生日信息birthday_raw通过程序处理后，生成用户生日字典BIRTHDAY_MAP. 

BIRTHDAY_MAP的结构如下：

```python
{
    uid: [mmdd, msg, is_moon, night_agree, only_leap],
    uid: [mmdd, msg, is_moon, night_agree, only_leap]
}
```

列表内元素含义（即lunar.py与main_v2.py中的处理逻辑）：

- mmdd：字符串格式，通常为"mmdd"形式，用来存储用户生日月份与日期。以"-mmdd"形式存储时，表示农历闰月生日。
- msg：字符串格式，用来存储用户自定义的生日祝福内容；
- is_moon：0或1，是否为农历生日；
- night_agree：0或1，生日消息推送模式。1代表0:00时若云宝在播，则立即推送；0代表暂不推送，等到当天晚上再推送；
- only_leap: 0或1，仅在mmdd中录入的是农历闰月生日时才生效，决定对于农历闰月生日的用户，在平年时是否过平月生日，为1则不过，为0则为过。

列表内元素初始值：

- msg: "\[欢迎姬\]今天是{uname}老师的生日，让我们祝ta生日快乐！"，后续用format(uname)处理用户名；
- is_moon: 0
- night_agree: 1
- only_leap: 1

birthday_raw支持的数据录入类型：

```python
{
    uid: "xxx",
    uid: ("xxx", "xxx", xxx),
    uid: {"mmdd": "xxx", "is_moon": xxx}
}
```

此外，还支持用list包裹的以上各种录入类型的组合。也就是说，可以支持同一个人录入多个生日。

程序中，对于birthday_raw的不同录入数据类型，处理方案如下：

- 仅录入字符串：字符串为生日日期信息，其余值为默认值；
- 录入元组：对元组解包，按顺序对应list中的元素，其余值为默认值；
- 录入字典：对字典解包，按key名称对应list中的元素，其余值为默认值；
- 录入列表：先通过for循环拆解列表，再按照上面的数据处理方法处理。

由此，得到闰年闰月出生的用户的数据录入方式：

- 只过闰月：uid: {"mmdd": "-xxxx", "is_moon": 1}
- 平年平月和闰年闰月：uid: {"mmdd": "-xxxx", "is_moon": 1, "only_leap": 0}
- 平年平月和闰年平月：uid: {"mmdd": "xxx", "is_moon": 1}

### 2.6.3 用户过生日时

同样使用interact_word_v2以及entry_effect接口，当观众进入直播间时，通过BIRTHDAY_MAP判断用户是否符合发送条件。若符合条件，则发送对应的生日祝福文本。

事件触发后，将用户uid存入stable_json/birthday_cache.json中。后续用户再次进房时会在birthday_cache.json里对uid进行校验，如果已经进入过直播间，则不会执行生日祝福程序。

birthday_cache会在每天0:00自动清空。由于其为独立的json文件，其内容不会受到每天8:59程序重启的影响。

## 2.7 彩蛋设置

彩蛋的触发条件被限制在特定事件触发时进行额外条件判断。例如，当任意一个人送出礼物时，判断这个人与预设的uid是否符合、时间段是否在彩蛋允许的事件内、礼物名称是否符合预设的礼物名称等等。如果事件符合彩蛋的预设条件，则程序会自动发送彩蛋弹幕。

此外，meta.json或者其他文件中的一些数据发生变动或者超过或低于阈值时，也会触发彩蛋。例如全局盲盒盈亏彩蛋以及个人盲盒亏损彩蛋。

由于彩蛋多种多样，这里没有办法具体写出每个彩蛋的工作原理。具体的彩蛋设置可以看eggs.py.

此外，由于用户会有在直播时添加或者修改彩蛋的需求，而程序不能在直播时重启，因此彩蛋需要支持代码热更新。这部分会在后面热更新里面具体说明。

## 2.8 热更新与热删除

### 2.8.1 普通礼物与盲盒热更新与热删除基本原理

以FastAPI接口为跳板，通过手动触发FastAPI接口从而让FastAPI执行预设的将礼物信息添加进内存的程序（前面FastAPI部分提到过）。

此外，通过在bashrc文件中添加函数，可以自定义向服务器发送热更新、热删除以及热发送弹幕的指令。

### 2.8.2 普通礼物与盲盒的热更新

执行FastAPI预设的函数以后，会向内存中写入想要添加的普通礼物的用户uid、用户名、礼物名称、礼物价值、礼物数量以及时间戳信息。如果录入的是盲盒，则还需要盲盒的更多key和value值，这些值在前面盲盒姬的部分都提到过。

目前只支持录入普通礼物、盲盒以及大航海，还不支持录入SuperChat. 或者说，SuperChat可以录入，但是没有办法录入SuperChat内容这种极其详细的信息，需要后续手动录入。

此外，录入至内存以后，meta.json中总电池数会发生改变，因此需同步判断“你看又⭕️”彩蛋的档位是否会增加。但无论档位是否增加，该彩蛋都不会触发，也就是不会主动发送“你看又⭕️”的弹幕。

### 2.8.3 普通礼物与盲盒的热删除

与热更新同理，执行FastAPI的预设函数删除内存中第一个与输入信息匹配的礼物信息，等待后续内存同步至json文件即可。

热删除时“你看又⭕️”彩蛋的档位判断逻辑：

- 若总电池数小于0则设为0；
- 前文提到，该彩蛋阈值为随机值。取随机范围的最小值，乘以当前档位，作为当前档位的最低理论电池数量。如果扣减后的总电池数量低于该阈值，则档位减1，然后再循环计算；
- 每次降档时，触发下一档位所需的电池阈值会随机回退随机范围内的一个值。

### 2.8.4 热发送弹幕

与热更新同理，只需传入send_danmaku所需参数即可。弹幕将以cookie所属人的身份发送。

### 2.8.5 代码热更新原理

（这部分会比较难，涉及到代码底层的东西）

在每30s一次的轮询中，通过os.path.getmtime，可以查询写在hotreload_config.py中的函数是否有过修改。

如果函数有过修改，通过python中的importlib.reload函数重新加载对应的python文件，并通过getattr重新写入全局命名空间，从而实现代码的热更新。

如果是常量的热更新，还需要遍历sys.modules来强制更新所有加载常量的模块。

前面提到的彩蛋热更新，就是热更新了gift_bot.py以及eggs.py中的一部分函数。

## 2.9 网页数据同步

电池计数器网页会实时同步直播的每个人的电池信息与礼物详情，并按照总电池数倒序排列，便于云宝下播时感谢礼物。同步通过FastAPI同步gift.json文件实现。

SuperChat记录姬网页会实时同步直播的SuperChat电池数与内容，并按照时间戳倒序排列，便于云宝漏掉SuperChat时快速查询。同步通过FastAPI同步superchat.jsonl文件实现。

# 3 推送姬

## 3.1 opus动态接口

哔哩哔哩opus接口，也就是动态接口中，单条动态（item）的大致格式如下：

```
item -> id_str # 动态id
     -> type # dynamic动态类型
     -> basic -> link
     -> modules -> module_dynamic -> major -> type # major动态类型
                                           -> opus -> pics
                                                   -> title
                                                   -> summary -> text
                                                   -> jump_url ->
                                           -> archive -> title
                                                      -> desc
                                                      -> cover
                                                      -> jump_url
                                           -> article -> title
                                                      -> desc
                                                      -> cover
                                                      -> jump_url
                                           -> ...
                                  -> desc -> text # 转发者的评语
                                  -> topic
     -> orig -> images
             -> cover
             -> text
             -> title
             -> modules -> module_author -> name
                        -> module_dynamic -> major -> ...
```

其中orig表示转发动态的原动态。

major动态类型与dynamic动态类型的命名方式有所不同，这主要是因为opus接口经历了好多次迭代，导致里面的接口名称很混乱，但dynamic会把动态类型分的比较细。所以，程序选择在获取动态内容的时候走major，而在获取动态类型的时候走dynamic.

major的类型包括但不限于：

- MAJOR_TYPE_OPUS：图文动态
- MAJOR_TYPE_ARCHIVE：视频动态
- MAJOR_TYPE_ARTICLE：专栏
- MAJOR_TYPE_MUSIC：音频动态

dynamic的类型包括但不限于：

- DYNAMIC_TYPE_FORWARD：转发动态
- DYNAMIC_TYPE_DRAW：图文动态
- DYNAMIC_TYPE_WORD：纯文本动态
- DYNAMIC_TYPE_AV：视频动态
- DYNAMIC_TYPE_SHORT：小视频动态
- DYNAMIC_TYPE_MUSIC：音频动态
- DYNAMIC_TYPE_ARTICLE：专栏

## 3.2 动态获取

通过带cookie访问动态api地址https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid=3493074573461871 ，api会返回一个字典，这个字典的data->items为一个列表，其中每一个元素（都是字典）就是一条动态信息。

通过提取动态字典的id_str，就可以获取到能看到的所有动态的动态ID. 需要注意的是，由于b站的翻页机制，程序只能获取到最靠前的十几条动态，且如果有置顶动态，置顶动态则永远为第一条。

哔哩哔哩的动态发送的越晚，其ID值越大。因此，在每30s的轮询中，若ID list中出现了ID较大且不在上一轮查询中的动态ID，也就找到了新发布的动态，对新发布的动态进行解析即可。

在30s轮询中若发送多条动态，根据实测推送姬若同时向两个群发送多条动态会导致推送姬账号直接被踢下线，因此每条动态通过asyncio.sleep(3)间隔3s再发送。

## 3.3 消息的组装

qq_bot.py为推送姬程序。由于NapCat允许将文本与图片混合发送，因此可先将需要发送的文本与图片内容逐个排列好，再直接交给NapCat推送。

程序中设定变量segments为承载所有消息块的列表。segments这个列表的元素有以下几种形式：

- 文本：

```python
{"type": "text", "data": {"text": "xxx"}}
```

- 图片：

```python
{"type": "image", "data": {"file": "xxx"}}
```

- @全体成员：

```python
{"type": "at", "data": {"qq": "all"}}
```

通过预设好的各种动态类型以及开播下播的模板，对每个segments片段按照顺序进行拼接。

对于图片形式的segments片段，由于图片以url形式推送至代码中，为了防止推送姬因为下载图片导致产生很大的推送延迟，需要先在服务器中把图片下载下来，再将图片替换为base64格式的字节串，再转为UTF-8格式的字符串存入image的字典当中。

所有segments片段通过追加模式写入segments这个list当中。其中，@全体成员的片段会直接插入到segments的最前端，即segments[0].

为防止动态内图片过多导致刷屏，推送姬设置了仅保留并发送第一张图片。

为防止转发动态过长导致刷屏，转发动态的原动态限制字符长度为250个字符，若超出则用“...”来代替。

## 3.4 消息的发送

将拼接好的segments与群号拼接成一个字典：

```python
payload = {
    "group_id": gid,
    "message": list(processed_segments)
}
```

向服务器上的NapCat API节点发起http post请求，其中，payload以json格式传入，从而实现消息的推送。

受到http阻塞影响，目前http post采用异步并发的形式发送，即两个群通过asyncio.gather的方式完全同步推送。

## 3.5 紧急停止

设置可通过FastAPI热更新的常量PUSH_STATUS，用于控制推送姬是否会以@全体成员形式推送消息。若PUSH_STATUS=0，则不会@全体成员，但仍会正常推送。

考虑到云宝可能由于反复开播下播导致推送姬在群里刷屏，以及推送姬账号一天只能@10次全体成员，因此程序设置了一个在开播与下播时自动更新的json文件runtime_state.json，用来控制推送姬是否以@全体成员的形式推送消息。

runtime_state的结构为：

```python
{
    "date": "xxx",
    "push_times": xxx,
    "push_live_times": xxx
}
```

push_times表示当天已经推送过的消息数，push_live_times表示当天已经推送过的开播与下播消息次数（动态推送不计入），其会在每天0:00时自动归零，由于是json文件，因此不受每天8:59程序重启的影响。

考虑到直播间网络卡顿会导致反复开播下播，以及可能某天有很多动态消息导致推送姬@全体成员次数超出上限，在以下情况下推送姬不会@全体成员，但仍会正常推送：

1. 自然日内已推送次数大于9，且本次推送为非开播推送；
2. 自然日内已推送次数大于10；
3. 自然日内开播与下播推送次数大于6.

算法代码如下（if内增加PUSH_TIMES与PUSH_LIVE_TIMES的值）：

- 对于LIVE事件：

```python
if hotglobal.PUSH_STATUS == 1 and ((hotglobal.PUSH_LIVE_TIMES <= 5 and hotglobal.PUSH_TIMES <= 8) or hotglobal.PUSH_TIMES == 9):
    ...
```

- 对于PREPARING事件：

```python
if hotglobal.PUSH_STATUS == 1 and hotglobal.PUSH_LIVE_TIMES <= 5 and hotglobal.PUSH_TIMES <= 8:
    ...
```

- 对于动态事件：

```python
if hotglobal.PUSH_STATUS == 1 and hotglobal.PUSH_TIMES <= 8:
    ...
```

# 4 代码仍存在的不足

1. 文件部署在root文件夹下，导致nginx同步时权限不足，需要逐一给网页需要获取的文件写权限；
2. 每天8:59之后，即使盲盒姬与礼物姬仍可以查询数据，但由于数据源已经归档，因此查询不到数据；
3. 盲盒姬设置了盲盒查询名单，这样做的好处是用户误输入盲盒名称，或者输入不存在的盲盒名称时，盲盒姬不会回复。但缺点是，每当有新盲盒出现时，都需要手动向盲盒查询名单中添加盲盒的映射关系。后续考虑当用户送出不存在于名单中的盲盒时，自动向名单中热更新新盲盒映射；
4. 受http阻塞影响，目前推送姬只能采用异步并发，但这样做较容易风控。

# 5 附加信息

## 5.1 未提及的内容

1. 全局变量STATUS: 这是卡米自己给自己设定的一个特殊变量，可以通过FastAPI传到电池计数器上，作为卡米是否睡觉的提示，或者作为彩蛋使用。
2. 电池计数器以及SuperChat记录姬的html文件、yqzhaya.com的html、css以及js文件。

## 5.2 在github上隐藏的文件的大致结构：

- data.py:

```python
SESSDATA = "xxx"
BILI_JCT = "xxx"
BUVID3 = "xxx"
BUVID4 = "xxx"
B_NUT = "xxx"
DEDEUSERID = "xxx"
UPDATE_TIME = "xxx"
```

- ids.py: 与data.py结构类似，记录不同用户的uid，以及一些具备共同特征的用户uid组成的list

- memory_store.py（MEMORY常量中，meta还包含其他彩蛋的控制变量。此外，MEMORY外部也包括少量的彩蛋控制变量）:

```python
import asyncio
from data import SESSDATA, BILI_JCT, BUVID3, BUVID4, DEDEUSERID
from bilibili_api import Credential, select_client
from ids import *
from constants import *

qq = None

select_client("aiohttp")

MEMORY = {
    "box": {},
    "gift": {},
    "all": [],
    "danmu": [],
    "meta": {
        "title": "",
        "live_time": 0,
        "total_battery": 0,
        "total_danmu_cnt_from_start": 0,
        "next_threshold": 4000,
        "current_gear": 0,
        "is_birthday_msg_sent": False,
    },
    "audience": {
        "interact_cache": []
    }
}

processed_records = []
processed_sc_records = []
last_query_time = {}
last_save_time = 0
last_log_save = 0
interact_cache = set()

reply_queue = asyncio.Queue()

credential = Credential(
    sessdata=SESSDATA,
    bili_jct=BILI_JCT,
    buvid3=BUVID3,
    buvid4=BUVID4,
    dedeuserid=DEDEUSERID
)

```

- constants.py:

```python
from ids import *
import random

CHECK_INTERVAL = 60

DANMU_COUNT = random.randint(30, 60)

ROOM_ID = 27885573
NAPCAT_API = "xxx"
TARGET_GROUP_LIST = ["xxx", "xxx"]
NAPCAT_TOKEN = "xxx"
TOKEN = "xxx"

email_password = "xxx"

WELCOME_MAP = {
    xxx: "xxx",
    xxx: "xxx",
}

REFUSE_WELCOME_LIST = [xxx, xxx]

COMBO_GUARD_PRICE = {
    "舰长": 1680,
    "提督": 15980,
    "总督": 159980,
    "大航海": 1680
}

GUARD_FIRST_PRICE = {
    "舰长": {0: 1680, 1380: 1380, 300: 1980},
    "大航海": {0: 1680, 1380: 1380, 300: 1980},
    "提督": {0: 15980, 4000: 19980},
    "总督": {0: 159980, 40000: 199980},
}

CN_MONTHS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12
}

BOX_MEMORY_MAP = {
    "xxx": "xxx盲盒",
    "xxx": "xxx盲盒"
}

BOX_NAME_LIST = ["xxx", "xxx"]
```

# 6 更新日志

注：更新日志与readme的更新时间不一定完全相同（因为写技术文档时间比较长，如果忙的话可能会过些天才写）。

**2026.8.29**

1. 更新推送姬若有大于1条待推送动态时的延迟3s推送机制；
2. 更新盲盒姬的正则判断与盲盒名称处理逻辑；
3. 对于用户进入直播间的监听程序，现在共用INTERACT_WORD_V2与ENTRY_EFFECT两个接口来监听，并设置异步锁防止二次执行。

**2026.8.21**

1. 明确FastAPI跳板机制与生命进程的基本原理；
2. 修改PUSH_STATUS逻辑为是否@全体成员；
3. runtime_state.json现在需考虑已推送总次数与已推送开播下播次数两个维度（原来只考虑第二个）；
4. 更新推送姬@全体成员的处理逻辑，以及@次数已满时不会@全体成员的处理逻辑（v2026.08.21）。

**2026.8.20**

1. 增加欢迎姬生日祝福的逻辑；
2. 更新推送姬@全体成员的处理逻辑（v2026.08.20）。

**2026.8.17**

1. 明确gift.json与box.json中当用户名发生改变时的处理逻辑，即该用户有礼物事件时检测用户名与之前的用户名是否一致。

**2026.8.16**

1. 增加收到LIVE与PREPARING信息，LIVE_STATUS变化后，自动忽略二次收到的LIVE与PREPARING且不改变LIVE_STATUS的信息的处理逻辑；
2. 增加一个通过PUSH_STATUS常量控制推送姬是否推送的逻辑，该常量通过FastAPI修改常量值；
3. 明确推送姬组装消息的segments片段格式，以及向segments列表追加写入的处理逻辑。

**2026.8.15**

创建技术文档，内容包含readme的更新日志中2026.8.15之前的所有部分。