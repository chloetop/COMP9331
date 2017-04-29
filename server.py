# -*- coding: utf-8 -*-
import socket
import select
import sys
import time
import threading


# --------------------1.black list ------------------
def AisBlackedByB(uname,sock,to_socket):  
    to_name = OnlineSocketUnameDict[to_socket]
    if to_name in blackListDict:        
        blacknameList = blackListDict[to_name]
        if uname in blacknameList:       # blocked 
            return 1
        elif uname not in blacknameList: # not be blocked 
            return 0
    elif to_name not in blackListDict:   # not be blocked 
        return 0


def BisBlackedByA(uname,sock,to_socket):
    to_name = OnlineSocketUnameDict[to_socket]
    if uname in blackListDict:             # sender has a blacklist
        blacknameList = blackListDict[uname]
        if to_name in blacknameList:       # blocked 
            return 1
        elif to_name not in blacknameList: # not be blocked 
            return 0
    elif uname not in blackListDict:       # not be blocked 
        return 0
    

#----------------------2. broadcast ------------------
def Broadcast(connection,uname, msg):
   
    if msg == MSG_LOGINBROADCAST  or msg == MSG_LOGOUTBROADCAST :       
        msg = uname + msg              # login/logout broadcast
    elif 'broadcast' in msg:           # broadcast message 
        msg = uname +':' + msg[9:]   
    for socket in CONNECTION_LIST:
        if socket != server_socket and socket != connection:   # not server, not self socket
            blackStatus = AisBlackedByB(uname,connection,socket)
            if AisBlackedByB(uname,connection,socket) == 0:    # not be blocked 
                if BisBlackedByA(uname,connection,socket) == 0: # not be blocked 
                    try:
                        socket.send(msg.encode())
                    except: # broken socket connection may be, chat client pressed ctrl+c for example
                        socket.close()
                        del OnlineSocketUnameDict[socket]
                        CONNECTION_LIST.remove(socket)

                elif BisBlackedByA(uname,connection,socket) == 1: # A blockB. Donot show A login/logout
                    if (MSG_LOGINBROADCAST not in msg) and (MSG_LOGOUTBROADCAST not in msg):
                        try:
                            socket.send(msg.encode())
                        except:# broken socket connection may be, chat client pressed ctrl+c for example
                            socket.close()
                            del OnlineSocketUnameDict[socket]
                            CONNECTION_LIST.remove(socket)
                                           
            elif AisBlackedByB(uname,connection,socket) == 1: # 有被block
                try:
                    connection.send(MSG_BROADCAST_BLOCKED.encode())
                except:# broken socket connection may be, chat client pressed ctrl+c for example
                    socket.close()
                    del OnlineSocketUnameDict[socket]
                    CONNECTION_LIST.remove(socket)
                      
#----------------------3. A user cannot login twice ------------------        
def Check_uname_already_online(uname):
    OnlineSocketUnameList = []
    OnlineSocketUnameList = list(OnlineSocketUnameDict.items())
    if len(OnlineSocketUnameList) !=0:
        for pair in OnlineSocketUnameList:
            if uname in pair:
                return 1
            else:
                return 0
    else:
        return 0
                    

#----------------------4. three times login-------------------
def ThreeTimeLogin(connection):
    status = 0      # have not logged in
    for i in range(1,4):
        connection.send(USERNAME.encode())
        uname = (connection.recv(MAX_SIZE)).decode()
        if uname:
            ulist = uname.split()
            if len(ulist)!=0:
                uname = ulist[0]        
                if Check_UsernameInTxt(uname):
                    connection.send(PASSWORD.encode())
                    upassword = (connection.recv(MAX_SIZE)).decode()                    
                    plist= upassword.split()
                    upassword = plist[0]
                    if Block(uname) == 1:   # be blocked 
                        connection.send(MSG_LOCKED.encode())
                        connection.close()
                        CONNECTION_LIST.remove(connection)
                        break
                    elif Block(uname) == 0: # not be blocked
                        if Check_Password(uname,upassword):
                            if Check_uname_already_online(uname) == 0:                          
                                connection.send(LOGINSUCCESS.encode())
                                status = 1  # login success
                                OnlineSocketUnameDict[connection] = uname
                                break
                            else:
                                connection.send(MSG_ALREADYLOGIN.encode())
                                connection.close()
                                CONNECTION_LIST.remove(connection)
                                break
                                
                        elif (not Check_Password(uname,upassword)) and i!=3:
                            connection.send(WRONGPASSWORD.encode())
                            continue
                        elif (not Check_Password(uname,upassword)) and i==3:
                            ADDINblockDict(uname, blockDict) # add to blockDict
                            connection.send(MSG_LOCKED.encode())
                            connection.close()
                            CONNECTION_LIST.remove(connection)
                            break
                           
                elif (not Check_UsernameInTxt(uname)): # wrong username
                    connection.send(NAMEERROR.encode())
                    if i!=3:
                        continue
                    if i == 3:
                        connection.close()
                        CONNECTION_LIST.remove(connection)
                        break

    if status == 1:        
        Broadcast(connection,uname,MSG_LOGINBROADCAST)
        OfflineMSGProcess(connection,uname)
        UpdatelastActiveTimeDict(uname)

#----------------------5. offline message process-------------------
def OfflineMSGProcess(connection,uname):
    if uname in offlineMsgDict:
        offlineMSGlist = offlineMsgDict[uname]
        for msg in offlineMSGlist:
            connection.send(msg.encode())
        offlineMsgDict[uname] = []    

           
#------------------6. username/password/block status validation check ------------------
def Check_UsernameInTxt(uname):
    if uname in passDict:
        return 1
    
def Check_Password(uname,upassword):
    if passDict[uname] == upassword:
        return 1

def Block(uname):
    if uname not in blockDict:
        return 0   
    elif uname in blockDict:
        current_time = time.time()
        block_time = blockDict[uname]
        if current_time - block_time < BLOCK_DURATION:
            return 1
        else:
            return 0
        

def ADDINblockDict(uname, blockDict):
    current_time = time.time()
    blockDict[uname] = current_time


#---------------------7. whoelse -------------------

def Whoelse(sock):         
    whoelseList = []
    for socket in CONNECTION_LIST:
        if socket != server_socket and socket != sock:
            whoelseList.append(OnlineSocketUnameDict[socket])
    whoelse = ''
    for who in whoelseList:
        who = who + ' '
        whoelse += who
    return whoelse +'\n'        
                          
#----------------------8. who since -------------------

def Whoelsesince(since_time, uname):
    sinceList = []
    current_time = time.time()
    
    lastActiveTimePairList = list(lastActiveTimeDict.items())
    for pair in lastActiveTimePairList:
        otherName = pair[0]
        lastActiveTime = pair[1]
        if current_time - lastActiveTime <= since_time and uname != otherName:
            sinceList.append(otherName)
    whoelsesince = ''
    for who in sinceList:
        who = who + ' '
        whoelsesince += who
    return whoelsesince +'\n'


#----------------------9. block / unblock function-------------------
def BlockUserProcess(sock,uname, blocked_user):   
    if uname == blocked_user:                     
        sock.send(ERROR_BLOCKSELF.encode())
    if not Check_UsernameInTxt(blocked_user):     
        sock.send(ERROR_BLOCKWRONGNAME.encode())          
    if uname != blocked_user and Check_UsernameInTxt(blocked_user):
        addBlack = []
        addBlack.append(blocked_user)
        if uname in blackListDict and blocked_user not in blackListDict[uname]:
            blackListDict[uname].extend(addBlack)
            msg = blocked_user + MSG_BLOCKSUCCESS
            sock.send(msg.encode())
            
        elif uname in blackListDict and blocked_user in blackListDict[uname]:
            
            sock.send(ERROR_BLOCKTWICE.encode())
        else:
            blackListDict[uname] = [blocked_user]           
            msg = blocked_user + MSG_BLOCKSUCCESS                   
            sock.send(msg.encode())
    
def Check_UsernameInblackListDict(uname, unblocked_user):
    if uname in blackListDict: # uname has blacklist
        if unblocked_user in blackListDict[uname]:
            return 1
    

def UnBlockUserProcess(sock,uname, unblocked_user):  
    if uname == unblocked_user:                      
        sock.send(ERROR_UNBLOCKSELF.encode())
    if not Check_UsernameInblackListDict(uname, unblocked_user) and uname != unblocked_user : # done: tested
        msg = ERROR + unblocked_user + ERROR_UNBLOCKWRONGNAME   
        sock.send(msg.encode())
    if uname != unblocked_user and Check_UsernameInblackListDict(uname, unblocked_user):
        blackListDict[uname].remove(unblocked_user)  
        msg = unblocked_user + MSG_UNBLOCKSUCCESS
        sock.send(msg.encode())   

# --------------------10. Process_logout----------
def Process_logout(sock, uname):
    Broadcast(sock,uname, MSG_LOGOUTBROADCAST)
    sock.close()
    del OnlineSocketUnameDict[sock]
    CONNECTION_LIST.remove(sock)


#------------11 -whether a name in the blacklist-----
def CheckInBlacknameList(uname, to_name):
    if to_name in blackListDict:
        blacknameList = blackListDict[to_name]
        if uname in blacknameList:              # be blocked 
            return 1
        else:
            return 0
    else:
        return 0 

#-------------12 username online check---------
def CheckUserOnline(to_name):
    try:
        onlineUserList = list(OnlineSocketUnameDict.values())
        if to_name in onlineUserList:
            return 1
        else:
            return 0
    except ValueError:
        return 0
        
        
#------------13. FindSocket by to_name-----------     
def FindSocket(to_name):
    OnlineSocketUnamePairList = list(OnlineSocketUnameDict.items())
    if len(OnlineSocketUnamePairList) != 0:
        try:
            for pair in OnlineSocketUnamePairList:
                socket, uname = pair
                if to_name == uname:
                    return socket
                else:
                    pass
        except ValueError:
            pass
    

#---------------------14. Process_message----------
def Process_message(sock,uname, msg, to_name):
    msg = msg[2:]
    head = uname +': '
    words = ' '.join(msg)
    message = head + words + '\n'    
    
    if uname != to_name:
        if to_name in passDict:
            
            # check Blacklist
            if CheckInBlacknameList(uname, to_name) == 0: 
                if CheckUserOnline(to_name) == 1: 
                    try:
                        to_socket = FindSocket(to_name)
                        to_socket.send(message.encode())
                    except ValueError:
                        pass

                elif CheckUserOnline(to_name) == 0:          # online check
                    sock.send(MSG_MESSAGE_OFFLINE.encode())
                    if to_name in offlineMsgDict: 
                        to_name_message_list = offlineMsgDict[to_name]
                        to_name_message_list.append(message)
                    else:
                        offlineMsgDict[to_name] = [message]                                 
            
            elif CheckInBlacknameList(uname, to_name) == 1:  # in blacklist
                sock.send(MSG_MESSAGE_BLOCKED.encode())                   
        elif to_name not in passDict:                        # this name not in txt file
            sock.send(ERROR_INVALIDUSER.encode())
    elif uname == to_name:
        sock.send(ERROR_INVALIDUSER.encode())

    
#---------------- 15.last activity time of a user---------------    
     
def UpdatelastActiveTimeDict(uname):
    current_time = time.time()
    lastActiveTimeDict[uname] = current_time

    
#-----------------16. timeout , logout user-----------------
    
def TimeOutLogoutUser(TIMEOUT):
    current_time = time.time()
    lastActiveTimePairList = []
    lastActiveTimePairList = list(lastActiveTimeDict.items())

    for pair in lastActiveTimePairList:
        uname = pair[0]
        lastActiveTime = pair[1]
        if current_time - lastActiveTime > TIMEOUT: 
            try:
                socket = FindOnlineTimeOutSocket(uname)
                # reject the socket
                if socket !=0:
                    Process_logout(socket, uname)
                    UpdatelastActiveTimeDict(uname)
                    
            except ValueError:
                pass

    
#-----------------17. socket online check ----------------
def FindOnlineTimeOutSocket(uname):
    OnlineSocketUnameList = []

    OnlineSocketUnameList = list(OnlineSocketUnameDict.items())
    if len(OnlineSocketUnameList) !=0:
        for pair in OnlineSocketUnameList:
            if uname in pair:
                socket = pair[0] 
                return socket
            elif uname not in pair:
                continue
        return 0               
    elif len(OnlineSocketUnameList) == 0:
        return 0


#----------------------18. command processing  -------------------
def CommandProcess(sock, data):
    msg = data.split()
    uname = OnlineSocketUnameDict[sock]
    
    if data:
        msg = data.split()
        try:       
            if msg[0] == 'message':      
                try: 
                    to_name = msg[1]                            
                    Process_message(sock,uname, msg, to_name)                    
                    UpdatelastActiveTimeDict(uname)
                except IndexError:
                    sock.send(ERROR_COMMAND_MESSAGE.encode())

            
            elif msg[0] == 'broadcast':     
                Broadcast(sock,uname,data)
                UpdatelastActiveTimeDict(uname)

            elif msg[0] == 'whoelse':       
                whoelse = Whoelse(sock)
                sock.send(whoelse.encode())
                UpdatelastActiveTimeDict(uname)
                
            elif msg[0] == 'whoelsesince':   
                try:
                    since_time = float(msg[1])
                    whosince = Whoelsesince(since_time, uname)
                    sock.send(whosince.encode())
                    UpdatelastActiveTimeDict(uname)                               
                except IndexError:
                    sock.send(ERROR_COMMAND_WHOELSESINCE.encode())

            elif msg[0] == 'block':         
                try: 
                    blocked_user = msg[1]                            
                    BlockUserProcess(sock,uname, blocked_user)
                    UpdatelastActiveTimeDict(uname)
                    
                except IndexError:
                    sock.send(ERROR_COMMAND_BLOCK.encode())

            elif msg[0] == 'unblock':       
                try:
                    unBlocked_user = msg[1]                            
                    UnBlockUserProcess(sock,uname, unBlocked_user)
                    UpdatelastActiveTimeDict(uname)                
                except IndexError:
                    sock.send(ERROR_COMMAND_UNBLOCK.encode())

                
            elif msg[0] == 'logout':            
                Process_logout(sock, uname)
                UpdatelastActiveTimeDict(uname)

                
            else:
                UpdatelastActiveTimeDict(uname)
                sock.send(ERROR_COMMAND.encode())
        except IndexError:
            sock.send(ERROR_COMMAND.encode())
           
#--------------------------19. main loop for select moudle -----------------------

def main():   
    try:
        while True:
            t = threading.Thread(target = TimeOutLogoutUser(TIMEOUT))
            t.setDaemon(True)
            t.start()
            
            read_sockets,write_sockets,error_sockets = select.select(CONNECTION_LIST,[],[],TIMEOUT)
            for sock in read_sockets:
                TimeOutLogoutUser(TIMEOUT)
                # 1. it is a connection request ---> process it to login
                if sock == server_socket:
                    connection, addr = server_socket.accept()
                    CONNECTION_LIST.append(connection)
                    ThreeTimeLogin(connection)  
                    
                # 2. it is client data ---> process command    
                else:
                    try:
                        TimeOutLogoutUser(TIMEOUT)

                        try:
                            data = sock.recv(MAX_SIZE).decode()
                            CommandProcess(sock, data)
                        except OSError:
                            pass
                            
                    except KeyboardInterrupt:
                        pass                                                                                   
    except KeyboardInterrupt:
        server_socket.close()       
        print('...............Server down...............')
        sys.exit()
                           

if __name__ == "__main__":
    if len(sys.argv) == 4:
        try:
            PORT = int(sys.argv[1])
            BLOCK_DURATION= int(sys.argv[2])
            TIMEOUT = float(sys.argv[3])
        except ValueError:
            print("Error. argvs value]")
    else:
        print("[Usage tip] python3 server.py port block_duration timeout")
        sys.exit()
    
# global Dict    
    passDict = {}                  # passDict  = { uname : pass }
    blockDict = {}                 # blockDict = { uname : time }

    lastActiveTimeDict = {}        # lastActiveTimeDict = {uname: time}
    OnlineSocketUnameDict = {}     # OnlineSocketUnameDict = {sock : uname}
    blackListDict = {}             # blackListDict = {uname: [uname1, uname2, ....]}
    offlineMsgDict = {}            # offlineMsgDict = {uname: [msg1],[msg2]...}
    
    file = open ('credentials.txt','rt') 
    for line in file:
        userInfo = line.split()
        passDict[userInfo[0]] = userInfo[1]           

# global 
    CONNECTION_LIST = []
    USERNAME = 'username: '
    NAMEERROR = 'Invalid  username\n'
    PASSWORD = 'password: '
    LOGINSUCCESS = 'Welcome to the greatest messaging application ever!\n'
    WRONGPASSWORD = 'Invalid Password. Please try again \n'
    MSG_LOCKED = 'Invalid Password. Your account has been blocked. Please try again later \n'
    MSG_ALREADYLOGIN = 'This username already online\n'
    
    MSG_LOGINBROADCAST = ' logged in\n'
    MSG_LOGOUTBROADCAST = ' logged out\n'
    MSG_BROADCAST_BLOCKED = 'Your message could not be delivered to some recipients\n'
    MSG_MESSAGE_BLOCKED = 'Your message could not be delivered as the recipient has blocked you\n'
    MSG_MESSAGE_OFFLINE = 'This user is offline. Will send when online\n'

    
    ERROR_INVALIDUSER = 'Error. Invalid user\n'
    ERROR_BLOCKSELF = 'Error. Cannot block self\n'
    ERROR_BLOCKTWICE = 'Error. Cannot block one user twice\n'
    ERROR_UNBLOCKSELF = 'Error. Cannot unblock self\n'
    ERROR_BLOCKWRONGNAME = 'Error. The input name is not in TXT\n'
    ERROR = 'Error. '
    ERROR_UNBLOCKWRONGNAME = ' was not blocked\n'
    ERROR_COMMAND = 'Error. Invalid command\n'
    ERROR_COMMAND_MESSAGE = 'Useage: message name words \n'
    ERROR_COMMAND_WHOELSESINCE = 'Useage: whoelsesince time \n'
    ERROR_COMMAND_BLOCK = 'Useage: block name \n'
    ERROR_COMMAND_UNBLOCK = 'Useage: unblock name \n'
    
    MSG_BLOCKSUCCESS = ' is blocked\n'
    MSG_UNBLOCKSUCCESS = ' is unblocked\n'
    LOGOUT = 'logout'

    
    # creat server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    MAX_SIZE = 4096
    # force to reuse the address
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", PORT))
    server_socket.listen(10)
    
    # Add server socket to the list of readable connections
    CONNECTION_LIST.append(server_socket)
    
    print()
    print('............. Server starting............. ')
    print('Server on port:',PORT)
    print()
    main()
    
    
