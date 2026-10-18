#!/bin/sh
# Lambda handler with AWS_LAMBDA_EXEC_WRAPPER=/opt/bootstrap (Lambda Web Adapter): starts the HTTP
# server that the adapter forwards API Gateway requests to.
exec python3 "${LAMBDA_TASK_ROOT:-.}/server.py"
