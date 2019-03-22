#!/usr/bin/env python3
import paramiko
import sys
from os.path import expanduser 
from os.path import exists
import time

from user_definition import *
from addressbook import alertdata
from create_efs import fill_data_2016


DIR_NAME = b'projectx'
STR_DIR_NAME = 'projectx'


# 1. SSH to box:
print( "Connecting to box" )
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ec2_address, username = user, key_filename = expanduser("~") + key_file)

# 2. Check whether the EC2 has git installed. Otherwise install git.
stdin, stdout, stderr = ssh.exec_command("git --version")

if(b"command not found" in stderr.read() ):
    print ("Installing Git")
    stdin, stdout, stderr = ssh.exec_command("sudo yum -y install git")
    
    while True:
        print("...")
        time.sleep(10)
        stdin, stdout, stderr = ssh.exec_command("git --version")
      
        if(b"command not found" in stderr.read()):
            print("...")
            time.sleep(10)
        else:
            print("Finished installing Git")
            break

#TODO DMW: Expire after time out
# 3 - 5. Check for lock file:
_, stdout, _ = ssh.exec_command("ls")
files = stdout.read()
file_names = files.split(b'\n')

print('Got the file names')

# TODO: enter again when deploy is stable
# while True:
#     if b'flock' not in file_names:
#         break
#     print("...")
#     time.sleep(10)

#TODO DMW : Expire after time out
print("No processes running. Updating files.")

ssh.exec_command("mkdir flock") # Creating dummy lock directory when we get past the loop

# 6. Git pull from bitbucket

stdin, stdout, stderr = ssh.exec_command("sudo rm -rf " + STR_DIR_NAME + ";" + " git clone git@github.com:smelancon/projectx.git ")
print("Pull from Git successfully")

if DIR_NAME in files:
    # Only do the above on the remote machine
    # 7. Remove and reset CRON file 
    ssh.exec_command("crontab -r")
    ### Kill all lockfiles
    ssh.exec_command("rm -rf /home/ec2-user/projectx/lockfiles/*.lock")
    ssh.exec_command("pkill -f Chrome; pkill -f chromedriver")
    for alert in alertdata.keys():
        # add the cronjob and log to /ver/log/syslog
        
        if alertdata[alert]['crontime'] == 1:
            newcronline = "* * * * * flock -n /home/ec2-user/projectx/lockfiles/%s.lock -c \'\"/home/ec2-user/projectx/code/bosun.py %s\"\' >> /home/ec2-user/logs/%s.log" % (alert, alert, alert)
        else:
            newcronline = "*/%s * * * * flock -n /home/ec2-user/projectx/lockfiles/%s.lock -c \'\"/home/ec2-user/projectx/code/bosun.py %s\"\' >> /home/ec2-user/logs/%s.log" % (alertdata[alert]['crontime'], alert, alert, alert)
        
        ssh.exec_command("crontab -l | { cat; echo \"" + newcronline + "\"; } | crontab -")
    print("Crontab updated")

# 8. Remove dummy lock directory to finish:
ssh.exec_command("rm -r flock")
# This updates the 2016 data
ssh.exec_command("cd ~/" + STR_DIR_NAME + "/code; python3 -c 'from create_efs import *; runOnDeploy()'")
print("Script fully executed ... exiting")

# 9. Close your connection.
ssh.close()

## EOF ##

