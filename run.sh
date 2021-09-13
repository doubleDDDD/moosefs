#!/bin/bash

# 跑在真实的存储节点上
master="172.20.0.3"
chunk1="172.20.0.4"
chunk2="172.20.0.5"
chunk3="172.20.0.6"

masters=($master)
chunks=($chunk1 $chunk2 $chunk3)

nohup mfsmaster kill > /dev/null 2>&1 &
nohup mfschunkserver kill > /dev/null 2>&1 &

master=false
chunk=false

# =~ 判断字符串的包含关系，右边是左边的子串
selfips=`ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{print $2}'|tr -d "addr:"​`
for selfip in $selfips; do
    if [[ "${masters[@]}" =~ "$selfip" ]];then
        master=true
    fi
done

for selfip in $selfips; do
    if [[ "${chunks[@]}" =~ "$selfip" ]];then
        chunk=true
    fi
done

# echo $master
# echo $chunk

if [ $master = true ];then
    mfsmaster start
    echo "master start"
fi

if [ $chunk = true ];then
    mfschunkserver start
    echo "chunk start"
fi

exit 0