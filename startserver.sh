#!/bin/bash
node0ip="172.20.0.3"
node1ip="172.20.0.4"
node2ip="172.20.0.5"
node3ip="172.20.0.6"

port0=22222
port1=22223
port2=22224
port3=22225
ports=($port0 $port1 $port2 $port3)

# mac
devnodeip1="172.17.0.2"
devnodeip2="172.20.0.2"
# wsl
devnodeip3="192.168.50.16"

targetiplist=($node0ip $node1ip $node2ip $node3ip)
devips=($devnodeip1 $devnodeip2 $devnodeip3)
devipsmac=($devnodeip1 $devnodeip2)
# 区分一下是自己的mac还是其他
mac=true

selfips=`ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{print $2}'|tr -d "addr:"​`
for selfip in $selfips; do
    if [[ "${targetiplist[@]}" =~ "$selfip" ]];then
        echo "$selfip has no need to run!"
        exit 1
    fi
done

for _selfip in $selfips; do
    if [[ "${devipsmac[@]}" =~ "$_selfip" ]];then
        mac=true
    else
        mac=false
    fi
done

if [ $mac = true ];then
    # mac
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
else
    # wsl
    for port in ${ports[@]}; do
        ssh root@localhost -p $port "cd /root/double_D/moosefs/moosefs && ./run.sh"
    done
fi