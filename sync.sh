#!/bin/bash

# 在所有节点中同步minio工程的代码，可以用github作跳板，就是不想每次都要在所有节点手动都操作一次
# node节点的IP都是固定的
node0ip="172.20.0.3"
node1ip="172.20.0.4"
node2ip="172.20.0.5"
node3ip="172.20.0.6"

# 跑这个脚本的应该只有一个node
devnodeip1="172.17.0.2"
devnodeip2="172.20.0.2"

# minio应该在的ip
targetiplist=($node0ip $node1ip $node2ip $node3ip)
devips=($devnodeip1 $devnodeip2)

# 得到自己的ip
# grep -v 选择不匹配的项
selfips=`ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{print $2}'|tr -d "addr:"​`
# echo $selfips
# selfips="172.17.0.3 172.20.0.3"
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

# rsync -avH --delete /root/moosefs root@172.20.0.3/4/5/6:/root/double_D/moosefs/moosefs
src=/root/moosefs
dst=/root/double_D/moosefs/moosefs
for ip in ${targetiplist[@]}; do
    rsync -avH --delete $src root@$ip:$dst
done

exit 0