In one terminal run:    
```bash
python code/metrics_collector.py
```     

In another terminal run:    
```bash
python code/metrics_emmiter.py
```    

or just:
```sh
docker-compose up
```    
then watch as collector collects metrics, ie:  
```sh
docker-compose logs -f metrics_collector
```   

##### Linux named pipe/FIFO:   
The linux pipe buffers are implemnted as circular buffers[1].    
A consequence of the circular buffer is that when it is full and a subsequent write is performed:      
  (a) then it starts overwriting the oldest data[2].         

The only difference between pipes and FIFOs is the manner in which they are created and opened.     
Once these tasks have been accomplished, I/O on pipes and FIFOs has exactly the same semantics[3].     

Since Linux 2.6.11, the pipe capacity is 16 pages(65,536bytes ie 65KB).       
The command:     
```sh
  cat /proc/sys/fs/pipe-max-size
  1048576 == 1MB
```
shows the value that acts as a ceiling on the default capacity of a new pipe[3]     

1. http://www.pixelbeat.org/programming/stdio_buffering/    
2. https://en.wikipedia.org/wiki/Circular_buffer   
3. http://man7.org/linux/man-pages/man7/pipe.7.html       



##### TODO:   
A. load test.    
B. unit tests     
C. test on python2 and python3     
D. use async operations on the python3 side(the metrics emitter has to be python2 but collector can be python3)     
   I would expect python3 async to perform really well.