# This is a script to integrate the CRG Derby Scoreboard application to TV broadcasts via a simple
#  REST/JSON API. More information on the CRG Derby Scoreboard application here:
#  https://sourceforge.net/projects/derbyscoreboard/
#
# Installation:
#  To run the script, you will need to install Python 3, along with the Requests and Flask modules. Installation
#  instructions here:
#  * https://www.python.org/
#  * http://python-requests.org/
#  * http://flask.pocoo.org/
#
# How to run the script:
#  You can run the script either in the same computer as your scoreboard application, or a separate one. The computers
#  will need to have Layer 3 IP connectivity between each other. To run the script on a Windows PC enter the following
#  command:
#   python derby_flask.py -s <scoreboard_ip_address>
#  On a Mac:
#   python3 derby_flask.py -s <scoreboard_ip_address>
#  Substitute <scoreboard_ip_address> for the IP address of your scoreboard server. If parameter "-s" is omitted, the 
#  script will assume the scoreboard application is running on the same computer (IP: 127.0.0.1).
#
# Using the API/integrating with TV broadcast systems:
#  Once the script is running, it will present a simple REST API with two calls:
#   GET http://<script_ip_address>:5000/register
#       Use this call once to initialize connectivity to the scoreboard application and create a session key
#   GET http://<script_ip_address>:5000/status
#       Use this call to get the current gamestate in JSON form. If there are no errors, the script will return the whole
#       game state every time. See the GAMESTATE global variable below for the format of the JSON object.
#  Both of the calls work without parameters. Substitute <script_ip_address> for the IP address of the computer where
#   this script is running.
#
# Caveats:
#  * When running multiple games in a row with the same scoreboard computer, quit and restart the script after every game
#    to avoid JamScores being wrong on the first jam of the subsequent games.
#
# This file was last modified on 2018-07-16


import sys, getopt, requests
import xml.etree.ElementTree as ET
from flask import Flask, jsonify

#connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 3
REQUESTS_READ_TIMEOUT    = 3

GAMESTATE = {
        'Error'                     : None,
        'ClockPeriodRunning'        : False,
        'ClockPeriodTime'           : '30:00',
        'ClockPeriodNumber'         : 0,
        'ClockJamRunning'           : False,
        'ClockJamTime'              : '02:00',
        'ClockJamNumber'            : 0,
        'ClockLineupRunning'        : False,
        'ClockLineupTime'           : '00:00',
        'ClockLineupNumber'         : 0,
        'ClockIntermissionRunning'  : False,
        'ClockIntermissionTime'     : '15:00',
        'ClockIntermissionNumber'   : 0,
        'ClockTimeoutRunning'       : False,
        'ClockTimeoutTime'          : '01:00',
        'ClockTimeoutNumber'        : 0,
        'Team1LeadJammer'           : False,
        'Team1Score'                : 0,
        'Team1Jamscore'             : 0,
        'Team1JammerName'           : None,
        'Team1JammerNumber'         : None,
        'Team2LeadJammer'           : False,
        'Team2Score'                : 0,
        'Team2Jamscore'             : 0,
        'Team2JammerName'           : None,
        'Team2JammerNumber'         : None} 

LASTSCORE = {'1':0, '2':0}        
        
        
SESSIONKEY = 'none'

SERVER = '127.0.0.1'
        
        
def registertoscoreboard(p_server):
    r = requests.get('http://%s:8000/XmlScoreBoard/register' % p_server, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    
    if r.status_code != requests.codes.ok:
        return (None)
            
    return(r.text)    
    
    
def getgameinfo(p_server, p_sessionkey):
    r = requests.get('http://%s:8000/XmlScoreBoard/get?key=%s' % (p_server, p_sessionkey), timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
            
    if r.status_code != requests.codes.ok:
        return (None)
            
    return(r.text)
    

app = Flask(__name__)
 
@app.route("/register/")
def register():
    global SESSIONKEY
    global SERVER
    
    retvalue = registertoscoreboard(SERVER)
    root = ET.fromstring(retvalue)
    for key in root.iter('Key'):
        SESSIONKEY = key.text
    
    return (jsonify({'sessionkey':SESSIONKEY}))
   
@app.route("/status/")   
def status():
    global GAMESTATE
    global LASTSCORE
        
    if SESSIONKEY == 'none':
        return (jsonify({'Error':'Not registered'}))
        
    try:
        retvalue = getgameinfo(SERVER, SESSIONKEY) 
    except:
        print('WARNING: Unable to contact scoreboard server or no update')
        retvalue = None
    if not retvalue is None:        
        root = ET.fromstring(retvalue)
        for clock in root.iter('Clock'):
            clockid = clock.get('Id')
            for elem in clock.iter('Running'):
                GAMESTATE['Clock' + clockid + 'Running'] = (elem.text == 'true')
            for elem in clock.iter('Time'):
                seconds=int(int(elem.text)/1000)
                m, s = divmod(seconds, 60)
                GAMESTATE['Clock' + clockid + 'Time'] = '%02d:%02d' % (m,s)
            for elem in clock.iter('Number'):
                if clockid == 'Jam':
                    if int(elem.text) != GAMESTATE['Clock' + 'Jam' + 'Number']:
                        LASTSCORE['1'] = GAMESTATE['Team' + '1' + 'Score']
                        LASTSCORE['2'] = GAMESTATE['Team' + '2' + 'Score']
                        GAMESTATE['Team' + '1' + 'Jamscore'] = 0
                        GAMESTATE['Team' + '2' + 'Jamscore'] = 0
                GAMESTATE['Clock' + clockid + 'Number'] = int(elem.text)
                    
        for team in root.iter('Team'):
            teamid = team.get('Id')
            for elem in team.iter('Score'):
                GAMESTATE['Team' + teamid + 'Score'] = int(elem.text)
                GAMESTATE['Team' + teamid + 'Jamscore'] = GAMESTATE['Team' + teamid + 'Score'] - LASTSCORE[teamid]
            for elem in team.iter('LeadJammer'):
                GAMESTATE['Team' + teamid + 'LeadJammer'] = (elem.text == 'Lead')
            for position in team.iter('Position'):
                positionid = position.get('Id')
                if positionid == 'Jammer':
                    for jname in position.iter('Name'):
                        GAMESTATE['Team' + teamid + 'JammerName'] = jname.text
                    for jnumber in position.iter('Number'):
                        GAMESTATE['Team' + teamid + 'JammerNumber'] = jnumber.text
                    break
        
    return (jsonify(GAMESTATE))   


def main(argv):
    global SERVER
    
    #get command line arguments
    try:
        opts, args = getopt.getopt(argv, 's:')
    except getopt.GetoptError:
        sys.exit(2)
        
    for opt, arg in opts:
        if opt == '-s':
            SERVER  = arg
    
    print('*** Using source server: %s' % SERVER)

    app.run(host='0.0.0.0', threaded=True)
    
 
if __name__ == "__main__":
    main(sys.argv[1:])