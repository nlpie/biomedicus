#!/bin/bash

b9 deploy --rtf --host 0.0.0.0 > services.log &
tail -f -n0 services.log | grep -qe "Done deploying all servers."

b9 serve-pipeline --rtf --include-label-text -p 55000 > serve-pipeline.log &
MTAP_CONFIG=gateway.yml mtap-gateway -v=3 -logtostderr
