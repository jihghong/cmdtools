from robot import Robot
from scripting import command

robots = [Robot('robot1', 3), Robot('robot2', 1, derived=True), Robot('robot3', 2)]

@command
def shutdown():
    print('shutdown engine')
