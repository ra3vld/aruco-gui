#!/usr/bin/env python 
# import the Flask class from the flask module

# ROS related imports
import rospy

from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped

from multiprocessing import Process, Queue
from aruco_detector.srv import *
#  flask related
from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit

# create the application object
q_in = Queue()
q_out = Queue()
HOST_IP = "0.0.0.0"
PORT = "5000"

keys = ["Scene_statuses", "calibation_status", "camera_position"]

app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet")


small_robot_pose = {"x": "", "y":"", "z": ""}
enemy1_robot_pose = {"x": "", "y":"", "z": ""}
enemy2_robot_pose = {"x": "", "y":"", "z": ""}
# socketio = SocketIO(app)
# use decorators to link the function to a url

class Gui(Process):
    def __init__(self, q_in, q_out, socketio):
        Process.__init__(self)
        self.big_robot_pose = {"x": "", "y":"", "z": ""}
        self.small_robot_pose = {"x": "", "y":"", "z": ""}
        self.enemy1_robot_pose = {"x": "", "y":"", "z": ""}
        self.enemy2_robot_pose = {"x": "", "y":"", "z": ""}
        self.info_str = ""
        self.q_in = q_in
        self.q_out = q_out
        self.socketio = socketio
        self.socketio.start_background_task(target = self.queue_read)

        @app.route('/t')
        def home():
            return "Hello, World!"  # return a string

        @app.route('/')
        def welcome():        
            return render_template('welcome.html')  # render a template


        @self.socketio.on("periodicRequest")
        def _on_periodicRequest(mes):
            self.socketio.emit ("big_pose", self.big_robot_pose)
            self.socketio.emit ("small_pose", self.small_robot_pose)
            self.socketio.emit ("enemy2_pose", self.enemy2_robot_pose)
            self.socketio.emit ("enemy1_pose", self.enemy1_robot_pose)
            for key in self.info_str:
                self.socketio.emit(str(key), self.info_str[key])

        @self.socketio.on('my_event')
        def on_connect(message):
            print (message)

        @self.socketio.on('message')
        def handle_message(message):
            cmd = message['id']
            res = ""
            if cmd == "setGreen":
                res = self.call_set_side("g")
            if cmd == "setOrange":
                res = self.call_set_side("o")
            if cmd == "recalibrate":
                res = self.call_recalib(message['data'])
            print('received message: ' + message)
            emit ("message_reply", str(res))
            es = {"x": "", "y":"", "z": ""}
            # socketio.emit ("big_pose", es, namespace='/test' )
            # socketio.emit ("big_pose", es)


        @self.socketio.on("connect")
        def handle_my_event():
            print('connect')

        @self.socketio.on("button")
        def handle_button(data):
            print (data)

    def run(self):
        socketio.run(app, host=HOST_IP) #,debug=True)

    def queue_read(self):
        while True:
            
            if self.q_in.empty():
                self.socketio.sleep(0.01)
            else:
                message = self.q_in.get()
                
                if message["topic"] == "big_robot_pose":
                    self.big_robot_pose = message["pose"]

                if message["topic"] == "small_robot_pose":
                    self.small_robot_pose = message["pose"]
                    

                if message["topic"] == "enemy1_robot_pose":
                    self.enemy1_robot_pose = message["pose"]
                    

                if message["topic"] == "enemy2_robot_pose":
                    self.enemy2_robot_pose = message["pose"]

                if message["topic"] == "info_str":
                    self.info_str = message["msg"]


                    # print ("read message: ", message)


    

    def call_recalib(self, is_manual):
        rospy.wait_for_service('ArucoRecalibrate', 3)
        resp1 = ""
        try:
            recal = rospy.ServiceProxy('ArucoRecalibrate', ArucoRecalibrate)
            resp1 = recal(is_manual)
        except rospy.ServiceException as e:
            print ("Service call failed: %s"%e)
        return resp1



    def call_set_side(self, color):
        rospy.wait_for_service('SetSide', 3)
        resp1 = ""
        try:
            setSide = rospy.ServiceProxy('SetSide', SetSide)
            resp1 = setSide(color)
        except rospy.ServiceException as e:
            print ("Service call failed: %s"%e)
        return resp1




def gui(q_in, q_out):
    g = Gui(q_in, q_out, socketio)
    g.start()
    



def poseStamed_to_dict(posestamped):
    
    res = {"x": "", "y":"", "z": ""}
    res["x"] = str(posestamped.pose.position.x)
    res["y"] = str(posestamped.pose.position.y)
    res["z"] = str(posestamped.pose.position.z)

    return res


def callback_big(data):
    big_robot_pose = poseStamed_to_dict(data)
    q_in.put({"topic":"big_robot_pose", "pose":big_robot_pose})

def callback_small(data):
    small_robot_pose = poseStamed_to_dict(data)
    q_in.put({"topic":"small_robot_pose", "pose":small_robot_pose})

def callback_enemy1(data):
    enemy1_robot_pose = poseStamed_to_dict(data)
    q_in.put({"topic":"enemy1_robot_pose", "pose":enemy1_robot_pose})

def callback_enemy2(data):
    enemy2_robot_pose = poseStamed_to_dict(data)
    q_in.put({"topic":"enemy2_robot_pose", "pose":enemy2_robot_pose})



def callback(msg):
    info_string =msg.data
    resul_data= {}
    for key in keys:
        value = find_key_value(info_string, key)
        resul_data.update({key:value})
    q_in.put({"topic":"info_str", "msg":resul_data})


def find_key_value(info_string, key):
    index = info_string.find(key)
    index_start = info_string.find(":", index)
    index_start += 1
    stop_index = info_string.find("}", index)
    if (index_start == -1) or (stop_index == -1):
        return ("cannot parse string: " + str(info_string))
    return info_string[index_start:stop_index]


# start the server with the 'run()' method
if __name__ == '__main__':
    # app.run(host='0.0.0.0') #,debug=True)
    # p = Process(target = gui, args =(q_in))
    
    g = Gui(q_in, q_out, socketio)
    g.start()
    
    # pub = rospy.Publisher('chatter', String, queue_size=10)
    rospy.init_node('talker', anonymous=True, disable_signals=True)
    rate = rospy.Rate(10) # 10hz
    rospy.loginfo("running on " + HOST_IP + ":"+PORT)
    
    rospy.Subscriber("/big_robot/aruco", PoseStamped, callback_big)
    rospy.Subscriber("/small_robot/aruco", PoseStamped, callback_small)
    rospy.Subscriber("/enemy_robot1/aruco", PoseStamped, callback_enemy1)
    rospy.Subscriber("/enemy_robot2/aruco", PoseStamped, callback_enemy2)
    subscriber = rospy.Subscriber("/aruco/info_to_gui", String, callback)

    
    while not rospy.is_shutdown():
        # hello_str = "hello world %s" % rospy.get_time()
        # # rospy.loginfo(hello_str)

        # pub.publish(hello_str)
        rate.sleep()

