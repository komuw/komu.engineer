

const std = @import("std");
const io = std.io;
const warn = std.debug.warn;
const json = std.json;

// run this program as:
// echo '{"event": "myLambdaEventName", "context": "myLambdaContext"}' | /usr/local/zig/zig run main.zig

pub fn main() !void {
    var stdout_file = try io.getStdOut();
    var line_buf: [200]u8 = undefined;
    const line = io.readLine(line_buf[0..]);
    warn("read: {}", line_buf);

    var used_buf: usize = 0;
    for (line_buf) |value| {
        if (value != 0) {
            used_buf += 1;
        } 
    }
    var p = json.Parser.init(std.debug.global_allocator, false);
    defer p.deinit();
    var tree = try p.parse( line_buf[0..used_buf]);
    defer tree.deinit();
    var root = tree.root;
    var event = root.Object.get("event").?.value;
    warn("event: {}", event.String);

//     var response =  %*
//   {
//   "EchoEvent": event,
//   "Message": "hello fom Nim version: " & system.NimVersion,
//   "CurrentTime":  format(times.now(), "d MMMM yyyy HH:mm")

//   }

   warn("ss" "{}" event.String);

}

// gdb ./main -ex run
