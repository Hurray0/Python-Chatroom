#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# Author: Hurray(hurray0@icloud.com)
# Date: 2017.05.28

from socket import *
import json
from Tkinter import *
import threading
import ctypes
import inspect
import sys
import struct

reload(sys)
sys.setdefaultencoding('utf8')

class R():
    SENDERPORT = 1501
    MYPORT = 1234
    MYGROUP = '224.1.1.1'

class Client():
    def __init__(self):
        self.isConnect = False

    def connect(self):
        """连接服务器"""
        if not self.isConnect:
            self.tcpCliSock = socket(AF_INET, SOCK_STREAM)
            self.tcpCliSock.connect(ADDR)
            self.isConnect = True
            print "连接成功"
        else:
            print "已经连接，不再重新连接"

    def disConnect(self):
        """断开服务器"""
        self.tcpCliSock.close()

    def showErr(self, info):
        """错误提示界面"""
        errTk = Tk()
        errTk.geometry('200x120')
        errTk.title("Error!")
        Label(errTk, text = info).pack(padx = 5, pady = 20, fill = 'x')
        bt = Button(errTk, text = "确定", command = errTk.destroy).pack()
        errTk.mainloop()

    class Login():
        """登录界面"""
        def __init__(self, father):
            self.father = father

        def goLogin(self, entry, loginWindow):
            """登录操作"""
            username = entry.get()
            self.father.username = username
            data = {"type": "login", "username": username}
            jData = json.dumps(data)
            try:
                self.father.connect()
            except Exception as e:
                print e
                self.father.showErr("网络连接异常，无法连接服务器")
                return False
            else:
                socket = self.father.tcpCliSock
                socket.send(jData)
                recv_jData = socket.recv(BUFSIZ)
                recv_data = json.loads(recv_jData)
                if recv_data["type"] == "login" and \
                        recv_data["username"] == username and \
                        recv_data["status"] == True:
                    # login success!
                    print "login success"
                    mainFrame = self.father.MainFrame(self.father)
                    loginWindow.destroy()
                    mainFrame.__main__()
                else:
                    # login failed
                    if recv_data["info"]:
                        self.father.showErr(recv_data["info"])
                    else:
                        self.father.showErr("未知登录错误")
                        #self.disConnect()

        def window(self):
            """登录窗口GUI"""
            tk = Tk()
            tk.geometry('250x150')
            tk.title('登录界面')
            frame = Frame(tk)
            frame.pack(expand = YES, fill = BOTH)
            Label(frame, font = ("Arial, 15"),
                    text = "请输入一个用户名：", anchor = 'w').pack(padx = 10,
                            pady = 15, fill = 'x')
            entry = Entry(frame)
            entry.pack(padx = 10, fill = 'x')
            entry.bind("<Key-Return>", lambda x : self.goLogin(entry, tk))
            button = Button(frame, text = "登录",
                    command = lambda : self.goLogin(entry, tk))
            button.pack()

            tk.mainloop()

        def __main__(self):
            # 建立窗口
            self.window()

    class MainFrame():
        """聊天主窗口"""
        def __init__(self, father):
            self.father = father
            self.socket = father.tcpCliSock # may raise a Exception
            self.rSocket = None
            self.sSocket = None

        class ListenThread(threading.Thread):
            """Socket监听线程，对收到的信息作出相应反馈"""
            def __init__(self, socket, father):
                threading.Thread.__init__(self)
                self.father = father
                self.socket = socket

            def run(self):
                while True:
                    try:
                        jData = self.socket.recv(BUFSIZ)
                        data = json.loads(jData)
                    except:
                        break
                    print "__receive__" + jData
                    switch = {
                            "list": self.list,
                            "singleChat": self.chat,
                            "groupChat": self.chat,
                            "pong": self.pong
                            }
                    switch[data['type']](data)
                print "结束监听"

            def list(self, data):
                """刷新列表"""
                listbox = self.father.listbox
                list = ['群聊', '组播']
                list += data['list']
                listbox.delete(0, END) # 清空现有列表
                for l in list:
                    listbox.insert(END, l) # 插入新列表

            def chat(self, data):
                """接收聊天信息并打印"""
                textArea = self.father.textArea
                text = ('[群聊]' if data['type'] == 'groupChat' else '') + \
                        data['from'] + ': ' + data['msg'] + '\n'
                textArea.insert(END, text)

            def pong(self, data):
                """ping pong!"""
                text = '[Server]pong\n'
                textArea.insert(END, text)

        class BroadListenThread(threading.Thread):
            """组播侦听线程"""
            def __init__(self, father):
                threading.Thread.__init__(self)
                self.father = father

            def run(self):
                print '开始监听组播'
                self.alive = True
                sock = self.father.rSocket
                while self.alive:
                    try:
                        jData, addr = sock.recvfrom(BUFSIZ)
                        data = json.loads(jData)
                    except Exception as e:
                        pass
                    else:
                        textArea = self.father.textArea
                        text = "[组播]" + data['from'] + ': ' + data['msg'] + '\n'
                        textArea.insert(END, text)
                        print "__receiveBroad__" + jData
                print '组播监听循环结束'

            def stop(self):
                self.alive = False

        class Window():
            def __init__(self, father):
                self.father = father

            def refresh(self, socket):
                """点击刷新按钮"""
                data = {"type": "list"}
                jData = json.dumps(data)
                socket.send(jData)

            def changeAddr(self):
                def setAddr(entry1, entry2, entry3, self, tk):
                    if self.father.rSocket:
                        # 停止之前的地址
                        self.father.broadListenThread.stop()
                        self.father.sSocket.sendto("", (R.MYGROUP, R.MYPORT)) # fake send
                        print '停止之前的地址'

                    try:
                        # 发送socket
                        R.MYGROUP = entry1.get()
                        R.MYPORT = int(entry2.get())
                        R.SENDERPORT = int(entry3.get())
                        s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
                        s.bind((HOST, R.SENDERPORT))
                        ttl_bin = struct.pack('@i', MYTTL)
                        s.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, ttl_bin)
                        status = s.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP,
                                inet_aton(R.MYGROUP) +
                                inet_aton(HOST))#加入到组播组
                        self.father.sSocket = s

                        # 监听socket
                        so = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
                        so.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                        so.bind((HOST, R.MYPORT))
                        status = so.setsockopt(IPPROTO_IP,
                                IP_ADD_MEMBERSHIP,
                                inet_aton(R.MYGROUP) +
                                inet_aton(HOST))
                        so.setblocking(0)
                        self.father.rSocket = so

                    except Exception as e:
                        print e
                        self.father.father.showErr("该地址不可使用")
                    else:
                        broadListenThread = self.father.BroadListenThread( \
                                self.father)
                        broadListenThread.start()
                        self.father.broadListenThread = broadListenThread
                        tk.destroy()

                def isset(v):
                    try:
                        type(eval(v))
                    except:
                        return False
                    else:
                        return True

                """修改组播地址"""
                tk = Tk()
                tk.geometry('270x120')
                tk.title('请修改组播设置')
                Label(tk, text = "组播地址: ").grid(row = 0, column = 0)
                Label(tk, text = "监听端口: ").grid(row = 1, column = 0)
                Label(tk, text = "本地端口: ").grid(row = 2, column = 0)
                entry1 = Entry(tk)
                entry1.grid(row = 0, column = 1)
                entry1.insert(END, R.MYGROUP)
                entry2 = Entry(tk)
                entry2.grid(row = 1, column = 1)
                entry2.insert(END, R.MYPORT)
                entry3 = Entry(tk)
                entry3.grid(row = 2, column = 1)
                entry3.insert(END, R.SENDERPORT)
                bt = Button(tk, text = "确定",
                        command = lambda : setAddr(entry1, entry2, entry3,
                            self, tk)).grid(row = 3, column = 0, columnspan = 2)

                tk.mainloop()

            def sendBroad(self, msg, et_input, username):
                sSocket = self.father.sSocket
                if not sSocket:
                    self.changeAddr()
                else:
                    data = {'type': 'broadChat', 'msg': msg, 'from': username}
                    jData = json.dumps(data)
                    print (R.MYGROUP, R.MYPORT)
                    sSocket.sendto(jData, (R.MYGROUP, R.MYPORT))
                    print '__sendBroad__' + jData

                    # 清空输入框
                    et_input.delete(0, END)

            def send(self, socket, lb_toName, et_input):
                """点击发送按钮"""
                text = et_input.get()
                toName = lb_toName['text']
                username = self.father.father.username
                print toName
                if toName == '群聊':
                    data = {'type': 'groupChat', 'msg': text, 'from': username}
                elif toName == '组播':
                    self.sendBroad(text, et_input, username)
                    return
                else:
                    # 私聊
                    data = {'type': 'singleChat', 'msg': text,
                            'to': toName, 'from': username}
                    textArea = self.father.textArea
                    t = "[->" + toName + ']' + text + '\n'
                    textArea.insert(END, t)
                jData = json.dumps(data)
                socket.send(jData)
                print '__send__' + jData
                et_input.delete(0, END)

            def changeSendTo(self, listbox, lb_toName):
                """双击选择列表"""
                try:
                    lb_toName['text'] = listbox.get(listbox.curselection()) 
                except:
                    pass # nothing choose

            def __main__(self):
                father = self.father
                tk = Tk()
                tk.geometry('600x400')
                tk.title('Chatroom')

                # 背景
                f = Frame(tk, bg = '#EEEEEE', width = 600, height = 400)
                f.place(x = 0, y = 0)

                # 聊天内容框
                textArea = Text(f, bg = '#FFFFFF', width = 60,
                        height = 22,
                        #state = DISABLED,
                        bd = 0)
                textArea.place(x = 10, y = 10, anchor = NW)
                textArea.bind("<KeyPress>", lambda x : "break")
                father.textArea = textArea
                textArea.focus_set()
                # 右侧选择聊天对象
                Label(f, text = "双击选择发送对象:", bg = "#EEEEEE").place(
                        x = 460, y = 10, anchor = NW)
                listbox = Listbox(f, width = 13, height = 13, bg = '#FFFFFF')
                listbox.place(x = 460, y = 35, anchor = NW)
                father.listbox = listbox
                bt_refresh = Button(f, text = "刷新列表", bd = 0,
                        command = lambda : self.refresh(father.socket))
                bt_refresh.place(x = 515, y = 290, anchor = CENTER)
                # 修改组播地址
                bt_changeAddr = Button(f, text = "组播地址",
                        command = self.changeAddr)
                bt_changeAddr.place(x = 515, y = 330, anchor = CENTER)
                bt_clear = Button(f, text = "清屏",
                        command = lambda : textArea.delete(0.0, END))
                bt_clear.place(x = 560, y = 372, anchor = CENTER)
                # 下方内容输入
                lb_toName = Label(f, text = "群聊", bg = '#FFFFFF', width = 8)
                lb_toName.place(x = 12, y = 360)
                listbox.bind('<Double-Button-1>',
                        lambda x : self.changeSendTo(listbox, lb_toName))
                self.lb_toName = lb_toName
                et_input = Entry(f, width = 37)
                et_input.place(x = 90, y = 358)
                et_input.bind('<Key-Return>',
                                lambda x : self.send(father.socket,
                            lb_toName, et_input))
                self.et_input = et_input
                # 发送按钮
                bt_send = Button(f, text = "ENTER",
                        command = lambda : self.send(father.socket,
                            lb_toName, et_input))
                bt_send.place(x = 480, y = 371, anchor = CENTER)

                # 刷新列表
                self.refresh(father.socket)

                tk.mainloop()

                father.socket.shutdown(2)
                print 'Socket 断开'
                try:
                    father.broadListenThread.stop()
                    father.sSocket.sendto("", (R.MYGROUP, R.MYPORT)) # fake send
                except:
                    pass
                print 'rSocket 断开'

        def __main__(self):
            # 开启监听线程
            listenThread = self.ListenThread(self.socket, self)
            listenThread.start()
            self.listenThread = listenThread

            # 组播侦听线程
            #print '开始监听'
            #broadListenThread = self.BroadListenThread(self)
            #broadListenThread.start()
            #self.broadListenThread = broadListenThread

            # 建立窗口
            window = self.Window(self)
            window.__main__()
            self.window = window

    def __main__(self):
        #pass
        login = Client.Login(self)
        login.__main__()

if __name__ == '__main__':
    global HOST
    global PORT
    global BUFSIZ
    global ADDR

    HOST = '0.0.0.0'
    PORT = 8945
    BUFSIZ = 1024
    ADDR = (HOST, PORT)
    MYTTL = 255

    client = Client()
    client.__main__()
