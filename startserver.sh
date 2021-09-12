#!/bin/bash
node0ip="172.20.0.3"
node1ip="172.20.0.4"
node2ip="172.20.0.5"
node3ip="172.20.0.6"

devnodeip1="172.17.0.2"
devnodeip2="172.20.0.2"

targetiplist=($node0ip $node1ip $node2ip $node3ip)
devips=($devnodeip1 $devnodeip2)

selfips=`ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{print $2}'|tr -d "addr:"​`
for selfip in $selfips; do
    if [[ ! "${devips[@]}" =~ "$selfip" ]];then
        echo "$selfip has no need to run!"
        exit 1
    fi
done

for ip in ${targetiplist[@]}; do
    if ping -c 1 $ip > /dev/null; then
        echo "$ip is ok"  # 双引号中变量是可以被解析的
    else
        echo "$ip is GG, exit!"
        exit 1
    fi
done

for ip in ${targetiplist[@]}; do
    ssh root@$ip "cd /root/double_D/moosefs/moosefs && ./run.sh"
done