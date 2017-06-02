#/usr/bin/python2.7
# -*- coding: utf-8 -*-
# Author: Hurray(hurray0@icloud.com)
# Date: 2017.05.28

from socket import *
from time import ctime
import threading
import json

global HOST
global PORT
global BUFSIZ
global ADDR

class User():
    def __init__(self, address, tcpCliSock):
        self.address = address
        self.tcpCliSock = tcpCliSock

class Handle():
    usernames = {} # user: usernames

    def __init__(self, user):
        self.user = user

    @staticmethod
    def getUser(username):
        def getKey(list, value):
            return [k for k,v in d.items() if v == value][0]
        return getKey(Handle.usernames, username)

    @staticmethod
    def delUsername(username):
        try:
            user = Handle.getUser(username)
            Handle.delUser(user)
        except:
            pass

    @staticmethod
    def delUser(user):
        try:
            Handle.usernames.pop(user)
        except Exception as e:
            print e

    @staticmethod
    def sendSocketToUsers(userList, data):
        jData = json.dumps(data)
        for user in userList:
            user.tcpCliSock.send(jData)
        print "__sendToAll__" + jData

    @staticmethod
    def sendSocketToNames(usernameList, data):
        """向用户列表发送相同的数据包"""
        def getKeys(list, valueList):
            return [k for k,v in list.items() if v in valueList]
        userList = getKeys(Handle.usernames, usernameList)
        Handle.sendSocketToUsers(userList, data)

    def sendSocketToMe(self, data):
        """给本用户发送信息包"""
        jData = json.dumps(data)
        self.user.tcpCliSock.send(jData)
        print '__send__' + jData

    def login(self, data):
        """处理登录信息包"""
        # already login
        if self.user in Handle.usernames.keys():
            data['status'] = False
            data['info'] = "您已经登录了"
        # username in use
        elif data['username'] in Handle.usernames.values():
            data['status'] = False
            data['info'] = "该用户名已被占用"
        else:
            data['status'] = True
            Handle.usernames[self.user] = data['username']
        self.sendSocketToMe(data)

    def ping(self, data):
        """ping pong!"""
        data = {'type': 'pong'}
        self.sendSocketToMe(data)

    def list(self, data):
        """获取在线用户列表"""
        nameList = Handle.usernames.values()
        data['list'] = nameList
        self.sendSocketToMe(data)

    def singleChat(self, data):
        """私聊"""
        toUsername = data['to']
        self.sendSocketToNames([toUsername], data)

    def groupChat(self, data):
        """群聊(公共聊天)"""
        userList = [user for user in Handle.usernames]
        self.sendSocketToUsers(userList, data)

    def logout(self, data):
        """登出"""
        print "用户"+ Handle.usernames[self.user] +"登出"
        Handle.delUser(self.user)

    def __main__(self, data):
        """处理信息包"""
        type = data['type']
        switch = {
                "login": self.login,
                "ping": self.ping,
                "list": self.list,
                "singleChat": self.singleChat,
                "groupChat": self.groupChat,
                "logout": self.logout
                }
        try:
            return switch[type](data)
        except Exception as e:
            print e
            data['status'] = False
            data['info'] = "未知错误"
            return data

class ClientThread(threading.Thread):
    def __init__(self, user):
        threading.Thread.__init__(self)
        self.user = user

    def run(self):
        try:
            handle = Handle(self.user) # handle input
            while True:
                jData = self.user.tcpCliSock.recv(BUFSIZ)
                data = json.loads(jData)
                print "___receive___" + jData
                if data['type'] == 'logout':
                    break
                else:
                    handle.__main__(data)
        except Exception as e:
            print "连接中断"
            print e
        finally:
            name = Handle.usernames[self.user]
            print "用户"+ str(name) +"登出"
            Handle.delUser(self.user)
            self.user.tcpCliSock.close()

    def stop(self):
        try:
            self.user.tcpCliSock.shutdown(2)
            self.user.tcpCliSock.close()
        except:
            pass

class Server():
    def __main__(self):
        tcpSerSock = socket(AF_INET, SOCK_STREAM)
        tcpSerSock.bind(ADDR)
        tcpSerSock.listen(5)

        threads = []

        while True:
            try:
                print 'Waiting for connection...'
                tcpCliSock, addr = tcpSerSock.accept()
                print '...connected from:', addr

                user = User(addr, tcpCliSock)
                clientThread = ClientThread(user)
                threads += [clientThread]
                clientThread.start()
            except KeyboardInterrupt:
                print 'KeyboardInterrupt:'
                for t in threads:
                    t.stop()
                break

        tcpSerSock.close()

if __name__ == '__main__':
    HOST = ''
    PORT = 8945
    BUFSIZ = 1024
    ADDR = (HOST, PORT)

    server = Server()
    server.__main__()
