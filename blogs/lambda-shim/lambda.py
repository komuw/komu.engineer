import json
import subprocess


# 1. the python program gets a request from AWS lambda.
# 2. it serializes that request into json.
# 3. it writes that json into stdin
# 4. the Go program reads from stdin
# 5. it unmarshals what it has read from stdin and acts on it.
# 5. it creates a json marshaled response
# 6. it writes that json response to stdout
# 7. the python program reads that response from stdout
# 8. it unmarshals what it read(the response)
# 9. it sends the response back to AWS lambda.

# To run this programs:
# a. go build main.go
# b. python lambda.py

# To run this programs in AWS lambda:
# a. CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build main.go
# b. zip mylambda.zip main lambda.py
# c. upload mylambda.zip to AWS lambda
# d. set Runtime to python3.6 and Handler to lambda.handle


proc = subprocess.Popen(
    ["./main"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True, bufsize=1
)


def handle(event, context):
    proc.stdin.write(json.dumps({"event": event}))
    # read event
    line = proc.stdout.readline()
    event = json.loads(line)

    proc.stdin.close()
    proc.stdout.close()
    return event


event_value = handle(event="my_event", context={"hello": "world"})
print("event_value::")
print(event_value)
