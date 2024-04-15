whadsniff --format=hexdump -i uart0 ble -a 2>&1 | tee ~/downloads/whadsniff.log
whadsniff -i uart0 ble -a 2>&1 | tee -a ~/downloads/whadsniff.log
