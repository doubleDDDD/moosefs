#!/bin/bash

# 跑在真实的存储节点上
master="172.20.0.3"
chunk1="172.20.0.4"
chunk2="172.20.0.5"
chunk3="172.20.0.6"

chunks=($chunk1 $chunk2 $chunk3)

mfsmaster stop
mfschunkserver stop

selfips=`ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{print $2}'|tr -d "addr:"​`
for selfip in $selfips; do
    if [[ ! "${devips[@]}" =~ "$selfip" ]];then
        echo "$selfip has no need to run!"
        exit 1
    fi
done