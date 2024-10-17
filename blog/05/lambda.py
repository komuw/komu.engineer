import os
import sys
import json
import shutil
import traceback
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
# b. python3 lambda.py

# To run this programs in AWS lambda(Python3.6):
# a. CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o main main.go
# b. zip mylambda.zip main lambda.py
# c. upload mylambda.zip to AWS lambda
# d. set Runtime to python3.6 and Handler to lambda.handle


os.environ["PATH"] = (
    os.environ["PATH"] + ":" + os.environ.get("LAMBDA_TASK_ROOT", "LAMBDA_TASK_ROOT")
)


def handle(event, context):
    """
    When sending data to another program via it's stdin, don't forget to send a newline.
    Always flush the stream after placing data into it, since it may be buffered.

    It's is possible to make the program hang on the proc.stdout.readline() line:
      - we send something to the binary program's stdin,
      - then in the next line we try reading from binary programs stdout(via readline)
      - however that binary program is still awating for input (maybe because we sent data without a newline or the binary program is buffering.)
    ref: https://eli.thegreenplace.net/2017/interacting-with-a-long-running-child-process-in-python/
    """
    try:
        proc = subprocess.Popen(
            ["./main"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True
        )

        # write to binary program
        write_data = json.dumps({"event": event}) + "\n"
        proc.stdin.write(write_data)
        proc.stdin.flush()

        # read from binary program
        line = proc.stdout.readline()

        event = json.loads(line)

        proc.stdin.close()
        proc.stdout.close()

        proc.terminate()
        proc.wait(timeout=1.2)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
        return {"error": repr(e)}
    return event


event_value = handle(event="my_event", context={"hello": "world"})
print("event_value::")
print(event_value)
