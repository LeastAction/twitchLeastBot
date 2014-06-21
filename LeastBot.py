#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      MTJacobson
#
# Created:     01/03/2014
# Copyright:   (c) MTJacobson 2014
# Licence:     <your licence
#-------------------------------------------------------------------------------

import time
import socket #imports module allowing connection to IRC
import threading #imports module allowing timing functions
import random
import sys
sys.path.append('D:\Git\lolLeastBot')
import lol_api
from chatterbotapi import ChatterBotFactory, ChatterBotType
from colorama import init, Fore
init()

FACTORY = ChatterBotFactory()
bot1 = FACTORY.create(ChatterBotType.JABBERWACKY)
bot1session = bot1.create_session()

#sets variables for connection to twitch chat
#channel = '#leastaction'
server = 'irc.twitch.tv'

#LeastBot
bot_owner = 'LeastBot'
nick = 'LeastBot'
password = open("D:\\Git\\twitchLeastBot\\oauth.txt", "r").readline()

#LeastBot Quality Assurance
BOT_OWNER_2 = 'lbqas'
NICK_2 = 'lbqas'
PASSWORD_2 =open("D:\\Git\\twitchLeastBot\\oauth_2.txt", "r").readline()

R = lol_api.RiotAPI()
##queue = 0
PREV_MSG_TIME = time.time()
PREV_MSG_SENT = ""

##def queuetimer(): #function for resetting the queue every 30 seconds
##    global queue
##    if queue: print 'queue reset: {0}'.format(queue)
##    queue = 0
##    threading.Timer(30,queuetimer).start()

###Monkey Patch for timestamps
##old_f = sys.stdout
##class F:
##    def write(self, x):
##        old_f.write('[{0}] '.format(time.strftime("%H:%M:%S")) + x)
##sys.stdout = F()


class Connection():
    def __init__(self, channel, nick, owner, password, server = 'irc.twitch.tv', debug=1):
        self.channel = channel
        self.nick = nick
        self.owner = owner
        self.password = password
        self.server = server
        self.debug = debug

        self.irc = None
        self.command_interpreter = None
        self.outbound_connection = None
        self.message_queue = {}

    def set_interpreter(self, command_interpreter):
        self.command_interpreter = command_interpreter

    def set_outbound_connection(self, outbound_connection):
        self.outbound_connection = outbound_connection

    def send_queue(self):
        """Loops through previously sent messages, resends if it hasn't appeared in 3 seconds since initially sending.
            Only attempts to resend once.
        """
        #if self.debug: print self.message_queue
        for curr_time in self.message_queue.keys():
            if time.time() - curr_time > 3:
                send_message(self.outbound_connection, self.message_queue[curr_time],self.debug)
                del self.message_queue[curr_time]


    def start(self):
        self.irc = socket.socket()
        self.irc.connect((self.server, 6667)) #connects to the server
        self.irc.settimeout(2) # set non-blocking mode timeout

        if not self.outbound_connection: self.outbound_connection = self # if no outbound socket is specified set own socket as outbound

        #sends variables for connection to twitch chat
        self.irc.send('PASS ' + self.password + '\r\n')
        self.irc.send('USER ' + self.nick + ' 0 * :' + self.owner + '\r\n')
        self.irc.send('NICK ' + self.nick + '\r\n')
        self.irc.send('JOIN ' + self.channel + '\r\n')

        read_buffer = ""
        bool_exit = False
        bool_reconnect = False

        while (1):
            if bool_exit == True:
                self.irc.close()
                break
            ##Receiving data from IRC and spitting it into manageable lines.
            try:
                read_buffer=read_buffer+self.irc.recv(1024)
            except socket.timeout:
                self.send_queue()
                time.sleep(1)
                continue

            temp=str.split(read_buffer, "\n")
            read_buffer=temp.pop( )

            if not temp: #connection shut down from server side
                bool_exit = True
                bool_reconnect = True

            for line in temp:
                if 'twitch.tv PRIVMSG ' + self.channel in line:
                    if self.debug: print Fore.GREEN + line
                    message = line.split('twitch.tv PRIVMSG ' + self.channel + ' :')[1]
                    ID = line.split("!",1)[0].lstrip(":")

                    if ID == 'leastbot':
                        for key in self.message_queue.keys():
                            if self.message_queue[key].rstrip('\r\n') == message.rstrip('\r\n'):
                                del self.message_queue[key]
                                break


                    if self.command_interpreter and ID != 'leastbot':
                        reply = self.command_interpreter._interpret(message,ID)
                        if not reply: reply = ""
                    else:
                        reply = ''

                    if reply == "EXIT":
                        bool_exit = True
                        reply = ''
                    elif reply[0:6] == 'ERROR:':
                        if self.debug: print Fore.RED + reply
                        reply = ''
                    if reply:
                        send_message(self.outbound_connection, reply, self.debug)
                        self.message_queue[time.time()] = reply

                elif ':jtv MODE '+ self.channel +  ' +o' in line and self.command_interpreter:
                    mod = line.split(':jtv MODE '+ self.channel +  ' +o ')[1]
                    if mod not in self.command_interpreter.moderators: self.command_interpreter.moderators.append(mod)

                elif ':jtv MODE '+ self.channel +  ' -o' in line and self.command_interpreter:
                    mod = line.split(':jtv MODE '+ self.channel +  ' -o ')[1]
                    if mod in self.command_interpreter.moderators: self.command_interpreter.moderators.remove(mod)

                ##IRC checks connectiond with ping. Every ping has to be replied to with a Pong.
                elif ('PING :tmi.twitch.tv' in line):
                    if self.debug: print Fore.RED + line
                    reply = line
                    reply = reply.replace('PING', 'PONG')
                    self.irc.send(reply)
                    if self.debug: print Fore.RED + reply
                else:
                    if self.debug: print Fore.WHITE + line

            self.send_queue()

        if bool_reconnect:
            self.start()

def send_message(connection, msg, debug):
    global PREV_MSG_TIME
    while (1):
        if time.time() - PREV_MSG_TIME > 2:
            if debug: print Fore.MAGENTA + "PRIVMSG "+ connection.channel + " :" + msg +"\r\n"
            connection.irc.send("PRIVMSG "+ connection.channel + " :" + msg +"\r\n")
            PREV_MSG_TIME = time.time()
            break
        else:
            time.sleep(0.5)

##    counter = 0
##    while (1):
##        print "prev: {}".format(PREV_MSG_SENT)
##        print "curr: {}".format(msg)
##        if counter == 15:
##            print "SEND AGAIN"
##            #send_message(irc,msg)
##        if PREV_MSG_SENT.rstrip('\r\n') == msg.rstrip('\r\n'):
##            PREV_MSG_SENT = ""
##            break
##        else:
##            counter += 1
##            time.sleep(0.2)

##def send_message(irc, msg):
##    global queue
##    queue += 1
##    if queue < 20: #ensures does not send >20 msgs per 30 seconds.
##        print Fore.MAGENTA + "PRIVMSG "+ channel + " :" + msg +"\r\n"
##        irc.send("PRIVMSG "+ channel + " :" + msg +"\r\n")
##    else:
##        print  Fore.MAGENTA + 'Message deleted'



class CommandInterpreter():

    def __init__(self, generic_commands_path=None):
        self.administrators = ['leastaction']
        self.moderators = []
        self._generic_commands_path = generic_commands_path
        self._reload_generic_commands()
        self._points_path = "D:\\Git\\twitchLeastBot\\dice_points.txt"
        self._reload_points()
        self._available_commands = [method for method in dir(self) if callable(getattr(self, method)) and method[0] != '_']
        self._admin_only = ['close','editpoints']
        self._mod_only = ['create']

    @staticmethod
    def _load_text(path):
        try:
            text_file = open(path, "r")
        except IOError:
            print Fore.RED + "ERROR: Could not open {0}".format(path)
            return {}
        lines = text_file.read().split('\n')

        text_dict = {}
        for line in lines:
            a = line.split("|")
            text_dict[a[0].lstrip('\r\n')] = a[1:]
        return text_dict

    @staticmethod
    def _represents_int(s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def _reload_generic_commands(self):
        self._generic_commands = CommandInterpreter._load_text(self._generic_commands_path)
        self._generic_commands.pop('\xef\xbb\xbf',0)

    def _reload_points(self):
        self._points = CommandInterpreter._load_text(self._points_path)

    def _save_points(self):
        write_data = ''
        for user in self._points.keys():
            write_data = write_data + '\n' + user + '|' + self._points[user][0]

        with open(self._points_path, 'w') as my_file:
            my_file.writelines(write_data.lstrip('\n'))

    def _interpret(self, message, ID):
        self._reload_generic_commands()
        self._reload_points()
        args = [x.rstrip('\r\n') for x in message.split(" ")]
        command_name = args[0]
        method_args = args[1:]

        if command_name[0:1] =='!':
            if command_name[1:] in self._available_commands:

                if command_name[1:] in self._admin_only:
                    if ID.lower() in self.administrators:
                        command = getattr(self,command_name[1:])
                    else:
                        return 'ERROR: Insufficient priveleges'

                elif command_name[1:] in self._mod_only:
                    if ID.lower() in self.moderators:
                        command = getattr(self,command_name[1:])
                    else:
                        return 'ERROR: Insufficient priveleges'

                else:
                    command = getattr(self,command_name[1:])

            elif command_name[1:] in self._generic_commands.keys():
                command = self._simple_message
                method_args = self._generic_commands[command_name[1:]] + method_args
            else:
                return 'ERROR: Command not recognized'

            return command(method_args,ID)

        else:
            return ''


    def _simple_message(self, args, ID):
        reply = args[1]
        string_insert = ""
        if args[0] == 'ID': string_insert = ID
        if args[0] == 'NAME': string_insert = " ".join(args[2:])
        if args[0]: reply = reply.format(string_insert)
        return reply

    def close(self,args, ID):
        """!close"""
        return 'EXIT'

    def chat(self, args, ID):
        """!chat [message]"""
        reply = ''
        if args: reply = bot1session.think(" ".join(args))
        return reply

    def rank(self, args, ID):
        """!rank [username]"""
        user = "".join(args)
        if user:
            try:
                reply = " ".join(args) + " is: " + R.get_stuff(user).replace('\n',' | ')
            except ValueError:
                reply = 'User Not Found.'
            return reply
        else:
            return ''

    def create(self, args, ID):
        """!create [command] [reply]"""
        if len(args) == 2:
            if args[0] in self._generic_commands.keys() + self._available_commands:
                return 'Command Already Exists.'
            else:
                write_this = "\n"+args[0]+"||"+" ".join(args[1:])
                with open(self._generic_commands_path, "a") as my_file:
                    my_file.write(write_this)
                return 'Command created.'

    def commands(self, args, ID):
        """!commands"""
        reply = 'Commands are: '
        for com in self._available_commands:
            if com not in (self._admin_only+self._mod_only):
                reply = reply + getattr(self,com).__doc__ + ', '
        for com in self._generic_commands.keys():
            if self._generic_commands[com][0] in ['ID','']:
                reply = reply + '!'+ com + ', '
            if self._generic_commands[com][0] in ['NAME']:
                reply = reply + '!'+ com + ' [' + self._generic_commands[com][0].lower() + '], '

        return reply.rstrip(', ')

    def points(self, args, ID):
        """!points"""
        user = ID
        if args and ID.lower() in (self.administrators + self.moderators):
            user = args[0]

        try:
            p = int(self._points[user.lower()][0])
        except KeyError:
            self._points[user.lower()] = ['50']
            p = 50

        self._save_points()
        reply = '{0} has {1} points.'.format(user,p)
        return reply

    def editpoints(self, args, ID):
        """!editpoints [username] [points]"""
        if len(args) == 2:
            self._points[args[0].lower()] = [str(args[1])]
            self._save_points()
            return "{0}'s points updated".format(args[0])
        else:
            return ''

    def dice(self, args, ID):
        """!dice [amount to bet] [dice roll guess 1-6]"""
        if not args: return 'Use command !dice [amount to bet] [dice roll guess 1-6]'

        if CommandInterpreter._represents_int(args[0]) and CommandInterpreter._represents_int(args[1]):
            win_mult = 5
            bet = int(args[0])
            guess = int(args[1])
            if guess not in [1,2,3,4,5,6]:
                reply = 'Not a valid guess.'
                return reply

            if bet <= 0:
                reply = 'Not a valid bet.'
                return reply

            dice_roll = random.randint(1,6)
            p = int(self._points[ID.lower()][0])
            if bet > p:
                return 'Not enough points for that bet!'
            if dice_roll == guess:
                self.editpoints([ID,p+win_mult*bet],'')
                return 'The dice rolls... {0}. You guessed correctly! You win {1} points!'.format(dice_roll, win_mult*bet)
            else:
                if p - bet == 0:
                    self.editpoints([ID,50],'')
                    return 'The dice rolls... {0}. You lost! You have no more points! 50 have been gifted to you by the wise and generous LeastBot'.format(dice_roll)
                else:
                    self.editpoints([ID,p-bet],'')
                    return 'The dice rolls... {0}. You lost! Better luck next time!'.format(dice_roll)

    def mods(self, args, ID):
        """!mods"""
        return 'mods: ' + ", ".join(self.moderators)

    def admins(self, args, ID):
        """!admins"""
        return 'admins: ' + ", ".join(self.administrators)



if __name__ == '__main__':
    ch = raw_input()
    #connect_secondary_bot(raw_input())
##    t1 = threading.Thread(target=connect_secondary_bot)
##    t1.start()
##    connect(ch)

    lb = Connection(channel = ch, nick = nick, owner = bot_owner, password = password, debug = 0)

    t1 = threading.Thread(target=lb.start)
    t1.start()

    time.sleep(3)

    lbqas = Connection(channel = ch, nick = NICK_2, owner = BOT_OWNER_2, password = PASSWORD_2)
    lbqas.set_interpreter(CommandInterpreter("D:\\Git\\twitchLeastBot\\" + lbqas.channel[1:] + "_commands.txt"))
    lbqas.set_outbound_connection(lb)

    lbqas.start()


