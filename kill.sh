#!/bin/bash

# 跑在真实的存储节点上
master="172.20.0.3"
chunk1="172.20.0.4"
chunk2="172.20.0.5"
chunk3="172.20.0.6"

# 懒得区分了，直接GG
mfsmaster stop
mfschunkserver stop