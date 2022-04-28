# Big Ass Fans i6

## Keep-alive

On client start, send `root { root2 { keep_alive {} } }`. That will trigger a
full query update from the device. And after that, send
`root { root2 { keep_alive { 1: 3 } } }` every 15 seconds.
