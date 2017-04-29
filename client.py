# -*- coding: utf-8 -*-
import socket
import sys
import select
 
def prompt() :
    sys.stdout.write('> ')
    sys.stdout.flush()
   
 
if __name__ == "__main__":
     
    if(len(sys.argv) < 3) :
        print ('Usage : python3 Client.py Hostname Port')
        sys.exit()
     
    host = sys.argv[1]
    port = int(sys.argv[2])
     
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
     
    # connect to server host
    try :
        s.connect((host, port))
    except :
        print ('Unable to connect Server') 
        sys.exit()
     
    print ('......Connected to Server. Start sending messages......')
    print()
    prompt()

    try: 
        while 1:
            rlist = [sys.stdin, s] 
            # Get the list sockets which are readable
            read_list, write_list, error_list = select.select(rlist , [], [])
             
            for sock in read_list:
                # incoming message from the server
                if sock == s:
                    data = sock.recv(4096).decode()
                    if not data:
                        print ('......Disconnected from Server......')
                        print()
                        sys.exit()
                        
                    elif data:
                        sys.stdout.write(data)
                        prompt()                       

                else:
                    msg = sys.stdin.readline()
                    s.send(msg.encode())
                    prompt()
                    
                    
                    
    except KeyboardInterrupt:
        msg = 'logout'
        s.send(msg.encode())
        sys.exit()
