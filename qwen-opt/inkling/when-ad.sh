#!/bin/bash
for i in $(seq 240); do grep -q "done AD" ~/models/inkling/dl.log && exec ~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/inkling/base-ad.jobs; sleep 60; done
