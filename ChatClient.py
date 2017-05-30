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
reload(sys)
sys.setdefaultencoding('utf8')

global HOST
global PORT
global BUFSIZ
global ADDR

def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)

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
        Button(errTk, text = "确定", command = errTk.destroy).pack()
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
                        father.showErr(recv_data["info"])
                    else:
                        father.showErr("未知登录错误")
                        #self.disConnect()

        def window(self):
            """登录窗口GUI"""
            tk = Tk()
            tk.geometry('250x200')
            tk.title('登录界面')
            frame = Frame(tk)
            frame.pack(expand = YES, fill = BOTH)
            Label(frame, font = ("Arial, 15"),
                    text = "请输入一个用户名：", anchor = 'w').pack(padx = 10,
                            pady = 15, fill = 'x')
            entry = Entry(frame)
            entry.pack(padx = 10, fill = 'x')
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

        def network_test_first(self):
            data = {"type": "ping"}
            jData = json.dumps(data)
            self.socket.send(jData)
            recv = self.socket.recv(BUFSIZ)
            jRecv = json.loads(recv)
            return jRecv["type"] == "pong"

        class ListenThread(threading.Thread):
            """Socket监听线程，对收到的信息作出相应反馈"""
            def __init__(self, socket, father):
                threading.Thread.__init__(self)
                self.father = father
                self.socket = socket

            def run(self):
                self.alive = True
                while self.alive:
                    jData = self.socket.recv(BUFSIZ)
                    print "__receive__" + jData
                    data = json.loads(jData)
                    switch = {
                            "list": self.list,
                            "singleChat": self.chat,
                            "groupChat": self.chat,
                            "pong": self.pong
                            }
                    #try:
                    switch[data['type']](data)
                    #except Exception as e:
                        #print e
                        #print "收到未知type数据包"
                print "结束监听"

            def stop(self):
                self.alive = False
                print "关闭监听"
                stop_thread(self)

            def list(self, data):
                """刷新列表"""
                listbox = self.father.listbox
                list = ['Global', 'Broad']
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

        class Window():
            def __init__(self, father):
                self.father = father

            def refresh(self, socket):
                """点击刷新按钮"""
                data = {"type": "list"}
                jData = json.dumps(data)
                socket.send(jData)

            def send(self, socket, lb_toName, et_input):
                """点击发送按钮"""
                text = et_input.get()
                toName = lb_toName['text']
                username = self.father.father.username
                print toName
                if toName == 'Global':
                    data = {'type': 'groupChat', 'msg': text, 'from': username}
                elif toName == 'Broad':
                    pass
                else:
                    # 私聊
                    data = {'type': 'singleChat', 'msg': text,
                            'to': toName, 'from': username}
                jData = json.dumps(data)
                socket.send(jData)

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
                father.textArea = textArea
                # 右侧选择聊天对象
                Label(f, text = "双击选择发送对象:", bg = "#EEEEEE").place(x = 460,
                        y = 10, anchor = NW)
                listbox = Listbox(f, width = 13, height = 15, bg = '#FFFFFF')
                listbox.place(x = 460, y = 35, anchor = NW)
                father.listbox = listbox
                bt_refresh = Button(f, text = "刷新列表", bd = 0,
                        command = lambda : self.refresh(father.socket))
                bt_refresh.place(x = 515, y = 320, anchor = CENTER)
                # 下方内容输入
                lb_toName = Label(f, text = "Global", bg = '#FFFFFF', width = 8)
                lb_toName.place(x = 12, y = 360)
                listbox.bind('<Double-Button-1>',
                        lambda x : self.changeSendTo(listbox, lb_toName))
                self.lb_toName = lb_toName
                et_input = Entry(f, width = 37)
                et_input.place(x = 90, y = 358)
                self.et_input = et_input
                # 发送按钮
                bt_send = Button(f, text = "发  送",
                        command = lambda : self.send(father.socket,
                            lb_toName, et_input))
                bt_send.place(x = 515, y = 370, anchor = CENTER)

                tk.mainloop()

                father.listenThread.stop()
                father.socket.close()

        def __main__(self):
            # 开启监听线程
            print '开始监听'
            listenThread = self.ListenThread(self.socket, self)
            listenThread.start()
            self.listenThread = listenThread

            # 建立窗口
            window = self.Window(self)
            window.__main__()
            self.window = window

    def __main__(self):
        #pass
        login = Client.Login(self)
        login.__main__()

if __name__ == '__main__':
    HOST = 'localhost'
    PORT = 8945
    BUFSIZ = 1024
    ADDR = (HOST, PORT)

    client = Client()
    client.__main__()
