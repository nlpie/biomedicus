#!/usr/bin/env bash

exec 3< <(biomedicus deploy --config biomedicus_deploy_config.yml)
sed '/Done deploying all servers.$/q' <&3 ; cat <&3 &

biomedicus run /input --watch -o /output --config biomedicus_default_pipeline.yml
