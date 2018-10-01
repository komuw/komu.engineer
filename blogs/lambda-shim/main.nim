import json
import times

# run this as:
# echo '{"event": "myLambdaEventName", "context": "myLambdaContext"}'| nim compile --run main.nim

# read from stdin
var request: string = readLine(stdin)
let jsonReq = parseJson(request)

# for this example, we only use event; in real life you may also want to use context as well.
let event = jsonReq["event"]

var response =  %*
  {
  "EchoEvent": event,
  "CurrentTime":  format(times.now(), "d MMMM yyyy HH:mm")

  }

# write to stdout
echo response