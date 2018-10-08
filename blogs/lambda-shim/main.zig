

const std = @import("std");
const io = std.io;
const warn = std.debug.warn;
const json = std.json;
const fmt = std.fmt;
const time = std.os.time;

// run this program as:
// echo '{"event": "myLambdaEventName", "context": "myLambdaContext"}' | /usr/local/zig/zig run main.zig

pub fn main() !void {
    var currentTime  = time.milliTimestamp();
    var line_buf: [200]u8 = undefined;
    const line = io.readLine(line_buf[0..]);
    var stdout_file = try io.getStdOut();
    const stdout = &stdout_file.outStream().stream;

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

    const s1 =
          \\{
        ;
    const s2 =
          \\"EchoEvent": 
        ;
    const s3 = 
         \\,
         ;
    const s4 = 
        \\ "CurrentTime":
        ;
    
    const s5 = 
         \\,
         ;

    const s6 =
          \\"Message": "hello from Zig"
        ;

    const s7 =
          \\}
        ;

    var required_buf_length = 1 + s1.len + s2.len + s3.len + event.String.len;

    var all_together: [1000  + s1.len + s2.len + s3.len + s4.len]u8 = undefined;
    const all_together_slice = all_together[0..];
    const response = try fmt.bufPrint(all_together_slice, "{} {} \"{}\" {} {} {} {} {} {}", s1, s2, event.String, s3, s4, currentTime, s5, s6, s7);

    try stdout.print("{}", response);

}

// gdb ./main
// gdb ./main -ex run
