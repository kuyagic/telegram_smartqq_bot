### Telegram SmartQQ Bot

#####本bot 依赖于 [MojoWebQQ](https://github.com/sjdy521/Mojo-Webqq) 项目

#### 数据流程
telegram_user <-> this_bot <--http server--> MojoWebQQ <--> QQ
####实现方式
Telegram 接收命令, 发送到 MojoWebQQ提供的API实现发送QQ消息

本程序监听的本地端口提供web 服务, MojoWebQQ收到消息后会主动推送到 本程序的接口.然后经过Bot 处理后 发送给用户实现 收取QQ消息
#### 文件说明

- misc/monit.bot.conf
	- 提供持久化程序监控和运行.需要修改对应监听端口
- misc/nginx.proxy_pass.conf
	- 提供本地服务的反向代理 实现 Telegram的 `Webhook` 方式的 bot
- misc/start_smartqq_api.pl
	- 启动MojoWebQQ的后台程序,并提供API

####如何开始

1. 首先按照 [隔壁](https://github.com/sjdy521/Mojo-Webqq) 的说明 安装 MojoWebQQ
2. 复制 `config.sample.json` 为 `config.json`
3. 根据需要修改 `env.json` 和 `config.json` 配置文件内都有项目说明
4. 在 程序目录 执行 `pip3 install -r requirements.txt` 安装依赖
5. 安装系统依赖 `monit` 并修改 monit.bot.conf 文件内的 程序目录. 然后 复制到 `monit` 的配置文件夹下 然后启动 `monit`
6. 最后 用 `netstat -ntpl` 检查是否运行正常
