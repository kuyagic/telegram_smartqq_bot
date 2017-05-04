#!/usr/bin/env perl
use Mojo::Webqq;
my ($host,$port,$post_api);

# 这里的配置对应 config.sample.json 里的 mojo_qq_api_base 项目.用于 telegram -> qq 的消息发送
$host = "127.0.0.1"; #发送消息接口监听地址，没有特殊需要请不要修改
$port = 10000;      #发送消息接口监听端口，修改为自己希望监听的端口

# 接收到的消息上报接口，如果不需要接收消息上报，可以删除或注释此行
# 这里是 bot 本地 Flask 监听端口和路径.
# 在 env.json 和 start.py 里配置
$post_api = 'http://127.0.0.1:5003/qq/';

my $client = Mojo::Webqq->new();
$client->load("ShowMsg");
$client->load("Openqq",data=>{listen=>[{host=>$host,port=>$port}], post_api=>$post_api});
$client->run();