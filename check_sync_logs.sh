#!/bin/bash
pm2 logs facepass-api --lines 100 --nostream > /tmp/pm2_logs.txt 2>&1
grep "!!!" /tmp/pm2_logs.txt | tail -n 20
echo "---"
grep "SYNC" /tmp/pm2_logs.txt | tail -n 20
