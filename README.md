# Video-Content-Processing-Service

It handles video content processing (hls,dash) on demand.

## Requirements

Python3

## Configuration

| Key                           | Comment                                              | Default                              |
| ----------------------------- | ---------------------------------------------------- | ------------------------------------ |
| PORT                          | The port to use for processing-handlers service      | 5000                                 |
| HOST                          | The host for processing-handlers service             | 127.0.0.1                            |
| DASH_HLS_OUTPUT_BASED_PATH    | dash, hls output path store                          |                                      |

## Install packages

pip install -r requirements

## Start the services (dev)

### Configurations

### Up backend processing handlers

python3 main.py
