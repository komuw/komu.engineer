import json
import times
import system

# run this as:
# echo '{"event": "myLambdaEventName", "context": "myLambdaContext"}'| nim compile --run main.nim

# to compile to use in AWS lambda; use a 64bit linux machine:
# nim c -d:release main.nim

# read from stdin
var request: string = readLine(stdin)
let jsonReq = parseJson(request)

# for this example, we only use event; in real life you may also want to use context as well.
let event = jsonReq["event"]

var response =  %*
  {
  "EchoEvent": event,
  "Message": "hello fom Nim version: " & system.NimVersion,
  "CurrentTime":  format(times.now(), "d MMMM yyyy HH:mm")

  }

# write to stdout
echo response