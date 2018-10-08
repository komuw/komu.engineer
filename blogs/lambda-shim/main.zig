

const std = @import("std");
const io = std.io;
const warn = std.debug.warn;
const json = std.json;
const fmt = @import("std").fmt;

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

    const s1 =
          \\{
        ;
    const s2 =
          \\"EchoEvent": 
        ;
    const s3 =
          \\}
        ;

    var required_buf_length = 1 + s1.len + s2.len + s3.len + event.String.len;
    warn("required_buf_length: {}", required_buf_length);


    var all_together: [100]u8 = undefined;
    // You can use slice syntax on an array to convert an array into a slice.
    const all_together_slice = all_together[0..];
    // String concatenation example.
    const response = try fmt.bufPrint(all_together_slice, "{} {} \"{}\" {}", s1, s2, event.String, s3 );
    warn("\n\n response {}", response );
}

// gdb ./main -ex run
