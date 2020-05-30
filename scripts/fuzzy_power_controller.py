#!/usr/bin/env python
from __future__ import division
from time import sleep
import rospy
from std_msgs.msg import Int16MultiArray
from fuzzy_functions import FuzzyTrapezoid, FuzzyTriangle

rospy.init_node('fuzzy_power_controller', anonymous=True)
pub = rospy.Publisher('/zumo/raw_power', Int16MultiArray, queue_size = 10)

#Size of target
targetUndersizeBigFn = FuzzyTrapezoid(0, 0, 60, 70)
targetUndersizeSmallFn = FuzzyTriangle(65, 80, 90)
targetIdealSizeFn = FuzzyTriangle(85, 90, 100)
targetOversizeSmallFn = FuzzyTriangle(90, 105, 120)
targetOversizeBigFn = FuzzyTrapezoid(115, 140, 500, 500)

#Rate of change in relation to target between readings
deceleratingBigFn = FuzzyTrapezoid(-20, -20, -10, -5)
deceleratingSmallFn = FuzzyTriangle(-6, -3, 0)
speedConstantFn = FuzzyTriangle(-5, 0, 5)
acceleratingSmallFn = FuzzyTriangle(0, 3, 6)
acceleratingBigFn = FuzzyTrapezoid(2.5, 10, 20, 20)

BIG_SPEED_CHANGE = 40
SMALL_SPEED_CHANGE = 20
NO_SPEED_CHANGE = 0
POWER_LIMIT = 120

power = 0
previousBallDimension = 0

def publishData(power, ballPosition, ballDimension):
	data = Int16MultiArray()
	data.data = [ballPosition, ballDimension, power]
	pub.publish(data)

def getPower(power, ballDimension, deltaV):
	closeBig = targetOversizeBigFn.getMembership(ballDimension)
	closeSmall = targetOversizeSmallFn.getMembership(ballDimension)
	atTarget = targetIdealSizeFn.getMembership(ballDimension)
	farSmall = targetUndersizeSmallFn.getMembership(ballDimension)
	farBig = targetUndersizeBigFn.getMembership(ballDimension)

	deceleratingBig = deceleratingBigFn.getMembership(deltaV)
	deceleratingSmall = deceleratingSmallFn.getMembership(deltaV)
	speedConstant = speedConstantFn.getMembership(deltaV)
	acceleratingSmall = acceleratingSmallFn.getMembership(deltaV)
	acceleratingBig = acceleratingBigFn.getMembership(deltaV)

	#print "closeBig:   ", closeBig
	#print "closeSmall: ", closeSmall
	#print "atTarget:   ", atTarget
	#print "farSmall:   ", farSmall
	#print "farBig:     ", farBig
	#print ""
	#print "deceleratingBig:   ", expandingBig
	#print "deceleratingSmall: ", expandingSmall
	#print "speedConstant:  ", constantSpeed
	#print "acceleratingSmall:   ", closingSmall
	#print "acceleratingBig:     ", closingBig

	memberships = []
	if closeBig > 0:		
		if deceleratingBig > 0: memberships.append([(closeBig+deceleratingBig)/2, -SMALL_SPEED_CHANGE])
		if deceleratingSmall > 0: memberships.append([(closeBig+deceleratingSmall)/2, -BIG_SPEED_CHANGE])
		if speedConstant > 0: memberships.append([(closeBig+speedConstant)/2, -BIG_SPEED_CHANGE])
		if acceleratingSmall > 0: memberships.append([(closeBig+acceleratingSmall)/2, -BIG_SPEED_CHANGE])
		if acceleratingBig > 0: memberships.append([(closeBig+acceleratingBig)/2, -BIG_SPEED_CHANGE])
		
	if (closeSmall > 0):
		if deceleratingBig > 0: memberships.append([(closeSmall+deceleratingBig)/2, BIG_SPEED_CHANGE])
		if deceleratingSmall > 0: memberships.append([(closeSmall+deceleratingSmall)/2, NO_SPEED_CHANGE])
		if speedConstant > 0: memberships.append([(closeSmall+speedConstant)/2, -SMALL_SPEED_CHANGE])
		if acceleratingSmall > 0: memberships.append([(closeSmall+acceleratingSmall)/2, -SMALL_SPEED_CHANGE])
		if acceleratingBig > 0: memberships.append([(closeSmall+acceleratingBig)/2, -BIG_SPEED_CHANGE])

	if (atTarget > 0): 
		if deceleratingBig > 0: memberships.append([(atTarget+deceleratingBig)/2, BIG_SPEED_CHANGE])
		if deceleratingSmall > 0: memberships.append([(atTarget+deceleratingSmall)/2, SMALL_SPEED_CHANGE])
		if speedConstant > 0: memberships.append([(atTarget+speedConstant)/2, NO_SPEED_CHANGE])
		if acceleratingSmall > 0: memberships.append([(atTarget+acceleratingSmall)/2, -SMALL_SPEED_CHANGE])
		if acceleratingBig > 0: memberships.append([(atTarget+acceleratingBig)/2, -BIG_SPEED_CHANGE])

	if (farSmall > 0): 
		if deceleratingBig > 0: memberships.append([(farSmall+deceleratingBig)/2, BIG_SPEED_CHANGE])
		if deceleratingSmall > 0: memberships.append([(farSmall+deceleratingSmall)/2, SMALL_SPEED_CHANGE])
		if speedConstant > 0: memberships.append([(farSmall+speedConstant)/2, SMALL_SPEED_CHANGE])
		if acceleratingSmall > 0: memberships.append([(farSmall+acceleratingSmall)/2, NO_SPEED_CHANGE])
		if acceleratingBig > 0: memberships.append([(farSmall+acceleratingBig)/2, -SMALL_SPEED_CHANGE])

	if (farBig > 0): 
		if deceleratingBig > 0: memberships.append([(farBig+deceleratingBig)/2, BIG_SPEED_CHANGE])
		if deceleratingSmall > 0: memberships.append([(farBig+deceleratingSmall)/2, BIG_SPEED_CHANGE])
		if speedConstant > 0: memberships.append([(farBig+speedConstant)/2, BIG_SPEED_CHANGE])
		if acceleratingSmall > 0: memberships.append([(farBig+acceleratingSmall)/2, BIG_SPEED_CHANGE])
		if acceleratingBig > 0: memberships.append([(farBig+acceleratingBig)/2, SMALL_SPEED_CHANGE])

	weightedAreaSum = 0
	areaSum = 0

	for m in memberships:
		m[0] = 40 * m[0] * (1 - (m[0]/2))
		weightedAreaSum += m[0] * m[1]
		areaSum += m[0]

	if (areaSum != 0):
		powerChange = weightedAreaSum / areaSum
		power += powerChange
		

	if (power > POWER_LIMIT):
		power = POWER_LIMIT
	if (power < -POWER_LIMIT):
		power = -POWER_LIMIT	
	return power


def callback(data):
	global power
	global previousBallDimension
	ballPosition = data.data[0]
	ballDimension = data.data[1]
	#Change in velocity relative to target
	deltaV = ballDimension - previousBallDimension

	power = getPower(power, ballDimension, deltaV)

	#print "Ball position: ", ballPosition, " Ball dimension: ", ballDimension, "Power: ", power
	publishData(power)
	previousBallDimension = ballDimension

def listener():
	rospy.Subscriber('/zumo/ball_pos', Int16MultiArray, callback)
	rospy.spin()

if __name__ == '__main__':
	listener()