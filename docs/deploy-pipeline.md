---
layout: default
title: End-to-end REST Pipeline
nav_order: 6
---

## About

This guide will illustrate how to host the entire BioMedICUS pipeline as a RESTful service.

## Pre-requisites

You will need to have [installed biomedicus](installation).
You will need the MTAP API gateway, available as a binary from the [MTAP releases page](https://github.com/nlpie/mtap/releases) or installable using the command: ``go install github.com/nlpie/mtap/go/mtap-gateway/mtap-gateway.go``.
This tutorial also uses the [jq utility](https://jqlang.github.io/jq/) to format json.

## Deploying and using the pipeline

First deploy the BioMedICUS default pipeline:

```bash
b9 deploy --rtf > deployment.log &
tail -f deployment.log
```

Wait for the deployment to finish ("Done deploying all servers.") and then Ctrl+C out of tail.

Next deploy the pipeline service.

```bash
b9 serve-pipeline --rtf --include-label-text -p 55000 > serve-pipeline.log &
```

Next we need to create a configuration file for the API Gateway. Save the following contents to a file named "gateway.yml".

```yml
gateway:
  port: 8080
  events: localhost:50100
  processors:
  pipelines:
    - Identifier: biomedicus-default-pipeline
      Endpoint: 127.0.0.1:55000
```

After saving this file, we can start the gateway using the following command:

```bash
MTAP_CONFIG=gateway.yml ./mtap-gateway-<version> -v=3 -logtostderr &> gateway.log &
```

{: .note }
The ``./mtap-gateway-<version>`` is the binary downloade earlier. If you installed the gateway using go replace ``./mtap-gateway-version`` with ``mtap-gateway``.

Now the biomedicus servers are running, the pipeline and api gateway are hosted, and we can send documents to the pipeline to process. You can use either [this file](../resources/97_204.txt) or one of your own:

```bash
BODY=$(jq --null-input --arg doc "$(base64 "97_204.txt")"  \
'{ "event": { "event_id": "97_204.txt", "binaries": { "rtf": $doc }}, "params": { "document_name": "plaintext" }}')
curl -X POST http://127.0.0.1:8080/v1/pipeline/biomedicus-default-pipeline/process \
-H 'Content-Type: application/json' \
-d "${BODY}" | python -m json.tool
```

## Deploy using the docker image

You can also deploy the end-to-end REST pipeline using the biomedicus docker image:

```bash
 docker run -it -d --rm -p 8080:8080 --name b9 --entrypoint "./rest_e2e.sh" ghcr.io/nlpie/biomedicus:latest
```

You can follow the deployment logs using this command:

```bash
docker logs -f b9
```

Once you see the following message the server is ready to use on the 8080 port. 

```bash
Starting new pipeline gateway for service: biomedicus-default-pipeline with address: 127.0.0.1:55000
```

## Conclusion

Additional information on the mtap-gateway as well as API specifications can be found in the [MTAP Documentation](https://nlpie.github.io/mtap/docs/api-gateway.html).
