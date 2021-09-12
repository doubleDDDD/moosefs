#!/bin/bash

# 跑在真实的存储节点上
master="172.20.0.3"
chunk1="172.20.0.4"
chunk2="172.20.0.5"
chunk3="172.20.0.6"

mfsmaster stop
mfschunkserver stop