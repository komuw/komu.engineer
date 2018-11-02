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


